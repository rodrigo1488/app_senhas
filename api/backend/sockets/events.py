"""Nomes de evento e helpers de room — devem casar exatamente com
`documentacao/REALTIME_PROTOCOL.md` e com o cliente Android
(`SocketManager.kt` / `RealtimeEvents.kt`)."""

# Eventos servidor -> cliente
EV_FILA_ATUALIZADA = "fila:atualizada"
EV_SENHA_CHAMADA = "senha:chamada"
EV_SENHA_CRIADA = "senha:criada"
EV_SENHA_POSICAO = "senha:posicao"
EV_PEDIDO_STATUS = "pedido:status"
EV_AVALIACAO_SOLICITADA = "avaliacao:solicitada"
EV_AUTH_ERRO = "auth:erro"
EV_TV_CONFIG_ATUALIZADA = "tv:config_atualizada"

# Eventos cliente -> servidor
EV_OPERADOR_CHAMAR_PROXIMA = "operador:chamar_proxima"
EV_OPERADOR_CHAMAR_NOVAMENTE = "operador:chamar_novamente"
EV_CLIENTE_CRIAR_SENHA = "cliente:criar_senha"
EV_CLIENTE_SALVAR_PEDIDO = "cliente:salvar_pedido"
EV_AVALIACAO_ENVIAR = "avaliacao:enviar"


def room_setor(setor_id: int) -> str:
    return f"setor:{setor_id}"


def room_ticket(ticket_token: str) -> str:
    return f"ticket:{ticket_token}"


def room_operador(setor_id: int, operador_id: int) -> str:
    return f"operador:{setor_id}:{operador_id}"


def room_operadores(setor_id: int) -> str:
    return f"operadores:{setor_id}"


def room_avaliacao(setor_id: int, operador_id: int) -> str:
    return f"avaliacao:{setor_id}:{operador_id}"
