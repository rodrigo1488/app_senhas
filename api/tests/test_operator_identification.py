import unittest

from backend import create_app
from backend.auth import create_session_token
from backend.extensions import db
from backend.models import Operador, Senha, Setor
from backend.services.fila_service import estado_atendimento_atual, serializar_fila
from backend.services.operador_pin_service import OperadorPinError, definir_pin
from werkzeug.security import check_password_hash


class OperatorIdentificationTest(unittest.TestCase):
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
            setor = Setor(
                nome="Balcão",
                senha_setor="SETOR",
                modo_identificacao_operador="pin",
            )
            db.session.add(setor)
            db.session.flush()
            operador = Operador(nome="Ana", setor_id=setor.id)
            definir_pin(operador, "1234", setor.id)
            db.session.add(operador)
            db.session.commit()
            self.setor_id = setor.id
            self.operador_id = operador.id

    def _generic_token(self):
        with self.app.app_context():
            return create_session_token(self.setor_id, "generic")

    def test_pin_is_hashed_and_duplicate_is_rejected(self):
        with self.app.app_context():
            operador = db.session.get(Operador, self.operador_id)
            self.assertNotEqual("1234", operador.pin_hash)
            self.assertTrue(check_password_hash(operador.pin_hash, "1234"))

            outro = Operador(nome="Beto", setor_id=self.setor_id)
            with self.assertRaises(OperadorPinError):
                definir_pin(outro, "1234", self.setor_id)

    def test_pin_identifies_operator_without_exposing_hash(self):
        client = self.app.test_client()
        response = client.post(
            "/api/v1/sessao/papel",
            json={"role": "operador", "pin": "1234"},
            headers={"Authorization": f"Bearer {self._generic_token()}"},
        )
        self.assertEqual(200, response.status_code)
        payload = response.get_json()
        self.assertEqual(self.operador_id, payload["operador"]["id"])
        self.assertNotIn("pin_hash", payload["operador"])

        invalid = client.post(
            "/api/v1/sessao/papel",
            json={"role": "operador", "pin": "9999"},
            headers={"Authorization": f"Bearer {self._generic_token()}"},
        )
        self.assertEqual(401, invalid.status_code)

    def test_client_role_cannot_call_as_operator(self):
        with self.app.app_context():
            token = create_session_token(self.setor_id, "cliente")
        response = self.app.test_client().post(
            "/api/v1/operador/chamar_proxima",
            json={"operador_id": self.operador_id},
            headers={"Authorization": f"Bearer {token}"},
        )
        self.assertEqual(403, response.status_code)

    def test_photo_mode_accepts_only_operator_from_same_sector(self):
        with self.app.app_context():
            setor = db.session.get(Setor, self.setor_id)
            setor.modo_identificacao_operador = "foto"
            db.session.commit()
        response = self.app.test_client().post(
            "/api/v1/sessao/papel",
            json={"role": "operador", "operador_id": self.operador_id},
            headers={"Authorization": f"Bearer {self._generic_token()}"},
        )
        self.assertEqual(200, response.status_code)
        self.assertEqual(self.operador_id, response.get_json()["operador"]["id"])

    def test_admin_cannot_enable_pin_with_unconfigured_operator(self):
        with self.app.app_context():
            setor = db.session.get(Setor, self.setor_id)
            setor.modo_identificacao_operador = "foto"
            db.session.add(Operador(nome="Sem PIN", setor_id=self.setor_id))
            db.session.commit()

        client = self.app.test_client()
        with client.session_transaction() as session:
            session["user_id"] = 1
        response = client.put(
            f"/api/v1/admin/setores/{self.setor_id}",
            json={"modo_identificacao_operador": "pin"},
        )
        self.assertEqual(400, response.status_code)
        self.assertIn("PIN", response.get_json()["error"])

    def test_order_is_private_to_operator_hydration(self):
        with self.app.app_context():
            senha = Senha(
                senha="N1000",
                tipo="normal",
                setor_id=self.setor_id,
                status="C",
                tem_pedido=True,
                pedido="Café sem açúcar",
            )
            db.session.add(senha)
            db.session.flush()
            from backend.models import AtendimentoAtual

            db.session.add(
                AtendimentoAtual(
                    senha_id=senha.id,
                    setor_id=self.setor_id,
                    operador_id=self.operador_id,
                )
            )
            db.session.commit()
            atendimento_publico = serializar_fila(self.setor_id)["atendimentos"][0]
            self.assertNotIn("pedido", atendimento_publico)
            atendimento = estado_atendimento_atual(self.setor_id, self.operador_id)
            self.assertTrue(atendimento["tem_pedido"])
            self.assertEqual("Café sem açúcar", atendimento["pedido"])


if __name__ == "__main__":
    unittest.main()
