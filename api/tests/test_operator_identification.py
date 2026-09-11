import unittest
from unittest.mock import patch

from backend import create_app
from backend.auth import create_session_token, decode_session_token
from backend.extensions import db
from backend.models import AtendimentoAtual, Finalizado, Operador, Senha, Setor
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
            with self.assertRaises(OperadorPinError):
                definir_pin(outro, "12345", self.setor_id)

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
            atendimento_operador = serializar_fila(
                self.setor_id,
                incluir_pedidos=True,
            )["atendimentos"][0]
            self.assertEqual(self.operador_id, atendimento_operador["operador_id"])
            self.assertEqual("Ana", atendimento_operador["operador_nome"])
            self.assertEqual("N1000", atendimento_operador["senha"])
            self.assertTrue(atendimento_operador["tem_pedido"])
            self.assertEqual("Café sem açúcar", atendimento_operador["pedido"])
            self.assertFalse(atendimento_operador["pedido_confirmado"])
            atendimento = estado_atendimento_atual(self.setor_id, self.operador_id)
            self.assertTrue(atendimento["tem_pedido"])
            self.assertEqual("Café sem açúcar", atendimento["pedido"])

    def test_operator_screen_session_has_detailed_queue_only_for_operator(self):
        with self.app.app_context():
            db.session.add(
                Senha(
                    senha="N2000",
                    tipo="normal",
                    setor_id=self.setor_id,
                    status="A",
                    tem_pedido=True,
                    pedido="Pão na chapa",
                    pedido_confirmado=False,
                )
            )
            db.session.commit()
            client_token = create_session_token(self.setor_id, "cliente")

        client = self.app.test_client()
        operator_session = client.post(
            "/api/v1/sessao/papel",
            json={"role": "operador"},
            headers={"Authorization": f"Bearer {self._generic_token()}"},
        )
        self.assertEqual(200, operator_session.status_code)
        operator_token = operator_session.get_json()["session_token"]
        with self.app.app_context():
            payload = decode_session_token(operator_token)
            self.assertEqual("operador", payload["role"])
            self.assertIsNone(payload["operador_id"])

        public_queue = client.get(
            "/api/v1/setor/fila",
            headers={"Authorization": f"Bearer {client_token}"},
        ).get_json()["pendentes"][0]
        operator_queue = client.get(
            "/api/v1/setor/fila",
            headers={"Authorization": f"Bearer {operator_token}"},
        ).get_json()["pendentes"][0]
        self.assertNotIn("pedido", public_queue)
        self.assertNotIn("tem_pedido", public_queue)
        self.assertEqual("Pão na chapa", operator_queue["pedido"])
        self.assertTrue(operator_queue["tem_pedido"])
        self.assertFalse(operator_queue["pedido_confirmado"])

    def test_identification_token_calls_once_and_cannot_change_identity(self):
        with self.app.app_context():
            db.session.add_all(
                [
                    Senha(senha="N3000", tipo="normal", setor_id=self.setor_id, status="A"),
                    Senha(senha="N3001", tipo="normal", setor_id=self.setor_id, status="A"),
                ]
            )
            db.session.commit()

        client = self.app.test_client()
        identified = client.post(
            "/api/v1/sessao/papel",
            json={"role": "operador", "pin": "1234"},
            headers={"Authorization": f"Bearer {self._generic_token()}"},
        )
        action_token = identified.get_json()["session_token"]

        identity_change = client.post(
            "/api/v1/sessao/papel",
            json={"role": "operador", "pin": "1234"},
            headers={"Authorization": f"Bearer {action_token}"},
        )
        self.assertEqual(403, identity_change.status_code)

        first_call = client.post(
            "/api/v1/operador/chamar_proxima",
            json={},
            headers={"Authorization": f"Bearer {action_token}"},
        )
        self.assertEqual(200, first_call.status_code)
        payload = first_call.get_json()
        self.assertTrue(payload["chamada_realizada"])
        self.assertIsInstance(payload["senha"], dict)
        self.assertEqual("N3000", payload["senha"]["senha"])
        self.assertEqual("normal", payload["tipo_chamado"])
        self.assertTrue(payload["mensagem"])
        with self.app.app_context():
            returned_session = decode_session_token(payload["session_token"])
            self.assertEqual("operador", returned_session["role"])
            self.assertIsNone(returned_session["operador_id"])

        replay = client.post(
            "/api/v1/operador/chamar_proxima",
            json={},
            headers={"Authorization": f"Bearer {action_token}"},
        )
        self.assertEqual(403, replay.status_code)

    def test_empty_queue_finalizes_current_service_and_returns_typed_success(self):
        with self.app.app_context():
            atual = Senha(
                senha="N4000",
                tipo="normal",
                setor_id=self.setor_id,
                status="C",
                token_unico="ticket-atual",
            )
            db.session.add(atual)
            db.session.flush()
            db.session.add(
                AtendimentoAtual(
                    senha_id=atual.id,
                    setor_id=self.setor_id,
                    operador_id=self.operador_id,
                )
            )
            db.session.commit()
            senha_id = atual.id

        client = self.app.test_client()
        identified = client.post(
            "/api/v1/sessao/papel",
            json={"role": "operador", "pin": "1234"},
            headers={"Authorization": f"Bearer {self._generic_token()}"},
        )
        self.assertEqual(200, identified.status_code)

        with (
            patch("backend.blueprints.api_bp.emit_fila_atualizada") as fila_emitida,
            patch("backend.blueprints.api_bp.emit_avaliacao_solicitada") as avaliacao_emitida,
        ):
            response = client.post(
                "/api/v1/operador/chamar_proxima",
                json={},
                headers={"Authorization": f"Bearer {identified.get_json()['session_token']}"},
            )
            fila_emitida.assert_called_once_with(self.setor_id)
            avaliacao_emitida.assert_called_once()

        self.assertEqual(200, response.status_code)
        payload = response.get_json()
        self.assertEqual(
            {
                "alerta_preferenciais",
                "chamada_realizada",
                "mensagem",
                "senha",
                "session_token",
                "tipo_chamado",
            },
            set(payload),
        )
        self.assertIsNone(payload["senha"])
        self.assertFalse(payload["chamada_realizada"])
        self.assertIsNone(payload["tipo_chamado"])
        self.assertIn("Não há senhas pendentes", payload["mensagem"])

        with self.app.app_context():
            token_payload = decode_session_token(payload["session_token"])
            self.assertEqual("operador", token_payload["role"])
            self.assertIsNone(token_payload["operador_id"])
            self.assertIsNone(
                AtendimentoAtual.query.filter_by(
                    setor_id=self.setor_id,
                    operador_id=self.operador_id,
                ).first()
            )
            self.assertEqual("F", db.session.get(Senha, senha_id).status)
            finalizado = Finalizado.query.filter_by(
                senha_id=senha_id,
                setor_id=self.setor_id,
                operador_id=self.operador_id,
            ).one()
            self.assertEqual("", finalizado.avaliacao)
            self.assertEqual([], serializar_fila(self.setor_id)["atendimentos"])


if __name__ == "__main__":
    unittest.main()
