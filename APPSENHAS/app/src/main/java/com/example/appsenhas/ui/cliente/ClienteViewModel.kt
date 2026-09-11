package com.example.appsenhas.ui.cliente

import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.setValue
import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.example.appsenhas.AppGraph
import com.example.appsenhas.data.remote.NetworkModule
import com.example.appsenhas.data.remote.dto.CriarSenhaRequest
import com.example.appsenhas.data.remote.dto.SalvarPedidoRequest
import com.example.appsenhas.data.remote.toUserMessage
import com.example.appsenhas.realtime.SocketEvent
import com.example.appsenhas.realtime.SocketManager
import kotlinx.coroutines.launch

class ClienteViewModel : ViewModel() {
    private val sessionRepository = AppGraph.sessionRepository

    var isLoading by mutableStateOf(false)
    var errorMessage by mutableStateOf<String?>(null)

    // Ticket ativo (null enquanto o cliente ainda não retirou senha)
    var ticketToken by mutableStateOf<String?>(null)
    var senha by mutableStateOf<String?>(null)
    var tipo by mutableStateOf<String?>(null)
    var posicao by mutableStateOf<Int?>(null)
    var setorNome by mutableStateOf<String?>(null)
    var chamada by mutableStateOf(false)
    var finalizada by mutableStateOf(false)
    var operadorNome by mutableStateOf<String?>(null)
    var operadorFoto by mutableStateOf<String?>(null)
    var temPedido by mutableStateOf(false)
    var pedidoTexto by mutableStateOf<String?>(null)
    var pedidoStatusMensagem by mutableStateOf<String?>(null)

    init {
        viewModelScope.launch {
            val token = sessionRepository.getSessionToken()
            if (token != null) {
                SocketManager.connectWithSessionToken(NetworkModule.currentHttpBaseUrl(), token)
            }
        }
        viewModelScope.launch {
            SocketManager.events.collect { event -> handleEvent(event) }
        }
    }

    private fun handleEvent(event: SocketEvent) {
        val currentToken = ticketToken
        when (event) {
            is SocketEvent.SenhaChamada -> {
                if (event.ticketToken == currentToken) {
                    chamada = true
                    operadorNome = event.operadorNome
                    operadorFoto = event.operadorFoto
                    posicao = 0
                }
            }
            is SocketEvent.SenhaPosicao -> {
                if (event.ticketToken == currentToken) {
                    posicao = event.posicao
                    setorNome = event.setorNome ?: setorNome
                    temPedido = event.temPedido
                    pedidoTexto = event.pedido
                    if (event.status == "C") chamada = true
                    if (event.status == "F") finalizada = true
                }
            }
            is SocketEvent.PedidoStatus -> {
                if (event.ticketToken == currentToken) {
                    pedidoStatusMensagem = event.mensagem
                }
            }
            else -> Unit
        }
    }

    fun criarSenha(tipoSenha: String) {
        errorMessage = null
        isLoading = true
        viewModelScope.launch {
            try {
                val senhaCriada = NetworkModule.apiService().criarSenha(CriarSenhaRequest(tipoSenha))
                ticketToken = senhaCriada.token_unico
                senha = senhaCriada.senha
                tipo = senhaCriada.tipo
                chamada = false
                finalizada = false
                posicao = null
                senhaCriada.token_unico?.let { SocketManager.emitTicketSeguir(it) }
            } catch (e: Exception) {
                errorMessage = e.toUserMessage("Não foi possível retirar a senha.")
            } finally {
                isLoading = false
            }
        }
    }

    fun enviarPedido(texto: String) {
        val token = ticketToken ?: return
        if (texto.isBlank()) return
        viewModelScope.launch {
            try {
                NetworkModule.apiService().salvarPedido(SalvarPedidoRequest(token, texto))
                temPedido = true
                pedidoTexto = texto
            } catch (e: Exception) {
                errorMessage = e.toUserMessage("Não foi possível salvar o pedido.")
            }
        }
    }

    fun novaSenha() {
        ticketToken = null
        senha = null
        tipo = null
        posicao = null
        chamada = false
        finalizada = false
        operadorNome = null
        operadorFoto = null
        temPedido = false
        pedidoTexto = null
        pedidoStatusMensagem = null
    }

    override fun onCleared() {
        super.onCleared()
        SocketManager.disconnect()
    }
}
