"""Envio de notificações Web Push (VAPID) para o celular do cliente do QR."""
from __future__ import annotations

import base64
import json
import os
import threading
from pathlib import Path
from typing import Any, Optional

from flask import current_app
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ec

from backend.models import Senha

_vapid_lock = threading.Lock()


def _base64url(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).decode("ascii").rstrip("=")


def ensure_vapid_keys() -> tuple[str, str]:
    """Usa chaves do ambiente ou gera um par persistente automaticamente."""
    public_env = (current_app.config.get("VAPID_PUBLIC_KEY") or os.getenv("VAPID_PUBLIC_KEY") or "").strip()
    private_env = (
        current_app.config.get("VAPID_PRIVATE_KEY")
        or os.getenv("VAPID_PRIVATE_KEY")
        or ""
    ).strip()
    if public_env and private_env:
        return public_env, private_env.replace("\\n", "\n")

    instance_dir = Path(current_app.instance_path)
    private_path = instance_dir / "vapid_private.pem"
    public_path = instance_dir / "vapid_public.txt"

    with _vapid_lock:
        instance_dir.mkdir(parents=True, exist_ok=True)
        if private_path.is_file() and public_path.is_file():
            return public_path.read_text(encoding="utf-8").strip(), str(private_path)

        private_key = ec.generate_private_key(ec.SECP256R1())
        private_pem = private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption(),
        )
        public_key = private_key.public_key().public_bytes(
            encoding=serialization.Encoding.X962,
            format=serialization.PublicFormat.UncompressedPoint,
        )

        private_tmp = private_path.with_suffix(".tmp")
        public_tmp = public_path.with_suffix(".tmp")
        private_tmp.write_bytes(private_pem)
        public_tmp.write_text(_base64url(public_key), encoding="utf-8")
        private_tmp.replace(private_path)
        private_path.chmod(0o600)
        public_tmp.replace(public_path)
        current_app.logger.info("Chaves VAPID geradas automaticamente no volume da API.")
        return public_path.read_text(encoding="utf-8").strip(), str(private_path)


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

        _, private_key = ensure_vapid_keys()
        email = current_app.config.get("VAPID_EMAIL") or "mailto:admin@compuflow.local"
        if not str(email).startswith("mailto:"):
            email = f"mailto:{email}"

        webpush(
            subscription_info=subscription,
            data=json.dumps(payload),
            vapid_private_key=private_key,
            vapid_claims={"sub": email},
            ttl=300,
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
    public_key, _ = ensure_vapid_keys()
    return public_key
