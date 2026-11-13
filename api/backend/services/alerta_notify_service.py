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
    "equipamento_offline",
)

# Grupos na UI: emitir senha × chamar senha × equipamento offline.
TIPOS_SEM_EMITIR = frozenset({"sem_retirada", "sem_retirada_recente"})
TIPOS_SEM_CHAMAR = frozenset({"sem_chamada", "sem_chamada_recente"})
TIPOS_EQUIPAMENTO = frozenset({"equipamento_offline"})

# Estado em memória: só alerta quem já esteve online neste processo (evita spam no boot).
_visto_online: set[str] = set()
_alerta_offline_aberto: dict[str, str] = {}

CFG_TELEGRAM_ATIVO = "alerta_telegram_ativo"
CFG_TELEGRAM_TOKEN = "alerta_telegram_bot_token"
CFG_TELEGRAM_CHAT = "alerta_telegram_chat_id"
CFG_WHATSAPP_ATIVO = "alerta_whatsapp_ativo"
CFG_WHATSAPP_DESTINO = "alerta_whatsapp_destino"
CFG_TIPOS = "alerta_notificar_tipos"

# Expediente de monitoramento (padrão: seg–sáb 07–21; domingo/feriados 08–12).
CFG_MON_INICIO = "alerta_monitor_hora_inicio"
CFG_MON_FIM = "alerta_monitor_hora_fim"
CFG_MON_DIAS = "alerta_monitor_dias"
CFG_MON_ESP_ATIVO = "alerta_monitor_especial_ativo"
CFG_MON_ESP_INICIO = "alerta_monitor_especial_hora_inicio"
CFG_MON_ESP_FIM = "alerta_monitor_especial_hora_fim"
CFG_MON_ESP_DIAS = "alerta_monitor_especial_dias"
CFG_MON_ESP_FERIADOS = "alerta_monitor_especial_feriados"

DEFAULT_MON_INICIO = 7
DEFAULT_MON_FIM = 21
DEFAULT_MON_DIAS = (0, 1, 2, 3, 4, 5)  # seg–sáb
DEFAULT_MON_ESP_INICIO = 8
DEFAULT_MON_ESP_FIM = 12
DEFAULT_MON_ESP_DIAS = (6,)  # domingo

_envio_lock = threading.Lock()


def _truthy(value: Optional[str]) -> bool:
    return (value or "").strip().lower() in ("1", "true", "yes", "on", "sim")


def _parse_hora_config(value: Any, default: int) -> int:
    """Aceita 7, '7', '07', '07:00' → hora 0–23."""
    if value is None or value == "":
        return default
    raw = str(value).strip()
    if ":" in raw:
        raw = raw.split(":", 1)[0]
    try:
        hora = int(raw)
    except (TypeError, ValueError):
        return default
    return max(0, min(23, hora))


def _parse_dias_config(value: Any, default: tuple[int, ...]) -> list[int]:
    if value is None:
        return list(default)
    if isinstance(value, (list, tuple, set)):
        partes = list(value)
    else:
        raw = str(value).strip()
        if not raw:
            return []
        partes = [p.strip() for p in raw.replace(";", ",").split(",") if p.strip()]
    dias: list[int] = []
    for parte in partes:
        try:
            dia = int(parte)
        except (TypeError, ValueError):
            continue
        if 0 <= dia <= 6 and dia not in dias:
            dias.append(dia)
    return sorted(dias)


def _hora_alerta_ate(inicio: int, fim: int) -> int:
    if fim <= inicio:
        return inicio
    return fim - 1


def ler_config_monitoramento() -> dict[str, Any]:
    """Janelas e dias usados pelo monitoramento de alertas."""
    hora_inicio = _parse_hora_config(get_configuracao(CFG_MON_INICIO), DEFAULT_MON_INICIO)
    hora_fim = _parse_hora_config(get_configuracao(CFG_MON_FIM), DEFAULT_MON_FIM)
    if hora_fim <= hora_inicio:
        hora_fim = min(23, hora_inicio + 1)

    dias = _parse_dias_config(get_configuracao(CFG_MON_DIAS), DEFAULT_MON_DIAS)

    esp_raw = get_configuracao(CFG_MON_ESP_ATIVO)
    especial_ativo = True if esp_raw is None else _truthy(esp_raw)

    esp_inicio = _parse_hora_config(
        get_configuracao(CFG_MON_ESP_INICIO), DEFAULT_MON_ESP_INICIO
    )
    esp_fim = _parse_hora_config(get_configuracao(CFG_MON_ESP_FIM), DEFAULT_MON_ESP_FIM)
    if esp_fim <= esp_inicio:
        esp_fim = min(23, esp_inicio + 1)

    esp_dias_raw = get_configuracao(CFG_MON_ESP_DIAS)
    especial_dias = _parse_dias_config(
        esp_dias_raw,
        DEFAULT_MON_ESP_DIAS if especial_ativo else (),
    )

    fer_raw = get_configuracao(CFG_MON_ESP_FERIADOS)
    especial_feriados = True if fer_raw is None else _truthy(fer_raw)
    if not especial_ativo:
        especial_dias = []
        especial_feriados = False

    return {
        "hora_inicio": hora_inicio,
        "hora_fim": hora_fim,
        "hora_alerta_ate": _hora_alerta_ate(hora_inicio, hora_fim),
        "dias": dias,
        "especial_ativo": especial_ativo,
        "especial_hora_inicio": esp_inicio,
        "especial_hora_fim": esp_fim,
        "especial_hora_alerta_ate": _hora_alerta_ate(esp_inicio, esp_fim),
        "especial_dias": especial_dias,
        "especial_feriados": especial_feriados,
    }


