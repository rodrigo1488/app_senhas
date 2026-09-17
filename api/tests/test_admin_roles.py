import io
import unittest
from unittest.mock import patch

from backend import create_app
from backend.extensions import db
from backend.models import Propaganda, Setor
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
            criar_usuario(
                email="mkt@test.local",
                senha="mkt12345",
                papel="marketing",
                nome="Marketing",
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

    def test_admin_creates_marketing_without_setores(self):
        client = self._login("admin@test.local", "admin123")
        resp = client.post(
            "/api/v1/admin/usuarios",
            json={
                "email": "mkt2@test.local",
                "senha": "senha123",
                "papel": "marketing",
            },
        )
        self.assertEqual(201, resp.status_code, resp.get_json())
        payload = resp.get_json()
        self.assertEqual("marketing", payload["papel"])
        self.assertEqual([], payload["setor_ids"])

    def test_gerente_cannot_create_marketing(self):
        client = self._login("gerente@test.local", "gerente123")
        self.assertEqual(
            403,
            client.post(
                "/api/v1/admin/usuarios",
                json={"email": "x@test.local", "senha": "123456", "papel": "marketing"},
            ).status_code,
        )

    def test_marketing_me_and_login(self):
        client = self._login("mkt@test.local", "mkt12345")
        me = client.get("/api/v1/admin/me").get_json()
        self.assertEqual("marketing", me["papel"])
        self.assertFalse(me["is_admin"])
        self.assertTrue(me["is_marketing"])
        self.assertEqual([], me["setor_ids"])

    def test_marketing_lists_setores_readonly_without_senha(self):
        client = self._login("mkt@test.local", "mkt12345")
        resp = client.get("/api/v1/admin/setores")
        self.assertEqual(200, resp.status_code)
        setores = resp.get_json()
        self.assertEqual(2, len(setores))
        self.assertTrue(all(s.get("senha_setor") == "" for s in setores))
        self.assertEqual(
            403,
            client.post("/api/v1/admin/setores", json={"nome": "X", "senha_setor": "X"}).status_code,
        )
        self.assertEqual(
            403,
            client.put(
                f"/api/v1/admin/setores/{self.setor1}",
                json={"nome": "Hack", "propagandas_ativas": True},
            ).status_code,
        )
        self.assertEqual(403, client.delete(f"/api/v1/admin/setores/{self.setor1}").status_code)

    @patch("backend.blueprints.admin_api_bp.process_propaganda_image", return_value="promo_mkt.jpg")
    def test_marketing_can_manage_propagandas_and_tvs(self, _mock_process):
        client = self._login("mkt@test.local", "mkt12345")
        self.assertEqual(200, client.get("/api/v1/admin/propagandas").status_code)
        self.assertEqual(200, client.get("/api/v1/admin/tvs").status_code)

        created = client.post(
            "/api/v1/admin/propagandas",
            data={"arquivo": (io.BytesIO(b"fake-image"), "promo.png")},
            content_type="multipart/form-data",
        )
        self.assertEqual(201, created.status_code, created.get_json())
        propaganda_id = created.get_json()["id"]

        updated = client.put(
            f"/api/v1/admin/propagandas/{propaganda_id}",
            json={"ativo": False},
        )
        self.assertEqual(200, updated.status_code)
        self.assertFalse(updated.get_json()["ativo"])

        linked = client.put(
            "/api/v1/admin/tvs/midias",
            json={"tipo": "setor", "id": self.setor1, "propaganda_ids": [propaganda_id]},
        )
        self.assertEqual(200, linked.status_code, linked.get_json())
        self.assertEqual([propaganda_id], linked.get_json()["propaganda_ids"])

        deleted = client.delete(f"/api/v1/admin/propagandas/{propaganda_id}")
        self.assertEqual(200, deleted.status_code)

    def test_marketing_blocked_from_operadores_usuarios_and_ops(self):
        client = self._login("mkt@test.local", "mkt12345")
        forbidden_gets = [
            "/api/v1/admin/operadores",
            "/api/v1/admin/usuarios",
            "/api/v1/admin/impressoras",
            "/api/v1/admin/analytics",
            "/api/v1/admin/dashboard",
            "/api/v1/admin/configuracao",
            f"/api/v1/admin/fila-ao-vivo?setor_id={self.setor1}",
        ]
        for path in forbidden_gets:
            resp = client.get(path)
            self.assertEqual(403, resp.status_code, path)

        self.assertEqual(
            403,
            client.post(
                "/api/v1/admin/usuarios",
                json={"email": "x@test.local", "senha": "123456", "papel": "admin"},
            ).status_code,
        )
        self.assertEqual(
            403,
            client.post("/api/v1/admin/operadores", data={"nome": "Op", "setor_id": str(self.setor1)}).status_code,
        )

    def test_gerente_still_cannot_write_propagandas(self):
        client = self._login("gerente@test.local", "gerente123")
        with self.app.app_context():
            item = Propaganda(arquivo="g.jpg", tipo="image", ordem=1, ativo=True)
            db.session.add(item)
            db.session.commit()
            propaganda_id = item.id
        self.assertEqual(
            403,
            client.post(
                "/api/v1/admin/propagandas",
                data={"arquivo": (io.BytesIO(b"fake-image"), "promo.png")},
                content_type="multipart/form-data",
            ).status_code,
        )
        self.assertEqual(
            403,
            client.put(f"/api/v1/admin/propagandas/{propaganda_id}", json={"ativo": False}).status_code,
        )

    def test_admin_access_unchanged(self):
        client = self._login("admin@test.local", "admin123")
        self.assertEqual(200, client.get("/api/v1/admin/operadores").status_code)
        self.assertEqual(200, client.get("/api/v1/admin/usuarios").status_code)
        self.assertEqual(200, client.get("/api/v1/admin/propagandas").status_code)
        self.assertEqual(200, client.get("/api/v1/admin/configuracao").status_code)


if __name__ == "__main__":
    unittest.main()
