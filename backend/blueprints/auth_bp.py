"""Login/logout do painel administrativo.

Autenticação local (tabela `usuarios` no Postgres/SQLite — ver
`backend/services/usuario_service.py`), sem depender de nenhum serviço
externo. Um usuário admin padrão é criado automaticamente na primeira
inicialização do banco (`backend/__init__.py::_seed_admin_padrao`).
"""
from flask import Blueprint, flash, make_response, redirect, render_template, request, session, url_for

from backend.services.usuario_service import autenticar

auth_bp = Blueprint("auth", __name__)


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if "user_id" in session and request.cookies.get("setor_id"):
        return redirect(url_for("filas.render_senhas"))

    if request.method == "POST":
        email = request.form["email"]
        senha = request.form["senha"]

        usuario = autenticar(email, senha)
        if usuario:
            session["user_id"] = usuario.id
            session.permanent = True
            resp = make_response(redirect(url_for("setores.selecionar_setor")))
            resp.set_cookie("user_id", str(usuario.id), max_age=60 * 60 * 24 * 365)
            resp.set_cookie("nome_empresa", usuario.nome_empresa or "", max_age=60 * 60 * 24 * 365)
            return resp

        flash("Email ou senha incorretos.", "error")
        return render_template("login.html"), 401

    return render_template("login.html")


@auth_bp.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("auth.login"))
