import unittest

from backend import create_app
from backend.extensions import db
from backend.models import Setor, Usuario
from backend.services.usuario_service import criar_ou_atualizar_admin, criar_usuario


class AdminRolesTest(unittest.TestCase):
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
            criar_ou_atualizar_admin("admin@test.local", "admin123")
            s1 = Setor(nome="Caixa", senha_setor="CAIXA")
            s2 = Setor(nome="Farmácia", senha_setor="FARMA")
            db.session.add_all([s1, s2])
            db.session.commit()
            self.setor1 = s1.id
            self.setor2 = s2.id
            criar_usuario(
                email="gerente@test.local",
                senha="gerente123",
                papel="gerente",
                nome="Gerente Caixa",
                setor_ids=[self.setor1],
            )

    def _login(self, email: str, senha: str):
        client = self.app.test_client()
        resp = client.post("/api/v1/admin/login", json={"email": email, "senha": senha})
        self.assertEqual(200, resp.status_code, resp.get_json())
        return client

    def test_me_includes_papel_and_setores(self):
        client = self._login("gerente@test.local", "gerente123")
        me = client.get("/api/v1/admin/me").get_json()
        self.assertEqual("gerente", me["papel"])
        self.assertEqual([self.setor1], me["setor_ids"])
        self.assertFalse(me["is_admin"])

    def test_gerente_lists_only_own_setores(self):
        client = self._login("gerente@test.local", "gerente123")
        setores = client.get("/api/v1/admin/setores").get_json()
        self.assertEqual(1, len(setores))
        self.assertEqual(self.setor1, setores[0]["id"])

    def test_gerente_cannot_create_setor_or_user(self):
        client = self._login("gerente@test.local", "gerente123")
        self.assertEqual(
            403,
            client.post("/api/v1/admin/setores", json={"nome": "X", "senha_setor": "X"}).status_code,
        )
        self.assertEqual(
            403,
            client.post(
                "/api/v1/admin/usuarios",
                json={"email": "x@test.local", "senha": "123456", "papel": "admin"},
            ).status_code,
        )

    def test_admin_creates_gerente_with_setores(self):
        client = self._login("admin@test.local", "admin123")
        resp = client.post(
            "/api/v1/admin/usuarios",
            json={
                "email": "g2@test.local",
                "senha": "senha123",
                "papel": "gerente",
                "setor_ids": [self.setor1, self.setor2],
            },
        )
        self.assertEqual(201, resp.status_code, resp.get_json())
        payload = resp.get_json()
        self.assertEqual("gerente", payload["papel"])
        self.assertEqual(sorted([self.setor1, self.setor2]), sorted(payload["setor_ids"]))

    def test_gerente_blocked_from_other_setor_fila(self):
        client = self._login("gerente@test.local", "gerente123")
        forbidden = client.get(f"/api/v1/admin/fila-ao-vivo?setor_id={self.setor2}")
        self.assertEqual(403, forbidden.status_code)
        allowed = client.get(f"/api/v1/admin/fila-ao-vivo?setor_id={self.setor1}")
        # 200 ou 404 do serviço; nunca 403
        self.assertNotEqual(403, allowed.status_code)


if __name__ == "__main__":
    unittest.main()
