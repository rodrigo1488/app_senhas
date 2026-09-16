package com.example.compuflow.realtime

import android.util.Log
import com.example.compuflow.data.remote.dto.AtendimentoDto
import com.example.compuflow.data.remote.dto.PropagandaImagemDto
import com.example.compuflow.data.remote.dto.SenhaDto
import com.example.compuflow.data.remote.dto.StreamingQueueItemDto
import io.socket.client.IO
import io.socket.client.Socket
import io.socket.emitter.Emitter
import io.socket.engineio.client.transports.Polling
import kotlinx.coroutines.flow.MutableSharedFlow
import kotlinx.coroutines.flow.SharedFlow
import kotlinx.coroutines.flow.asSharedFlow
import org.json.JSONArray
import org.json.JSONObject

/**
 * Cliente único de Socket.IO do app, implementando o contrato de
 * `documentacao/REALTIME_PROTOCOL.md`. Uma única instância de socket por
 * sessão (namespace `/`, sem reconexão manual de rooms — tudo é feito pelo
 * servidor no `connect` via `auth`).
 */
object SocketManager {
    private const val TAG = "SocketManager"

    private var socket: Socket? = null

    private val _events = MutableSharedFlow<SocketEvent>(extraBufferCapacity = 64)
    val events: SharedFlow<SocketEvent> = _events.asSharedFlow()

    /** Conecta autenticado por papel (cliente/operador/avaliacao/tv) — ver §1 do protocolo. */
    fun connectWithSessionToken(httpBaseUrl: String, sessionToken: String) {
        connect(httpBaseUrl, mapOf("session_token" to sessionToken))
    }

    /** Conecta anonimamente para acompanhar uma senha específica (fallback web/QR). */
    fun connectWithTicketToken(httpBaseUrl: String, ticketToken: String) {
        connect(httpBaseUrl, mapOf("ticket_token" to ticketToken))
    }

