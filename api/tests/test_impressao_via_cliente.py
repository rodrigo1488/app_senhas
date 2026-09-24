import base64
import unittest
from unittest.mock import patch

from backend import create_app
from backend.auth import create_session_token
from backend.extensions import db
from backend.models import Impressora, Setor
from backend.services.usuario_service import criar_ou_atualizar_admin


class ImpressaoViaClienteTest(unittest.TestCase):
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
            from backend import _migrate_usuario_papeis, _migrate_impressao_via_cliente_column

            _migrate_usuario_papeis()
            _migrate_impressao_via_cliente_column()
            criar_ou_atualizar_admin("admin@test.local", "admin123")
            setor = Setor(
                nome="Balcão",
                senha_setor="SETOR",
                impressao_via_cliente=True,
            )
            db.session.add(setor)
            db.session.commit()
            self.setor_id = setor.id
            db.session.add(
                Impressora(nome="Caixa", ip="192.168.0.50", porta=9100, setor_id=setor.id)
            )
            db.session.commit()

    def _cliente_token(self):
        with self.app.app_context():
            return create_session_token(self.setor_id, "cliente")

    def test_criar_senha_devolve_escpos_para_o_tablet(self):
        token = self._cliente_token()
        with patch(
            "backend.services.impressao_service.imprimir_senha_em_background"
        ) as mock_bg:
            response = self.app.test_client().post(
                "/api/v1/senha",
                headers={"Authorization": f"Bearer {token}"},
                json={"tipo": "normal"},
            )
        self.assertEqual(200, response.status_code, response.get_json())
        payload = response.get_json()
        impressao = payload["impressao"]
        self.assertTrue(impressao["via_cliente"])
        self.assertEqual("192.168.0.50", impressao["impressora_ip"])
        self.assertEqual(9100, impressao["impressora_porta"])
        raw = base64.b64decode(impressao["escpos_base64"])
        self.assertGreater(len(raw), 20)
        mock_bg.assert_not_called()

    def test_sem_flag_imprime_no_servidor(self):
        with self.app.app_context():
            setor = db.session.get(Setor, self.setor_id)
            setor.impressao_via_cliente = False
            db.session.commit()
        token = self._cliente_token()
        with patch(
            "backend.services.impressao_service.imprimir_senha_em_background"
        ) as mock_bg:
            response = self.app.test_client().post(
                "/api/v1/senha",
                headers={"Authorization": f"Bearer {token}"},
                json={"tipo": "preferencial"},
            )
        self.assertEqual(200, response.status_code, response.get_json())
        payload = response.get_json()
        self.assertEqual({"via_cliente": False}, payload.get("impressao"))
        mock_bg.assert_called_once()

    def test_admin_liga_flag_no_setor(self):
        with self.app.app_context():
            admin = criar_ou_atualizar_admin("admin2@test.local", "admin123")
            admin_id = admin.id
        client = self.app.test_client()
        with client.session_transaction() as sess:
            sess["user_id"] = admin_id
        response = client.put(
            f"/api/v1/admin/setores/{self.setor_id}",
            json={"impressao_via_cliente": False},
        )
        self.assertEqual(200, response.status_code, response.get_json())
        self.assertFalse(response.get_json()["impressao_via_cliente"])


if __name__ == "__main__":
    unittest.main()
