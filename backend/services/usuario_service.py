"""Regras de negócio para usuários administradores do painel (`/login`).

Substitui o login via Supabase por autenticação local (tabela `usuarios`),
com senha armazenada como hash (`werkzeug.security`, já é dependência do
Flask — nunca em texto puro, diferente do código legado baseado em
Supabase).
"""
from werkzeug.security import check_password_hash, generate_password_hash

from backend.extensions import db
from backend.models import Usuario


def autenticar(email: str, senha: str) -> Usuario | None:
    """Retorna o Usuario se email/senha forem válidos, senão None."""
    if not email or not senha:
        return None
    usuario = Usuario.query.filter_by(email=email).first()
    if usuario and check_password_hash(usuario.senha_hash, senha):
        return usuario
    return None


def existe_algum_admin() -> bool:
    return db.session.query(Usuario.id).first() is not None


def criar_ou_atualizar_admin(email: str, senha: str, nome_empresa: str | None = None) -> Usuario:
    """Cria um novo admin, ou atualiza a senha se o email já existir.

    Usado tanto para semear o admin padrão na primeira inicialização
    (`backend/__init__.py::_init_database`) quanto pelo script de linha de
    comando `scripts/criar_admin.py`.
    """
    usuario = Usuario.query.filter_by(email=email).first()
    if usuario is None:
        usuario = Usuario(email=email)
        db.session.add(usuario)
    usuario.senha_hash = generate_password_hash(senha)
    if nome_empresa is not None:
        usuario.nome_empresa = nome_empresa
    db.session.commit()
    return usuario
