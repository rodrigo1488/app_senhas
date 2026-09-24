"""Tela de cliente (retirar senha) e painel de TV (fallback web) — os
equivalentes Android estão em `api_bp.py` (`POST /api/v1/senha`) e no
`SocketManager` do app (room `setor:<id>`)."""
from flask import Blueprint, make_response, redirect, render_template, request, send_file, url_for

from backend.auth import create_session_token, login_required
from backend.models import Operador, Senha, Setor
from backend.services.fila_service import FilaError, criar_senha, estado_atendimento_atual, verificar_senha
from backend.services.impressao_service import despachar_impressao_senha
from backend.sockets.emitters import broadcast_posicao_fila, emit_fila_atualizada
from backend.utils import gerar_qr_code_bytes, get_notification_url


filas_bp = Blueprint("filas", __name__)


@filas_bp.route("/senhas", methods=["GET", "POST"])
@login_required
def render_senhas():
    return render_template("senhas.html")


@filas_bp.route("/retirar_senha/<tipo>")
@login_required
def retirar_senha(tipo):
    setor_id = request.cookies.get("setor_id")
    if not setor_id:
        return "Setor não selecionado."

    try:
        senha = criar_senha(int(setor_id), tipo)
    except FilaError as exc:
        return str(exc), 400

    setor = Setor.query.get(int(setor_id))
    # Web legado: impressão via cliente só funciona no APK; aqui só imprime no servidor
    # quando o setor NÃO está em modo impressao_via_cliente.
    despachar_impressao_senha(setor, senha)

    emit_fila_atualizada(int(setor_id))
    broadcast_posicao_fila(int(setor_id))

    resp = make_response(redirect(url_for("filas.render_senhas")))
    resp.set_cookie("setor_id", str(setor_id))
    return resp


@filas_bp.route("/senha_atual")
@login_required
def senha_atual_view():
    setor_id = request.cookies.get("setor_id")
    if not setor_id:
        return redirect(url_for("setores.selecionar_setor"))
    session_token = create_session_token(int(setor_id), role="tv")
    estado = estado_atendimento_atual(int(setor_id))
    estado_inicial = {
        "senha_atual": estado["senha"] if estado else "Aguardando próxima senha...",
        "operador": estado["operador_nome"] if estado else "",
        "foto_operador": estado["operador_foto"] if estado else None,
        "tem_pedido": bool(estado["tem_pedido"]) if estado else False,
        "pedido": estado["pedido"] if estado else None,
    }
    return render_template("senha_atual.html", session_token=session_token, estado_inicial=estado_inicial)


@filas_bp.route("/qr/<token>")
def qr_code(token):
    senha = Senha.query.filter_by(token_unico=token).first()
    if not senha:
        return "Token não encontrado", 404
    data = gerar_qr_code_bytes(get_notification_url(token))
    import io

    return send_file(io.BytesIO(data), mimetype="image/png")
