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
                if (event.operadorNome != null && event.operadorNome == meuOperadorNome) {
                    senhaChamadaAtual = event.senha
                    temPedidoAtual = event.temPedido
                    pedidoAtual = event.pedido
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
            } catch (e: Exception) {
                errorMessage = e.toUserMessage("Não foi possível carregar a fila.")
            }
        }
    }

    fun chamarProxima() {
        val operadorId = meuOperadorId ?: return
        errorMessage = null
        isLoading = true
        viewModelScope.launch {
            try {
                NetworkModule.apiService().chamarProxima(ChamarProximaRequest(operadorId))
                // Resultado chega via fila:atualizada / senha:chamada (socket) — ver protocolo.
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
            } catch (e: Exception) {
                errorMessage = e.toUserMessage("Não foi possível confirmar o pedido.")
            }
        }
    }

    override fun onCleared() {
        super.onCleared()
        SocketManager.disconnect()
    }
}