def _salvar_config_monitoramento(data: dict[str, Any]) -> None:
    keys = (
        "hora_inicio",
        "hora_fim",
        "dias",
        "especial_ativo",
        "especial_hora_inicio",
        "especial_hora_fim",
        "especial_dias",
        "especial_feriados",
    )
    if not any(k in data for k in keys):
        return

    atual = ler_config_monitoramento()
    hora_inicio = _parse_hora_config(data.get("hora_inicio", atual["hora_inicio"]), DEFAULT_MON_INICIO)
    hora_fim = _parse_hora_config(data.get("hora_fim", atual["hora_fim"]), DEFAULT_MON_FIM)
    if hora_fim <= hora_inicio:
        raise ValueError("Horário final do monitoramento deve ser depois do inicial")

    if "dias" in data:
        dias = _parse_dias_config(data.get("dias"), ())
    else:
        dias = list(atual["dias"])

    especial_ativo = (
        bool(data.get("especial_ativo"))
        if "especial_ativo" in data
        else bool(atual["especial_ativo"])
    )
    esp_inicio = _parse_hora_config(
        data.get("especial_hora_inicio", atual["especial_hora_inicio"]),
        DEFAULT_MON_ESP_INICIO,
    )
    esp_fim = _parse_hora_config(
        data.get("especial_hora_fim", atual["especial_hora_fim"]),
        DEFAULT_MON_ESP_FIM,
    )
    if especial_ativo and esp_fim <= esp_inicio:
        raise ValueError("Horário final especial deve ser depois do inicial")

    if "especial_dias" in data:
        especial_dias = _parse_dias_config(data.get("especial_dias"), ())
    else:
        especial_dias = list(atual["especial_dias"])

    especial_feriados = (
        bool(data.get("especial_feriados"))
        if "especial_feriados" in data
        else bool(atual["especial_feriados"])
    )
    if not especial_ativo:
        especial_dias = []
        especial_feriados = False

    set_configuracao(CFG_MON_INICIO, str(hora_inicio))
    set_configuracao(CFG_MON_FIM, str(hora_fim))
    set_configuracao(CFG_MON_DIAS, ",".join(str(d) for d in dias))
    set_configuracao(CFG_MON_ESP_ATIVO, "1" if especial_ativo else "0")
    set_configuracao(CFG_MON_ESP_INICIO, str(esp_inicio))
    set_configuracao(CFG_MON_ESP_FIM, str(esp_fim))
    set_configuracao(CFG_MON_ESP_DIAS, ",".join(str(d) for d in especial_dias))
    set_configuracao(CFG_MON_ESP_FERIADOS, "1" if especial_feriados else "0")


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
    """Converte os toggles da UI (ou lista legada) na lista de tipos internos."""
    if (
        "alerta_sem_emitir" in data
        or "alerta_sem_chamar" in data
        or "alerta_equipamento_offline" in data
    ):
        tipos: list[str] = []
        if data.get("alerta_sem_emitir"):
            tipos.extend(sorted(TIPOS_SEM_EMITIR))
        if data.get("alerta_sem_chamar"):
            tipos.extend(sorted(TIPOS_SEM_CHAMAR))
        if data.get("alerta_equipamento_offline"):
            tipos.extend(sorted(TIPOS_EQUIPAMENTO))
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
    if selecionados & TIPOS_EQUIPAMENTO:
        selecionados |= set(TIPOS_EQUIPAMENTO)
    return sorted(selecionados)


def ler_config_alerta() -> dict[str, Any]:
    contatos = listar_contatos_whatsapp()
    ativos = [c["telefone"] for c in contatos if c.get("ativo")]
    tipos = _tipos_habilitados()
    monitor = ler_config_monitoramento()
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
        "alerta_equipamento_offline": bool(tipos & TIPOS_EQUIPAMENTO),
        "whatsapp_service_url": (
            os.getenv("WHATSAPP_SERVICE_URL") or "http://whatsapp:3001"
        ).rstrip("/"),
        **monitor,
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
    _salvar_config_monitoramento(data)
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


