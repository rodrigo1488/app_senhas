import unittest
from datetime import timedelta
from zoneinfo import ZoneInfo

from backend import create_app
from backend.extensions import db
from backend.models import AtendimentoAtual, Operador, Senha, Setor
from backend.services.fila_service import criar_senha, encerrar_senhas_vencidas, posicao_na_fila, serializar_fila
from backend.timezone import FUSO_SP, agora_sp, inicio_fim_dia_sp


class NumeracaoSenhaTest(unittest.TestCase):
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
            setor = Setor(nome="Balcão", senha_setor="SETOR")
            db.session.add(setor)
            db.session.commit()
            self.setor_id = setor.id

    def test_contagem_crescente_por_tipo(self):
        with self.app.app_context():
            n1 = criar_senha(self.setor_id, "normal")
            n2 = criar_senha(self.setor_id, "normal")
            p1 = criar_senha(self.setor_id, "preferencial")
            n3 = criar_senha(self.setor_id, "normal")

            self.assertEqual("N1", n1.senha)
            self.assertEqual("N2", n2.senha)
            self.assertEqual("P1", p1.senha)
            self.assertEqual("N3", n3.senha)

    def test_zera_no_dia_seguinte(self):
        with self.app.app_context():
            ontem = agora_sp().replace(hour=12, minute=0, second=0, microsecond=0) - timedelta(days=1)
            db.session.add(
                Senha(
                    senha="N9",
                    tipo="normal",
                    setor_id=self.setor_id,
                    status="F",
                    data_hora=ontem,
                )
            )
            db.session.commit()

            hoje = criar_senha(self.setor_id, "normal")
            self.assertEqual("N1", hoje.senha)

    def test_encerra_pendentes_e_atendimentos_do_dia_anterior(self):
        with self.app.app_context():
            ontem = agora_sp().replace(hour=18, minute=0, second=0, microsecond=0) - timedelta(days=1)
            operador = Operador(nome="Ana", setor_id=self.setor_id)
            pendente = Senha(
                senha="N4",
                tipo="normal",
                setor_id=self.setor_id,
                status="A",
                data_hora=ontem,
            )
            em_atendimento = Senha(
                senha="N5",
                tipo="normal",
                setor_id=self.setor_id,
                status="C",
                data_hora=ontem,
                chamada_em=ontem,
            )
            db.session.add_all([operador, pendente, em_atendimento])
            db.session.flush()
            db.session.add(
                AtendimentoAtual(
                    senha_id=em_atendimento.id,
                    setor_id=self.setor_id,
                    operador_id=operador.id,
                    data_hora=ontem,
                )
            )
            db.session.commit()
            pendente_id = pendente.id
            atendimento_id = em_atendimento.id

            encerrados = encerrar_senhas_vencidas()
            self.assertEqual([self.setor_id], encerrados)

            pendente = db.session.get(Senha, pendente_id)
            em_atendimento = db.session.get(Senha, atendimento_id)
            self.assertEqual("F", pendente.status)
            self.assertEqual("F", em_atendimento.status)
            self.assertIsNotNone(pendente.finalizado_em)
            self.assertEqual(0, AtendimentoAtual.query.count())

            fila = serializar_fila(self.setor_id)
            self.assertEqual([], fila["pendentes"])
            self.assertEqual([], fila["atendimentos"])

            hoje = criar_senha(self.setor_id, "normal")
            self.assertEqual("N1", hoje.senha)

    def test_fuso_oficial_e_sao_paulo(self):
        self.assertEqual("America/Sao_Paulo", str(FUSO_SP))
        self.assertEqual(ZoneInfo("America/Sao_Paulo"), FUSO_SP)
        agora = agora_sp()
        self.assertIsNone(agora.tzinfo)
        inicio, fim = inicio_fim_dia_sp(agora)
        self.assertEqual(0, inicio.hour)
        self.assertEqual(0, inicio.minute)
        self.assertEqual(24, int((fim - inicio).total_seconds() // 3600))

    def test_posicao_respeita_prioridade_e_atualiza_apos_chamada(self):
        with self.app.app_context():
            n1 = criar_senha(self.setor_id, "normal")
            n2 = criar_senha(self.setor_id, "normal")
            p1 = criar_senha(self.setor_id, "preferencial")
            p2 = criar_senha(self.setor_id, "preferencial")

            self.assertEqual(3, posicao_na_fila(n2.token_unico)["posicao"])
            self.assertEqual(1, posicao_na_fila(p2.token_unico)["posicao"])

            p1.status = "C"
            db.session.commit()

            self.assertEqual(2, posicao_na_fila(n2.token_unico)["posicao"])
            self.assertEqual(0, posicao_na_fila(p2.token_unico)["posicao"])


if __name__ == "__main__":
    unittest.main()
