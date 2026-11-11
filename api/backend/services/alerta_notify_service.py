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
    "sem_retirada_recente",
    "sem_chamada",
    "sem_chamada_recente",
)

# Dois grupos na UI: emitir senha × chamar senha.
TIPOS_SEM_EMITIR = frozenset({"sem_retirada", "sem_retirada_recente"})
TIPOS_SEM_CHAMAR = frozenset({"sem_chamada", "sem_chamada_recente"})

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
    """Tipos ativos. Ausência da chave = todos ligados; string vazia = todos desligados."""
    raw = get_configuracao(CFG_TIPOS)
    if raw is None:
        return set(TIPOS_ALERTA_PADRAO)
    raw = raw.strip()
    if not raw:
        return set()
    return {
        parte.strip()
        for parte in raw.split(",")
        if parte.strip() in TIPOS_ALERTA_PADRAO
    }


def tipos_alerta_habilitados() -> set[str]:
    return _tipos_habilitados()


def _somente_digitos(valor: str) -> str:
    return "".join(ch for ch in (valor or "") if ch.isdigit())


def normalizar_telefone_whatsapp(valor: str) -> str:
    digits = _somente_digitos(valor)
    if len(digits) < 10:
        raise ValueError("Informe o telefone com DDI e DDD (somente números)")
    return digits


def listar_contatos_whatsapp(*, apenas_ativos: bool = False) -> list[dict[str, Any]]:
    from backend.models import AlertaWhatsappContato

    q = AlertaWhatsappContato.query.order_by(
        AlertaWhatsappContato.ativo.desc(),
        AlertaWhatsappContato.nome.asc(),
        AlertaWhatsappContato.id.asc(),
    )
    if apenas_ativos:
        q = q.filter_by(ativo=True)
    return [row.to_dict() for row in q.all()]


def destinos_whatsapp_ativos() -> list[str]:
    """Telefones ativos da lista; cai no destino legado se a lista estiver vazia."""
    from backend.models import AlertaWhatsappContato

    rows = (
        AlertaWhatsappContato.query.filter_by(ativo=True)
        .order_by(AlertaWhatsappContato.id.asc())
        .all()
    )
    destinos: list[str] = []
    vistos: set[str] = set()
    for row in rows:
        try:
            telefone = normalizar_telefone_whatsapp(row.telefone or "")
        except ValueError:
            continue
        if telefone in vistos:
            continue
        vistos.add(telefone)
        destinos.append(telefone)
    if destinos:
        return destinos
    legado = _somente_digitos(get_configuracao(CFG_WHATSAPP_DESTINO, "") or "")
    return [legado] if legado else []


def salvar_contato_whatsapp(data: dict[str, Any], *, contato_id: int | None = None) -> dict[str, Any]:
    from backend.models import AlertaWhatsappContato

    agora = agora_sp()

    if contato_id is None:
        nome = str(data.get("nome") or "").strip()
        telefone = normalizar_telefone_whatsapp(str(data.get("telefone") or ""))
        contato = AlertaWhatsappContato(
            nome=nome or telefone,
            telefone=telefone,
            ativo=bool(data.get("ativo", True)),
            criado_em=agora,
            atualizado_em=agora,
        )
        db.session.add(contato)
    else:
        contato = AlertaWhatsappContato.query.get(contato_id)
        if contato is None:
            raise ValueError("Contato não encontrado")
        if "telefone" in data:
            contato.telefone = normalizar_telefone_whatsapp(str(data.get("telefone") or ""))
        if "nome" in data:
            nome = str(data.get("nome") or "").strip()
            contato.nome = nome or contato.telefone
        if "ativo" in data:
            contato.ativo = bool(data.get("ativo"))
        contato.atualizado_em = agora

    db.session.commit()
    return contato.to_dict()


def excluir_contato_whatsapp(contato_id: int) -> None:
    from backend.models import AlertaWhatsappContato

    contato = AlertaWhatsappContato.query.get(contato_id)
    if contato is None:
        raise ValueError("Contato não encontrado")
    db.session.delete(contato)
    db.session.commit()


