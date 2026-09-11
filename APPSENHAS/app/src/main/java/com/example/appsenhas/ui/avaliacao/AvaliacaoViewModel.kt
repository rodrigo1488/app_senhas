package com.example.appsenhas.ui.avaliacao

import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.setValue
import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.example.appsenhas.AppGraph
import com.example.appsenhas.data.remote.NetworkModule
import com.example.appsenhas.data.remote.dto.EnviarAvaliacaoRequest
import com.example.appsenhas.data.remote.toUserMessage
import com.example.appsenhas.realtime.SocketEvent
import com.example.appsenhas.realtime.SocketManager
import kotlinx.coroutines.launch

class AvaliacaoViewModel : ViewModel() {
    private val sessionRepository = AppGraph.sessionRepository

    private var meuOperadorId: Int? = null

    var operadorNome by mutableStateOf<String?>(null)
    var operadorFoto by mutableStateOf<String?>(null)
    var senhaId by mutableStateOf<Int?>(null)
    var senha by mutableStateOf<String?>(null)
    var enviado by mutableStateOf(false)
    var isLoading by mutableStateOf(true)
    var errorMessage by mutableStateOf<String?>(null)

    init {
        viewModelScope.launch {
            meuOperadorId = sessionRepository.getOperadorId()
            operadorNome = sessionRepository.getOperadorNome()

            val token = sessionRepository.getSessionToken()
            if (token != null) {
                SocketManager.connectWithSessionToken(NetworkModule.currentHttpBaseUrl(), token)
            }
            hidratarPendente()
        }
        viewModelScope.launch {
            SocketManager.events.collect { event -> handleEvent(event) }
        }
    }

    private fun handleEvent(event: SocketEvent) {
        if (event is SocketEvent.AvaliacaoSolicitada && event.operadorId == meuOperadorId) {
            senhaId = event.senhaId
            senha = event.senha
            operadorNome = event.operadorNome ?: operadorNome
            operadorFoto = event.operadorFoto ?: operadorFoto
            enviado = false
        }
    }

    private fun hidratarPendente() {
        val operadorId = meuOperadorId ?: return
        isLoading = true
        viewModelScope.launch {
            try {
                val pendente = NetworkModule.apiService().avaliacaoPendente(operadorId)
                senhaId = pendente.senha_id
                senha = pendente.senha
                if (pendente.operador_nome != null) operadorNome = pendente.operador_nome
                if (pendente.operador_foto != null) operadorFoto = pendente.operador_foto
            } catch (e: Exception) {
                errorMessage = e.toUserMessage("Não foi possível carregar a avaliação pendente.")
            } finally {
                isLoading = false
            }
        }
    }

    fun enviarAvaliacao(nota: Int) {
        val idSenha = senhaId ?: return
        val operadorId = meuOperadorId ?: return
        errorMessage = null
        viewModelScope.launch {
            try {
                NetworkModule.apiService().enviarAvaliacao(EnviarAvaliacaoRequest(idSenha, operadorId, nota))
                enviado = true
            } catch (e: Exception) {
                errorMessage = e.toUserMessage("Não foi possível enviar a avaliação.")
            }
        }
    }

    override fun onCleared() {
        super.onCleared()
        SocketManager.disconnect()
    }
}
