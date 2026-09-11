"""Tela de operador (fallback web) — o app Android usa os endpoints
equivalentes em `api_bp.py`. Aqui mantemos as mesmas URLs do `app.py` legado
(`/senhas_pendentes`, `/chamar_proxima`, `/chamar_senha_novamente`) para não
quebrar nada que já aponte para elas, só trocando a fonte de dados para os
`services` novos e emitindo os eventos do protocolo (nunca mais um "aviso +
fetch")."""
from flask import Blueprint, jsonify, make_response, redirect, render_template, request

from backend.auth import create_session_token, login_required
from backend.models import AtendimentoAtual, Operador, Senha
from backend.services.fila_service import (
    FilaError,
    chamar_novamente,
    chamar_proxima,
    confirmar_pedido,
    estado_atendimento_atual,
    listar_operadores,
    serializar_fila,
)
from backend.services.impressao_service import imprimir_senha_com_ip
from backend.sockets.emitters import (
    broadcast_posicao_fila,
    emit_avaliacao_solicitada,
    emit_fila_atualizada,
    emit_pedido_status,
    emit_senha_chamada,
    emit_senha_posicao,
)

operador_bp = Blueprint("operador", __name__)


def _serializar_fila_legado(setor_id: int):
    """Mantém o formato de tupla que os templates legados esperam."""
    senhas = Senha.query.filter_by(setor_id=setor_id, status="A").order_by(Senha.tipo.desc(), Senha.id.asc()).all()
    operadores = listar_operadores(setor_id)

    atendimentos_query = (
        AtendimentoAtual.query.filter_by(setor_id=setor_id).order_by(AtendimentoAtual.id.desc()).all()
    )
    vistos = set()
    atendimentos = []
    for atendimento in atendimentos_query:
        if atendimento.operador_id in vistos:
            continue
        vistos.add(atendimento.operador_id)
        operador = Operador.query.get(atendimento.operador_id)
        senha = Senha.query.get(atendimento.senha_id)
        if operador and senha:
            atendimentos.append((operador.id, operador.nome, senha.senha, senha.tipo, operador.foto_perfil))
    atendimentos.sort(key=lambda a: a[1] or "")

    return (
        [(s.id, s.senha, s.tipo) for s in senhas],
        [(o.id, o.nome, o.foto_perfil) for o in operadores],
        atendimentos,
    )


@operador_bp.route("/senhas_pendentes")
@login_required
def senhas_pendentes():
    setor_id = request.cookies.get("setor_id")
    if not setor_id:
        return "Setor não selecionado."
    senhas, operadores, atendimentos = _serializar_fila_legado(int(setor_id))
    session_token = create_session_token(int(setor_id), role="operador")
    senha_atual_info = estado_atendimento_atual(int(setor_id))
    return render_template(
        "senhas_pendentes.html",
        senhas=senhas,
        operadores=operadores,
        atendimentos=atendimentos,
        session_token=session_token,
        senha_atual_info=senha_atual_info,
    )


@operador_bp.route("/chamar_proxima", methods=["GET", "POST"])
@login_required
def chamar_proxima_route():
    if request.method == "GET":
        return render_template("identificar_operador.html")

    operador_id = request.form["operador_id"]
    setor_id = request.cookies.get("setor_id")
    if not setor_id:
        return make_response(jsonify({"success": False, "error": "Setor não selecionado"}), 400)

    try:
        resultado = chamar_proxima(int(setor_id), int(operador_id))
    except FilaError as exc:
        return make_response(jsonify({"success": False, "error": str(exc)}), 400)

    emit_fila_atualizada(int(setor_id))
    emit_senha_chamada(resultado.senha, resultado.operador.nome, resultado.operador.foto_perfil, resultado.alerta_preferenciais)
    broadcast_posicao_fila(int(setor_id))

    if resultado.senha_anterior_finalizada and resultado.senha_anterior_finalizada.token_unico:
        try:
            from backend.services.fila_service import posicao_na_fila
            emit_senha_posicao(posicao_na_fila(resultado.senha_anterior_finalizada.token_unico))
        except FilaError:
            pass

    if resultado.senha_anterior_finalizada:
        emit_avaliacao_solicitada(
            int(setor_id), int(operador_id), resultado.operador.nome, resultado.operador.foto_perfil,
            resultado.senha_anterior_finalizada.id, resultado.senha_anterior_finalizada.senha,
        )

    impressora_ip = request.cookies.get("end_impressora_local")
    if impressora_ip:
        imprimir_senha_com_ip(resultado.senha.senha, impressora_ip)

    resp = make_response(jsonify({
        "success": True,
        "senha": resultado.senha.senha,
        "tipo": resultado.tipo_chamado,
        "alerta_preferenciais": resultado.alerta_preferenciais,
    }))
    resp.set_cookie("operador_id", str(operador_id))
    return resp


@operador_bp.route("/chamar_senha_novamente", methods=["POST"])
@login_required
def chamar_senha_novamente():
    data = request.get_json(silent=True) or {}
    senha_codigo = data.get("senha")
    operador_id = data.get("operador_id")
    if not senha_codigo or not operador_id:
        return jsonify({"error": "Senha e operador_id são obrigatórios"}), 400

    try:
        senha = chamar_novamente_por_codigo(senha_codigo)
    except FilaError as exc:
        return jsonify({"error": str(exc)}), 404

    impressora_ip = request.cookies.get("end_impressora_local")
    if impressora_ip:
        imprimir_senha_com_ip(senha.senha, impressora_ip)

    operador = Operador.query.get(operador_id)
    emit_senha_chamada(senha, operador.nome if operador else "", operador.foto_perfil if operador else None)

    return jsonify({"success": True, "message": f"Senha {senha.senha} chamada novamente"})


def chamar_novamente_por_codigo(senha_codigo: str):
    senha = Senha.query.filter_by(senha=senha_codigo, status="C").first()
    if not senha:
        raise FilaError("Senha não encontrada ou não está sendo atendida")
    return senha


@operador_bp.route("/operador/confirmar_pedido", methods=["POST"])
@login_required
def confirmar_pedido_route():
    data = request.get_json(silent=True) or {}
    senha_codigo = data.get("senha")
    mensagem = data.get("mensagem", "Pedido sendo preparado")
    if not senha_codigo:
        return jsonify({"error": "senha é obrigatório"}), 400
    try:
        senha = confirmar_pedido(senha_codigo)
    except FilaError as exc:
        return jsonify({"error": str(exc)}), 404
    if senha.token_unico:
        emit_pedido_status(senha.token_unico, senha.pedido, "preparando", mensagem)
    return jsonify({"success": True})
