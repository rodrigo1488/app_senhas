import io
import unittest
from datetime import datetime, timedelta
from unittest.mock import patch

from backend import create_app
from backend.auth import create_session_token
from backend.extensions import db
from backend.models import AtendimentoAtual, Finalizado, Operador, Propaganda, Senha, Setor, TvDispositivo
from backend.services.fila_service import listar_chamadas_recentes
from backend.services.streaming_service import chave_by_sid, connected_by_chave
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
        connected_by_chave.clear()
        chave_by_sid.clear()
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
        self.assertTrue(all(i.get("tipo") == "image" for i in payload["imagens"]))
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

        with self.app.app_context():
            setor = db.session.get(Setor, self.setor_id)
            self.assertTrue(setor.propagandas_ativas)

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
        self.assertEqual("image", payload["tipo"])
        self.assertTrue(payload["ativo"])

        listed = client.get("/api/v1/admin/propagandas")
        self.assertEqual(200, listed.status_code)
        self.assertEqual(1, len(listed.get_json()))

    @patch("backend.blueprints.admin_api_bp.save_propaganda_video", return_value="promo.mp4")
    def test_admin_upload_video_mp4(self, _mock_save):
        client = self._admin_client()
        response = client.post(
            "/api/v1/admin/propagandas",
            data={"arquivo": (io.BytesIO(b"fake-mp4"), "promo.mp4")},
            content_type="multipart/form-data",
        )
        self.assertEqual(201, response.status_code, response.get_json())
        payload = response.get_json()
        self.assertEqual("promo.mp4", payload["arquivo"])
        self.assertEqual("video", payload["tipo"])

    def test_admin_rejeita_video_nao_mp4(self):
        client = self._admin_client()
        response = client.post(
            "/api/v1/admin/propagandas",
            data={"arquivo": (io.BytesIO(b"fake-avi"), "promo.avi")},
            content_type="multipart/form-data",
        )
        self.assertEqual(400, response.status_code)

    @patch("backend.blueprints.admin_api_bp.process_propaganda_image", side_effect=["a.jpg", "b.jpg"])
    @patch("backend.blueprints.admin_api_bp.save_propaganda_video", return_value="c.mp4")
    def test_admin_upload_varias_midias_de_uma_vez(self, _mock_video, _mock_image):
        client = self._admin_client()
        response = client.post(
            "/api/v1/admin/propagandas",
            data={
                "arquivo": [
                    (io.BytesIO(b"img-a"), "a.png"),
                    (io.BytesIO(b"img-b"), "b.png"),
                    (io.BytesIO(b"vid"), "c.mp4"),
                ]
            },
            content_type="multipart/form-data",
        )
        self.assertEqual(201, response.status_code, response.get_json())
        payload = response.get_json()
        self.assertEqual(3, payload["criadas"])
        self.assertEqual(["a.jpg", "b.jpg", "c.mp4"], [item["arquivo"] for item in payload["itens"]])
        self.assertEqual(["image", "image", "video"], [item["tipo"] for item in payload["itens"]])

        listed = client.get("/api/v1/admin/propagandas").get_json()
        self.assertEqual(3, len(listed))
        self.assertEqual([1, 2, 3], [item["ordem"] for item in listed])

    @patch("backend.blueprints.admin_api_bp.save_propaganda_video", return_value="promo.mp4")
    def test_admin_rejeita_video_grande(self, _mock_save):
        client = self._admin_client()
        with self.app.app_context():
            original = self.app.config["MAX_VIDEO_SIZE"]
            self.app.config["MAX_VIDEO_SIZE"] = 8
        try:
            response = client.post(
                "/api/v1/admin/propagandas",
                data={"arquivo": (io.BytesIO(b"0123456789"), "promo.mp4")},
                content_type="multipart/form-data",
            )
        finally:
            with self.app.app_context():
                self.app.config["MAX_VIDEO_SIZE"] = original
        self.assertEqual(400, response.status_code)

    @patch("backend.blueprints.admin_api_bp.save_propaganda_video", return_value="promo.mp4")
    def test_admin_upload_video_direciona_tvs_e_liga_propagandas(self, _mock_save):
        client = self._admin_client()
        response = client.post(
            "/api/v1/admin/propagandas",
            data={
                "arquivo": (io.BytesIO(b"fake-mp4"), "promo.mp4"),
                "setor_ids": f"[{self.setor_id}]",
            },
            content_type="multipart/form-data",
        )
        self.assertEqual(201, response.status_code, response.get_json())
        payload = response.get_json()
        self.assertEqual([self.setor_id], payload["setor_ids"])

        with self.app.app_context():
            setor = db.session.get(Setor, self.setor_id)
            self.assertTrue(setor.propagandas_ativas)

        tv = self.app.test_client().get(
            "/api/v1/setor/tv_config",
            headers={"Authorization": f"Bearer {self._token()}"},
        )
        self.assertEqual(200, tv.status_code)
        imagens = tv.get_json()["imagens"]
        self.assertEqual(1, len(imagens))
        self.assertEqual("video", imagens[0]["tipo"])
        self.assertEqual("promo.mp4", imagens[0]["arquivo"])

    def test_streaming_paginas_de_compatibilidade(self):
        client = self.app.test_client()
        self.assertEqual(200, client.get("/smart").status_code)
        self.assertEqual(200, client.get("/legacy").status_code)
        self.assertEqual(200, client.get("/stream").status_code)
        health = client.get("/check_health")
        self.assertEqual(200, health.status_code)
        self.assertEqual("ok", health.get_json()["status"])
        device = client.get("/device_info")
        self.assertEqual(200, device.status_code)
        self.assertIn("ip_address", device.get_json())
        settings = client.get("/api/global_settings")
        self.assertEqual(200, settings.status_code)
        self.assertIn("imageDuration", settings.get_json()["settings"])

    def test_streaming_register_poll_assign_e_poll(self):
        client = self.app.test_client()
        with self.app.app_context():
            p1 = Propaganda(arquivo="a.jpg", tipo="image", ordem=1, ativo=True)
            p2 = Propaganda(arquivo="b.mp4", tipo="video", ordem=2, ativo=True)
            db.session.add_all([p1, p2])
            db.session.commit()

        register = client.post(
            "/api/register_poll",
            json={"ip_address": "10.0.0.8", "device_name": "TV Sala", "nome": "TV Sala"},
        )
        self.assertEqual(200, register.status_code, register.get_json())
        self.assertEqual("ok", register.get_json()["status"])

        with self.app.app_context():
            dispositivo = TvDispositivo.query.filter_by(chave="10.0.0.8").first()
            self.assertIsNotNone(dispositivo)
            self.assertEqual("streaming", dispositivo.tipo)
            self.assertEqual("TV Sala", dispositivo.nome)

        media = client.get("/api/media")
        self.assertEqual(200, media.status_code)
        paths = [item["path"] for item in media.get_json()["files"]]
        self.assertEqual(["/media/a.jpg", "/media/b.mp4"], paths)

        assign = client.post(
            "/api/assign",
            json={
                "ip_address": "10.0.0.8",
                "media_list": [
                    {"path": "/media/a.jpg", "type": "image"},
                    {"path": "/media/b.mp4", "type": "video"},
                ],
            },
        )
        self.assertEqual(200, assign.status_code, assign.get_json())

        poll = client.get("/api/poll/10.0.0.8")
        self.assertEqual(200, poll.status_code)
        queue = poll.get_json()["queue"]
        self.assertEqual(["/media/a.jpg", "/media/b.mp4"], [item["path"] for item in queue])
        self.assertEqual(["image", "video"], [item["type"] for item in queue])

        clients = client.get("/api/clients").get_json()
        self.assertEqual(1, len(clients))
        self.assertTrue(clients[0]["is_online"])
        self.assertEqual("TV Sala", clients[0]["nome"])

    def test_admin_lista_tvs_e_envia_midias_por_tv_e_setor(self):
        admin = self._admin_client()
        public = self.app.test_client()

        with self.app.app_context():
            p1 = Propaganda(arquivo="sala.jpg", tipo="image", ordem=1, ativo=True)
            p2 = Propaganda(arquivo="promo.mp4", tipo="video", ordem=2, ativo=True)
            db.session.add_all([p1, p2])
            db.session.commit()
            p1_id, p2_id = p1.id, p2.id

        listed = admin.get("/api/v1/admin/tvs").get_json()
        setores = [tv for tv in listed if tv["tipo"] == "setor"]
        streaming = [tv for tv in listed if tv["tipo"] == "streaming"]
        self.assertEqual(1, len(setores))
        self.assertEqual("Balcão", setores[0]["nome"])
        self.assertEqual([], streaming)

        public.post(
            "/api/register_poll",
            json={"ip_address": "10.1.0.4", "nome": "TV Recepção"},
        )

        listed = admin.get("/api/v1/admin/tvs").get_json()
        streaming = [tv for tv in listed if tv["tipo"] == "streaming"]
        self.assertEqual(1, len(streaming))
        self.assertEqual("TV Recepção", streaming[0]["nome"])
        tv_id = streaming[0]["id"]

        enviar_streaming = admin.put(
            "/api/v1/admin/tvs/midias",
            json={"tipo": "streaming", "id": tv_id, "propaganda_ids": [p2_id]},
        )
        self.assertEqual(200, enviar_streaming.status_code, enviar_streaming.get_json())
        self.assertEqual([p2_id], enviar_streaming.get_json()["propaganda_ids"])

        poll = public.get("/api/poll/10.1.0.4").get_json()
        self.assertEqual(["/media/promo.mp4"], [item["path"] for item in poll["queue"]])
        self.assertEqual("video", poll["queue"][0]["type"])

        enviar_setor = admin.put(
            "/api/v1/admin/tvs/midias",
            json={"tipo": "setor", "id": self.setor_id, "propaganda_ids": [p1_id]},
        )
        self.assertEqual(200, enviar_setor.status_code, enviar_setor.get_json())

        tv_config = public.get(
            "/api/v1/setor/tv_config",
            headers={"Authorization": f"Bearer {self._token()}"},
        )
        self.assertEqual(200, tv_config.status_code)
        payload = tv_config.get_json()
        self.assertTrue(payload["propagandas_ativas"])
        self.assertEqual(["sala.jpg"], [item["arquivo"] for item in payload["imagens"]])

        with self.app.app_context():
            dispositivo = TvDispositivo.query.filter_by(chave=f"setor:{self.setor_id}").first()
            self.assertIsNotNone(dispositivo)
            self.assertEqual("setor", dispositivo.tipo)

        listed = admin.get("/api/v1/admin/tvs").get_json()
        setor_tv = next(tv for tv in listed if tv["tipo"] == "setor")
        self.assertEqual([p1_id], setor_tv["propaganda_ids"])
        streaming_tv = next(tv for tv in listed if tv["tipo"] == "streaming")
        self.assertEqual([p2_id], streaming_tv["propaganda_ids"])

    def test_apk_tv_streaming_nome_automatico_e_reconexao(self):
        client = self.app.test_client()
        generic = self._token("generic")

        first = client.post(
            "/api/v1/setor/tv_streaming/entrar",
            headers={"Authorization": f"Bearer {generic}"},
            json={"device_id": "tablet-a", "device_name": "Android"},
        )
        self.assertEqual(200, first.status_code, first.get_json())
        body = first.get_json()
        self.assertEqual("Balcão", body["dispositivo"]["nome"])
        self.assertEqual("apk:tablet-a", body["dispositivo"]["chave"])
        self.assertTrue(body["session_token"])

        second_device = client.post(
            "/api/v1/setor/tv_streaming/entrar",
            headers={"Authorization": f"Bearer {generic}"},
            json={"device_id": "tablet-b", "device_name": "Android"},
        )
        self.assertEqual(200, second_device.status_code, second_device.get_json())
        self.assertEqual("2 Balcão", second_device.get_json()["dispositivo"]["nome"])

        again = client.post(
            "/api/v1/setor/tv_streaming/entrar",
            headers={"Authorization": f"Bearer {generic}"},
            json={"device_id": "tablet-a", "device_name": "Android"},
        )
        self.assertEqual(200, again.status_code, again.get_json())
        self.assertEqual("Balcão", again.get_json()["dispositivo"]["nome"])
        self.assertEqual(
            first.get_json()["dispositivo"]["id"],
            again.get_json()["dispositivo"]["id"],
        )

        streaming_token = again.get_json()["session_token"]
        fila = client.get(
            "/api/v1/setor/tv_streaming/fila",
            headers={"Authorization": f"Bearer {streaming_token}"},
        )
        self.assertEqual(200, fila.status_code, fila.get_json())
        self.assertEqual("Balcão", fila.get_json()["dispositivo"]["nome"])
        self.assertEqual([], fila.get_json()["queue"])


if __name__ == "__main__":
    unittest.main()
