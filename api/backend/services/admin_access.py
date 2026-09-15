"""Escopo de acesso do painel: admin (tudo) vs gerente (setores vinculados)."""
from __future__ import annotations

from functools import wraps

from flask import jsonify, session

from backend.extensions import db
from backend.models import Operador, Setor, Usuario

PAPEL_ADMIN = "admin"
PAPEL_GERENTE = "gerente"
PAPEIS_VALIDOS = {PAPEL_ADMIN, PAPEL_GERENTE}


class AdminAccessError(Exception):
    def __init__(self, message: str, status: int = 403):
        super().__init__(message)
        self.message = message
        self.status = status


def normalizar_papel(valor) -> str:
    papel = (valor or PAPEL_ADMIN).strip().lower()
    if papel not in PAPEIS_VALIDOS:
        raise ValueError("Papel deve ser admin ou gerente")
    return papel


def usuario_atual() -> Usuario | None:
    user_id = session.get("user_id")
    if not user_id:
        return None
    return db.session.get(Usuario, user_id)


def is_admin(usuario: Usuario | None = None) -> bool:
    user = usuario or usuario_atual()
    if not user:
        return False
    return (user.papel or PAPEL_ADMIN).strip().lower() == PAPEL_ADMIN


def setor_ids_permitidos(usuario: Usuario | None = None) -> list[int] | None:
    """None = sem restrição (admin). Lista (pode ser vazia) = gerente."""
    user = usuario or usuario_atual()
    if not user:
        raise AdminAccessError("Não autenticado", 401)
    if is_admin(user):
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


def set_usuario_setores(usuario: Usuario, setor_ids: list[int]) -> None:
    ids = sorted({int(x) for x in setor_ids if x is not None})
    if ids:
        encontrados = Setor.query.filter(Setor.id.in_(ids)).all()
        if len(encontrados) != len(ids):
            raise ValueError("Um ou mais setores são inválidos")
        usuario.setores = encontrados
    else:
        usuario.setores = []
