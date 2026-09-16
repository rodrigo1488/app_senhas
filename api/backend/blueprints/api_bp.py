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
from collections import defaultdict
from threading import Lock
from time import monotonic

from flask import Blueprint, jsonify, request

from backend.auth import (
    api_token_required,
    consume_operator_action_token,
    create_operator_action_token,
    create_session_token,
)
from backend.models import AtendimentoAtual, Impressora, Operador, Senha, Setor
from backend.services.tv_config_service import serializar_tv_config
from backend.services.avaliacao_service import AvaliacaoError, buscar_avaliacao_pendente, registrar_avaliacao
from backend.services.fila_service import (
    FilaError,
    chamar_novamente,
    chamar_proxima,
    confirmar_pedido,
    criar_senha,
    estado_atendimento_atual,
    listar_chamadas_recentes,
    listar_operadores,
    salvar_pedido,
    serializar_fila,
)
from backend.services.impressao_service import imprimir_senha_em_background
from backend.services.operador_pin_service import identificar_operador_por_pin
from backend.sockets.emitters import (
    broadcast_posicao_fila,
    emit_avaliacao_solicitada,
    emit_fila_atualizada,
    emit_pedido_status,
    emit_senha_chamada,
    emit_senha_posicao,
)

api_bp = Blueprint("api_v1", __name__, url_prefix="/api/v1")
_PIN_MAX_ATTEMPTS = 5
_PIN_WINDOW_SECONDS = 300
_pin_attempts: dict[tuple[int, str], list[float]] = defaultdict(list)
_pin_attempts_lock = Lock()


def _pin_attempt_key(setor_id: int) -> tuple[int, str]:
    return setor_id, request.remote_addr or "unknown"


def _pin_is_blocked(key: tuple[int, str]) -> bool:
    now = monotonic()
    with _pin_attempts_lock:
        recent = [value for value in _pin_attempts[key] if now - value < _PIN_WINDOW_SECONDS]
        _pin_attempts[key] = recent
        return len(recent) >= _PIN_MAX_ATTEMPTS


def _register_pin_failure(key: tuple[int, str]) -> None:
    with _pin_attempts_lock:
        _pin_attempts[key].append(monotonic())


def _clear_pin_failures(key: tuple[int, str]) -> None:
    with _pin_attempts_lock:
        _pin_attempts.pop(key, None)


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

    setor_id = session_payload["setor_id"]
    operador_id = data.get("operador_id")
    operador = None
    if role == "operador":
        if session_payload.get("role") == "operador" and session_payload.get("operador_id"):
            return jsonify({"error": "Identificação anterior não pode trocar de operador"}), 403
        setor = Setor.query.get(setor_id)
        modo = (setor.modo_identificacao_operador if setor else "foto") or "foto"
        identificacao_informada = bool(data.get("pin")) or operador_id is not None
        if not identificacao_informada:
            operador_id = None
        elif modo == "pin":
            attempt_key = _pin_attempt_key(setor_id)
            if _pin_is_blocked(attempt_key):
                return jsonify({"error": "Muitas tentativas. Aguarde 5 minutos"}), 429
            operador = identificar_operador_por_pin(setor_id, data.get("pin") or "")
            if not operador:
                _register_pin_failure(attempt_key)
                return jsonify({"error": "PIN inválido"}), 401
            _clear_pin_failures(attempt_key)
        else:
            operador = Operador.query.filter_by(id=operador_id, setor_id=setor_id).first()
            if not operador:
                return jsonify({"error": "Operador inválido para este setor"}), 400
        if operador:
            operador_id = operador.id
    elif role == "avaliacao" and operador_id:
        operador = Operador.query.filter_by(id=operador_id, setor_id=setor_id).first()
        if not operador:
            return jsonify({"error": "Operador inválido para este setor"}), 400
    else:
        operador_id = None

    if role == "operador" and operador:
        session_token = create_operator_action_token(setor_id, operador.id)
    else:
        session_token = create_session_token(setor_id, role=role, operador_id=operador_id)
    return jsonify({
        "session_token": session_token,
        "operador": operador.to_dict() if operador else None,
    })


@api_bp.route("/sessao/liberar_operador", methods=["POST"])
@api_token_required
def liberar_operador(session_payload):
    role = "operador" if session_payload.get("role") == "operador" else "generic"
    session_token = create_session_token(session_payload["setor_id"], role=role)
    return jsonify({"session_token": session_token, "operador": None})


# --- Setor / operadores -------------------------------------------------------

@api_bp.route("/setor/operadores", methods=["GET"])
@api_token_required
def setor_operadores(session_payload):
    setor = Setor.query.get(session_payload["setor_id"])
    operadores = listar_operadores(session_payload["setor_id"])
    modo = (setor.modo_identificacao_operador if setor else "foto") or "foto"
    return jsonify({
        "modo_identificacao_operador": modo,
        "operadores": [o.to_dict() for o in operadores],
    })


@api_bp.route("/setor/fila", methods=["GET"])
@api_token_required
def setor_fila(session_payload):
    """Estado inicial da fila — usado só para hidratar a tela na abertura do
    app; qualquer mudança depois disso chega via `fila:atualizada`."""
    return jsonify(
        serializar_fila(
            session_payload["setor_id"],
            incluir_pedidos=session_payload.get("role") == "operador",
        )
    )


@api_bp.route("/setor/tv_config", methods=["GET"])
@api_token_required
def setor_tv_config(session_payload):
    """Configuração da TV: layout e fila de mídia (imagem/vídeo) do setor."""
    setor = Setor.query.get(session_payload["setor_id"])
    if setor and session_payload.get("role") == "tv":
        from backend.services.streaming_service import registrar_setor_tv

        registrar_setor_tv(setor)
    return jsonify(serializar_tv_config(setor))


