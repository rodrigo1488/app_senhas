"""Escopo de acesso do painel: admin (tudo), gerente (setores) e marketing (mídias)."""
from __future__ import annotations

from functools import wraps

from flask import jsonify, request, session

from backend.extensions import db
from backend.models import Setor, Usuario

PAPEL_ADMIN = "admin"
PAPEL_GERENTE = "gerente"
PAPEL_MARKETING = "marketing"
PAPEIS_VALIDOS = {PAPEL_ADMIN, PAPEL_GERENTE, PAPEL_MARKETING}

# Rotas que o marketing pode usar além de GET /setores (somente leitura).
_PREFIXOS_MARKETING = (
    "/api/v1/admin/me",
    "/api/v1/admin/logout",
    "/api/v1/admin/propagandas",
    "/api/v1/admin/tvs",
)


class AdminAccessError(Exception):
    def __init__(self, message: str, status: int = 403):
        super().__init__(message)
        self.message = message
        self.status = status


def normalizar_papel(valor) -> str:
    papel = (valor or PAPEL_ADMIN).strip().lower()
    if papel not in PAPEIS_VALIDOS:
        raise ValueError("Papel deve ser admin, gerente ou marketing")
    return papel


def papel_de(usuario: Usuario | None = None) -> str:
    user = usuario or usuario_atual()
    if not user:
        return PAPEL_ADMIN
    return (user.papel or PAPEL_ADMIN).strip().lower()


def usuario_atual() -> Usuario | None:
    user_id = session.get("user_id")
    if not user_id:
        return None
    return db.session.get(Usuario, user_id)


def is_admin(usuario: Usuario | None = None) -> bool:
    user = usuario or usuario_atual()
    if not user:
        return False
    return papel_de(user) == PAPEL_ADMIN


def is_marketing(usuario: Usuario | None = None) -> bool:
    user = usuario or usuario_atual()
    if not user:
        return False
    return papel_de(user) == PAPEL_MARKETING


def is_gerente(usuario: Usuario | None = None) -> bool:
    user = usuario or usuario_atual()
    if not user:
        return False
    return papel_de(user) == PAPEL_GERENTE


def setor_ids_permitidos(usuario: Usuario | None = None) -> list[int] | None:
    """None = sem restrição de setor (admin ou marketing). Lista = gerente."""
    user = usuario or usuario_atual()
    if not user:
        raise AdminAccessError("Não autenticado", 401)
    if is_admin(user) or is_marketing(user):
        return None
    return [s.id for s in (user.setores or [])]


def assert_setor_permitido(setor_id: int, usuario: Usuario | None = None) -> None:
    permitidos = setor_ids_permitidos(usuario)
    if permitidos is None:
        return
    if int(setor_id) not in permitidos:
        raise AdminAccessError("Sem permissão para este setor")


def filtrar_setor_id(setor_id: int | None, usuario: Usuario | None = None) -> int | None:
    """Valida/ajusta setor_id do request ao escopo do usuário."""
    permitidos = setor_ids_permitidos(usuario)
    if permitidos is None:
        return setor_id
    if not permitidos:
        raise AdminAccessError("Nenhum setor atribuído a este gerente")
    if setor_id is None:
        return None
    if int(setor_id) not in permitidos:
        raise AdminAccessError("Sem permissão para este setor")
    return int(setor_id)


def query_setores_visiveis(usuario: Usuario | None = None):
    permitidos = setor_ids_permitidos(usuario)
    q = Setor.query.order_by(Setor.nome)
    if permitidos is not None:
        if not permitidos:
            return q.filter(False)
        q = q.filter(Setor.id.in_(permitidos))
    return q


def require_admin(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        user = usuario_atual()
        if not user:
            return jsonify({"error": "Não autenticado"}), 401
        if not is_admin(user):
            return jsonify({"error": "Apenas administradores podem executar esta ação"}), 403
        return view(*args, **kwargs)

    return wrapped


def require_admin_ou_marketing(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        user = usuario_atual()
        if not user:
            return jsonify({"error": "Não autenticado"}), 401
        if not is_admin(user) and not is_marketing(user):
            return jsonify({"error": "Apenas administradores e marketing podem executar esta ação"}), 403
        return view(*args, **kwargs)

    return wrapped


def path_permitido_marketing(path: str, method: str) -> bool:
    path_n = (path or "").rstrip("/") or "/"
    method_n = (method or "GET").upper()
    if method_n == "OPTIONS":
        return True
    if path_n in {"/api/v1/admin/me", "/api/v1/admin/logout"}:
        return True
    if path_n == "/api/v1/admin/setores" and method_n == "GET":
        return True
    return any(path_n == prefixo or path_n.startswith(prefixo + "/") for prefixo in _PREFIXOS_MARKETING)


def restringir_marketing_se_necessario():
    """Resposta 403 se o usuário marketing tentar uma rota fora de mídias/TVs."""
    if "user_id" not in session:
        user_id_cookie = request.cookies.get("user_id")
        if user_id_cookie:
            session["user_id"] = user_id_cookie
            session.permanent = True
    user = usuario_atual()
    if not user or not is_marketing(user):
        return None
    if path_permitido_marketing(request.path, request.method):
        return None
    return jsonify({"error": "Sem permissão para esta área"}), 403


def set_usuario_setores(usuario: Usuario, setor_ids: list[int]) -> None:
    ids = sorted({int(x) for x in setor_ids if x is not None})
    if ids:
        encontrados = Setor.query.filter(Setor.id.in_(ids)).all()
        if len(encontrados) != len(ids):
            raise ValueError("Um ou mais setores são inválidos")
        usuario.setores = encontrados
    else:
        usuario.setores = []
