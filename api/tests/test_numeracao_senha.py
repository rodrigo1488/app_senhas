import unittest
from datetime import datetime, timedelta

from backend import create_app
from backend.extensions import db
from backend.models import Senha, Setor
from backend.services.fila_service import criar_senha, posicao_na_fila


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
            ontem = datetime.now().replace(hour=12, minute=0, second=0, microsecond=0) - timedelta(days=1)
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
