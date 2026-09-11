"""Envio de notificações Web Push (VAPID) para o celular do cliente do QR."""
from __future__ import annotations

import json
import os
from typing import Any, Optional

from flask import current_app

from backend.models import Senha


def cliente_acompanhar_url(token: str) -> str:
    from backend.utils import get_notification_url

    return get_notification_url(token)


def enviar_web_push(
    senha: Senha,
    *,
    title: str,
    body: str,
    tag: str,
    require_interaction: bool = False,
    extra: Optional[dict[str, Any]] = None,
) -> bool:
    """Envia push se a senha tiver subscription. Retorna True se enviou."""
    if not senha or not senha.push_subscription:
        return False
    if not senha.token_unico:
        return False

    try:
        subscription = json.loads(senha.push_subscription)
    except (TypeError, ValueError):
        current_app.logger.warning("push_subscription inválida para senha_id=%s", senha.id)
        return False

    payload = {
        "title": title,
        "body": body,
        "icon": "/icon-192.png",
        "badge": "/icon-192.png",
        "tag": tag,
        "requireInteraction": require_interaction,
        "data": {
            "url": f"/acompanhar/{senha.token_unico}",
            "token": senha.token_unico,
            "tag": tag,
            **(extra or {}),
        },
    }

    try:
        from pywebpush import webpush

        email = current_app.config.get("VAPID_EMAIL") or "mailto:admin@appsenhas.local"
        if not str(email).startswith("mailto:"):
            email = f"mailto:{email}"

        webpush(
            subscription_info=subscription,
            data=json.dumps(payload),
            vapid_private_key=current_app.config["VAPID_PRIVATE_KEY"],
            vapid_claims={"sub": email},
        )
        return True
    except ImportError:
        current_app.logger.warning("pywebpush não instalado — push ignorado")
        return False
    except Exception as exc:  # pragma: no cover
        current_app.logger.error("Erro ao enviar Web Push (senha %s): %s", senha.id, exc)
        return False


def push_posicao(senha: Senha, posicao: int, status: str) -> None:
    codigo = senha.senha or ""
    if status == "F" or posicao == -1:
        enviar_web_push(
            senha,
            title="Atendimento finalizado",
            body=f"Senha {codigo}: avalie seu atendimento.",
            tag="senha-finalizada",
            require_interaction=True,
        )
        return
    if status == "C" or posicao == 0:
        # Chamada já notifica em emit_senha_chamada; evita duplicar.
        return
    if 0 < posicao <= 3:
        enviar_web_push(
            senha,
            title="Sua vez está próxima",
            body=f"Senha {codigo}: {posicao} à frente. Fique atento!",
            tag="senha-perto",
            require_interaction=False,
        )


def push_chamada(senha: Senha, operador_nome: str | None = None) -> None:
    quem = f" com {operador_nome}" if operador_nome else ""
    enviar_web_push(
        senha,
        title=f"Senha {senha.senha} chamada!",
        body=f"Dirija-se ao atendimento{quem}.",
        tag="senha-chamada",
        require_interaction=True,
    )


def push_pedido(senha: Senha, mensagem: str) -> None:
    enviar_web_push(
        senha,
        title="Pedido em preparo",
        body=mensagem or f"Seu pedido da senha {senha.senha} está sendo preparado.",
        tag="pedido-status",
        require_interaction=False,
    )


def get_vapid_public_key() -> str:
    return (
        current_app.config.get("VAPID_PUBLIC_KEY")
        or os.getenv("VAPID_PUBLIC_KEY")
        or ""
    )
