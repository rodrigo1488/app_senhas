"""Funções que emitem os eventos do protocolo de tempo real.

Chamadas tanto pelos handlers de socket (`backend/sockets/handlers.py`) quanto
pelas rotas REST usadas pelo app Android (`backend/blueprints/api_bp.py`) e pelos
templates web de fallback — qualquer ação que mude o estado da fila passa por
aqui para notificar todo mundo com o payload completo (sem exigir um `fetch`
depois).
"""
from backend.extensions import socketio
from backend.models import Senha
from backend.services.fila_service import serializar_fila
from backend.services.push_service import push_chamada, push_pedido, push_posicao
from backend.sockets.events import (
    EV_AVALIACAO_SOLICITADA,
    EV_CLIENTE_CONFIG_ATUALIZADA,
    EV_FILA_ATUALIZADA,
    EV_PEDIDO_STATUS,
    EV_SENHA_CHAMADA,
    EV_SENHA_CRIADA,
    EV_SENHA_POSICAO,
    EV_TV_CONFIG_ATUALIZADA,
    room_avaliacao,
    room_cliente_midia,
    room_operador,
    room_operadores,
    room_setor,
    room_ticket,
)


def emit_fila_atualizada(setor_id: int) -> None:
    socketio.emit(EV_FILA_ATUALIZADA, serializar_fila(setor_id), room=room_setor(setor_id))
    socketio.emit(
        EV_FILA_ATUALIZADA,
        serializar_fila(setor_id, incluir_pedidos=True),
        room=room_operadores(setor_id),
    )


def emit_senha_criada(senha: Senha, to_sid: str | None = None, impressao: dict | None = None) -> None:
    payload = senha.to_dict()
    if impressao is not None:
        payload["impressao"] = impressao
    if to_sid:
        socketio.emit(EV_SENHA_CRIADA, payload, room=to_sid)
    else:
        socketio.emit(EV_SENHA_CRIADA, payload, room=room_ticket(senha.token_unico))


def emit_senha_chamada(
    senha: Senha,
    operador_nome: str,
    operador_foto: str | None,
    alerta_preferenciais: bool = False,
    operador_id: int | None = None,
) -> None:
    payload = {
        "setor_id": senha.setor_id,
        "senha_id": senha.id,
        "senha": senha.senha,
        "tipo": senha.tipo,
        "operador_id": operador_id,
        "operador_nome": operador_nome,
        "operador_foto": operador_foto,
        "alerta_preferenciais": alerta_preferenciais,
    }
    if senha.setor_id:
        socketio.emit(EV_SENHA_CHAMADA, payload, room=room_setor(senha.setor_id))
        if operador_id:
            socketio.emit(
                EV_SENHA_CHAMADA,
                {
                    **payload,
                    "ticket_token": senha.token_unico,
                    "tem_pedido": bool(senha.tem_pedido),
                    "pedido": senha.pedido,
                    "pedido_confirmado": bool(senha.pedido_confirmado),
                },
                room=room_operador(senha.setor_id, operador_id),
            )
    if senha.token_unico:
        socketio.emit(
            EV_SENHA_CHAMADA,
            {
                **payload,
                "ticket_token": senha.token_unico,
                "tem_pedido": bool(senha.tem_pedido),
                "pedido": senha.pedido,
                "pedido_confirmado": bool(senha.pedido_confirmado),
            },
            room=room_ticket(senha.token_unico),
        )
        push_chamada(senha, operador_nome)


def emit_senha_posicao(posicao_info: dict) -> None:
    socketio.emit(EV_SENHA_POSICAO, posicao_info, room=room_ticket(posicao_info["token_unico"]))
    token = posicao_info.get("token_unico")
    if not token:
        return
    senha = Senha.query.filter_by(token_unico=token).first()
    if not senha:
        return
    try:
        push_posicao(
            senha,
            int(posicao_info.get("posicao", 99)),
            str(posicao_info.get("status") or senha.status or ""),
        )
    except Exception:
        pass


def broadcast_posicao_fila(setor_id: int) -> None:
    """Recalcula e emite a posição de todas as senhas aguardando de um setor."""
    from backend.services.fila_service import posicao_na_fila

    pendentes = Senha.query.filter_by(setor_id=setor_id, status="A").filter(Senha.token_unico.isnot(None)).all()
    for senha in pendentes:
        try:
            emit_senha_posicao(posicao_na_fila(senha.token_unico))
        except Exception:
            continue


def emit_pedido_status(ticket_token: str, pedido: str, status: str, mensagem: str) -> None:
    socketio.emit(
        EV_PEDIDO_STATUS,
        {"ticket_token": ticket_token, "pedido": pedido, "status": status, "mensagem": mensagem},
        room=room_ticket(ticket_token),
    )
    if status == "preparando":
        senha = Senha.query.filter_by(token_unico=ticket_token).first()
        if senha:
            push_pedido(senha, mensagem)


def emit_tv_config_atualizada(setor_id: int, payload: dict) -> None:
    socketio.emit(EV_TV_CONFIG_ATUALIZADA, payload, room=room_setor(setor_id))
    from backend.services.streaming_service import emitir_filas_streaming_do_setor

    emitir_filas_streaming_do_setor(setor_id)


def emit_cliente_config_atualizada(setor_id: int, payload: dict) -> None:
    socketio.emit(EV_CLIENTE_CONFIG_ATUALIZADA, payload, room=room_setor(setor_id))
    socketio.emit(EV_CLIENTE_CONFIG_ATUALIZADA, payload, room=room_cliente_midia(setor_id))


def emit_avaliacao_solicitada(setor_id: int, operador_id: int, operador_nome: str, operador_foto: str | None, senha_id: int, senha_codigo: str) -> None:
    payload = {
        "setor_id": setor_id,
        "operador_id": operador_id,
        "operador_nome": operador_nome,
        "operador_foto": operador_foto,
        "senha_id": senha_id,
        "senha": senha_codigo,
    }
    from backend.sockets.events import room_avaliacao_setor

    # Tablet ligado a um operador específico (legado) + tablet do setor (app novo).
    socketio.emit(EV_AVALIACAO_SOLICITADA, payload, room=room_avaliacao(setor_id, operador_id))
    socketio.emit(EV_AVALIACAO_SOLICITADA, payload, room=room_avaliacao_setor(setor_id))
