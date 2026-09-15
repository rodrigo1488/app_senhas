import io
import unittest
from datetime import datetime, timedelta
from unittest.mock import patch

from backend import create_app
from backend.auth import create_session_token
from backend.extensions import db
from backend.models import AtendimentoAtual, Finalizado, Operador, Propaganda, Senha, Setor
from backend.services.fila_service import listar_chamadas_recentes
from backend.services.usuario_service import criar_ou_atualizar_admin


class PropagandasTvTest(unittest.TestCase):
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

    def _token(self, role="tv"):
        with self.app.app_context():
            return create_session_token(self.setor_id, role)

    def _admin_client(self):
        client = self.app.test_client()
        with client.session_transaction() as sess:
            sess["user_id"] = self.admin_id
        return client

    def test_vapid_public_key_is_available_without_manual_configuration(self):
        response = self.app.test_client().get("/api/vapid-public-key")
        self.assertEqual(200, response.status_code)
        payload = response.get_json()
        self.assertTrue(payload["configured"])
        self.assertGreater(len(payload["publicKey"]), 40)

    def test_migration_creates_propaganda_table_and_setor_flag(self):
        with self.app.app_context():
            self.assertTrue(hasattr(Setor, "propagandas_ativas"))
            p = Propaganda(arquivo="promo.jpg", ordem=1, ativo=True)
            db.session.add(p)
            db.session.commit()
            self.assertIsNotNone(p.id)
            setor = db.session.get(Setor, self.setor_id)
            self.assertFalse(setor.propagandas_ativas)

    def test_setor_toggle_propagandas_ativas(self):
        client = self._admin_client()

        response = client.put(
            f"/api/v1/admin/setores/{self.setor_id}",
            json={"propagandas_ativas": True},
        )
        self.assertEqual(200, response.status_code)
        self.assertTrue(response.get_json()["propagandas_ativas"])

        with self.app.app_context():
            setor = db.session.get(Setor, self.setor_id)
            self.assertTrue(setor.propagandas_ativas)

    def test_setor_persiste_layout_tv_web_e_rejeita_valor_invalido(self):
        client = self._admin_client()

        response = client.put(
            f"/api/v1/admin/setores/{self.setor_id}",
            json={"layout_tv_web": "fila"},
        )
        self.assertEqual(200, response.status_code)
        self.assertEqual("fila", response.get_json()["layout_tv_web"])

        invalid = client.put(
            f"/api/v1/admin/setores/{self.setor_id}",
            json={"layout_tv_web": "desconhecido"},
        )
        self.assertEqual(400, invalid.status_code)

        with self.app.app_context():
            setor = db.session.get(Setor, self.setor_id)
            self.assertEqual("fila", setor.layout_tv_web)

    def test_tv_config_empty_when_disabled(self):
        with self.app.app_context():
            db.session.add(Propaganda(arquivo="a.jpg", ordem=1, ativo=True))
            db.session.commit()

        response = self.app.test_client().get(
            "/api/v1/setor/tv_config",
            headers={"Authorization": f"Bearer {self._token()}"},
        )
        self.assertEqual(200, response.status_code)
        payload = response.get_json()
        self.assertFalse(payload["propagandas_ativas"])
        self.assertEqual("propaganda", payload["layout_tv_web"])
        self.assertEqual("Balcão", payload["setor_nome"])
        self.assertEqual([], payload["imagens"])
        self.assertEqual(15_000, payload["intervalo_ms"])

    def test_tv_config_lists_only_active_ordered(self):
        with self.app.app_context():
            setor = db.session.get(Setor, self.setor_id)
            setor.propagandas_ativas = True
            imagens = [
                Propaganda(arquivo="c.jpg", ordem=3, ativo=True),
                Propaganda(arquivo="a.jpg", ordem=1, ativo=True),
                Propaganda(arquivo="b.jpg", ordem=2, ativo=False),
            ]
            db.session.add_all(imagens)
            setor.propagandas.extend(imagens)
            db.session.commit()

        response = self.app.test_client().get(
            "/api/v1/setor/tv_config",
            headers={"Authorization": f"Bearer {self._token()}"},
        )
        self.assertEqual(200, response.status_code)
        payload = response.get_json()
        self.assertTrue(payload["propagandas_ativas"])
        arquivos = [i["arquivo"] for i in payload["imagens"]]
        self.assertEqual(["a.jpg", "c.jpg"], arquivos)
        self.assertEqual(15_000, payload["intervalo_ms"])

    def test_admin_vincula_varias_propagandas_a_varios_setores(self):
        client = self._admin_client()

        with self.app.app_context():
            outro = Setor(nome="Caixa", senha_setor="CAIXA", propagandas_ativas=True)
            p1 = Propaganda(arquivo="a.jpg", ordem=1, ativo=True)
            p2 = Propaganda(arquivo="b.jpg", ordem=2, ativo=True)
            exclusiva = Propaganda(arquivo="somente-balcao.jpg", ordem=3, ativo=True)
            exclusiva.setores.append(db.session.get(Setor, self.setor_id))
            db.session.add_all([outro, p1, p2, exclusiva])
            db.session.commit()
            outro_id = outro.id
            propaganda_ids = [p1.id, p2.id]
            outro_token = create_session_token(outro_id, "tv")

        response = client.put(
            "/api/v1/admin/propagandas/setores",
            json={"propaganda_ids": propaganda_ids, "setor_ids": [self.setor_id, outro_id]},
        )
        self.assertEqual(200, response.status_code)
        self.assertEqual(2, response.get_json()["atualizadas"])

        listed = client.get("/api/v1/admin/propagandas").get_json()
        vinculadas = [item for item in listed if item["id"] in propaganda_ids]
        self.assertTrue(all(item["setor_ids"] == [self.setor_id, outro_id] for item in vinculadas))

        response = self.app.test_client().get(
            "/api/v1/setor/tv_config",
            headers={"Authorization": f"Bearer {outro_token}"},
        )
        self.assertEqual(["a.jpg", "b.jpg"], [item["arquivo"] for item in response.get_json()["imagens"]])

    def test_tv_chamadas_recentes_restaura_atual_e_historico_do_setor(self):
        agora = datetime.now()
        with self.app.app_context():
            operador = Operador(nome="Ana", setor_id=self.setor_id)
            outro_setor = Setor(nome="Outro", senha_setor="OUTRO")
            db.session.add_all([operador, outro_setor])
            db.session.flush()

            atual = Senha(
                senha="N12",
                tipo="normal",
                setor_id=self.setor_id,
                status="C",
                chamada_em=agora,
            )
            anterior = Senha(
                senha="P8",
                tipo="preferencial",
                setor_id=self.setor_id,
                status="F",
                chamada_em=agora - timedelta(minutes=5),
                finalizado_em=agora - timedelta(minutes=2),
            )
            externa = Senha(
                senha="N99",
                tipo="normal",
                setor_id=outro_setor.id,
                status="F",
                chamada_em=agora + timedelta(minutes=1),
            )
            db.session.add_all([atual, anterior, externa])
            db.session.flush()
            db.session.add_all(
                [
                    AtendimentoAtual(
                        senha_id=atual.id,
                        setor_id=self.setor_id,
                        operador_id=operador.id,
                        data_hora=agora,
                    ),
                    Finalizado(
                        senha_id=anterior.id,
                        setor_id=self.setor_id,
                        operador_id=operador.id,
                        data_hora=agora - timedelta(minutes=2),
                    ),
                    Finalizado(
                        senha_id=externa.id,
                        setor_id=outro_setor.id,
                        operador_id=operador.id,
                        data_hora=agora + timedelta(minutes=1),
                    ),
                ]
            )
            db.session.commit()

        response = self.app.test_client().get(
            "/api/v1/setor/tv_chamadas_recentes",
            headers={"Authorization": f"Bearer {self._token()}"},
        )
        self.assertEqual(200, response.status_code)
        chamadas = response.get_json()["chamadas"]
        self.assertEqual(["N12", "P8"], [item["senha"] for item in chamadas])
        self.assertEqual(["atual", "finalizada"], [item["status"] for item in chamadas])
        self.assertEqual("Ana", chamadas[0]["operador_nome"])

    def test_tv_chamadas_recentes_exige_papel_tv(self):
        response = self.app.test_client().get(
            "/api/v1/setor/tv_chamadas_recentes",
            headers={"Authorization": f"Bearer {self._token('cliente')}"},
        )
        self.assertEqual(403, response.status_code)

    def test_tv_chamadas_recentes_respeita_limite(self):
        with self.app.app_context():
            operador = Operador(nome="Bia", setor_id=self.setor_id)
            db.session.add(operador)
            db.session.flush()
            for index in range(10):
                senha = Senha(
                    senha=f"N{index + 1}",
                    tipo="normal",
                    setor_id=self.setor_id,
                    status="F",
                    chamada_em=datetime.now() - timedelta(minutes=index),
                )
                db.session.add(senha)
                db.session.flush()
                db.session.add(
                    Finalizado(
                        senha_id=senha.id,
                        setor_id=self.setor_id,
                        operador_id=operador.id,
                    )
                )
            db.session.commit()

            chamadas = listar_chamadas_recentes(self.setor_id, limite=4)
            self.assertEqual(4, len(chamadas))
            self.assertEqual(["N1", "N2", "N3", "N4"], [item["senha"] for item in chamadas])

    @patch("backend.blueprints.admin_api_bp.process_propaganda_image", return_value="promo_tv.jpg")
    def test_admin_upload_propaganda(self, _mock_process):
        client = self._admin_client()

        data = {
            "arquivo": (io.BytesIO(b"fake-image"), "promo.png"),
        }
        response = client.post(
            "/api/v1/admin/propagandas",
            data=data,
            content_type="multipart/form-data",
        )
        self.assertEqual(201, response.status_code, response.get_json())
        payload = response.get_json()
        self.assertEqual("promo_tv.jpg", payload["arquivo"])
        self.assertTrue(payload["ativo"])

        listed = client.get("/api/v1/admin/propagandas")
        self.assertEqual(200, listed.status_code)
        self.assertEqual(1, len(listed.get_json()))


if __name__ == "__main__":
    unittest.main()
