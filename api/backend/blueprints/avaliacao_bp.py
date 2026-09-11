"""Tela de avaliação (fallback web) — equivalente Android em
`api_bp.py::enviar_avaliacao`."""
from flask import Blueprint, redirect, render_template, request, url_for

from backend.auth import create_session_token, login_required
from backend.models import Operador
from backend.services.avaliacao_service import AvaliacaoError, buscar_avaliacao_pendente, registrar_avaliacao

avaliacao_bp = Blueprint("avaliacao", __name__)


@avaliacao_bp.route("/avaliacao_pendente")
@login_required
def avaliacao_pendente():
    setor_id = request.cookies.get("setor_id")
    operador_id = request.cookies.get("operador_id")
    pendente = buscar_avaliacao_pendente(int(setor_id), int(operador_id)) if setor_id and operador_id else None
    if pendente:
        return redirect(url_for("avaliacao.avaliacao", senha_id=pendente["senha_id"], setor_id=setor_id, operador_id=operador_id, auto_finalize="1"))
    return redirect(url_for("setores.setor_opcoes", setor_id=setor_id))


@avaliacao_bp.route("/avaliacao", methods=["GET", "POST"])
@login_required
def avaliacao():
    setor_id = request.args.get("setor_id") or request.cookies.get("setor_id")
    operador_id = request.args.get("operador_id") or request.cookies.get("operador_id")
    auto_finalize = request.args.get("auto_finalize")

    pendente = None
    operador = Operador.query.get(int(operador_id)) if operador_id else None

    if setor_id and operador_id:
        pendente = buscar_avaliacao_pendente(int(setor_id), int(operador_id))

    if request.method == "POST":
        nota = request.form["nota"]
        try:
            registrar_avaliacao(int(pendente["senha_id"]), int(setor_id), int(operador_id), nota)
        except AvaliacaoError:
            pass
        session_token = create_session_token(int(setor_id), role="avaliacao", operador_id=int(operador_id)) if setor_id and operador_id else None
        return render_template("avaliacao.html", saudacao=True, session_token=session_token)

    session_token = create_session_token(int(setor_id), role="avaliacao", operador_id=int(operador_id)) if setor_id and operador_id else None

    return render_template(
        "avaliacao.html",
        senha_id=pendente["senha_id"] if pendente else None,
        setor_id=setor_id,
        operador_id=operador_id,
        auto_finalize=(auto_finalize == "1"),
        senha_texto=pendente["senha"] if pendente else None,
        operador_nome=pendente["operador_nome"] if pendente else (operador.nome if operador else None),
        operador_foto=pendente["operador_foto"] if pendente else (operador.foto_perfil if operador else None),
        session_token=session_token,
    )
