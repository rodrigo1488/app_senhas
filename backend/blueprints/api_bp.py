"""API REST enxuta para o app Android (Fase 3 do plano).

Convenções:
- Autenticação: header `Authorization: Bearer <session_token>` (JWT emitido
  por `/api/v1/setor/login` + `/api/v1/sessao/papel`).
- Todas as ações que mudam o estado da fila emitem os eventos do protocolo
  de tempo real (`backend/sockets/emitters.py`) — o app Android só precisa
  escutar os sockets para saber o resultado; as respostas REST são só o
  "ack" da própria ação.
- Nenhum endpoint aqui existe para ser consultado em intervalo (nada de
  `GET /fila` a cada N segundos) — os únicos GETs são para hidratar a tela
  na abertura (login, lista de operadores, estado inicial da fila).
"""
from flask import Blueprint, jsonify, request

from backend.auth import api_token_required, create_session_token
from backend.models import Impressora, Operador, Senha, Setor
from backend.services.avaliacao_service import AvaliacaoError, buscar_avaliacao_pendente, registrar_avaliacao
from backend.services.fila_service import (
    FilaError,
    chamar_novamente,
    chamar_proxima,
    confirmar_pedido,
    criar_senha,
    estado_atendimento_atual,
    listar_operadores,
    salvar_pedido,
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

api_bp = Blueprint("api_v1", __name__, url_prefix="/api/v1")


@api_bp.route("/health")
def health():
    return jsonify({"status": "ok"})


# --- Login por código de setor -----------------------------------------------

@api_bp.route("/setor/login", methods=["POST"])
def setor_login():
    data = request.get_json(silent=True) or {}
    codigo = (data.get("codigo_setor") or "").strip()
    if not codigo:
        return jsonify({"error": "codigo_setor é obrigatório"}), 400

    setor = Setor.query.filter_by(senha_setor=codigo).first()
    if not setor:
        return jsonify({"error": "Código de setor inválido"}), 401

    # Token "genérico": o papel (cliente/operador/avaliacao/tv) é escolhido
    # depois, na tela de seleção de modo do app — ver `/sessao/papel`.
    session_token = create_session_token(setor.id, role="generic")
    return jsonify({"session_token": session_token, "setor": setor.to_dict()})


@api_bp.route("/sessao/papel", methods=["POST"])
@api_token_required
def selecionar_papel(session_payload):
    """Re-emite o token com o papel escolhido na tela de seleção de modo
    (cliente/operador/avaliacao/tv). Chamado uma vez após `/setor/login`."""
    data = request.get_json(silent=True) or {}
    role = data.get("role")
    if role not in {"cliente", "operador", "avaliacao", "tv"}:
        return jsonify({"error": "role deve ser cliente, operador, avaliacao ou tv"}), 400

    operador_id = data.get("operador_id")
    session_token = create_session_token(session_payload["setor_id"], role=role, operador_id=operador_id)
    return jsonify({"session_token": session_token})


# --- Setor / operadores -------------------------------------------------------

@api_bp.route("/setor/operadores", methods=["GET"])
@api_token_required
def setor_operadores(session_payload):
    operadores = listar_operadores(session_payload["setor_id"])
    return jsonify({"operadores": [o.to_dict() for o in operadores]})


@api_bp.route("/setor/fila", methods=["GET"])
@api_token_required
def setor_fila(session_payload):
    """Estado inicial da fila — usado só para hidratar a tela na abertura do
    app; qualquer mudança depois disso chega via `fila:atualizada`."""
    return jsonify(serializar_fila(session_payload["setor_id"]))


@api_bp.route("/setor/atendimento_atual", methods=["GET"])
@api_token_required
def setor_atendimento_atual(session_payload):
    estado = estado_atendimento_atual(session_payload["setor_id"])
    return jsonify(estado or {})


# --- Cliente -------------------------------------------------------------------

@api_bp.route("/senha", methods=["POST"])
@api_token_required
def criar_senha_route(session_payload):
    data = request.get_json(silent=True) or {}
    tipo = data.get("tipo", "normal")
    setor_id = session_payload["setor_id"]

    try:
        senha = criar_senha(setor_id, tipo)
    except FilaError as exc:
        return jsonify({"error": str(exc)}), 400

    setor = Setor.query.get(setor_id)
    impressora = Impressora.query.filter_by(setor_id=setor_id).first()
    if impressora:
        imprimir_senha_com_ip(
            senha.senha, impressora.ip,
            nome_setor=setor.nome if setor else "Setor",
            descricao_setor=setor.descricao if setor else "",
            token_unico=senha.token_unico,
        )

    emit_fila_atualizada(setor_id)

    return jsonify(senha.to_dict())


@api_bp.route("/senha/pedido", methods=["POST"])
@api_token_required
def salvar_pedido_route(session_payload):
    data = request.get_json(silent=True) or {}
    ticket_token = data.get("ticket_token")
    pedido = (data.get("pedido") or "").strip()
    if not ticket_token or not pedido:
        return jsonify({"error": "ticket_token e pedido são obrigatórios"}), 400
    try:
        senha = salvar_pedido(ticket_token, pedido)
    except FilaError as exc:
        return jsonify({"error": str(exc)}), 404
    if senha.setor_id:
        emit_fila_atualizada(senha.setor_id)
    return jsonify({"success": True})


@api_bp.route("/senha/<token>/posicao", methods=["GET"])
@api_token_required
def posicao_route(session_payload, token):
    from backend.services.fila_service import posicao_na_fila

    try:
        return jsonify(posicao_na_fila(token))
    except FilaError as exc:
        return jsonify({"error": str(exc)}), 404


# --- Operador ------------------------------------------------------------------

@api_bp.route("/operador/chamar_proxima", methods=["POST"])
@api_token_required
def chamar_proxima_route(session_payload):
    data = request.get_json(silent=True) or {}
    operador_id = data.get("operador_id") or session_payload.get("operador_id")
    setor_id = session_payload["setor_id"]
    if not operador_id:
        return jsonify({"error": "operador_id é obrigatório"}), 400

    try:
        resultado = chamar_proxima(setor_id, int(operador_id))
    except FilaError as exc:
        return jsonify({"error": str(exc)}), 400

    emit_fila_atualizada(setor_id)
    emit_senha_chamada(resultado.senha, resultado.operador.nome, resultado.operador.foto_perfil, resultado.alerta_preferenciais)
    broadcast_posicao_fila(setor_id)

    if resultado.senha_anterior_finalizada:
        finalizada = resultado.senha_anterior_finalizada
        if finalizada.token_unico:
            from backend.services.fila_service import posicao_na_fila

            try:
                emit_senha_posicao(posicao_na_fila(finalizada.token_unico))
            except FilaError:
                pass
        emit_avaliacao_solicitada(
            setor_id, int(operador_id), resultado.operador.nome, resultado.operador.foto_perfil,
            finalizada.id, finalizada.senha,
        )

    impressora = Impressora.query.filter_by(setor_id=setor_id).first()
    if impressora:
        imprimir_senha_com_ip(resultado.senha.senha, impressora.ip)

    return jsonify({
        "senha": resultado.senha.to_dict(),
        "tipo_chamado": resultado.tipo_chamado,
        "alerta_preferenciais": resultado.alerta_preferenciais,
    })


@api_bp.route("/operador/chamar_novamente", methods=["POST"])
@api_token_required
def chamar_novamente_route(session_payload):
    data = request.get_json(silent=True) or {}
    senha_id = data.get("senha_id")
    if not senha_id:
        return jsonify({"error": "senha_id é obrigatório"}), 400
    try:
        senha = chamar_novamente(int(senha_id))
    except FilaError as exc:
        return jsonify({"error": str(exc)}), 404

    operador = Operador.query.get(session_payload.get("operador_id")) if session_payload.get("operador_id") else None
    emit_senha_chamada(senha, operador.nome if operador else "", operador.foto_perfil if operador else None)
    return jsonify({"success": True})


@api_bp.route("/operador/confirmar_pedido", methods=["POST"])
@api_token_required
def confirmar_pedido_route(session_payload):
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


# --- Avaliação -----------------------------------------------------------------

@api_bp.route("/avaliacao/pendente", methods=["GET"])
@api_token_required
def avaliacao_pendente_route(session_payload):
    operador_id = request.args.get("operador_id") or session_payload.get("operador_id")
    if not operador_id:
        return jsonify({"error": "operador_id é obrigatório"}), 400
    pendente = buscar_avaliacao_pendente(session_payload["setor_id"], int(operador_id))
    return jsonify(pendente or {})


@api_bp.route("/avaliacao", methods=["POST"])
@api_token_required
def enviar_avaliacao_route(session_payload):
    data = request.get_json(silent=True) or {}
    senha_id = data.get("senha_id")
    operador_id = data.get("operador_id") or session_payload.get("operador_id")
    nota = data.get("nota")
    if not (senha_id and operador_id and nota is not None):
        return jsonify({"error": "senha_id, operador_id e nota são obrigatórios"}), 400
    try:
        registrar_avaliacao(int(senha_id), session_payload["setor_id"], int(operador_id), nota)
    except AvaliacaoError as exc:
        return jsonify({"error": str(exc)}), 400
    return jsonify({"success": True})
