import unittest

from backend import create_app
from backend.extensions import db
from backend.models import Operador, Setor
from backend.services.fila_service import chamar_proxima, criar_senha, posicao_na_fila
from backend.utils import set_configuracao


class SequenciaChamadaTest(unittest.TestCase):
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
            setor = Setor(nome="Balcão", senha_setor="SETOR")
            db.session.add(setor)
            db.session.commit()
            self.setor_id = setor.id
            operador = Operador(nome="Ana", setor_id=setor.id)
            db.session.add(operador)
            db.session.commit()
            self.operador_id = operador.id

    def _codigos_chamados(self, quantidade: int) -> list[str]:
        codigos = []
        for _ in range(quantidade):
            resultado = chamar_proxima(self.setor_id, self.operador_id)
            self.assertIsNotNone(resultado.senha)
            codigos.append(resultado.senha.senha)
        return codigos

    def test_proporcao_intercala_duas_normais_e_uma_preferencial(self):
        with self.app.app_context():
            set_configuracao("modo_chamada", "proporcao")
            set_configuracao("proporcao_normais", "2")
            criar_senha(self.setor_id, "normal")
            criar_senha(self.setor_id, "normal")
            criar_senha(self.setor_id, "preferencial")
            criar_senha(self.setor_id, "preferencial")
            criar_senha(self.setor_id, "normal")

            self.assertEqual(["N1", "N2", "P1", "N3", "P2"], self._codigos_chamados(5))

    def test_preferencial_primeiro_esgota_preferenciais(self):
        with self.app.app_context():
            set_configuracao("modo_chamada", "preferencial_primeiro")
            criar_senha(self.setor_id, "normal")
            criar_senha(self.setor_id, "normal")
            criar_senha(self.setor_id, "preferencial")
            criar_senha(self.setor_id, "preferencial")
            criar_senha(self.setor_id, "normal")

            self.assertEqual(["P1", "P2", "N1", "N2", "N3"], self._codigos_chamados(5))

    def test_posicao_acompanha_modo_proporcao(self):
        with self.app.app_context():
            set_configuracao("modo_chamada", "proporcao")
            set_configuracao("proporcao_normais", "2")
            n1 = criar_senha(self.setor_id, "normal")
            n2 = criar_senha(self.setor_id, "normal")
            p1 = criar_senha(self.setor_id, "preferencial")
            p2 = criar_senha(self.setor_id, "preferencial")

            self.assertEqual(0, posicao_na_fila(n1.token_unico)["posicao"])
            self.assertEqual(1, posicao_na_fila(n2.token_unico)["posicao"])
            self.assertEqual(2, posicao_na_fila(p1.token_unico)["posicao"])
            self.assertEqual(3, posicao_na_fila(p2.token_unico)["posicao"])

    def test_admin_salva_modo_chamada(self):
        with self.app.app_context():
            from backend import _migrate_usuario_papeis
            from backend.services.usuario_service import criar_ou_atualizar_admin

            _migrate_usuario_papeis()
            admin = criar_ou_atualizar_admin("admin@test.local", "admin123")
            admin_id = admin.id

        client = self.app.test_client()
        with client.session_transaction() as sess:
            sess["user_id"] = admin_id

        resp = client.put(
            "/api/v1/admin/configuracao/fila",
            json={
                "modo_chamada": "preferencial_primeiro",
                "proporcao_normais": "2",
                "limite_preferenciais_alerta": "3",
            },
        )
        self.assertEqual(200, resp.status_code)
        self.assertEqual("preferencial_primeiro", resp.get_json()["modo_chamada"])

        get_resp = client.get("/api/v1/admin/configuracao")
        self.assertEqual("preferencial_primeiro", get_resp.get_json()["modo_chamada"])


if __name__ == "__main__":
    unittest.main()
