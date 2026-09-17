import unittest

from backend import create_app
from backend.auth import create_session_token
from backend.extensions import db
from backend.models import Propaganda, Senha, Setor
from backend.services.usuario_service import criar_ou_atualizar_admin


class PropagandasClienteTest(unittest.TestCase):
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
            setor = Setor(nome="Balcão", senha_setor="SETOR", propagandas_ativas=False)
            db.session.add(setor)
            db.session.commit()
            self.setor_id = setor.id

    def _token(self, role="cliente"):
        with self.app.app_context():
            return create_session_token(self.setor_id, role)

    def _admin_client(self):
        client = self.app.test_client()
        with client.session_transaction() as sess:
            sess["user_id"] = self.admin_id
        return client

    def test_cliente_config_exige_papel_cliente(self):
        response = self.app.test_client().get(
            "/api/v1/setor/cliente_config",
            headers={"Authorization": f"Bearer {self._token('tv')}"},
        )
        self.assertEqual(403, response.status_code)

    def test_vincular_midia_cliente_nao_altera_tv_config(self):
        admin = self._admin_client()
        with self.app.app_context():
            tv = Propaganda(arquivo="tv.jpg", tipo="image", ordem=1, ativo=True)
            espera = Propaganda(arquivo="espera.jpg", tipo="image", ordem=2, ativo=True)
            db.session.add_all([tv, espera])
            db.session.commit()
            tv_id, espera_id = tv.id, espera.id

        enviar_tv = admin.put(
            "/api/v1/admin/tvs/midias",
            json={"tipo": "setor", "id": self.setor_id, "propaganda_ids": [tv_id]},
        )
        self.assertEqual(200, enviar_tv.status_code, enviar_tv.get_json())

        enviar_cliente = admin.put(
            "/api/v1/admin/propagandas/cliente",
            json={"setor_id": self.setor_id, "propaganda_ids": [espera_id]},
        )
        self.assertEqual(200, enviar_cliente.status_code, enviar_cliente.get_json())
        self.assertEqual([espera_id], enviar_cliente.get_json()["propaganda_ids"])
        self.assertTrue(enviar_cliente.get_json()["propagandas_cliente_ativas"])

        tv_config = self.app.test_client().get(
            "/api/v1/setor/tv_config",
            headers={"Authorization": f"Bearer {self._token('tv')}"},
        )
        self.assertEqual(200, tv_config.status_code)
        tv_payload = tv_config.get_json()
        self.assertTrue(tv_payload["propagandas_ativas"])
        self.assertEqual(["tv.jpg"], [item["arquivo"] for item in tv_payload["imagens"]])
        self.assertIn("layout_tv_web", tv_payload)

        cliente_config = self.app.test_client().get(
            "/api/v1/setor/cliente_config",
            headers={"Authorization": f"Bearer {self._token('cliente')}"},
        )
        self.assertEqual(200, cliente_config.status_code)
        payload = cliente_config.get_json()
        self.assertTrue(payload["propagandas_ativas"])
        self.assertEqual(["espera.jpg"], [item["arquivo"] for item in payload["imagens"]])
        self.assertEqual(15_000, payload["intervalo_ms"])
        self.assertNotIn("layout_tv_web", payload)
        self.assertNotIn("orientacao_tv", payload)

    def test_flag_desligada_devolve_lista_vazia(self):
        admin = self._admin_client()
        with self.app.app_context():
            espera = Propaganda(arquivo="espera.jpg", tipo="image", ordem=1, ativo=True)
            db.session.add(espera)
            db.session.commit()
            espera_id = espera.id

        admin.put(
            "/api/v1/admin/propagandas/cliente",
            json={"setor_id": self.setor_id, "propaganda_ids": [espera_id]},
        )
        desligar = admin.put(
            f"/api/v1/admin/setores/{self.setor_id}",
            json={"propagandas_cliente_ativas": False},
        )
        self.assertEqual(200, desligar.status_code)
        self.assertFalse(desligar.get_json()["propagandas_cliente_ativas"])

        cliente_config = self.app.test_client().get(
            "/api/v1/setor/cliente_config",
            headers={"Authorization": f"Bearer {self._token('cliente')}"},
        )
        self.assertEqual(200, cliente_config.status_code)
        payload = cliente_config.get_json()
        self.assertFalse(payload["propagandas_ativas"])
        self.assertEqual([], payload["imagens"])

        tv_config = self.app.test_client().get(
            "/api/v1/setor/tv_config",
            headers={"Authorization": f"Bearer {self._token('tv')}"},
        )
        self.assertFalse(tv_config.get_json()["propagandas_ativas"])
        self.assertEqual([], tv_config.get_json()["imagens"])

    def test_verificar_senha_inclui_so_midias_da_espera(self):
        admin = self._admin_client()
        with self.app.app_context():
            tv = Propaganda(arquivo="tv.jpg", tipo="image", ordem=1, ativo=True)
            espera = Propaganda(arquivo="espera.mp4", tipo="video", ordem=2, ativo=True)
            senha = Senha(senha="N01", tipo="normal", setor_id=self.setor_id, token_unico="tok-espera")
            db.session.add_all([tv, espera, senha])
            db.session.commit()
            tv_id, espera_id = tv.id, espera.id

        admin.put(
            "/api/v1/admin/tvs/midias",
            json={"tipo": "setor", "id": self.setor_id, "propaganda_ids": [tv_id]},
        )
        admin.put(
            "/api/v1/admin/propagandas/cliente",
            json={"setor_id": self.setor_id, "propaganda_ids": [espera_id]},
        )

        response = self.app.test_client().get("/api/verificar_senha/tok-espera")
        self.assertEqual(200, response.status_code)
        midias = response.get_json()["midias"]
        self.assertTrue(midias["propagandas_ativas"])
        self.assertEqual(["espera.mp4"], [item["arquivo"] for item in midias["imagens"]])
        self.assertEqual("video", midias["imagens"][0]["tipo"])
        self.assertNotIn("layout_tv_web", midias)


if __name__ == "__main__":
    unittest.main()
