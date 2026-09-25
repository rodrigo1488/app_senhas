import unittest

from backend import create_app
from backend.extensions import db
from backend.models import AtendimentoAtual, Finalizado, Operador, Senha, Setor
from backend.services.fila_service import FilaError, criar_senha, limpar_fila_setor
from backend.services.usuario_service import criar_ou_atualizar_admin


class LimparFilaSetorTest(unittest.TestCase):
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
            from backend import _migrate_usuario_papeis

            _migrate_usuario_papeis()
            admin = criar_ou_atualizar_admin("admin@test.local", "admin123")
            self.admin_id = admin.id
            setor = Setor(nome="Caixa", senha_setor="CAIXA")
            db.session.add(setor)
            db.session.commit()
            self.setor_id = setor.id
            op = Operador(nome="Ana", setor_id=setor.id)
            db.session.add(op)
            db.session.commit()
            self.operador_id = op.id

    def _admin_client(self):
        client = self.app.test_client()
        with client.session_transaction() as sess:
            sess["user_id"] = self.admin_id
        return client

    def test_limpar_fila_finaliza_aguardando_e_atendimento(self):
        with self.app.app_context():
            a1 = criar_senha(self.setor_id, "normal")
            a2 = criar_senha(self.setor_id, "preferencial")
            chamada = criar_senha(self.setor_id, "normal")
            chamada.status = "C"
            db.session.add(
                AtendimentoAtual(
                    senha_id=chamada.id,
                    setor_id=self.setor_id,
                    operador_id=self.operador_id,
                )
            )
            db.session.commit()
            ids = [a1.id, a2.id, chamada.id]

            result = limpar_fila_setor(self.setor_id)
            self.assertEqual(3, result["removidas"])
            self.assertEqual(2, result["aguardando"])
            self.assertEqual(1, result["em_atendimento"])

            for sid in ids:
                senha = db.session.get(Senha, sid)
                self.assertEqual("F", senha.status)
                self.assertIsNotNone(senha.finalizado_em)

            self.assertEqual(0, AtendimentoAtual.query.filter_by(setor_id=self.setor_id).count())
            self.assertEqual(1, Finalizado.query.filter_by(setor_id=self.setor_id).count())
            self.assertEqual(
                0,
                Senha.query.filter(Senha.setor_id == self.setor_id, Senha.status.in_(("A", "C"))).count(),
            )

    def test_limpar_fila_vazia(self):
        with self.app.app_context():
            result = limpar_fila_setor(self.setor_id)
            self.assertEqual(0, result["removidas"])

    def test_limpar_fila_rejeita_streaming(self):
        with self.app.app_context():
            setor = Setor(nome="Mídia", tipo_setor="streaming")
            db.session.add(setor)
            db.session.commit()
            with self.assertRaises(FilaError):
                limpar_fila_setor(setor.id)

    def test_admin_endpoint_limpar_fila(self):
        with self.app.app_context():
            criar_senha(self.setor_id, "normal")
            criar_senha(self.setor_id, "preferencial")

        client = self._admin_client()
        response = client.post(f"/api/v1/admin/setores/{self.setor_id}/limpar-fila")
        self.assertEqual(200, response.status_code, response.get_json())
        payload = response.get_json()
        self.assertTrue(payload["ok"])
        self.assertEqual(2, payload["removidas"])

        with self.app.app_context():
            self.assertEqual(
                0,
                Senha.query.filter(Senha.setor_id == self.setor_id, Senha.status.in_(("A", "C"))).count(),
            )


if __name__ == "__main__":
    unittest.main()
