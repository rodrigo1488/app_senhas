import unittest
from datetime import datetime, timedelta

from backend import create_app
from backend.auth import create_session_token
from backend.extensions import db
from backend.models import Operador, Propaganda, Senha, Setor, TvDispositivo, TIPO_SETOR_STREAMING
from backend.services.analytics_service import montar_analytics
from backend.services.usuario_service import criar_ou_atualizar_admin


class SetorStreamingTest(unittest.TestCase):
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
            atendimento = Setor(nome="Balcão", senha_setor="SETOR", tipo_setor="atendimento")
            db.session.add(atendimento)
            db.session.commit()
            self.atendimento_id = atendimento.id

    def _admin_client(self):
        client = self.app.test_client()
        with client.session_transaction() as sess:
            sess["user_id"] = self.admin_id
        return client

    def test_persiste_tipo_streaming_e_migra_existentes_como_atendimento(self):
        client = self._admin_client()
        created = client.post(
            "/api/v1/admin/setores",
            json={"nome": "Lobby", "tipo_setor": "streaming", "propagandas_ativas": True},
        )
        self.assertEqual(201, created.status_code, created.get_json())
        payload = created.get_json()
        self.assertEqual("streaming", payload["tipo_setor"])
        self.assertEqual("", payload["senha_setor"])
        self.assertEqual("propaganda", payload["layout_tv_web"])

        listed = client.get("/api/v1/admin/setores").get_json()
        by_id = {item["id"]: item for item in listed}
        self.assertEqual("atendimento", by_id[self.atendimento_id]["tipo_setor"])
        self.assertEqual("streaming", by_id[payload["id"]]["tipo_setor"])

        with self.app.app_context():
            setor = db.session.get(Setor, payload["id"])
            self.assertEqual(TIPO_SETOR_STREAMING, setor.tipo_setor)
            self.assertTrue(setor.propagandas_ativas)

    def test_rejeita_operador_e_impressora_em_setor_streaming(self):
        client = self._admin_client()
        created = client.post("/api/v1/admin/setores", json={"nome": "Mídia", "tipo_setor": "streaming"})
        setor_id = created.get_json()["id"]

        op = client.post(
            "/api/v1/admin/operadores",
            data={"nome": "Ana", "setor_id": str(setor_id)},
            content_type="multipart/form-data",
        )
        self.assertEqual(400, op.status_code)
        self.assertIn("streaming", (op.get_json() or {}).get("error", "").lower())

        imp = client.post(
            "/api/v1/admin/impressoras",
            json={"nome": "Caixa", "ip": "10.0.0.9", "setor_id": setor_id},
        )
        self.assertEqual(400, imp.status_code)

        with self.app.app_context():
            setor = db.session.get(Setor, setor_id)
            db.session.add(Operador(nome="Legacy", setor_id=self.atendimento_id))
            db.session.commit()

        convert = client.put(
            f"/api/v1/admin/setores/{self.atendimento_id}",
            json={"tipo_setor": "streaming"},
        )
        self.assertEqual(400, convert.status_code)

    def test_lista_tvs_agrupa_streaming_e_nao_quebra_tv_config_atendimento(self):
        client = self._admin_client()
        public = self.app.test_client()
        streaming = client.post(
            "/api/v1/admin/setores",
            json={"nome": "Lobby", "tipo_setor": "streaming"},
        ).get_json()
        lobby_id = streaming["id"]

        with self.app.app_context():
            p1 = Propaganda(arquivo="sala.jpg", tipo="image", ordem=1, ativo=True)
            db.session.add(p1)
            setor = db.session.get(Setor, self.atendimento_id)
            setor.propagandas_ativas = True
            db.session.commit()
            p1_id = p1.id

        listed = client.get("/api/v1/admin/tvs").get_json()
        setores_tv = [tv for tv in listed if tv["tipo"] == "setor"]
        self.assertEqual(1, len(setores_tv))
        self.assertEqual("Balcão", setores_tv[0]["nome"])
        self.assertTrue(all(tv["id"] != lobby_id for tv in setores_tv))

        register = public.post(
            "/api/register_poll",
            json={"ip_address": "10.8.0.2", "nome": "TV Lobby", "setor_id": lobby_id},
        )
        self.assertEqual(200, register.status_code, register.get_json())
        self.assertEqual(lobby_id, register.get_json()["setor_id"])

        listed = client.get("/api/v1/admin/tvs").get_json()
        streaming_tvs = [tv for tv in listed if tv["tipo"] == "streaming"]
        self.assertEqual(1, len(streaming_tvs))
        self.assertEqual(lobby_id, streaming_tvs[0]["setor_id"])
        self.assertEqual("Lobby", streaming_tvs[0]["setor_nome"])
        tv_id = streaming_tvs[0]["id"]

        enviar = client.put(
            "/api/v1/admin/tvs/midias",
            json={"tipo": "streaming", "id": tv_id, "propaganda_ids": [p1_id]},
        )
        self.assertEqual(200, enviar.status_code, enviar.get_json())

        avulsa = public.post(
            "/api/register_poll",
            json={"ip_address": "10.8.0.9", "nome": "TV Avulsa"},
        )
        self.assertEqual(200, avulsa.status_code)
        listed = client.get("/api/v1/admin/tvs").get_json()
        avulsas = [tv for tv in listed if tv["tipo"] == "streaming" and not tv.get("setor_id")]
        self.assertEqual(1, len(avulsas))

        enviar_setor = client.put(
            "/api/v1/admin/tvs/midias",
            json={"tipo": "setor", "id": self.atendimento_id, "propaganda_ids": [p1_id]},
        )
        self.assertEqual(200, enviar_setor.status_code, enviar_setor.get_json())

        with self.app.app_context():
            token = create_session_token(self.atendimento_id, "tv")
        tv_config = public.get(
            "/api/v1/setor/tv_config",
            headers={"Authorization": f"Bearer {token}"},
        )
        self.assertEqual(200, tv_config.status_code)
        payload = tv_config.get_json()
        self.assertTrue(payload["propagandas_ativas"])
        self.assertEqual("Balcão", payload["setor_nome"])
        self.assertEqual(["sala.jpg"], [item["arquivo"] for item in payload["imagens"]])

        with self.app.app_context():
            dispositivo = TvDispositivo.query.filter_by(chave=f"setor:{self.atendimento_id}").first()
            self.assertIsNotNone(dispositivo)
            self.assertEqual("setor", dispositivo.tipo)

    def test_fluxo_por_setor_ignora_streaming_e_compara_atendimento(self):
        client = self._admin_client()
        outro = client.post(
            "/api/v1/admin/setores",
            json={"nome": "Farmácia", "tipo_setor": "atendimento", "senha_setor": "FARMA"},
        ).get_json()
        streaming = client.post(
            "/api/v1/admin/setores",
            json={"nome": "Lobby", "tipo_setor": "streaming"},
        ).get_json()

        hoje = datetime(2026, 9, 17, 10, 0, 0)
        with self.app.app_context():
            db.session.add_all(
                [
                    Senha(
                        senha="A001",
                        tipo="normal",
                        setor_id=self.atendimento_id,
                        status="A",
                        token_unico="t-a001",
                        data_hora=hoje,
                    ),
                    Senha(
                        senha="A002",
                        tipo="normal",
                        setor_id=self.atendimento_id,
                        status="A",
                        token_unico="t-a002",
                        data_hora=hoje + timedelta(hours=1),
                    ),
                    Senha(
                        senha="B001",
                        tipo="normal",
                        setor_id=outro["id"],
                        status="A",
                        token_unico="t-b001",
                        data_hora=hoje,
                    ),
                    Senha(
                        senha="X001",
                        tipo="normal",
                        setor_id=streaming["id"],
                        status="A",
                        token_unico="t-x001",
                        data_hora=hoje,
                    ),
                ]
            )
            db.session.commit()

            data = montar_analytics(from_s="2026-09-17", to_s="2026-09-17")

        fluxo = data["fluxo_por_setor"]
        nomes = {item["nome"] for item in fluxo["setores"]}
        self.assertIn("Balcão", nomes)
        self.assertIn("Farmácia", nomes)
        self.assertNotIn("Lobby", nomes)
        self.assertEqual("hora", fluxo["granularidade"])

        chaves = {item["nome"]: item["chave"] for item in fluxo["setores"]}
        por_label = {row["label"]: row for row in fluxo["series"]}
        self.assertEqual(1, por_label["10h"][chaves["Balcão"]])
        self.assertEqual(1, por_label["10h"][chaves["Farmácia"]])
        self.assertEqual(1, por_label["11h"][chaves["Balcão"]])
        self.assertEqual(3, data["kpis"]["emitidas"])
        self.assertTrue(all(row["setor"] != "Lobby" for row in data["por_setor"]))

        filtros = {item["nome"] for item in data["filtros"]["setores"]}
        self.assertNotIn("Lobby", filtros)

    def test_setor_streaming_nao_emite_senha(self):
        with self.app.app_context():
            setor = Setor(nome="Painel", tipo_setor="streaming")
            db.session.add(setor)
            db.session.commit()
            token = create_session_token(setor.id, "cliente")

        response = self.app.test_client().post(
            "/api/v1/senha",
            headers={"Authorization": f"Bearer {token}"},
            json={"tipo": "normal"},
        )
        self.assertEqual(400, response.status_code)
        self.assertIn("streaming", (response.get_json() or {}).get("error", "").lower())


if __name__ == "__main__":
    unittest.main()
