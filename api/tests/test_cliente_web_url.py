import os
import unittest
from unittest.mock import patch

from backend import create_app
from backend.extensions import db
from backend.utils import get_cliente_web_base, get_notification_url, set_ngrok_url


class ClienteWebUrlTest(unittest.TestCase):
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

    def test_prioridade_url_do_painel_sobre_env(self):
        with self.app.app_context():
            set_ngrok_url("https://fila.empresa.com/")
            with patch.dict(os.environ, {"ADMIN_WEB_URL": "http://localhost:3000"}, clear=False):
                self.assertEqual("https://fila.empresa.com", get_cliente_web_base())
                self.assertEqual(
                    "https://fila.empresa.com/acompanhar/abc",
                    get_notification_url("abc"),
                )

    def test_fallback_para_admin_web_url(self):
        with self.app.app_context():
            with patch.dict(os.environ, {"ADMIN_WEB_URL": "https://painel.local"}, clear=False):
                self.assertEqual("https://painel.local", get_cliente_web_base())


if __name__ == "__main__":
    unittest.main()
