"""Envio de alertas do expediente para Telegram e WhatsApp (Baileys)."""
from __future__ import annotations

import logging
import os
import threading
from typing import Any, Optional

import requests

from backend.extensions import db
from backend.timezone import agora_sp
from backend.utils import get_configuracao, set_configuracao

logger = logging.getLogger(__name__)

TIPOS_ALERTA_PADRAO = (
    "sem_retirada",
    "sem_chamada",
    "sem_chamada_recente",
)

CFG_TELEGRAM_ATIVO = "alerta_telegram_ativo"
CFG_TELEGRAM_TOKEN = "alerta_telegram_bot_token"
CFG_TELEGRAM_CHAT = "alerta_telegram_chat_id"
CFG_WHATSAPP_ATIVO = "alerta_whatsapp_ativo"
CFG_WHATSAPP_DESTINO = "alerta_whatsapp_destino"
CFG_TIPOS = "alerta_notificar_tipos"

_envio_lock = threading.Lock()


def _truthy(value: Optional[str]) -> bool:
    return (value or "").strip().lower() in ("1", "true", "yes", "on", "sim")


def _tipos_habilitados() -> set[str]:
    raw = (get_configuracao(CFG_TIPOS) or ",".join(TIPOS_ALERTA_PADRAO)).strip()
    if not raw:
        return set(TIPOS_ALERTA_PADRAO)
    return {parte.strip() for parte in raw.split(",") if parte.strip()}


def ler_config_alerta() -> dict[str, Any]:
    return {
        "telegram_ativo": _truthy(get_configuracao(CFG_TELEGRAM_ATIVO)),
        "telegram_bot_token": get_configuracao(CFG_TELEGRAM_TOKEN, "") or "",
        "telegram_chat_id": get_configuracao(CFG_TELEGRAM_CHAT, "") or "",
        "whatsapp_ativo": _truthy(get_configuracao(CFG_WHATSAPP_ATIVO)),
        "whatsapp_destino": get_configuracao(CFG_WHATSAPP_DESTINO, "") or "",
        "tipos": sorted(_tipos_habilitados()),
        "whatsapp_service_url": (
            os.getenv("WHATSAPP_SERVICE_URL") or "http://whatsapp:3001"
        ).rstrip("/"),
    }


def salvar_config_alerta(data: dict[str, Any]) -> dict[str, Any]:
    set_configuracao(CFG_TELEGRAM_ATIVO, "1" if data.get("telegram_ativo") else "0")
    if "telegram_bot_token" in data:
        set_configuracao(CFG_TELEGRAM_TOKEN, str(data.get("telegram_bot_token") or "").strip())
    if "telegram_chat_id" in data:
        set_configuracao(CFG_TELEGRAM_CHAT, str(data.get("telegram_chat_id") or "").strip())
    set_configuracao(CFG_WHATSAPP_ATIVO, "1" if data.get("whatsapp_ativo") else "0")
    if "whatsapp_destino" in data:
        set_configuracao(CFG_WHATSAPP_DESTINO, str(data.get("whatsapp_destino") or "").strip())
    if "tipos" in data:
        tipos = data.get("tipos") or []
        if isinstance(tipos, str):
            tipos = [p.strip() for p in tipos.split(",") if p.strip()]
        limpos = [t for t in tipos if t in TIPOS_ALERTA_PADRAO]
        set_configuracao(CFG_TIPOS, ",".join(limpos) if limpos else ",".join(TIPOS_ALERTA_PADRAO))
    return ler_config_alerta()


def _whatsapp_headers() -> dict[str, str]:
    token = (os.getenv("WHATSAPP_INTERNAL_TOKEN") or "").strip()
    headers = {"Content-Type": "application/json"}
    if token:
        headers["X-Internal-Token"] = token
    return headers


def status_whatsapp() -> dict[str, Any]:
    base = (os.getenv("WHATSAPP_SERVICE_URL") or "http://whatsapp:3001").rstrip("/")
    try:
        resp = requests.get(f"{base}/status", headers=_whatsapp_headers(), timeout=8)
        if resp.status_code >= 400:
            return {
                "status": "error",
                "connected": False,
                "error": resp.json().get("error") if resp.headers.get("content-type", "").startswith("application/json") else resp.text,
            }
        return resp.json()
    except Exception as exc:
        return {"status": "unreachable", "connected": False, "error": str(exc)}


def logout_whatsapp() -> dict[str, Any]:
    base = (os.getenv("WHATSAPP_SERVICE_URL") or "http://whatsapp:3001").rstrip("/")
    resp = requests.post(f"{base}/logout", headers=_whatsapp_headers(), timeout=15)
    if resp.status_code >= 400:
        detalhe = "Falha no logout"
        try:
            detalhe = resp.json().get("error") or detalhe
        except Exception:
            detalhe = resp.text or detalhe
        raise RuntimeError(detalhe)
    try:
        return resp.json()
    except Exception:
        return {"ok": True}


