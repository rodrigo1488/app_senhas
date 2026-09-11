"""Handlers de Socket.IO — implementam o handshake de autenticação e os
poucos eventos cliente->servidor que fazem sentido via socket (o app Android
usa majoritariamente REST para ações e sockets só para receber updates; os
handlers abaixo existem para os templates web de fallback que já falam
Socket.IO nativamente, e para clientes que preferirem o caminho 100% socket).

Nenhum destes handlers faz polling nem agenda `sleep`; cada um reage a um
evento pontual e emite o payload completo de uma vez (ver
`documentacao/REALTIME_PROTOCOL.md`).
"""
from flask import request, session
from flask_socketio import emit, join_room

from backend.auth import decode_session_token
from backend.extensions import socketio
from backend.models import AtendimentoAtual, Impressora, Operador, Senha, Setor
from backend.services.avaliacao_service import AvaliacaoError, registrar_avaliacao
from backend.services.fila_service import (
    FilaError,
    chamar_novamente,
    chamar_proxima,
    confirmar_pedido,
    criar_senha,
    posicao_na_fila,
    salvar_pedido,
)
from backend.services.impressao_service import imprimir_senha_com_ip
from backend.sockets.emitters import (
    broadcast_posicao_fila,
    emit_avaliacao_solicitada,
    emit_fila_atualizada,
    emit_pedido_status,
    emit_senha_chamada,
    emit_senha_criada,
    emit_senha_posicao,
)
from backend.sockets.events import EV_AUTH_ERRO, room_operador, room_setor, room_ticket


def _extract_token(auth) -> str | None:
    if isinstance(auth, dict) and auth.get("session_token"):
        return auth["session_token"]
    return request.args.get("session_token")


@socketio.on("connect")
def handle_connect(auth=None):
    """Handshake único: autentica e já entra nas rooms certas — substitui os
    antigos eventos manuais `join_setor` / `join_token_room`.

    Dois modos de autenticação são aceitos em `auth`:
    - `session_token`: JWT emitido por `/api/v1/setor/login` (app Android) ou
      pelas rotas web de setor/operador/avaliação/TV (usuário identificado).
    - `ticket_token`: o `token_unico` de uma senha específica — usado pela
      página pública de acompanhamento (`notificacao.html`, acessada via QR
      Code por clientes anônimos, sem login de setor).
    """
    ticket_token = auth.get("ticket_token") if isinstance(auth, dict) else None
    if ticket_token:
        if not Senha.query.filter_by(token_unico=ticket_token).first():
            emit(EV_AUTH_ERRO, {"mensagem": "Ticket não encontrado"})
            return False
        session["ticket_token"] = ticket_token
        join_room(room_ticket(ticket_token))
        try:
            emit_senha_posicao(posicao_na_fila(ticket_token))
        except FilaError:
            pass
        return True

    token = _extract_token(auth)
    payload = decode_session_token(token) if token else None

    if not payload:
        emit(EV_AUTH_ERRO, {"mensagem": "Sessão inválida ou expirada"})
        return False  # rejeita a conexão

    session["setor_id"] = payload.get("setor_id")
    session["role"] = payload.get("role")
    session["operador_id"] = payload.get("operador_id")

    setor_id = payload.get("setor_id")
    if setor_id:
        join_room(room_setor(setor_id))

    if payload.get("role") == "operador" and payload.get("operador_id"):
        join_room(room_operador(setor_id, payload["operador_id"]))

    if payload.get("role") == "avaliacao" and payload.get("operador_id"):
        from backend.sockets.events import room_avaliacao

        join_room(room_avaliacao(setor_id, payload["operador_id"]))

    return True


@socketio.on("disconnect")
def handle_disconnect():
    pass  # flask-socketio já remove o sid de todas as rooms automaticamente


@socketio.on("ticket:seguir")
def handle_ticket_seguir(data):
    """Cliente pede para acompanhar um ticket específico (ex.: depois de criar
    uma senha, ou ao reabrir o app com um token salvo)."""
    ticket_token = (data or {}).get("ticket_token")
    if not ticket_token:
        return
    if not Senha.query.filter_by(token_unico=ticket_token).first():
        emit("erro", {"mensagem": "Ticket não encontrado"})
        return
    join_room(room_ticket(ticket_token))
    try:
        emit_senha_posicao(posicao_na_fila(ticket_token))
    except FilaError:
        pass


@socketio.on("cliente:criar_senha")
def handle_cliente_criar_senha(data):
    setor_id = session.get("setor_id")
    if not setor_id:
        emit("erro", {"mensagem": "Sessão sem setor associado"})
        return
    tipo = (data or {}).get("tipo", "normal")
    senha = criar_senha(setor_id, tipo)
    join_room(room_ticket(senha.token_unico))
    emit_senha_criada(senha, to_sid=request.sid)
    emit_fila_atualizada(setor_id)

    impressora = Impressora.query.filter_by(setor_id=setor_id).first()
    if impressora:
        setor = Setor.query.get(setor_id)
        imprimir_senha_com_ip(
            senha.senha, impressora.ip,
            nome_setor=setor.nome if setor else "Setor",
            descricao_setor=setor.descricao if setor else "",
            token_unico=senha.token_unico,
        )