    private fun connect(httpBaseUrl: String, auth: Map<String, String>) {
        disconnect()
        val optionsBuilder = IO.Options.builder()
            .setAuth(auth)
            .setReconnection(true)
            .setTimeout(20_000)

        // Túnel HTTPS (Next rewrite) costuma quebrar upgrade WebSocket — força polling.
        if (httpBaseUrl.startsWith("https://", ignoreCase = true)) {
            optionsBuilder.setTransports(arrayOf(Polling.NAME))
        }

        val options = optionsBuilder.build()

        val newSocket = try {
            IO.socket(httpBaseUrl, options)
        } catch (e: Exception) {
            Log.e(TAG, "Falha ao criar socket para $httpBaseUrl", e)
            _events.tryEmit(SocketEvent.ConnectError(e.message))
            return
        }

        newSocket.on(Socket.EVENT_CONNECT, listener { _events.tryEmit(SocketEvent.Connected) })
        newSocket.on(Socket.EVENT_DISCONNECT, listener { args ->
            _events.tryEmit(SocketEvent.Disconnected(args.getOrNull(0)?.toString()))
        })
        newSocket.on(Socket.EVENT_CONNECT_ERROR, listener { args ->
            _events.tryEmit(SocketEvent.ConnectError(args.getOrNull(0)?.toString()))
        })

        newSocket.on(SocketEvents.AUTH_ERRO, listener { args ->
            val obj = args.jsonObjectOrNull(0)
            _events.tryEmit(SocketEvent.AuthErro(obj?.optStringOrNull("mensagem")))
        })

        newSocket.on(SocketEvents.TV_CONFIG_ATUALIZADA, listener { args ->
            val obj = args.jsonObjectOrNull(0) ?: return@listener
            _events.tryEmit(
                SocketEvent.TvConfigAtualizada(
                    propagandasAtivas = obj.optBoolean("propagandas_ativas", false),
                    layoutTvWeb = obj.optString("layout_tv_web", "propaganda").ifBlank { "propaganda" },
                    imagens = obj.optJSONArray("imagens").toPropagandaList(),
                    intervaloMs = obj.optLong("intervalo_ms", 15_000L).coerceAtLeast(1_000L),
                )
            )
        })

        newSocket.on(SocketEvents.QUEUE_UPDATED, listener { args ->
            val obj = args.jsonObjectOrNull(0) ?: return@listener
            _events.tryEmit(
                SocketEvent.QueueUpdated(
                    queue = obj.optJSONArray("queue").toStreamingQueueList(),
                )
            )
        })

        newSocket.on(SocketEvents.FILA_ATUALIZADA, listener { args ->
            val obj = args.jsonObjectOrNull(0) ?: return@listener
            _events.tryEmit(
                SocketEvent.FilaAtualizada(
                    setorId = obj.optInt("setor_id"),
                    pendentes = obj.optJSONArray("pendentes").toSenhaList(),
                    atendimentos = obj.optJSONArray("atendimentos").toAtendimentoList(),
                )
            )
        })

        newSocket.on(SocketEvents.SENHA_CRIADA, listener { args ->
            val obj = args.jsonObjectOrNull(0) ?: return@listener
            _events.tryEmit(SocketEvent.SenhaCriada(obj.toSenhaDto()))
        })

        newSocket.on(SocketEvents.SENHA_CHAMADA, listener { args ->
            val obj = args.jsonObjectOrNull(0) ?: return@listener
            _events.tryEmit(
                SocketEvent.SenhaChamada(
                    setorId = obj.optIntOrNull("setor_id"),
                    ticketToken = obj.optStringOrNull("ticket_token"),
                    senhaId = obj.optIntOrNull("senha_id"),
                    senha = obj.optString("senha"),
                    tipo = obj.optStringOrNull("tipo"),
                    operadorId = obj.optIntOrNull("operador_id"),
                    operadorNome = obj.optStringOrNull("operador_nome"),
                    operadorFoto = obj.optStringOrNull("operador_foto"),
                    temPedido = obj.optBoolean("tem_pedido", false),
                    pedido = obj.optStringOrNull("pedido"),
                    pedidoConfirmado = obj.optBoolean("pedido_confirmado", false),
                )
            )
        })

        newSocket.on(SocketEvents.SENHA_POSICAO, listener { args ->
            val obj = args.jsonObjectOrNull(0) ?: return@listener
            _events.tryEmit(
                SocketEvent.SenhaPosicao(
                    ticketToken = obj.optString("ticket_token"),
                    posicao = obj.optInt("posicao", -1),
                    senha = obj.optString("senha"),
                    status = obj.optStringOrNull("status"),
                    setorNome = obj.optStringOrNull("setor_nome"),
                    temPedido = obj.optBoolean("tem_pedido", false),
                    pedido = obj.optStringOrNull("pedido"),
                    pedidoConfirmado = obj.optBoolean("pedido_confirmado", false),
                )
            )
        })

        newSocket.on(SocketEvents.PEDIDO_STATUS, listener { args ->
            val obj = args.jsonObjectOrNull(0) ?: return@listener
            _events.tryEmit(
                SocketEvent.PedidoStatus(
                    ticketToken = obj.optString("ticket_token"),
                    pedido = obj.optStringOrNull("pedido"),
                    status = obj.optString("status"),
                    mensagem = obj.optStringOrNull("mensagem"),
                )
            )
        })

        newSocket.on(SocketEvents.AVALIACAO_SOLICITADA, listener { args ->
            val obj = args.jsonObjectOrNull(0) ?: return@listener
            _events.tryEmit(
                SocketEvent.AvaliacaoSolicitada(
                    setorId = obj.optInt("setor_id"),
                    operadorId = obj.optInt("operador_id"),
                    operadorNome = obj.optStringOrNull("operador_nome"),
                    operadorFoto = obj.optStringOrNull("operador_foto"),
                    senhaId = obj.optInt("senha_id"),
                    senha = obj.optString("senha"),
                )
            )
        })

        socket = newSocket
        newSocket.connect()
    }

    fun disconnect() {
        socket?.off()
        socket?.disconnect()
        socket = null
    }

    fun isConnected(): Boolean = socket?.connected() == true

    // --- Emissão de eventos cliente -> servidor (protocolo §4) -------------

    fun emitChamarProxima(operadorId: Int) {
        emit(SocketEvents.OPERADOR_CHAMAR_PROXIMA, JSONObject().put("operador_id", operadorId))
    }

    fun emitChamarNovamente(senhaId: Int) {
        emit(SocketEvents.OPERADOR_CHAMAR_NOVAMENTE, JSONObject().put("senha_id", senhaId))
    }

    fun emitConfirmarPedido(senha: String, mensagem: String) {
        emit(SocketEvents.OPERADOR_CONFIRMAR_PEDIDO, JSONObject().put("senha", senha).put("mensagem", mensagem))
    }

