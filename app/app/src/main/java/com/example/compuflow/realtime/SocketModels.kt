package com.example.compuflow.realtime

import com.example.compuflow.data.remote.dto.AtendimentoDto
import com.example.compuflow.data.remote.dto.SenhaDto

/** Eventos recebidos do servidor, já convertidos para tipos Kotlin —
 * espelham `documentacao/REALTIME_PROTOCOL.md` §3. */
sealed class SocketEvent {
    data class FilaAtualizada(
        val setorId: Int,
        val pendentes: List<SenhaDto>,
        val atendimentos: List<AtendimentoDto>,
    ) : SocketEvent()

    data class SenhaCriada(val senha: SenhaDto) : SocketEvent()

    data class SenhaChamada(
        val setorId: Int?,
        val ticketToken: String?,
        val senha: String,
        val tipo: String?,
        val operadorId: Int?,
        val operadorNome: String?,
        val operadorFoto: String?,
        val temPedido: Boolean,
        val pedido: String?,
        val pedidoConfirmado: Boolean,
    ) : SocketEvent()

    data class SenhaPosicao(
        val ticketToken: String,
        val posicao: Int,
        val senha: String,
        val status: String?,
        val setorNome: String?,
        val temPedido: Boolean,
        val pedido: String?,
        val pedidoConfirmado: Boolean,
    ) : SocketEvent()

    data class PedidoStatus(
        val ticketToken: String,
        val pedido: String?,
        val status: String,
        val mensagem: String?,
    ) : SocketEvent()

    data class AvaliacaoSolicitada(
        val setorId: Int,
        val operadorId: Int,
        val operadorNome: String?,
        val operadorFoto: String?,
        val senhaId: Int,
        val senha: String,
    ) : SocketEvent()

    data class AuthErro(val mensagem: String?) : SocketEvent()
    data object Connected : SocketEvent()
    data class Disconnected(val reason: String?) : SocketEvent()
    data class ConnectError(val mensagem: String?) : SocketEvent()
}
