import unittest
from unittest.mock import patch

from backend import create_app
from backend.extensions import db
from backend.models import AlertaLog, AlertaWhatsappContato, Setor
from backend.services.alerta_notify_service import (
    despachar_alertas_pendentes,
    salvar_config_alerta,
)
from backend.services.usuario_service import criar_ou_atualizar_admin
from backend.timezone import agora_sp


class AlertaNotifyTest(unittest.TestCase):
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
            db.session.add(caixa)
            db.session.commit()
            self.caixa_id = caixa.id

    def test_despacha_telegram_e_whatsapp_uma_vez(self):
        with self.app.app_context():
            salvar_config_alerta(
                {
                    "telegram_ativo": True,
                    "telegram_bot_token": "token",
                    "telegram_chat_id": "123",
                    "whatsapp_ativo": True,
                    "whatsapp_destino": "5511999999999",
                    "tipos": ["sem_chamada"],
                }
            )
            agora = agora_sp()
            log = AlertaLog(
                chave="sem_chamada:1:2026-11-10:07",
                tipo="sem_chamada",
                severidade="warning",
                mensagem="Caixa: horário 07h sem chamada de senha.",
                setor_id=self.caixa_id,
                ocorrido_em=agora,
                enviado_telegram=False,
                enviado_whatsapp=False,
            )
            db.session.add(log)
            db.session.commit()
            alerta_id = log.id

            with patch(
                "backend.services.alerta_notify_service.enviar_telegram"
            ) as tg, patch(
                "backend.services.alerta_notify_service.enviar_whatsapp"
            ) as wa:
                primeiro = despachar_alertas_pendentes([alerta_id])
                segundo = despachar_alertas_pendentes([alerta_id])

            self.assertEqual(1, primeiro["telegram"])
            self.assertEqual(1, primeiro["whatsapp"])
            self.assertEqual(0, segundo["telegram"])
            self.assertEqual(0, segundo["whatsapp"])
            self.assertEqual(1, tg.call_count)
            self.assertEqual(1, wa.call_count)

            row = db.session.get(AlertaLog, alerta_id)
            self.assertTrue(row.enviado_telegram)
            self.assertTrue(row.enviado_whatsapp)

    def test_canal_desligado_nao_marca_enviado_e_reativa_envia(self):
        with self.app.app_context():
            salvar_config_alerta(
                {
                    "telegram_ativo": False,
                    "telegram_bot_token": "token",
                    "telegram_chat_id": "123",
                    "whatsapp_ativo": False,
                    "whatsapp_destino": "5511999999999",
                    "tipos": ["sem_chamada"],
                }
            )
            log = AlertaLog(
                chave="sem_chamada:1:2026-11-10:08",
                tipo="sem_chamada",
                severidade="warning",
                mensagem="Caixa: horário 08h sem chamada de senha.",
                setor_id=self.caixa_id,
                ocorrido_em=agora_sp(),
                enviado_telegram=False,
                enviado_whatsapp=False,
            )
            db.session.add(log)
            db.session.commit()
            alerta_id = log.id

            with patch(
                "backend.services.alerta_notify_service.enviar_telegram"
            ) as tg, patch(
                "backend.services.alerta_notify_service.enviar_whatsapp"
            ) as wa:
                parado = despachar_alertas_pendentes([alerta_id])
                self.assertEqual(0, parado["telegram"])
                self.assertEqual(0, parado["whatsapp"])
                self.assertEqual(0, tg.call_count)
                self.assertEqual(0, wa.call_count)

                row = db.session.get(AlertaLog, alerta_id)
                self.assertFalse(row.enviado_telegram)
                self.assertFalse(row.enviado_whatsapp)

                salvar_config_alerta(
                    {
                        "telegram_ativo": True,
                        "telegram_bot_token": "token",
                        "telegram_chat_id": "123",
                        "whatsapp_ativo": True,
                        "whatsapp_destino": "5511999999999",
                        "tipos": ["sem_chamada"],
                    }
                )
                reativado = despachar_alertas_pendentes([alerta_id])

            self.assertEqual(1, reativado["telegram"])
            self.assertEqual(1, reativado["whatsapp"])
            self.assertEqual(1, tg.call_count)
            self.assertEqual(1, wa.call_count)
            row = db.session.get(AlertaLog, alerta_id)
            self.assertTrue(row.enviado_telegram)
            self.assertTrue(row.enviado_whatsapp)

    def test_despacha_whatsapp_para_todos_contatos_ativos(self):
        with self.app.app_context():
            salvar_config_alerta(
                {
                    "telegram_ativo": False,
                    "whatsapp_ativo": True,
                    "tipos": ["sem_chamada"],
                }
            )
            db.session.add_all(
                [
                    AlertaWhatsappContato(nome="A", telefone="5511111111111", ativo=True),
                    AlertaWhatsappContato(nome="B", telefone="5511222222222", ativo=True),
                    AlertaWhatsappContato(nome="C", telefone="5511333333333", ativo=False),
                ]
            )
            log = AlertaLog(
                chave="sem_chamada:1:2026-11-10:09",
                tipo="sem_chamada",
                severidade="warning",
                mensagem="Caixa: horário 09h sem chamada de senha.",
                setor_id=self.caixa_id,
                ocorrido_em=agora_sp(),
                enviado_telegram=False,
                enviado_whatsapp=False,
            )
            db.session.add(log)
            db.session.commit()
            alerta_id = log.id

            with patch(
                "backend.services.alerta_notify_service.enviar_whatsapp"
            ) as wa:
                resultado = despachar_alertas_pendentes([alerta_id])

            self.assertEqual(1, resultado["whatsapp"])
            self.assertEqual(2, wa.call_count)
            destinos = sorted(call.kwargs["destino"] for call in wa.call_args_list)
            self.assertEqual(["5511111111111", "5511222222222"], destinos)
            row = db.session.get(AlertaLog, alerta_id)
            self.assertTrue(row.enviado_whatsapp)

    def test_falha_parcial_whatsapp_nao_reenvia_aos_que_receberam(self):
        with self.app.app_context():
            salvar_config_alerta(
                {
                    "telegram_ativo": False,
                    "whatsapp_ativo": True,
                    "tipos": ["sem_chamada"],
                }
            )
            db.session.add_all(
                [
                    AlertaWhatsappContato(nome="A", telefone="5511111111111", ativo=True),
                    AlertaWhatsappContato(nome="B", telefone="5511222222222", ativo=True),
                ]
            )
            log = AlertaLog(
                chave="sem_chamada:1:2026-11-10:10",
                tipo="sem_chamada",
                severidade="warning",
                mensagem="Caixa: horário 10h sem chamada de senha.",
                setor_id=self.caixa_id,
                ocorrido_em=agora_sp(),
                enviado_telegram=False,
                enviado_whatsapp=False,
            )
            db.session.add(log)
            db.session.commit()
            alerta_id = log.id

            def enviar_parcial(mensagem, *, destino):
                if destino.endswith("2222"):
                    raise RuntimeError("destino indisponível")

            with patch(
                "backend.services.alerta_notify_service.enviar_whatsapp",
                side_effect=enviar_parcial,
            ) as wa:
                primeiro = despachar_alertas_pendentes([alerta_id])
                segundo = despachar_alertas_pendentes([alerta_id])

            self.assertEqual(1, primeiro["whatsapp"])
            self.assertEqual(1, primeiro["falhas"])
            self.assertEqual(0, segundo["whatsapp"])
            self.assertEqual(0, segundo["falhas"])
            # 1º ciclo tenta os 2 contatos; 2º não reenvia porque já marcou enviado.
            self.assertEqual(2, wa.call_count)
            row = db.session.get(AlertaLog, alerta_id)
            self.assertTrue(row.enviado_whatsapp)