    fun emitCriarSenha(tipo: String) {
        emit(SocketEvents.CLIENTE_CRIAR_SENHA, JSONObject().put("tipo", tipo))
    }

    fun emitSalvarPedido(ticketToken: String, pedido: String) {
        emit(SocketEvents.CLIENTE_SALVAR_PEDIDO, JSONObject().put("ticket_token", ticketToken).put("pedido", pedido))
    }

    fun emitEnviarAvaliacao(senhaId: Int, nota: Int) {
        emit(SocketEvents.AVALIACAO_ENVIAR, JSONObject().put("senha_id", senhaId).put("nota", nota))
    }

    fun emitTicketSeguir(ticketToken: String) {
        emit(SocketEvents.TICKET_SEGUIR, JSONObject().put("ticket_token", ticketToken))
    }

    private fun emit(event: String, payload: JSONObject) {
        val current = socket
        if (current == null || !current.connected()) {
            Log.w(TAG, "Tentativa de emitir '$event' sem socket conectado")
            return
        }
        current.emit(event, payload)
    }

    /** Pequeno helper para criar um `Emitter.Listener` a partir de uma lambda Kotlin. */
    private inline fun listener(crossinline body: (Array<out Any?>) -> Unit): Emitter.Listener =
        Emitter.Listener { args -> body(args) }
}

// --- Helpers de parsing (org.json) ------------------------------------------

private fun Array<out Any?>.jsonObjectOrNull(index: Int): JSONObject? =
    this.getOrNull(index) as? JSONObject

private fun JSONObject.optStringOrNull(key: String): String? =
    if (has(key) && !isNull(key)) getString(key) else null

private fun JSONObject.optIntOrNull(key: String): Int? =
    if (has(key) && !isNull(key)) optInt(key) else null

private fun JSONObject?.toSenhaDto(): SenhaDto {
    val obj = this ?: JSONObject()
    return SenhaDto(
        id = obj.optInt("id"),
        senha = obj.optString("senha"),
        tipo = obj.optString("tipo"),
        setor_id = obj.optIntOrNull("setor_id"),
        status = obj.optStringOrNull("status"),
        token_unico = obj.optStringOrNull("token_unico"),
        tem_pedido = obj.optBoolean("tem_pedido", false),
        pedido = obj.optStringOrNull("pedido"),
        pedido_confirmado = obj.optBoolean("pedido_confirmado", false),
    )
}

private fun JSONArray?.toPropagandaList(): List<PropagandaImagemDto> {
    if (this == null) return emptyList()
    return (0 until length()).map { i ->
        val obj = optJSONObject(i) ?: JSONObject()
        PropagandaImagemDto(
            id = obj.optInt("id"),
            arquivo = obj.optString("arquivo"),
            ordem = obj.optInt("ordem"),
            tipo = obj.optString("tipo", "image").ifBlank { "image" },
        )
    }
}

private fun JSONArray?.toStreamingQueueList(): List<StreamingQueueItemDto> {
    if (this == null) return emptyList()
    return (0 until length()).map { i ->
        val obj = optJSONObject(i) ?: JSONObject()
        StreamingQueueItemDto(
            path = obj.optString("path"),
            type = obj.optString("type", "image").ifBlank { "image" },
            order = obj.optInt("order"),
            duration = obj.optLong("duration", 15_000L).coerceAtLeast(1_000L),
        )
    }
}

private fun JSONArray?.toSenhaList(): List<SenhaDto> {
    if (this == null) return emptyList()
    return (0 until length()).map { i -> optJSONObject(i).toSenhaDto() }
}

private fun JSONArray?.toAtendimentoList(): List<AtendimentoDto> {
    if (this == null) return emptyList()
    return (0 until length()).map { i ->
        val obj = optJSONObject(i) ?: JSONObject()
        AtendimentoDto(
            operador_id = obj.optInt("operador_id"),
            operador_nome = obj.optString("operador_nome"),
            operador_foto = obj.optStringOrNull("operador_foto"),
            senha = obj.optString("senha"),
            tipo = obj.optString("tipo"),
            senha_id = obj.optIntOrNull("senha_id"),
            tem_pedido = obj.optBoolean("tem_pedido", false),
            pedido = obj.optStringOrNull("pedido"),
            pedido_confirmado = obj.optBoolean("pedido_confirmado", false),
        )
    }
}