@api_bp.route("/setor/tv_chamadas_recentes", methods=["GET"])
@api_token_required
def setor_tv_chamadas_recentes(session_payload):
    """Histórico curto usado exclusivamente para hidratar o painel TV web."""
    if session_payload.get("role") != "tv":
        return jsonify({"error": "Sessão de TV obrigatória"}), 403
    return jsonify(
        {
            "chamadas": listar_chamadas_recentes(
                session_payload["setor_id"],
                limite=8,
            )
        }
    )


@api_bp.route("/setor/atendimento_atual", methods=["GET"])
@api_token_required
def setor_atendimento_atual(session_payload):
    if session_payload.get("role") != "operador" or not session_payload.get("operador_id"):
        return jsonify({"error": "Sessão de operador obrigatória"}), 403
    estado = estado_atendimento_atual(
        session_payload["setor_id"],
        session_payload["operador_id"],
    )
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
        imprimir_senha_em_background(
            senha.senha, impressora.ip,
            nome_setor=setor.nome if setor else "Setor",
            descricao_setor=setor.descricao if setor else "",
            token_unico=senha.token_unico,
        )

    emit_fila_atualizada(setor_id)
    broadcast_posicao_fila(setor_id)

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
    if session_payload.get("role") != "operador" or not session_payload.get("operador_id"):
        return jsonify({"error": "Sessão de operador obrigatória"}), 403
    operador_id = session_payload["operador_id"]
    if not consume_operator_action_token(session_payload):
        return jsonify({"error": "Identificação expirada ou já utilizada"}), 403
    if data.get("operador_id") not in {None, operador_id}:
        return jsonify({"error": "Não é permitido chamar por outro operador"}), 403
    setor_id = session_payload["setor_id"]
    if not operador_id:
        return jsonify({"error": "operador_id é obrigatório"}), 400

    try:
        resultado = chamar_proxima(setor_id, int(operador_id))
    except FilaError as exc:
        return jsonify({"error": str(exc)}), 400

    emit_fila_atualizada(setor_id)
    if resultado.senha:
        emit_senha_chamada(
            resultado.senha,
            resultado.operador.nome,
            resultado.operador.foto_perfil,
            resultado.alerta_preferenciais,
            resultado.operador.id,
        )
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

    mensagem = (
        f"Senha {resultado.senha.senha} chamada com sucesso."
        if resultado.senha
        else "Atendimento finalizado. Não há senhas pendentes."
        if resultado.senha_anterior_finalizada
        else "Não há senhas pendentes."
    )
    return jsonify({
        "senha": resultado.senha.to_dict() if resultado.senha else None,
        "chamada_realizada": resultado.chamada_realizada,
        "mensagem": mensagem,
        "tipo_chamado": resultado.tipo_chamado,
        "alerta_preferenciais": resultado.alerta_preferenciais,
        "session_token": create_session_token(setor_id, role="operador"),
    })


@api_bp.route("/operador/chamar_novamente", methods=["POST"])
@api_token_required
def chamar_novamente_route(session_payload):
    if session_payload.get("role") != "operador" or not session_payload.get("operador_id"):
        return jsonify({"error": "Sessão de operador obrigatória"}), 403
    data = request.get_json(silent=True) or {}
    senha_id = data.get("senha_id")
    if not senha_id:
        return jsonify({"error": "senha_id é obrigatório"}), 400
    atendimento = AtendimentoAtual.query.filter_by(
        setor_id=session_payload["setor_id"],
        operador_id=session_payload["operador_id"],
        senha_id=int(senha_id),
    ).first()
    if not atendimento:
        return jsonify({"error": "Senha não pertence ao atendimento deste operador"}), 403
    try:
        senha = chamar_novamente(int(senha_id))
    except FilaError as exc:
        return jsonify({"error": str(exc)}), 404

    operador = Operador.query.get(session_payload.get("operador_id")) if session_payload.get("operador_id") else None
    emit_senha_chamada(
        senha,
        operador.nome if operador else "",
        operador.foto_perfil if operador else None,
        operador_id=operador.id if operador else None,
    )
    return jsonify({"success": True})


@api_bp.route("/operador/confirmar_pedido", methods=["POST"])
@api_token_required
def confirmar_pedido_route(session_payload):
    if session_payload.get("role") != "operador" or not session_payload.get("operador_id"):
        return jsonify({"error": "Sessão de operador obrigatória"}), 403
    data = request.get_json(silent=True) or {}
    senha_codigo = data.get("senha")
    mensagem = data.get("mensagem", "Pedido sendo preparado")
    if not senha_codigo:
        return jsonify({"error": "senha é obrigatório"}), 400
    senha_atual = (
        Senha.query.join(AtendimentoAtual, AtendimentoAtual.senha_id == Senha.id)
        .filter(
            AtendimentoAtual.setor_id == session_payload["setor_id"],
            AtendimentoAtual.operador_id == session_payload["operador_id"],
            Senha.senha == senha_codigo,
        )
        .first()
    )
    if not senha_atual:
        return jsonify({"error": "Senha não pertence ao atendimento deste operador"}), 403
    try:
        senha = confirmar_pedido(
            senha_codigo,
            session_payload["setor_id"],
            session_payload["operador_id"],
        )
    except FilaError as exc:
        return jsonify({"error": str(exc)}), 404
    emit_fila_atualizada(session_payload["setor_id"])
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
