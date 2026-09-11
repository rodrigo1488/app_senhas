"""Login/logout do painel administrativo.

Autenticação local (tabela `usuarios`). O formulário visual do admin fica no
Next.js (`web/`); estas rotas mantêm compatibilidade e logout de sessão Flask.
"""
import os

from flask import Blueprint, make_response, redirect, request, session, url_for

from backend.services.usuario_service import autenticar

auth_bp = Blueprint("auth", __name__)


def _admin_web_url(path: str = "/login") -> str:
    base = os.getenv("ADMIN_WEB_URL", "http://localhost:3000").rstrip("/")
    if not path.startswith("/"):
        path = "/" + path
    return f"{base}{path}"


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "GET":
        if "user_id" in session:
            return redirect(_admin_web_url("/admin"))
        return redirect(_admin_web_url("/login"))

    # POST legado (form HTML) — ainda aceito para compatibilidade.
    email = request.form.get("email") or (request.get_json(silent=True) or {}).get("email")
    senha = request.form.get("senha") or (request.get_json(silent=True) or {}).get("senha")
    usuario = autenticar(email or "", senha or "")
    if usuario:
        session["user_id"] = usuario.id
        session.permanent = True
        resp = make_response(redirect(_admin_web_url("/admin")))
        resp.set_cookie("user_id", str(usuario.id), max_age=60 * 60 * 24 * 365)
        resp.set_cookie("nome_empresa", usuario.nome_empresa or "", max_age=60 * 60 * 24 * 365)
        return resp

    return redirect(_admin_web_url("/login"))


@auth_bp.route("/logout")
def logout():
    session.clear()
    resp = make_response(redirect(_admin_web_url("/login")))
    resp.set_cookie("user_id", "", expires=0)
    resp.set_cookie("nome_empresa", "", expires=0)
    return resp
