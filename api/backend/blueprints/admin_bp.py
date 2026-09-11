"""Painel administrativo Jinja (legado).

O painel principal agora é o Next.js em `web/` (porta 3000). Estas rotas
apenas redirecionam para o frontend novo, mantendo bookmarks antigos
funcionando. A API JSON usada pelo Next está em `admin_api_bp.py`.
"""
import os

from flask import Blueprint, redirect

from backend.auth import login_required

admin_bp = Blueprint("admin", __name__, url_prefix="/admin")


def _admin_web_url(path: str = "/admin") -> str:
    base = os.getenv("ADMIN_WEB_URL", "http://localhost:3000").rstrip("/")
    if not path.startswith("/"):
        path = "/" + path
    return f"{base}{path}"


@admin_bp.route("")
@login_required
def admin():
    return redirect(_admin_web_url("/admin"))


@admin_bp.route("/operador/add", methods=["GET", "POST"])
@login_required
def add_operador():
    return redirect(_admin_web_url("/admin/operadores"))


@admin_bp.route("/operador/edit/<int:operador_id>", methods=["GET", "POST"])
@login_required
def edit_operador(operador_id: int):
    return redirect(_admin_web_url(f"/admin/operadores/{operador_id}"))


@admin_bp.route("/operador/delete/<int:operador_id>")
@login_required
def delete_operador(operador_id: int):
    return redirect(_admin_web_url("/admin/operadores"))


@admin_bp.route("/impressora/add", methods=["GET", "POST"])
@login_required
def add_impressora():
    return redirect(_admin_web_url("/admin/impressoras"))


@admin_bp.route("/impressora/delete/<int:impressora_id>")
@login_required
def delete_impressora(impressora_id: int):
    return redirect(_admin_web_url("/admin/impressoras"))


@admin_bp.route("/setor/add", methods=["GET", "POST"])
@login_required
def add_setor():
    return redirect(_admin_web_url("/admin/setores"))


@admin_bp.route("/setor/edit/<int:setor_id>", methods=["GET", "POST"])
@login_required
def edit_setor(setor_id: int):
    return redirect(_admin_web_url("/admin/setores"))


@admin_bp.route("/setor/delete/<int:setor_id>")
@login_required
def delete_setor(setor_id: int):
    return redirect(_admin_web_url("/admin/setores"))


@admin_bp.route("/configuracao", methods=["GET", "POST"])
@login_required
def configuracao_empresa():
    return redirect(_admin_web_url("/admin/configuracoes"))


@admin_bp.route("/configuracao/ngrok", methods=["GET", "POST"])
@login_required
def configuracao_ngrok():
    return redirect(_admin_web_url("/admin/configuracoes"))


@admin_bp.route("/configuracao/fila", methods=["POST"])
@login_required
def configuracao_fila():
    return redirect(_admin_web_url("/admin/configuracoes"))