def _rotulo_tipo_equipamento(tipo: str) -> str:
    if tipo == "setor":
        return "Painel de senhas"
    if tipo == "streaming":
        return "TV de streaming"
    if tipo == "tablet":
        return "Tablet"
    return tipo or "Equipamento"


def _listar_estado_equipamentos() -> list[dict[str, Any]]:
    """Snapshot online/offline das TVs (socket) e tablets (presença HTTP)."""
    from backend.services.presenca_service import listar_tablets_presenca
    from backend.services.streaming_service import esta_online, listar_tvs_admin

    itens: list[dict[str, Any]] = []
    for tv in listar_tvs_admin():
        chave = str(tv.get("chave") or "")
        if not chave:
            continue
        itens.append(
            {
                "chave_dispositivo": f"tv:{chave}",
                "online": bool(esta_online(chave)),
                "nome": (tv.get("nome") or chave).strip() or chave,
                "tipo": tv.get("tipo") or "streaming",
                "setor_id": tv.get("setor_id"),
                "setor_nome": tv.get("setor_nome"),
                "extra": None,
            }
        )

    for tablet in listar_tablets_presenca():
        device_id = tablet["device_id"]
        papel = tablet["papel_rotulo"]
        nome = tablet.get("nome") or f"Tablet {papel}"
        itens.append(
            {
                "chave_dispositivo": f"tablet:{device_id}",
                "online": bool(tablet.get("is_online")),
                "nome": nome,
                "tipo": "tablet",
                "setor_id": tablet.get("setor_id"),
                "setor_nome": tablet.get("setor_nome"),
                "extra": papel,
            }
        )
    return itens


def montar_eventos_equipamento_offline() -> list[dict[str, Any]]:
    """Detecta transição online→offline e monta eventos de AlertaLog.

    Só alerta equipamentos já vistos online neste processo (evita falso positivo
    após reinício da API). Um episódio offline gera uma única chave até voltar.
    """
    from backend.services.analytics_service import _no_expediente

    if "equipamento_offline" not in _tipos_habilitados():
        return []

    agora = agora_sp()
    if not _no_expediente(agora):
        return []

    eventos: list[dict[str, Any]] = []
    for item in _listar_estado_equipamentos():
        chave_disp = item["chave_dispositivo"]
        online = bool(item["online"])
        if online:
            _visto_online.add(chave_disp)
            _alerta_offline_aberto.pop(chave_disp, None)
            continue
        if chave_disp not in _visto_online:
            continue
        chave_alerta = _alerta_offline_aberto.get(chave_disp)
        if chave_alerta:
            continue

        ocorrido = agora
        chave_alerta = (
            f"equipamento_offline:{chave_disp}:{ocorrido.strftime('%Y%m%d%H%M%S')}"
        )
        _alerta_offline_aberto[chave_disp] = chave_alerta

        tipo_eq = _rotulo_tipo_equipamento(str(item.get("tipo") or ""))
        nome = item.get("nome") or chave_disp
        partes = [f"Equipamento offline: {nome} ({tipo_eq})"]
        if item.get("extra"):
            partes[0] = f"Equipamento offline: {nome} ({tipo_eq} · {item['extra']})"
        setor_nome = (item.get("setor_nome") or "").strip()
        if setor_nome:
            partes.append(f"Setor {setor_nome}")
        partes.append("Verifique energia e conexão.")
        eventos.append(
            {
                "chave": chave_alerta,
                "tipo": "equipamento_offline",
                "severidade": "critical",
                "mensagem": " · ".join(partes),
                "setor_id": item.get("setor_id"),
                "ocorrido_em": ocorrido,
            }
        )
    return eventos


def verificar_e_despachar_equipamentos_offline() -> list[int]:
    """Gera logs de equipamentos que acabaram de ficar offline e despacha."""
    from backend.services.analytics_service import registrar_logs_alerta

    eventos = montar_eventos_equipamento_offline()
    if not eventos:
        return []
    novos_ids = registrar_logs_alerta(eventos)
    if novos_ids:
        despachar_alertas_pendentes(novos_ids)
    return novos_ids


def gerar_e_despachar_alertas_hoje() -> dict[str, Any]:
    from backend.services.analytics_service import montar_analytics

    hoje = agora_sp().date().isoformat()
    montar_analytics(from_s=hoje, to_s=hoje)
    offline_ids = verificar_e_despachar_equipamentos_offline()
    envio = despachar_alertas_pendentes()
    return {"dia": hoje, "equipamentos_offline": len(offline_ids), **envio}


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
