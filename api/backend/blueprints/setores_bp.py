"""Seleção de setor — usada pelo admin/kiosk via navegador (o app Android usa
`/api/v1/setor/login` em `api_bp.py` para o mesmo fim, autenticando por
código do setor em vez de escolher de uma lista)."""
from flask import Blueprint, make_response, redirect, render_template, request, url_for

from backend.auth import login_required
from backend.models import Impressora, Setor, setor_eh_streaming

setores_bp = Blueprint("setores", __name__)


@setores_bp.route("/")
@login_required
def home():
    return redirect(url_for("setores.selecionar_setor"))


@setores_bp.route("/setores", methods=["GET", "POST"])
@login_required
def selecionar_setor():
    if request.method == "POST":
        setor_id = request.form["setor_id"]
        impressora = Impressora.query.filter_by(setor_id=setor_id).first()
        resp = make_response(redirect(url_for("setores.setor_opcoes", setor_id=setor_id)))
        resp.set_cookie("setor_id", str(setor_id))
        if impressora:
            resp.set_cookie("end_impressora_local", impressora.ip)
        return resp

    setores = [s for s in Setor.query.all() if not setor_eh_streaming(s)]
    return render_template("selecionar_setor.html", setores=setores)


@setores_bp.route("/setor/<int:setor_id>/opcoes")
@login_required
def setor_opcoes(setor_id):
    return render_template("setor_opcoes.html", setor_id=setor_id)
