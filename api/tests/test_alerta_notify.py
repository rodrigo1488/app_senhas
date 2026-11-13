import unittest
from unittest.mock import patch

from backend import create_app
from backend.extensions import db
from backend.models import AlertaLog, AlertaWhatsappContato, Setor
from backend.services import alerta_notify_service
from backend.services.alerta_notify_service import (
    despachar_alertas_pendentes,
    montar_eventos_equipamento_offline,
    salvar_config_alerta,
    salvar_contato_whatsapp,
    verificar_e_despachar_equipamentos_offline,
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
            alerta_notify_service._visto_online.clear()
            alerta_notify_service._alerta_offline_aberto.clear()

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

    def test_dois_grupos_alerta_habilitam_tipos(self):
        with self.app.app_context():
            so_emitir = salvar_config_alerta(
                {
                    "alerta_sem_emitir": True,
                    "alerta_sem_chamar": False,
                    "alerta_equipamento_offline": False,
                }
            )
            self.assertTrue(so_emitir["alerta_sem_emitir"])
            self.assertFalse(so_emitir["alerta_sem_chamar"])
            self.assertFalse(so_emitir["alerta_equipamento_offline"])
            self.assertEqual(
                ["sem_retirada", "sem_retirada_recente"],
                so_emitir["tipos"],
            )

            so_chamar = salvar_config_alerta(
                {
                    "alerta_sem_emitir": False,
                    "alerta_sem_chamar": True,
                    "alerta_equipamento_offline": False,
                }
            )
            self.assertFalse(so_chamar["alerta_sem_emitir"])
            self.assertTrue(so_chamar["alerta_sem_chamar"])
            self.assertEqual(
                ["sem_chamada", "sem_chamada_recente"],
                so_chamar["tipos"],
            )

            so_equip = salvar_config_alerta(
                {
                    "alerta_sem_emitir": False,
                    "alerta_sem_chamar": False,
                    "alerta_equipamento_offline": True,
                }
            )
            self.assertTrue(so_equip["alerta_equipamento_offline"])
            self.assertEqual(["equipamento_offline"], so_equip["tipos"])

            nenhum = salvar_config_alerta(
                {
                    "alerta_sem_emitir": False,
                    "alerta_sem_chamar": False,
                    "alerta_equipamento_offline": False,
                }
            )
            self.assertEqual([], nenhum["tipos"])
            self.assertFalse(nenhum["alerta_sem_emitir"])
            self.assertFalse(nenhum["alerta_sem_chamar"])
            self.assertFalse(nenhum["alerta_equipamento_offline"])

    def test_alerta_equipamento_offline_envia_whatsapp_uma_vez(self):
        with self.app.app_context():
            salvar_config_alerta(
                {
                    "whatsapp_ativo": True,
                    "alerta_sem_emitir": False,
                    "alerta_sem_chamar": False,
                    "alerta_equipamento_offline": True,
                    "hora_inicio": 0,
                    "hora_fim": 23,
                    "dias": [0, 1, 2, 3, 4, 5, 6],
                    "especial_ativo": False,
                }
            )
            salvar_contato_whatsapp(
                {"nome": "Ops", "telefone": "5511988887777", "ativo": True}
            )

            tv_online = {
                "chave": "setor:1",
                "nome": "Caixa",
                "tipo": "setor",
                "setor_id": self.caixa_id,
                "setor_nome": "Caixa",
            }

            with patch(
                "backend.services.analytics_service._no_expediente",
                return_value=True,
            ), patch(
                "backend.services.streaming_service.listar_tvs_admin",
                return_value=[tv_online],
            ), patch(
                "backend.services.streaming_service.esta_online",
                side_effect=[True, False, False],
            ), patch(
                "backend.services.presenca_service.listar_tablets_presenca",
                return_value=[],
            ), patch(
                "backend.services.alerta_notify_service.enviar_whatsapp"
            ) as wa:
                # 1º ciclo: marca como visto online
                self.assertEqual([], montar_eventos_equipamento_offline())
                # 2º ciclo: cai offline → cria e despacha
                ids = verificar_e_despachar_equipamentos_offline()
                self.assertEqual(1, len(ids))
                self.assertEqual(1, wa.call_count)
                # 3º ciclo: continua offline → não reenvia
                ids2 = verificar_e_despachar_equipamentos_offline()
                self.assertEqual([], ids2)
                self.assertEqual(1, wa.call_count)

            row = db.session.get(AlertaLog, ids[0])
            self.assertEqual("equipamento_offline", row.tipo)
            self.assertTrue(row.enviado_whatsapp)
            self.assertIn("Caixa", row.mensagem)
            self.assertIn("offline", row.mensagem.lower())

    def test_salva_periodo_e_dias_monitoramento(self):
        with self.app.app_context():
            padrao = salvar_config_alerta({})
            self.assertEqual(7, padrao["hora_inicio"])
            self.assertEqual(21, padrao["hora_fim"])
            self.assertEqual([0, 1, 2, 3, 4, 5], padrao["dias"])
            self.assertTrue(padrao["especial_ativo"])
            self.assertEqual(8, padrao["especial_hora_inicio"])
            self.assertEqual(12, padrao["especial_hora_fim"])
            self.assertEqual([6], padrao["especial_dias"])
            self.assertTrue(padrao["especial_feriados"])

            salvo = salvar_config_alerta(
                {
                    "hora_inicio": "08:00",
                    "hora_fim": 20,
                    "dias": [0, 2, 4],
                    "especial_ativo": True,
                    "especial_hora_inicio": 9,
                    "especial_hora_fim": "14:30",
                    "especial_dias": [6],
                    "especial_feriados": False,
                }
            )
            self.assertEqual(8, salvo["hora_inicio"])
            self.assertEqual(20, salvo["hora_fim"])
            self.assertEqual([0, 2, 4], salvo["dias"])
            self.assertEqual(9, salvo["especial_hora_inicio"])
            self.assertEqual(14, salvo["especial_hora_fim"])
            self.assertEqual([6], salvo["especial_dias"])
            self.assertFalse(salvo["especial_feriados"])

            with self.assertRaises(ValueError):
                salvar_config_alerta({"hora_inicio": 10, "hora_fim": 10})

    def test_atualiza_contato_sem_telefone_nao_exige_numero(self):
        with self.app.app_context():
            criado = salvar_contato_whatsapp(
                {"nome": "Principal", "telefone": "5511999999999", "ativo": True}
            )
            atualizado = salvar_contato_whatsapp(
                {"nome": "Gerência", "ativo": False},
                contato_id=criado["id"],
            )
            self.assertEqual("Gerência", atualizado["nome"])
            self.assertEqual("5511999999999", atualizado["telefone"])
            self.assertFalse(atualizado["ativo"])
