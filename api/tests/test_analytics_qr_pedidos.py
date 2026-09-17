import unittest
from datetime import timedelta

from backend import create_app
from backend.extensions import db
from backend.models import QrScan, Senha, Setor, TIPO_SETOR_STREAMING, TvDispositivo
from backend.services.analytics_service import montar_analytics
from backend.services.fila_service import criar_senha, salvar_pedido, verificar_senha
from backend.services.usuario_service import criar_ou_atualizar_admin
from backend.timezone import agora_sp


class AnalyticsQrPedidosTest(unittest.TestCase):
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
            criar_ou_atualizar_admin("admin@test.local", "admin123")
            caixa = Setor(nome="Caixa", senha_setor="CAIXA")
            farma = Setor(nome="Farmácia", senha_setor="FARMA")
            db.session.add_all([caixa, farma])
            db.session.commit()
            self.caixa_id = caixa.id
            self.farma_id = farma.id

    def _hoje(self) -> str:
        return agora_sp().date().isoformat()

    def _analytics(self, **kwargs):
        params = {"from_s": self._hoje(), "to_s": self._hoje()}
        params.update(kwargs)
        return montar_analytics(**params)

    def test_scan_do_qr_incrementa_na_abertura(self):
        with self.app.app_context():
            senha = criar_senha(self.caixa_id, "normal")
            client = self.app.test_client()

            vazio = self._analytics()
            self.assertEqual(0, vazio["kpis"]["qr_escaneados"])
            self.assertEqual(1, vazio["kpis"]["emitidas"])

            resp = client.get(f"/api/verificar_senha/{senha.token_unico}")
            self.assertEqual(200, resp.status_code)

            dados = self._analytics()
            self.assertEqual(1, dados["kpis"]["qr_escaneados"])
            self.assertEqual(1, dados["por_setor"][0]["qr_escaneados"])

    def test_mesmo_token_nao_conta_scan_duas_vezes(self):
        with self.app.app_context():
            senha = criar_senha(self.caixa_id, "normal")
            client = self.app.test_client()
            url = f"/api/verificar_senha/{senha.token_unico}"
            self.assertEqual(200, client.get(url).status_code)
            self.assertEqual(200, client.get(url).status_code)
            verificar_senha(senha.token_unico)

            self.assertEqual(1, QrScan.query.filter_by(senha_id=senha.id).count())
            self.assertEqual(1, self._analytics()["kpis"]["qr_escaneados"])

    def test_pedido_adiantado_incrementa_e_edicao_nao_duplica(self):
        with self.app.app_context():
            senha = criar_senha(self.caixa_id, "normal")
            client = self.app.test_client()

            self.assertEqual(0, self._analytics()["kpis"]["pedidos_adiantados"])

            resp = client.post(
                f"/api/salvar_pedido/{senha.token_unico}",
                json={"pedido": "Pão na chapa"},
            )
            self.assertEqual(200, resp.status_code)

            primeiro = db.session.get(Senha, senha.id)
            marcado = primeiro.pedido_em
            self.assertTrue(primeiro.tem_pedido)
            self.assertIsNotNone(marcado)

            client.post(
                f"/api/salvar_pedido/{senha.token_unico}",
                json={"pedido": "Pão na chapa sem manteiga"},
            )
            de_novo = db.session.get(Senha, senha.id)
            self.assertEqual(marcado, de_novo.pedido_em)

            dados = self._analytics()
            self.assertEqual(1, dados["kpis"]["pedidos_adiantados"])
            self.assertEqual(1, dados["por_setor"][0]["pedidos_adiantados"])

    def test_filtro_de_periodo_no_scan_e_no_pedido(self):
        with self.app.app_context():
            ontem = agora_sp() - timedelta(days=1)
            senha_scan = criar_senha(self.caixa_id, "normal")
            senha_pedido = criar_senha(self.caixa_id, "normal")
            salvar_pedido(senha_pedido.token_unico, "Café")

            scan = QrScan.query.filter_by(senha_id=senha_scan.id).first()
            self.assertIsNone(scan)
            db.session.add(
                QrScan(senha_id=senha_scan.id, setor_id=self.caixa_id, scanned_at=ontem)
            )
            senha_pedido.pedido_em = ontem
            db.session.commit()

            hoje = self._analytics()
            self.assertEqual(0, hoje["kpis"]["qr_escaneados"])
            self.assertEqual(0, hoje["kpis"]["pedidos_adiantados"])

            ontem_iso = ontem.date().isoformat()
            passado = self._analytics(from_s=ontem_iso, to_s=ontem_iso)
            self.assertEqual(1, passado["kpis"]["qr_escaneados"])
            self.assertEqual(1, passado["kpis"]["pedidos_adiantados"])

    def test_filtro_de_setor_nao_mistura_filas_nem_tv_streaming(self):
        with self.app.app_context():
            s_caixa = criar_senha(self.caixa_id, "normal")
            s_farma = criar_senha(self.farma_id, "normal")
            verificar_senha(s_caixa.token_unico)
            verificar_senha(s_farma.token_unico)
            salvar_pedido(s_caixa.token_unico, "X")
            salvar_pedido(s_farma.token_unico, "Y")
            streaming = Setor(
                nome="TV Hall",
                senha_setor="STREAM",
                tipo_setor=TIPO_SETOR_STREAMING,
            )
            db.session.add(streaming)
            db.session.add(
                TvDispositivo(
                    tipo="streaming",
                    chave="tv-stream-1",
                    nome="TV Propagandas",
                )
            )
            db.session.commit()

            so_caixa = self._analytics(setor_id=self.caixa_id)
            self.assertEqual(1, so_caixa["kpis"]["qr_escaneados"])
            self.assertEqual(1, so_caixa["kpis"]["pedidos_adiantados"])
            self.assertEqual(1, len(so_caixa["por_setor"]))
            self.assertEqual(self.caixa_id, so_caixa["por_setor"][0]["setor_id"])
            self.assertTrue(all(s["id"] != 0 for s in so_caixa["filtros"]["setores"]))
            self.assertEqual(["Caixa"], [s["nome"] for s in so_caixa["filtros"]["setores"]])

            geral = self._analytics()
            self.assertEqual(2, geral["kpis"]["qr_escaneados"])
            self.assertEqual(2, geral["kpis"]["pedidos_adiantados"])
            nomes = {s["nome"] for s in geral["filtros"]["setores"]}
            self.assertEqual({"Caixa", "Farmácia"}, nomes)
            self.assertNotIn("TV Hall", nomes)
            self.assertNotIn("TV Propagandas", nomes)

    def test_analytics_http_expõe_os_kpis(self):
        with self.app.app_context():
            senha = criar_senha(self.caixa_id, "normal")
            client = self.app.test_client()
            client.get(f"/api/verificar_senha/{senha.token_unico}")
            client.post(
                f"/api/salvar_pedido/{senha.token_unico}",
                json={"pedido": "Suco"},
            )
            login = client.post(
                "/api/v1/admin/login",
                json={"email": "admin@test.local", "senha": "admin123"},
            )
            self.assertEqual(200, login.status_code)
            resp = client.get(
                f"/api/v1/admin/analytics?from={self._hoje()}&to={self._hoje()}"
            )
            self.assertEqual(200, resp.status_code)
            kpis = resp.get_json()["kpis"]
            self.assertEqual(1, kpis["qr_escaneados"])
            self.assertEqual(1, kpis["pedidos_adiantados"])


if __name__ == "__main__":
    unittest.main()
