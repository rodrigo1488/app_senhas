import unittest
from datetime import datetime, timedelta

from backend import create_app
from backend.extensions import db
from backend.models import AlertaLog, Senha, Setor
from backend.services.analytics_service import _alertas_horario, montar_analytics
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

    def test_grade_vai_ate_22h_e_fluxo_omite_madrugada(self):
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
            self.assertEqual(22, dados["heatmap"]["hora_fim"])
            self.assertEqual(21, dados["heatmap"]["hora_alerta_ate"])
            self.assertIn(22, {c["hora"] for c in dados["heatmap"]["celulas"]})

            labels = [row["label"] for row in dados["fluxo_por_setor"]["series"]]
            self.assertEqual([f"{hora:02d}h" for hora in range(7, 23)], labels)
            self.assertEqual(1, dados["por_hora"][9]["retiradas"])
            self.assertEqual(0, dados["por_hora"][9]["chamadas"])
            self.assertEqual(1, dados["por_hora"][11]["chamadas"])

            tipos = {a["tipo"] for a in dados["alertas"]}
            self.assertIn("sem_retirada", tipos)
            self.assertIn("sem_chamada", tipos)
            chamadas = [a for a in dados["alertas"] if a["tipo"] == "sem_chamada"]
            self.assertTrue(any(a.get("setor_id") == self.caixa_id and "Caixa:" in a["mensagem"] for a in chamadas))

    def test_lacunas_07_a_21_e_hora_sem_chamada(self):
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
        alertas = {
            (a["tipo"], a.get("setor_id")): a
            for a in _alertas_horario(senhas, inicio, fim, agora, {1: caixa, 2: farm})[0]
        }

        retirada = alertas[("sem_retirada", None)]["mensagem"]
        self.assertIn("07h–08h", retirada)
        self.assertIn("11h–14h", retirada)
        self.assertNotIn("09h", retirada)
        self.assertNotIn("10h", retirada)
        self.assertEqual("warning", alertas[("sem_retirada", None)]["severidade"])

        chamada = alertas[("sem_chamada", 1)]["mensagem"]
        self.assertTrue(chamada.startswith("Caixa:"))
        self.assertIn("07h–08h", chamada)
        self.assertIn("10h–14h", chamada)
        self.assertNotIn("09h", chamada)

        farm_chamada = alertas[("sem_chamada", 2)]["mensagem"]
        self.assertTrue(farm_chamada.startswith("Farmácia:"))
        self.assertIn("07h–14h", farm_chamada)

        recente = alertas[("sem_chamada_recente", 1)]
        self.assertEqual("critical", recente["severidade"])
        self.assertIn("Caixa:", recente["mensagem"])
        self.assertIn("09:20", recente["mensagem"])
        self.assertIn("6h10", recente["mensagem"])
        self.assertIn("Farmácia:", alertas[("sem_chamada_recente", 2)]["mensagem"])

    def test_ociosidade_por_setor_respeita_minutos(self):
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
        agora = datetime(2026, 11, 9, 7, 40)
        alertas, eventos = _alertas_horario([], datetime(2026, 11, 9), datetime(2026, 11, 10), agora)
        self.assertEqual([], alertas)
        self.assertEqual([], eventos)

    def test_linha_do_tempo_grava_setor_uma_vez(self):
        with self.app.app_context():
            agora = agora_sp().replace(minute=0, second=0, microsecond=0)
            if agora.hour < 8:
                self.skipTest("antes das 08h a hora das 07h ainda não encerrou")
            dia = agora.date().isoformat()
            montar_analytics(from_s=dia, to_s=dia)
            montar_analytics(from_s=dia, to_s=dia)

            logs = AlertaLog.query.filter_by(setor_id=self.caixa_id, tipo="sem_chamada").all()
            chaves = [row.chave for row in logs]
            self.assertEqual(len(chaves), len(set(chaves)))
            self.assertTrue(any("Caixa:" in row.mensagem and "07h" in row.mensagem for row in logs))

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
                AlertaLog.query.filter_by(setor_id=self.caixa_id, tipo="sem_chamada").count(),
            )