def _expandir_tipos_grupos(data: dict[str, Any]) -> list[str] | None:
    """Converte os dois toggles da UI (ou lista legada) na lista de tipos internos."""
    if "alerta_sem_emitir" in data or "alerta_sem_chamar" in data:
        tipos: list[str] = []
        if data.get("alerta_sem_emitir"):
            tipos.extend(sorted(TIPOS_SEM_EMITIR))
        if data.get("alerta_sem_chamar"):
            tipos.extend(sorted(TIPOS_SEM_CHAMAR))
        return tipos
    if "tipos" not in data:
        return None
    tipos = data.get("tipos") or []
    if isinstance(tipos, str):
        tipos = [p.strip() for p in tipos.split(",") if p.strip()]
    selecionados = {t for t in tipos if t in TIPOS_ALERTA_PADRAO}
    # Se a UI mandar só o grupo "sem_chamada", inclui também a ociosidade.
    if selecionados & TIPOS_SEM_CHAMAR:
        selecionados |= set(TIPOS_SEM_CHAMAR)
    if selecionados & TIPOS_SEM_EMITIR:
        selecionados |= set(TIPOS_SEM_EMITIR)
    return sorted(selecionados)


def ler_config_alerta() -> dict[str, Any]:
    contatos = listar_contatos_whatsapp()
    ativos = [c["telefone"] for c in contatos if c.get("ativo")]
    tipos = _tipos_habilitados()
    return {
        "telegram_ativo": _truthy(get_configuracao(CFG_TELEGRAM_ATIVO)),
        "telegram_bot_token": get_configuracao(CFG_TELEGRAM_TOKEN, "") or "",
        "telegram_chat_id": get_configuracao(CFG_TELEGRAM_CHAT, "") or "",
        "whatsapp_ativo": _truthy(get_configuracao(CFG_WHATSAPP_ATIVO)),
        # Mantido para compatibilidade; a UI usa a lista de contatos.
        "whatsapp_destino": ativos[0] if ativos else (get_configuracao(CFG_WHATSAPP_DESTINO, "") or ""),
        "whatsapp_contatos": contatos,
        "tipos": sorted(tipos),
        "alerta_sem_emitir": bool(tipos & TIPOS_SEM_EMITIR),
        "alerta_sem_chamar": bool(tipos & TIPOS_SEM_CHAMAR),
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
        # Compatibilidade com clientes antigos: grava no destino legado.
        set_configuracao(CFG_WHATSAPP_DESTINO, str(data.get("whatsapp_destino") or "").strip())
    tipos = _expandir_tipos_grupos(data)
    if tipos is not None:
        # Lista vazia = ambos desligados (não volta ao padrão).
        set_configuracao(CFG_TIPOS, ",".join(tipos))
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
    resp = requests.post(f"{base}/logout", headers=_whatsapp_headers(), timeout=30)
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


def reconnect_whatsapp() -> dict[str, Any]:
    base = (os.getenv("WHATSAPP_SERVICE_URL") or "http://whatsapp:3001").rstrip("/")
    resp = requests.post(f"{base}/reconnect", headers=_whatsapp_headers(), timeout=30)
    if resp.status_code >= 400:
        detalhe = "Falha ao gerar QR"
        try:
            detalhe = resp.json().get("error") or detalhe
        except Exception:
            detalhe = resp.text or detalhe
        raise RuntimeError(detalhe)
    try:
        return resp.json()
    except Exception:
        return status_whatsapp()


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


def enviar_whatsapp_para_contatos(mensagem: str) -> int:
    """Envia para todos os destinos ativos. Levanta se algum falhar após tentar todos."""
    destinos = destinos_whatsapp_ativos()
    if not destinos:
        return 0
    falhas: list[str] = []
    enviados = 0
    for destino in destinos:
        try:
            enviar_whatsapp(mensagem, destino=destino)
            enviados += 1
        except Exception as exc:
            falhas.append(f"{destino}: {exc}")
            logger.exception("Falha ao enviar WhatsApp para %s", destino)
    if falhas and enviados == 0:
        raise RuntimeError("; ".join(falhas))
    if falhas:
        raise RuntimeError(
            f"Enviado para {enviados}/{len(destinos)}; falhas: " + "; ".join(falhas)
        )
    return enviados


def _mensagem_envio(alerta) -> str:
    empresa = (get_configuracao("nome_empresa") or "CompuFlow").strip() or "CompuFlow"
    when = alerta.ocorrido_em.strftime("%d/%m %H:%M") if alerta.ocorrido_em else ""
    prefixo = f"[{empresa}] Alerta"
    if when:
        prefixo = f"{prefixo} · {when}"
    return f"{prefixo}\n{alerta.mensagem}"


def despachar_alertas_pendentes(alerta_ids: Optional[list[int]] = None) -> dict[str, int]:
    """Envia alertas ainda não notificados. Seguro para chamar em paralelo.

    `enviado_*` só vira True após envio bem-sucedido. Canal desligado ou sem
    credencial não marca o flag — assim o alerta ainda pode sair quando o
    canal for reativado ou configurado.
    """
    from backend.models import AlertaLog

    with _envio_lock:
        cfg = ler_config_alerta()
        tipos = set(cfg["tipos"])
        tg_ativo = bool(cfg["telegram_ativo"])
        wa_ativo = bool(cfg["whatsapp_ativo"])
        if not tipos:
            return {"telegram": 0, "whatsapp": 0, "falhas": 0, "avaliados": 0}
        if not tg_ativo and not wa_ativo and not alerta_ids:
            return {"telegram": 0, "whatsapp": 0, "falhas": 0, "avaliados": 0}

        q = AlertaLog.query.filter(AlertaLog.tipo.in_(tipos))
        if alerta_ids:
            q = q.filter(AlertaLog.id.in_(alerta_ids))
        else:
            pendencias = []
            if tg_ativo:
                pendencias.append(AlertaLog.enviado_telegram.is_(False))
            if wa_ativo:
                pendencias.append(AlertaLog.enviado_whatsapp.is_(False))
            if not pendencias:
                return {"telegram": 0, "whatsapp": 0, "falhas": 0, "avaliados": 0}
            q = q.filter(db.or_(*pendencias))
        rows = q.order_by(AlertaLog.id.asc()).limit(100).all()
        enviados_tg = 0
        enviados_wa = 0
        falhas = 0
        alterou = False
        destinos_wa = destinos_whatsapp_ativos() if wa_ativo else []

        for alerta in rows:
            texto = _mensagem_envio(alerta)
            mudou = False
            if tg_ativo and not alerta.enviado_telegram:
                token = cfg["telegram_bot_token"]
                chat = cfg["telegram_chat_id"]
                if token and chat:
                    try:
                        enviar_telegram(texto, token=token, chat_id=chat)
                        alerta.enviado_telegram = True
                        enviados_tg += 1
                        mudou = True
                    except Exception:
                        falhas += 1
                        logger.exception("Falha ao enviar alerta %s no Telegram", alerta.id)
                else:
                    logger.warning(
                        "Telegram ativo sem token/chat_id; alerta %s permanece pendente",
                        alerta.id,
                    )

            if wa_ativo and not alerta.enviado_whatsapp:
                if destinos_wa:
                    # Marca enviado se ao menos um destino receber. Evita reenvio
                    # duplicado aos contatos que já receberam quando outro falha.
                    ok_algum = False
                    for destino in destinos_wa:
                        try:
                            enviar_whatsapp(texto, destino=destino)
                            ok_algum = True
                        except Exception:
                            falhas += 1
                            logger.exception(
                                "Falha ao enviar alerta %s no WhatsApp para %s",
                                alerta.id,
                                destino,
                            )
                    if ok_algum:
                        alerta.enviado_whatsapp = True
                        enviados_wa += 1
                        mudou = True
                else:
                    logger.warning(
                        "WhatsApp ativo sem contatos; alerta %s permanece pendente",
                        alerta.id,
                    )

            if mudou:
                alerta.atualizado_em = agora_sp()
                alterou = True

        if alterou:
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
