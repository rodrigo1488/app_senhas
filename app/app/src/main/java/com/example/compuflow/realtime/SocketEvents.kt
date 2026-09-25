package com.example.compuflow.realtime

/**
 * Nomes de evento e room idênticos aos definidos em
 * `documentacao/REALTIME_PROTOCOL.md` e `backend/sockets/events.py`.
 * Não existem apelidos por plataforma — qualquer mudança de nome precisa
 * ser refletida nos dois lados.
 */
object SocketEvents {
    // Servidor -> cliente
    const val FILA_ATUALIZADA = "fila:atualizada"
    const val SENHA_CRIADA = "senha:criada"
    const val SENHA_CHAMADA = "senha:chamada"
    const val SENHA_POSICAO = "senha:posicao"
    const val PEDIDO_STATUS = "pedido:status"
    const val AVALIACAO_SOLICITADA = "avaliacao:solicitada"
    const val AUTH_ERRO = "auth:erro"
    const val TV_CONFIG_ATUALIZADA = "tv:config_atualizada"
    const val CLIENTE_CONFIG_ATUALIZADA = "cliente:config_atualizada"
    const val QUEUE_UPDATED = "queue_updated"
    const val MEDIA_PREVIEW = "media_preview"

    // Cliente -> servidor
    const val OPERADOR_CHAMAR_PROXIMA = "operador:chamar_proxima"
    const val OPERADOR_CHAMAR_NOVAMENTE = "operador:chamar_novamente"
    const val OPERADOR_CONFIRMAR_PEDIDO = "operador:confirmar_pedido"
    const val CLIENTE_CRIAR_SENHA = "cliente:criar_senha"
    const val CLIENTE_SALVAR_PEDIDO = "cliente:salvar_pedido"
    const val AVALIACAO_ENVIAR = "avaliacao:enviar"
    const val TICKET_SEGUIR = "ticket:seguir"
}
