package com.example.appsenhas.ui.operador

import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.setValue
import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.example.appsenhas.AppGraph
import com.example.appsenhas.data.remote.NetworkModule
import com.example.appsenhas.data.remote.dto.AtendimentoDto
import com.example.appsenhas.data.remote.dto.ChamarNovamenteRequest
import com.example.appsenhas.data.remote.dto.ChamarProximaRequest
import com.example.appsenhas.data.remote.dto.ConfirmarPedidoRequest
import com.example.appsenhas.data.remote.dto.SenhaDto
import com.example.appsenhas.data.remote.toUserMessage
import com.example.appsenhas.realtime.SocketEvent
import com.example.appsenhas.realtime.SocketManager
import kotlinx.coroutines.launch

class OperadorViewModel : ViewModel() {
    private val sessionRepository = AppGraph.sessionRepository

    var meuOperadorId: Int? = null
        private set
    var meuOperadorNome: String? = null
        private set

    var pendentes by mutableStateOf<List<SenhaDto>>(emptyList())
    var atendimentos by mutableStateOf<List<AtendimentoDto>>(emptyList())

    var senhaChamadaAtual by mutableStateOf<String?>(null)
    var pedidoAtual by mutableStateOf<String?>(null)
    var temPedidoAtual by mutableStateOf(false)
    var pedidoDialogVisible by mutableStateOf(false)
        private set

    var isLoading by mutableStateOf(false)
    var errorMessage by mutableStateOf<String?>(null)

    val meuAtendimento: AtendimentoDto?
        get() = atendimentos.firstOrNull { it.operador_id == meuOperadorId }

    init {
        viewModelScope.launch {
            meuOperadorId = sessionRepository.getOperadorId()
            meuOperadorNome = sessionRepository.getOperadorNome()

            val token = sessionRepository.getSessionToken()
            if (token != null) {
                SocketManager.connectWithSessionToken(NetworkModule.currentHttpBaseUrl(), token)
            }
            hidratarFila()
        }
        viewModelScope.launch {
            SocketManager.events.collect { event -> handleEvent(event) }
        }
    }

    private fun handleEvent(event: SocketEvent) {
        when (event) {
            is SocketEvent.FilaAtualizada -> {
                pendentes = event.pendentes
                atendimentos = event.atendimentos
            }
            is SocketEvent.SenhaChamada -> {
                if (event.operadorId != null && event.operadorId == meuOperadorId) {
                    senhaChamadaAtual = event.senha
                    temPedidoAtual = event.temPedido
                    pedidoAtual = event.pedido
                    pedidoDialogVisible = event.temPedido
                }
            }
            else -> Unit
        }
    }

    private fun hidratarFila() {
        viewModelScope.launch {
            try {
                val fila = NetworkModule.apiService().estadoFila()
                pendentes = fila.pendentes
                atendimentos = fila.atendimentos
                val atual = NetworkModule.apiService().atendimentoAtual()
                if (atual.senha != null) {
                    senhaChamadaAtual = atual.senha
                    temPedidoAtual = atual.tem_pedido
                    pedidoAtual = atual.pedido
                    pedidoDialogVisible = atual.tem_pedido && !atual.pedido_confirmado
                }
            } catch (e: Exception) {
                errorMessage = e.toUserMessage("Não foi possível carregar a fila.")
            }
        }
    }

    fun chamarProxima() {
        if (meuOperadorId == null) return
        errorMessage = null
        isLoading = true
        viewModelScope.launch {
            try {
                val response = NetworkModule.apiService().chamarProxima(ChamarProximaRequest())
                senhaChamadaAtual = response.senha.senha
                temPedidoAtual = response.senha.tem_pedido
                pedidoAtual = response.senha.pedido
                pedidoDialogVisible = response.senha.tem_pedido
            } catch (e: Exception) {
                errorMessage = e.toUserMessage("Não foi possível chamar a próxima senha.")
            } finally {
                isLoading = false
            }
        }
    }

    fun chamarNovamente(senhaId: Int) {
        viewModelScope.launch {
            try {
                NetworkModule.apiService().chamarNovamente(ChamarNovamenteRequest(senhaId))
            } catch (e: Exception) {
                errorMessage = e.toUserMessage("Não foi possível chamar novamente.")
            }
        }
    }

    fun confirmarPedido() {
        val senha = senhaChamadaAtual ?: return
        viewModelScope.launch {
            try {
                NetworkModule.apiService().confirmarPedido(ConfirmarPedidoRequest(senha))
                pedidoDialogVisible = false
            } catch (e: Exception) {
                errorMessage = e.toUserMessage("Não foi possível confirmar o pedido.")
            }
        }
    }

    fun trocarOperador(onSuccess: () -> Unit) {
        viewModelScope.launch {
            try {
                val response = NetworkModule.apiService().liberarOperador()
                sessionRepository.saveGenericSession(response.session_token)
                SocketManager.disconnect()
                onSuccess()
            } catch (e: Exception) {
                errorMessage = e.toUserMessage("Não foi possível trocar o operador.")
            }
        }
    }

    override fun onCleared() {
        super.onCleared()
        SocketManager.disconnect()
    }
}
