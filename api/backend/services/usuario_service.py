"""Regras de negócio para usuários do painel (`/login`).

Autenticação local (tabela `usuarios`), com senha em hash
(`werkzeug.security`). Suporta papéis `admin` e `gerente`.
"""
from werkzeug.security import check_password_hash, generate_password_hash

from backend.extensions import db
from backend.models import Usuario
from backend.services.admin_access import PAPEL_ADMIN, normalizar_papel, set_usuario_setores


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
    """Cria um novo admin, ou atualiza a senha se o email já existir."""
    usuario = Usuario.query.filter_by(email=email).first()
    if usuario is None:
        usuario = Usuario(email=email, papel=PAPEL_ADMIN)
        db.session.add(usuario)
    usuario.senha_hash = generate_password_hash(senha)
    usuario.papel = PAPEL_ADMIN
    if nome_empresa is not None:
        usuario.nome_empresa = nome_empresa
    db.session.commit()
    return usuario


def criar_usuario(
    *,
    email: str,
    senha: str,
    papel: str = PAPEL_ADMIN,
    nome: str | None = None,
    setor_ids: list[int] | None = None,
) -> Usuario:
    email_n = (email or "").strip().lower()
    if not email_n or not senha:
        raise ValueError("Email e senha são obrigatórios")
    if Usuario.query.filter_by(email=email_n).first():
        raise ValueError("Já existe um usuário com este email")
    papel_n = normalizar_papel(papel)
    if papel_n == "gerente" and not setor_ids:
        raise ValueError("Gerente precisa de ao menos um setor")
    usuario = Usuario(
        email=email_n,
        senha_hash=generate_password_hash(senha),
        nome=(nome or "").strip() or None,
        papel=papel_n,
    )
    db.session.add(usuario)
    db.session.flush()
    if papel_n == "gerente":
        set_usuario_setores(usuario, setor_ids or [])
    else:
        usuario.setores = []
    db.session.commit()
    return usuario


def atualizar_usuario(
    usuario: Usuario,
    *,
    email: str | None = None,
    senha: str | None = None,
    papel: str | None = None,
    nome: str | None = None,
    setor_ids: list[int] | None = None,
) -> Usuario:
    if email is not None:
        email_n = email.strip().lower()
        if not email_n:
            raise ValueError("Email é obrigatório")
        outro = Usuario.query.filter(Usuario.email == email_n, Usuario.id != usuario.id).first()
        if outro:
            raise ValueError("Já existe um usuário com este email")
        usuario.email = email_n
    if senha:
        usuario.senha_hash = generate_password_hash(senha)
    if nome is not None:
        usuario.nome = nome.strip() or None
    if papel is not None:
        usuario.papel = normalizar_papel(papel)
    papel_atual = normalizar_papel(usuario.papel)
    if papel_atual == "gerente":
        if setor_ids is not None:
            if not setor_ids:
                raise ValueError("Gerente precisa de ao menos um setor")
            set_usuario_setores(usuario, setor_ids)
        elif not usuario.setores:
            raise ValueError("Gerente precisa de ao menos um setor")
    else:
        usuario.setores = []
    db.session.commit()
    return usuario