@socketio.on("cliente:salvar_pedido")
def handle_cliente_salvar_pedido(data):
    ticket_token = (data or {}).get("ticket_token")
    pedido = (data or {}).get("pedido", "").strip()
    if not ticket_token or not pedido:
        emit("erro", {"mensagem": "ticket_token e pedido são obrigatórios"})
        return
    try:
        senha = salvar_pedido(ticket_token, pedido)
    except FilaError as exc:
        emit("erro", {"mensagem": str(exc)})
        return
    if senha.setor_id:
        emit_fila_atualizada(senha.setor_id)


@socketio.on("operador:chamar_proxima")
def handle_operador_chamar_proxima(data):
    if session.get("role") != "operador" or not session.get("operador_id"):
        emit("erro", {"mensagem": "Sessão de operador obrigatória"})
        return
    setor_id = session.get("setor_id")
    operador_id = session.get("operador_id")
    if (data or {}).get("operador_id") not in {None, operador_id}:
        emit("erro", {"mensagem": "Não é permitido chamar por outro operador"})
        return
    if not setor_id or not operador_id:
        emit("erro", {"mensagem": "setor_id/operador_id não identificados"})
        return
    try:
        resultado = chamar_proxima(setor_id, operador_id)
    except FilaError as exc:
        emit("erro", {"mensagem": str(exc)})
        return

    emit_fila_atualizada(setor_id)
    emit_senha_chamada(
        resultado.senha,
        resultado.operador.nome,
        resultado.operador.foto_perfil,
        resultado.alerta_preferenciais,
        resultado.operador.id,
    )
    broadcast_posicao_fila(setor_id)

    if resultado.senha_anterior_finalizada and resultado.senha_anterior_finalizada.token_unico:
        try:
            emit_senha_posicao(posicao_na_fila(resultado.senha_anterior_finalizada.token_unico))
        except FilaError:
            pass

    if resultado.senha_anterior_finalizada:
        operador = Operador.query.get(operador_id)
        emit_avaliacao_solicitada(
            setor_id, operador_id, operador.nome, operador.foto_perfil,
            resultado.senha_anterior_finalizada.id, resultado.senha_anterior_finalizada.senha,
        )


@socketio.on("operador:chamar_novamente")
def handle_operador_chamar_novamente(data):
    if session.get("role") != "operador" or not session.get("operador_id"):
        emit("erro", {"mensagem": "Sessão de operador obrigatória"})
        return
    senha_id = (data or {}).get("senha_id")
    if not senha_id:
        emit("erro", {"mensagem": "senha_id é obrigatório"})
        return
    atendimento = AtendimentoAtual.query.filter_by(
        setor_id=session.get("setor_id"),
        operador_id=session.get("operador_id"),
        senha_id=senha_id,
    ).first()
    if not atendimento:
        emit("erro", {"mensagem": "Senha não pertence ao atendimento deste operador"})
        return
    try:
        senha = chamar_novamente(senha_id)
    except FilaError as exc:
        emit("erro", {"mensagem": str(exc)})
        return
    operador = Operador.query.get(session.get("operador_id"))
    emit_senha_chamada(
        senha,
        operador.nome if operador else "",
        operador.foto_perfil if operador else None,
        operador_id=operador.id if operador else None,
    )


@socketio.on("operador:confirmar_pedido")
def handle_operador_confirmar_pedido(data):
    if session.get("role") != "operador" or not session.get("operador_id"):
        emit("erro", {"mensagem": "Sessão de operador obrigatória"})
        return
    data = data or {}
    senha_codigo = data.get("senha")
    mensagem = data.get("mensagem", "Pedido sendo preparado")
    if not senha_codigo:
        emit("erro", {"mensagem": "senha é obrigatório"})
        return
    senha_atual = (
        Senha.query.join(AtendimentoAtual, AtendimentoAtual.senha_id == Senha.id)
        .filter(
            AtendimentoAtual.setor_id == session.get("setor_id"),
            AtendimentoAtual.operador_id == session.get("operador_id"),
            Senha.senha == senha_codigo,
        )
        .first()
    )
    if not senha_atual:
        emit("erro", {"mensagem": "Senha não pertence ao atendimento deste operador"})
        return
    try:
        senha = confirmar_pedido(
            senha_codigo,
            session.get("setor_id"),
            session.get("operador_id"),
        )
    except FilaError as exc:
        emit("erro", {"mensagem": str(exc)})
        return
    if senha.token_unico:
        emit_pedido_status(senha.token_unico, senha.pedido, "preparando", mensagem)


@socketio.on("avaliacao:enviar")
def handle_avaliacao_enviar(data):
    data = data or {}
    senha_id = data.get("senha_id")
    setor_id = data.get("setor_id") or session.get("setor_id")
    operador_id = data.get("operador_id") or session.get("operador_id")
    nota = data.get("nota")
    if not (senha_id and setor_id and operador_id and nota is not None):
        emit("erro", {"mensagem": "senha_id, setor_id, operador_id e nota são obrigatórios"})
        return
    try:
        registrar_avaliacao(senha_id, setor_id, operador_id, nota)
    except AvaliacaoError as exc:
        emit("erro", {"mensagem": str(exc)})
