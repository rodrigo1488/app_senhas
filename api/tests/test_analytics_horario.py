import unittest
from datetime import date, datetime, timedelta

from backend import create_app
from backend.extensions import db
from backend.models import AlertaLog, Senha, Setor
from backend.services.alerta_notify_service import salvar_config_alerta
from backend.services.analytics_service import (
    _alertas_horario,
    _eh_feriado_nacional,
    _faixa_expediente,
    montar_analytics,
)
from backend.services.usuario_service import criar_ou_atualizar_admin
from backend.timezone import agora_sp


class AnalyticsHorarioTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = create_app(
            {
                "TESTING": True,
                "SECRET_KEY": "test-secret",
                "SQLALCHEMY_DATABASE_URI": "sqlite://",
            }
        )

    def setUp(self):
        with self.app.app_context():
            db.drop_all()
            db.create_all()
            criar_ou_atualizar_admin("admin@test.local", "admin123")
            caixa = Setor(nome="Caixa", senha_setor="CAIXA")
            db.session.add(caixa)
            db.session.commit()
            self.caixa_id = caixa.id

    def test_grade_vai_ate_21h_e_fluxo_omite_madrugada(self):
        with self.app.app_context():
            ontem = (agora_sp() - timedelta(days=1)).replace(
                hour=9, minute=15, second=0, microsecond=0
            )
            db.session.add(
                Senha(
                    senha="N001",
                    tipo="normal",
                    setor_id=self.caixa_id,
                    status="C",
                    token_unico="horario-1",
                    data_hora=ontem,
                    chamada_em=ontem.replace(hour=11, minute=5),
                )
            )
            db.session.commit()

            dia = ontem.date().isoformat()
            dados = montar_analytics(from_s=dia, to_s=dia)

            self.assertEqual(7, dados["heatmap"]["hora_inicio"])
            self.assertEqual(21, dados["heatmap"]["hora_fim"])
            self.assertEqual(20, dados["heatmap"]["hora_alerta_ate"])

            labels = [row["label"] for row in dados["fluxo_por_setor"]["series"]]
            self.assertEqual([f"{hora:02d}h" for hora in range(7, 22)], labels)
            self.assertEqual(1, dados["por_hora"][9]["retiradas"])
            self.assertEqual(0, dados["por_hora"][9]["chamadas"])
            self.assertEqual(1, dados["por_hora"][11]["chamadas"])

            tipos = {a["tipo"] for a in dados["alertas"]}
            self.assertIn("sem_retirada", tipos)
            self.assertNotIn("sem_chamada", tipos)

    def test_faixa_domingo_e_feriado(self):
        with self.app.app_context():
            domingo = date(2026, 11, 8)  # domingo
            natal = date(2026, 12, 25)
            util = date(2026, 11, 9)  # segunda
            self.assertEqual((8, 12, 11), _faixa_expediente(domingo))
            self.assertEqual((8, 12, 11), _faixa_expediente(natal))
            self.assertTrue(_eh_feriado_nacional(natal))
            self.assertEqual((7, 21, 20), _faixa_expediente(util))

    def test_config_monitoramento_altera_faixa_e_dias(self):
        with self.app.app_context():
            salvar_config_alerta(
                {
                    "hora_inicio": 9,
                    "hora_fim": 18,
                    "dias": [0, 1, 2, 3, 4],  # seg–sex
                    "especial_ativo": True,
                    "especial_hora_inicio": 10,
                    "especial_hora_fim": 13,
                    "especial_dias": [5],  # sábado
                    "especial_feriados": False,
                }
            )
            segunda = date(2026, 11, 9)
            sabado = date(2026, 11, 14)
            domingo = date(2026, 11, 8)
            natal = date(2026, 12, 25)
            self.assertEqual((9, 18, 17), _faixa_expediente(segunda))
            self.assertEqual((10, 13, 12), _faixa_expediente(sabado))
            self.assertIsNone(_faixa_expediente(domingo))
            # Natal é sexta, mas feriados especiais desligados → usa faixa do dia útil
            self.assertEqual((9, 18, 17), _faixa_expediente(natal))

            agora = datetime(2026, 11, 8, 11, 0)
            alertas, _ = _alertas_horario(
                [], datetime(2026, 11, 8), datetime(2026, 11, 9), agora
            )
            self.assertEqual([], alertas)

    def test_lacunas_retirada_e_sem_alerta_horario_chamada(self):
        with self.app.app_context():
            agora = datetime(2026, 11, 9, 15, 30)
            inicio = datetime(2026, 11, 9)
            fim = datetime(2026, 11, 10)
            senhas = [
                Senha(
                    senha="N001",
                    tipo="normal",
                    setor_id=1,
                    status="C",
                    data_hora=datetime(2026, 11, 9, 9, 5),
                    chamada_em=datetime(2026, 11, 9, 9, 20),
                ),
                Senha(
                    senha="N002",
                    tipo="normal",
                    setor_id=1,
                    status="A",
                    data_hora=datetime(2026, 11, 9, 10, 10),
                ),
            ]

            caixa = Setor(id=1, nome="Caixa", senha_setor="CAIXA")
            farm = Setor(id=2, nome="Farmácia", senha_setor="FARMA")
            alertas_lista, eventos = _alertas_horario(
                senhas, inicio, fim, agora, {1: caixa, 2: farm}
            )
            alertas = {(a["tipo"], a.get("setor_id")): a for a in alertas_lista}

            retirada = alertas[("sem_retirada", None)]["mensagem"]
            self.assertIn("07h–08h", retirada)
            self.assertIn("11h–14h", retirada)
            self.assertNotIn("09h", retirada)
            self.assertNotIn("10h", retirada)
            self.assertEqual("warning", alertas[("sem_retirada", None)]["severidade"])

            self.assertNotIn(("sem_chamada", 1), alertas)
            self.assertNotIn(("sem_chamada", 2), alertas)
            self.assertFalse(any(e["tipo"] == "sem_chamada" for e in eventos))
            self.assertFalse(
                any("sem chamada de senha" in (e.get("mensagem") or "") for e in eventos)
            )

            recente = alertas[("sem_chamada_recente", 1)]
            self.assertEqual("critical", recente["severidade"])
            self.assertIn("Caixa:", recente["mensagem"])
            self.assertIn("09:20", recente["mensagem"])
            self.assertIn("6h10", recente["mensagem"])
            self.assertIn("Farmácia:", alertas[("sem_chamada_recente", 2)]["mensagem"])

    def test_lacunas_domingo_usa_faixa_08_12(self):
        with self.app.app_context():
            agora = datetime(2026, 11, 8, 11, 30)  # domingo
            inicio = datetime(2026, 11, 8)
            fim = datetime(2026, 11, 9)
            alertas, _ = _alertas_horario([], inicio, fim, agora)
            por_tipo = {a["tipo"]: a for a in alertas}
            self.assertIn("sem_retirada", por_tipo)
            self.assertIn("08h–10h", por_tipo["sem_retirada"]["mensagem"])
            self.assertNotIn("07h", por_tipo["sem_retirada"]["mensagem"])
            self.assertIn("08:00", por_tipo["sem_retirada_recente"]["mensagem"])
            self.assertNotIn("07:00", por_tipo["sem_chamada_recente"]["mensagem"])

    def test_ociosidade_por_setor_respeita_minutos(self):
        with self.app.app_context():
            agora = datetime(2026, 11, 9, 10, 0)
            inicio = datetime(2026, 11, 9)
            fim = datetime(2026, 11, 10)
            senhas = [
                Senha(
                    senha="N001",
                    tipo="normal",
                    setor_id=1,
                    status="C",
                    data_hora=datetime(2026, 11, 9, 9, 0),
                    chamada_em=datetime(2026, 11, 9, 9, 30),
                ),
            ]
            caixa = Setor(
                id=1,
                nome="Caixa",
                senha_setor="CAIXA",
                # 09:00→10:00 = 60 min emissão; 09:30→10:00 = 30 min chamada
                alerta_sem_emitir_minutos=70,
                alerta_ociosidade_minutos=45,
            )
            rapido = Setor(
                id=2,
                nome="Farmácia",
                senha_setor="FARMA",
                alerta_sem_emitir_minutos=20,
                alerta_ociosidade_minutos=20,
            )

            alertas_45 = {
                (a["tipo"], a.get("setor_id")): a
                for a in _alertas_horario(senhas, inicio, fim, agora, {1: caixa})[0]
            }
            self.assertNotIn(("sem_chamada_recente", 1), alertas_45)
            self.assertNotIn(("sem_retirada_recente", 1), alertas_45)

            alertas_20 = {
                (a["tipo"], a.get("setor_id")): a
                for a in _alertas_horario(senhas, inicio, fim, agora, {2: rapido})[0]
            }
            # Farmácia sem emissão/chamada desde 07:00 → passa dos 20 min
            self.assertIn(("sem_chamada_recente", 2), alertas_20)
            self.assertIn("20 min", alertas_20[("sem_chamada_recente", 2)]["mensagem"])
            self.assertIn(("sem_retirada_recente", 2), alertas_20)

            caixa.alerta_ociosidade_minutos = 20
            caixa.alerta_sem_emitir_minutos = 20
            alertas_caixa = {
                (a["tipo"], a.get("setor_id")): a
                for a in _alertas_horario(senhas, inicio, fim, agora, {1: caixa})[0]
            }
            self.assertIn(("sem_chamada_recente", 1), alertas_caixa)
            self.assertIn("30 min", alertas_caixa[("sem_chamada_recente", 1)]["mensagem"])
            self.assertIn(("sem_retirada_recente", 1), alertas_caixa)
            self.assertIn("emitir", alertas_caixa[("sem_retirada_recente", 1)]["mensagem"])

    def test_antes_de_uma_hora_nao_alerta_chamada_em_andamento(self):
        with self.app.app_context():
            agora = datetime(2026, 11, 9, 7, 40)
            alertas, eventos = _alertas_horario(
                [], datetime(2026, 11, 9), datetime(2026, 11, 10), agora
            )
            self.assertEqual([], alertas)
            self.assertEqual([], eventos)

    def test_linha_do_tempo_grava_retirada_uma_vez(self):
        with self.app.app_context():
            agora = agora_sp().replace(minute=0, second=0, microsecond=0)
            if agora.hour < 8:
                self.skipTest("antes das 08h a hora das 07h ainda não encerrou")
            if agora.weekday() == 6 or _eh_feriado_nacional(agora.date()):
                if agora.hour < 9:
                    self.skipTest("faixa especial ainda não fechou a primeira hora")
            dia = agora.date().isoformat()
            montar_analytics(from_s=dia, to_s=dia)
            montar_analytics(from_s=dia, to_s=dia)

            logs = AlertaLog.query.filter_by(tipo="sem_retirada").all()
            chaves = [row.chave for row in logs]
            self.assertEqual(len(chaves), len(set(chaves)))
            self.assertTrue(any("sem retirada" in row.mensagem for row in logs))
            self.assertEqual(
                0,
                AlertaLog.query.filter_by(tipo="sem_chamada").count(),
            )

    def test_setor_com_alerta_desligado_nao_gera_log(self):
        with self.app.app_context():
            agora = agora_sp().replace(minute=0, second=0, microsecond=0)
            if agora.hour < 8:
                self.skipTest("antes das 08h a hora das 07h ainda não encerrou")
            caixa = db.session.get(Setor, self.caixa_id)
            caixa.alertas_ativos = False
            db.session.commit()
            dia = agora.date().isoformat()
            montar_analytics(from_s=dia, to_s=dia)
            self.assertEqual(
                0,
                AlertaLog.query.filter_by(setor_id=self.caixa_id).count(),
            )
