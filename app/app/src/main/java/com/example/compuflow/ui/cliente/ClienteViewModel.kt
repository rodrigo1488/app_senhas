package com.example.compuflow.ui.cliente

import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableIntStateOf
import androidx.compose.runtime.mutableLongStateOf
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.setValue
import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.example.compuflow.AppGraph
import com.example.compuflow.data.remote.NetworkModule
import com.example.compuflow.data.remote.dto.CriarSenhaRequest
import com.example.compuflow.data.remote.dto.PropagandaImagemDto
import com.example.compuflow.data.remote.toUserMessage
import com.example.compuflow.print.ThermalNetworkPrinter
import com.example.compuflow.realtime.SocketEvent
import com.example.compuflow.realtime.SocketManager
import kotlinx.coroutines.Job
import kotlinx.coroutines.delay
import kotlinx.coroutines.launch

class ClienteViewModel : ViewModel() {
    private val sessionRepository = AppGraph.sessionRepository

    var isLoading by mutableStateOf(false)
        private set
    var errorMessage by mutableStateOf<String?>(null)
        private set
    var statusMessage by mutableStateOf<String?>(null)
        private set
    var imagens by mutableStateOf<List<PropagandaImagemDto>>(emptyList())
        private set
    var intervaloMs by mutableLongStateOf(15_000L)
        private set
    var imagemIndex by mutableIntStateOf(0)
        private set

    private var rotationJob: Job? = null

    val currentItem: PropagandaImagemDto?
        get() = imagens.getOrNull(imagemIndex)

    init {
        viewModelScope.launch {
            val token = sessionRepository.getSessionToken()
            if (token != null) {
                SocketManager.connectWithSessionToken(NetworkModule.currentHttpBaseUrl(), token)
            }
            carregarMidias()
        }
        viewModelScope.launch {
            SocketManager.events.collect { event ->
                if (event is SocketEvent.ClienteConfigAtualizada) {
                    applyConfig(event.imagens, event.intervaloMs)
                }
            }
        }
    }

    fun criarSenha(tipoSenha: String) {
        if (isLoading) return
        errorMessage = null
        statusMessage = null
        isLoading = true
        viewModelScope.launch {
            try {
                val criada = NetworkModule.apiService().criarSenha(CriarSenhaRequest(tipoSenha))
                val printResult = ThermalNetworkPrinter.enviarSeNecessario(criada.impressao)
                if (printResult.isFailure) {
                    errorMessage = printResult.exceptionOrNull()?.message
                        ?: "Senha gerada, mas a impressão falhou."
                } else if (criada.impressao?.via_cliente == true) {
                    statusMessage = "Senha ${criada.senha} impressa"
                }
            } catch (e: Exception) {
                errorMessage = e.toUserMessage("Não foi possível retirar a senha.")
            } finally {
                isLoading = false
            }
        }
    }

    fun onMediaEnded() {
        if (imagens.size <= 1) return
        imagemIndex = (imagemIndex + 1) % imagens.size
        restartRotation()
    }

    private suspend fun carregarMidias() {
        try {
            val config = NetworkModule.apiService().clienteConfig()
            applyConfig(config.imagens, config.intervalo_ms.coerceAtLeast(1_000L))
        } catch (_: Exception) {
            // Sem mídia continua a tela de retirada como hoje.
        }
    }

    private fun applyConfig(imgs: List<PropagandaImagemDto>, intervalo: Long) {
        imagens = imgs
        intervaloMs = intervalo
        imagemIndex = if (imgs.isEmpty()) 0 else imagemIndex % imgs.size
        restartRotation()
    }

    private fun restartRotation() {
        rotationJob?.cancel()
        if (imagens.size <= 1) return
        val atual = imagens.getOrNull(imagemIndex) ?: return
        if (atual.tipo.equals("video", ignoreCase = true)) return
        rotationJob = viewModelScope.launch {
            delay(intervaloMs)
            onMediaEnded()
        }
    }

    override fun onCleared() {
        super.onCleared()
        rotationJob?.cancel()
        SocketManager.disconnect()
    }
}
