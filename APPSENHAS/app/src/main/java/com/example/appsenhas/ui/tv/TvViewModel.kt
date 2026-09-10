package com.example.appsenhas.ui.tv

import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.setValue
import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.example.appsenhas.AppGraph
import com.example.appsenhas.data.remote.NetworkModule
import com.example.appsenhas.data.remote.dto.AtendimentoDto
import com.example.appsenhas.data.remote.dto.SenhaDto
import com.example.appsenhas.data.remote.toUserMessage
import com.example.appsenhas.realtime.SocketEvent
import com.example.appsenhas.realtime.SocketManager
import kotlinx.coroutines.launch

class TvViewModel : ViewModel() {
    private val sessionRepository = AppGraph.sessionRepository

    var pendentes by mutableStateOf<List<SenhaDto>>(emptyList())
    var atendimentos by mutableStateOf<List<AtendimentoDto>>(emptyList())

    var ultimaChamadaSenha by mutableStateOf<String?>(null)
    var ultimaChamadaOperador by mutableStateOf<String?>(null)

    var errorMessage by mutableStateOf<String?>(null)

    init {
        viewModelScope.launch {
            val token = sessionRepository.getSessionToken()
            if (token != null) {
                SocketManager.connectWithSessionToken(NetworkModule.currentHttpBaseUrl(), token)
            }
            try {
                val fila = NetworkModule.apiService().estadoFila()
                pendentes = fila.pendentes
                atendimentos = fila.atendimentos
                ultimaChamadaSenha = atendimentos.firstOrNull()?.senha
                ultimaChamadaOperador = atendimentos.firstOrNull()?.operador_nome
            } catch (e: Exception) {
                errorMessage = e.toUserMessage("Não foi possível carregar a fila.")
            }
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
                ultimaChamadaSenha = event.senha
                ultimaChamadaOperador = event.operadorNome
            }
            else -> Unit
        }
    }

    override fun onCleared() {
        super.onCleared()
        SocketManager.disconnect()
    }
}
