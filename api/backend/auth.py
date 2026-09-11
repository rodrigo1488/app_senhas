"""Autenticação da aplicação.

Existem dois mecanismos, propositalmente separados:

1. **Admin (Supabase + sessão Flask)** — usado só pelo painel administrativo em
   `/admin/*`. Mantido como estava (login por e-mail/senha na tabela `users`
   do Supabase), apenas organizado em funções reutilizáveis.

2. **Token de sessão por código de setor (JWT)** — usado pelas telas
   operacionais (cliente, operador, avaliação, TV), tanto nos templates web
   de fallback quanto pelo app Android e pelo handshake do Socket.IO. Substitui
   os cookies soltos `setor_id` / `operador_id` / `end_impressora_local` do
   código legado por um token assinado, com todos os dados necessários.
"""
import time
import uuid
from functools import wraps

import jwt
from flask import current_app, jsonify, redirect, request, session, url_for


# ---------------------------------------------------------------------------
# Admin (Supabase)
# ---------------------------------------------------------------------------

def require_login():
    """Verifica se o admin está logado (sessão ou cookie). Retorna um redirect
    para `/login` se não estiver, ou `None` se estiver autenticado."""
    if "user_id" in session:
        session.permanent = True
        return None

    user_id_cookie = request.cookies.get("user_id")
    if user_id_cookie:
        session["user_id"] = user_id_cookie
        session.permanent = True
        return None

    return redirect(url_for("auth.login"))


def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        auth_result = require_login()
        if auth_result:
            return auth_result
        return view(*args, **kwargs)

    return wrapped


def api_login_required(view):
    """Igual a `login_required`, mas responde 401 JSON (para o painel Next)."""
    @wraps(view)
    def wrapped(*args, **kwargs):
        if "user_id" in session:
            session.permanent = True
            return view(*args, **kwargs)
        user_id_cookie = request.cookies.get("user_id")
        if user_id_cookie:
            session["user_id"] = user_id_cookie
            session.permanent = True
            return view(*args, **kwargs)
        return jsonify({"error": "Não autenticado"}), 401

    return wrapped


# ---------------------------------------------------------------------------
# Token de sessão por código de setor (JWT) — web kiosk + app Android + sockets
# ---------------------------------------------------------------------------

def create_session_token(
    setor_id: int,
    role: str,
    operador_id: int | None = None,
    *,
    purpose: str | None = None,
    ttl_seconds: int | None = None,
    jti: str | None = None,
) -> str:
    """Gera um token de sessão para um setor/papel específico.

    `role` é um dos: "cliente", "operador", "avaliacao", "tv". O backend usa
    papel, operador e propósito para restringir endpoints e rooms.
    """
    now = int(time.time())
    payload = {
        "setor_id": setor_id,
        "role": role,
        "operador_id": operador_id,
        "iat": now,
        "exp": now + (ttl_seconds or current_app.config["SESSION_TOKEN_TTL_SECONDS"]),
    }
    if purpose:
        payload["purpose"] = purpose
    if jti:
        payload["jti"] = jti
    return jwt.encode(payload, current_app.config["SECRET_KEY"], algorithm=current_app.config["JWT_ALGORITHM"])


def create_operator_action_token(setor_id: int, operador_id: int) -> str:
    """Emite uma credencial curta e de uso único para uma chamada."""
    from backend.extensions import db
    from backend.models import Configuracao

    jti = uuid.uuid4().hex
    db.session.add(
        Configuracao(
            chave=f"operator_action_jti:{jti}",
            valor="issued",
            descricao="Token temporário de identificação do operador",
        )
    )
    db.session.commit()
    return create_session_token(
        setor_id,
        role="operador",
        operador_id=operador_id,
        purpose="chamar_proxima",
        ttl_seconds=120,
        jti=jti,
    )


def consume_operator_action_token(payload: dict) -> bool:
    """Consome atomicamente o token; replays deixam de autorizar chamadas."""
    from backend.extensions import db
    from backend.models import Configuracao

    if payload.get("purpose") != "chamar_proxima" or not payload.get("jti"):
        return False
    deleted = Configuracao.query.filter_by(
        chave=f"operator_action_jti:{payload['jti']}",
        valor="issued",
    ).delete(synchronize_session=False)
    db.session.commit()
    return deleted == 1


def decode_session_token(token: str) -> dict | None:
    if not token:
        return None
    try:
        return jwt.decode(token, current_app.config["SECRET_KEY"], algorithms=[current_app.config["JWT_ALGORITHM"]])
    except jwt.PyJWTError:
        return None


def get_bearer_token() -> str | None:
    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        return auth_header[len("Bearer "):]
    return request.args.get("session_token") or request.cookies.get("session_token")


def api_token_required(view):
    """Decorator para rotas REST usadas pelo app Android / web kiosk novo.

    Em caso de sucesso, injeta `session_payload` como kwarg na view.
    """
    @wraps(view)
    def wrapped(*args, **kwargs):
        token = get_bearer_token()
        payload = decode_session_token(token) if token else None
        if not payload:
            return jsonify({"error": "Sessão inválida ou expirada"}), 401
        return view(*args, session_payload=payload, **kwargs)

    return wrapped