def enviar_telegram(mensagem: str, *, token: str, chat_id: str) -> None:
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    resp = requests.post(
        url,
        json={"chat_id": chat_id, "text": mensagem, "disable_web_page_preview": True},
        timeout=15,
    )
    if resp.status_code >= 400:
        detalhe = resp.text
        try:
            detalhe = resp.json()
        except Exception:
            pass
        raise RuntimeError(f"Telegram HTTP {resp.status_code}: {detalhe}")


def enviar_whatsapp(mensagem: str, *, destino: str) -> None:
    base = (os.getenv("WHATSAPP_SERVICE_URL") or "http://whatsapp:3001").rstrip("/")
    resp = requests.post(
        f"{base}/send",
        headers=_whatsapp_headers(),
        json={"to": destino, "text": mensagem},
        timeout=30,
    )
    if resp.status_code >= 400:
        detalhe = resp.text
        try:
            detalhe = resp.json().get("error") or resp.json()
        except Exception:
            pass
        raise RuntimeError(f"WhatsApp HTTP {resp.status_code}: {detalhe}")


def _mensagem_envio(alerta) -> str:
    empresa = (get_configuracao("nome_empresa") or "CompuFlow").strip() or "CompuFlow"
    when = alerta.ocorrido_em.strftime("%d/%m %H:%M") if alerta.ocorrido_em else ""
    prefixo = f"[{empresa}] Alerta"
    if when:
        prefixo = f"{prefixo} · {when}"
    return f"{prefixo}\n{alerta.mensagem}"


def despachar_alertas_pendentes(alerta_ids: Optional[list[int]] = None) -> dict[str, int]:
    """Envia alertas ainda não notificados. Seguro para chamar em paralelo."""
    from backend.models import AlertaLog

    with _envio_lock:
        cfg = ler_config_alerta()
        tipos = set(cfg["tipos"])
        q = AlertaLog.query.filter(AlertaLog.tipo.in_(tipos or TIPOS_ALERTA_PADRAO))
        if alerta_ids:
            q = q.filter(AlertaLog.id.in_(alerta_ids))
        else:
            q = q.filter(
                db.or_(
                    AlertaLog.enviado_telegram.is_(False),
                    AlertaLog.enviado_whatsapp.is_(False),
                )
            )
        rows = q.order_by(AlertaLog.id.asc()).limit(100).all()
        enviados_tg = 0
        enviados_wa = 0
        falhas = 0

        for alerta in rows:
            texto = _mensagem_envio(alerta)
            if cfg["telegram_ativo"] and not alerta.enviado_telegram:
                token = cfg["telegram_bot_token"]
                chat = cfg["telegram_chat_id"]
                if token and chat:
                    try:
                        enviar_telegram(texto, token=token, chat_id=chat)
                        alerta.enviado_telegram = True
                        enviados_tg += 1
                    except Exception:
                        falhas += 1
                        logger.exception("Falha ao enviar alerta %s no Telegram", alerta.id)
                else:
                    alerta.enviado_telegram = True
            elif not cfg["telegram_ativo"] and not alerta.enviado_telegram:
                alerta.enviado_telegram = True

            if cfg["whatsapp_ativo"] and not alerta.enviado_whatsapp:
                destino = cfg["whatsapp_destino"]
                if destino:
                    try:
                        enviar_whatsapp(texto, destino=destino)
                        alerta.enviado_whatsapp = True
                        enviados_wa += 1
                    except Exception:
                        falhas += 1
                        logger.exception("Falha ao enviar alerta %s no WhatsApp", alerta.id)
                else:
                    alerta.enviado_whatsapp = True
            elif not cfg["whatsapp_ativo"] and not alerta.enviado_whatsapp:
                alerta.enviado_whatsapp = True

            alerta.atualizado_em = agora_sp()

        if rows:
            db.session.commit()
        return {"telegram": enviados_tg, "whatsapp": enviados_wa, "falhas": falhas, "avaliados": len(rows)}


def gerar_e_despachar_alertas_hoje() -> dict[str, Any]:
    from backend.services.analytics_service import montar_analytics

    hoje = agora_sp().date().isoformat()
    montar_analytics(from_s=hoje, to_s=hoje)
    envio = despachar_alertas_pendentes()
    return {"dia": hoje, **envio}


def iniciar_rotina_alertas(app) -> None:
    if app.config.get("TESTING"):
        return
    from backend.extensions import socketio

    socketio.start_background_task(_loop_alertas, app)


def _loop_alertas(app) -> None:
    from backend.extensions import socketio

    # Aguarda o boot estabilizar antes do primeiro ciclo.
    socketio.sleep(20)
    while True:
        with app.app_context():
            try:
                gerar_e_despachar_alertas_hoje()
            except Exception:
                app.logger.exception("Falha na rotina de alertas")
                try:
                    db.session.rollback()
                except Exception:
                    pass
        socketio.sleep(60)
