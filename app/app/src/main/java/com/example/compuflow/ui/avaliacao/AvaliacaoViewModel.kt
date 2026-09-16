package com.example.compuflow.ui.avaliacao

import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableIntStateOf
import androidx.compose.runtime.mutableLongStateOf
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.setValue
import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.example.compuflow.AppGraph
import com.example.compuflow.data.remote.NetworkModule
import com.example.compuflow.data.remote.dto.EnviarAvaliacaoRequest
import com.example.compuflow.data.remote.dto.PropagandaImagemDto
import com.example.compuflow.data.remote.toUserMessage
import com.example.compuflow.realtime.SocketEvent
import com.example.compuflow.realtime.SocketManager
import kotlinx.coroutines.Job
import kotlinx.coroutines.delay
import kotlinx.coroutines.launch

enum class AvaliacaoFase {
    IDLE,
    RATING,
    THANKS,
}

class AvaliacaoViewModel : ViewModel() {
    private val sessionRepository = AppGraph.sessionRepository

    var fase by mutableStateOf(AvaliacaoFase.IDLE)
    var idleModo by mutableStateOf("propaganda") // propaganda | estatica
    var imagens by mutableStateOf<List<PropagandaImagemDto>>(emptyList())
    var intervaloMs by mutableLongStateOf(15_000L)
    var imagemIndex by mutableIntStateOf(0)

    var operadorId by mutableStateOf<Int?>(null)
    var operadorNome by mutableStateOf<String?>(null)
    var operadorFoto by mutableStateOf<String?>(null)
    var senhaId by mutableStateOf<Int?>(null)
    var senha by mutableStateOf<String?>(null)
    var isLoading by mutableStateOf(true)
    var errorMessage by mutableStateOf<String?>(null)

    private var rotationJob: Job? = null
    private var thanksJob: Job? = null

    val currentIdleItem: PropagandaImagemDto?
        get() = when {
            imagens.isEmpty() -> null
            idleModo == "estatica" -> imagens.firstOrNull()
            else -> imagens.getOrNull(imagemIndex)
        }

    init {
        viewModelScope.launch {
            idleModo = sessionRepository.getAvaliacaoIdleModo()
            val token = sessionRepository.getSessionToken()
            if (token != null) {
                SocketManager.connectWithSessionToken(NetworkModule.currentHttpBaseUrl(), token)
            }
            carregarIdleMidia()
            hidratarPendente()
        }
        viewModelScope.launch {
            SocketManager.events.collect { event -> handleEvent(event) }
        }
    }

    fun definirIdleModo(modo: String) {
        idleModo = if (modo == "estatica") "estatica" else "propaganda"
        viewModelScope.launch { sessionRepository.saveAvaliacaoIdleModo(idleModo) }
        restartRotation()
    }

    private fun handleEvent(event: SocketEvent) {
        when (event) {
            is SocketEvent.AvaliacaoSolicitada -> mostrarAvaliacao(
                senhaId = event.senhaId,
                senha = event.senha,
                operadorId = event.operadorId,
                operadorNome = event.operadorNome,
                operadorFoto = event.operadorFoto,
            )
            is SocketEvent.TvConfigAtualizada -> {
                imagens = event.imagens
                intervaloMs = event.intervaloMs
                if (imagemIndex >= imagens.size) imagemIndex = 0
                restartRotation()
            }
            else -> Unit
        }
    }

    private fun mostrarAvaliacao(
        senhaId: Int?,
        senha: String?,
        operadorId: Int?,
        operadorNome: String?,
        operadorFoto: String?,
    ) {
        if (senhaId == null) return
        thanksJob?.cancel()
        this.senhaId = senhaId
        this.senha = senha
        this.operadorId = operadorId
        this.operadorNome = operadorNome
        this.operadorFoto = operadorFoto
        fase = AvaliacaoFase.RATING
        rotationJob?.cancel()
    }

    private suspend fun carregarIdleMidia() {
        try {
            val config = NetworkModule.apiService().tvConfig()
            imagens = config.imagens
            intervaloMs = config.intervalo_ms.coerceAtLeast(1_000L)
            restartRotation()
        } catch (_: Exception) {
            // Idle sem mídia continua ok.
        }
    }

    private fun hidratarPendente() {
        isLoading = true
        viewModelScope.launch {
            try {
                val pendente = NetworkModule.apiService().avaliacaoPendente()
                if (pendente.senha_id != null) {
                    mostrarAvaliacao(
                        senhaId = pendente.senha_id,
                        senha = pendente.senha,
                        operadorId = pendente.operador_id,
                        operadorNome = pendente.operador_nome,
                        operadorFoto = pendente.operador_foto,
                    )
                } else {
                    fase = AvaliacaoFase.IDLE
                    restartRotation()
                }
            } catch (e: Exception) {
                errorMessage = e.toUserMessage("Não foi possível carregar a avaliação pendente.")
                fase = AvaliacaoFase.IDLE
            } finally {
                isLoading = false
            }
        }
    }

    fun enviarAvaliacao(nota: Int) {
        val idSenha = senhaId ?: return
        val idOperador = operadorId ?: return
        errorMessage = null
        viewModelScope.launch {
            try {
                NetworkModule.apiService().enviarAvaliacao(
                    EnviarAvaliacaoRequest(idSenha, idOperador, nota),
                )
                fase = AvaliacaoFase.THANKS
                thanksJob?.cancel()
                thanksJob = launch {
                    delay(2_500)
                    limparEVoltarIdle()
                }
            } catch (e: Exception) {
                errorMessage = e.toUserMessage("Não foi possível enviar a avaliação.")
            }
        }
    }

    private fun limparEVoltarIdle() {
        senhaId = null
        senha = null
        operadorId = null
        operadorFoto = null
        // Mantém nome só se quiser; limpa para não confundir idle.
        operadorNome = null
        fase = AvaliacaoFase.IDLE
        restartRotation()
    }

    fun onIdleMediaEnded() {
        if (fase != AvaliacaoFase.IDLE || idleModo == "estatica") return
        if (imagens.size <= 1) return
        imagemIndex = (imagemIndex + 1) % imagens.size
        restartRotation()
    }

    private fun restartRotation() {
        rotationJob?.cancel()
        if (fase != AvaliacaoFase.IDLE) return
        if (idleModo == "estatica") return
        if (imagens.size <= 1) return
        val item = currentIdleItem ?: return
        if (item.tipo.equals("video", ignoreCase = true)) return
        rotationJob = viewModelScope.launch {
            delay(intervaloMs)
            onIdleMediaEnded()
        }
    }

    override fun onCleared() {
        super.onCleared()
        rotationJob?.cancel()
        thanksJob?.cancel()
        SocketManager.disconnect()
    }
}
