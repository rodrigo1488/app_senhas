package com.example.compuflow.ui.tv

import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.setValue
import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.example.compuflow.AppGraph
import com.example.compuflow.data.remote.NetworkModule
import com.example.compuflow.data.remote.dto.AtendimentoDto
import com.example.compuflow.data.remote.dto.PropagandaImagemDto
import com.example.compuflow.data.remote.dto.SenhaDto
import com.example.compuflow.data.remote.dto.TvChamadaRecenteDto
import com.example.compuflow.data.remote.toUserMessage
import com.example.compuflow.realtime.SocketEvent
import com.example.compuflow.realtime.SocketManager
import kotlinx.coroutines.Job
import kotlinx.coroutines.channels.Channel
import kotlinx.coroutines.delay
import kotlinx.coroutines.flow.receiveAsFlow
import kotlinx.coroutines.isActive
import kotlinx.coroutines.launch

class TvViewModel : ViewModel() {
    private val sessionRepository = AppGraph.sessionRepository
    private val soundDeduplicator = CallSoundDeduplicator()
    private val _callSoundEvents = Channel<Unit>(capacity = Channel.CONFLATED)
    val callSoundEvents = _callSoundEvents.receiveAsFlow()

    var pendentes by mutableStateOf<List<SenhaDto>>(emptyList())
    var atendimentos by mutableStateOf<List<AtendimentoDto>>(emptyList())
    var chamadas by mutableStateOf<List<TvChamadaRecenteDto>>(emptyList())

    var ultimaChamadaSenha by mutableStateOf<String?>(null)
    var ultimaChamadaOperador by mutableStateOf<String?>(null)
    var ultimaChamadaOperadorFoto by mutableStateOf<String?>(null)

    var ultimaNormalSenha by mutableStateOf<String?>(null)
    var ultimaNormalFoto by mutableStateOf<String?>(null)
    var ultimaPreferencialSenha by mutableStateOf<String?>(null)
    var ultimaPreferencialFoto by mutableStateOf<String?>(null)

    var layoutTvWeb by mutableStateOf("propaganda")
    var orientacaoTv by mutableStateOf("horizontal")
    var imagens by mutableStateOf<List<PropagandaImagemDto>>(emptyList())
    var intervaloMs by mutableStateOf(15_000L)
    var imagemIndex by mutableStateOf(0)

    var errorMessage by mutableStateOf<String?>(null)

    private var rotationJob: Job? = null
    /** Playlist + intervalo. Poll/socket com o mesmo valor não reinicia o timer. */
    private var mediaFingerprint: String = ""
    private var lastAdvanceAtMs: Long = 0L

    val isFilaLayout: Boolean
        get() = layoutTvWeb == "fila"

    init {
        viewModelScope.launch {
            val token = sessionRepository.getSessionToken()
            if (token != null) {
                SocketManager.connectWithSessionToken(NetworkModule.currentHttpBaseUrl(), token)
            }
            refreshPainel(silent = false)
        }
        viewModelScope.launch {
            SocketManager.events.collect { event ->
                if (event is SocketEvent.Connected) {
                    refreshPainel(silent = true)
                } else {
                    handleEvent(event)
                }
            }
        }
        // Reserva se o socket não entregar fila/chamadas (túnel HTTPS).
        viewModelScope.launch {
            while (isActive) {
                delay(4_000)
                refreshFila(silent = true)
            }
        }
        viewModelScope.launch {
            while (isActive) {
                delay(60_000)
                refreshConfig(silent = true)
            }
        }
    }

    private suspend fun refreshPainel(silent: Boolean) {
        refreshFila(silent)
        refreshConfig(silent)
        refreshChamadas(silent)
    }

    private suspend fun refreshFila(silent: Boolean) {
        try {
            val fila = NetworkModule.apiService().estadoFila()
            pendentes = fila.pendentes
            atendimentos = fila.atendimentos
            syncFromAtendimentos(fila.atendimentos)
            if (!silent) errorMessage = null
        } catch (e: Exception) {
            if (!silent) errorMessage = e.toUserMessage("Não foi possível carregar a fila.")
        }
    }

    private suspend fun refreshChamadas(silent: Boolean) {
        try {
            chamadas = NetworkModule.apiService().tvChamadasRecentes().chamadas
        } catch (_: Exception) {
            if (!silent) {
                // Painel segue sem histórico até a primeira chamada ao vivo.
            }
        }
    }

    private suspend fun refreshConfig(silent: Boolean) {
        try {
            val config = NetworkModule.apiService().tvConfig()
            applyTvConfig(
                layout = config.layout_tv_web,
                orientacao = config.orientacao_tv,
                imgs = config.imagens,
                intervalo = config.intervalo_ms.coerceAtLeast(1_000L),
            )
        } catch (_: Exception) {
            if (!silent) {
                // Sem config de propaganda, mantém layout padrão.
            }
        }
    }

    private fun applyTvConfig(
        layout: String,
        orientacao: String,
        imgs: List<PropagandaImagemDto>,
        intervalo: Long,
    ) {
        layoutTvWeb = if (layout == "fila") "fila" else "propaganda"
        orientacaoTv = if (orientacao == "vertical") "vertical" else "horizontal"
        val fingerprint = buildString {
            append(intervalo)
            imgs.forEach { item ->
                append('|')
                append(item.id)
                append(':')
                append(item.arquivo)
                append(':')
                append(item.tipo)
            }
        }
        if (fingerprint == mediaFingerprint) return
        mediaFingerprint = fingerprint
        imagens = imgs
        intervaloMs = intervalo
        if (imgs.isEmpty()) {
            imagemIndex = 0
            rotationJob?.cancel()
            rotationJob = null
            return
        }
        if (imagemIndex >= imgs.size) imagemIndex = 0
        restartRotation()
    }

    private fun restartRotation() {
        rotationJob?.cancel()
        if (imagens.isEmpty()) return
        val atual = imagens.getOrNull(imagemIndex) ?: return
        if (atual.tipo.equals("video", ignoreCase = true)) return
        if (imagens.size <= 1) return
        rotationJob = viewModelScope.launch {
            delay(intervaloMs)
            imagemIndex = (imagemIndex + 1) % imagens.size
            restartRotation()
        }
    }

    fun onMediaEnded() {
        if (imagens.size <= 1) return
        val now = System.currentTimeMillis()
        if (now - lastAdvanceAtMs < 800L) return
        lastAdvanceAtMs = now
        imagemIndex = (imagemIndex + 1) % imagens.size
        restartRotation()
    }

    private fun syncFromAtendimentos(lista: List<AtendimentoDto>) {
        ultimaChamadaSenha = lista.firstOrNull()?.senha
        ultimaChamadaOperador = lista.firstOrNull()?.operador_nome
        ultimaChamadaOperadorFoto = lista.firstOrNull()?.operador_foto
        lista.firstOrNull { it.tipo == "normal" }?.let {
            ultimaNormalSenha = it.senha
            ultimaNormalFoto = it.operador_foto
        }
        lista.firstOrNull { it.tipo == "preferencial" }?.let {
            ultimaPreferencialSenha = it.senha
            ultimaPreferencialFoto = it.operador_foto
        }
    }

    private fun prependChamada(event: SocketEvent.SenhaChamada) {
        val next = TvChamadaRecenteDto(
            senha_id = event.senhaId ?: (System.currentTimeMillis() and 0x7fffffff).toInt(),
            senha = event.senha,
            tipo = event.tipo ?: "normal",
            operador_id = event.operadorId,
            operador_nome = event.operadorNome,
            operador_foto = event.operadorFoto,
            chamada_em = System.currentTimeMillis().toString(),
            status = "atual",
        )
        chamadas = listOf(next) + chamadas.filter { item ->
            if (event.senhaId != null) item.senha_id != event.senhaId else item.senha != event.senha
        }.take(7)
    }

    private fun handleEvent(event: SocketEvent) {
        when (event) {
            is SocketEvent.FilaAtualizada -> {
                pendentes = event.pendentes
                atendimentos = event.atendimentos
                syncFromAtendimentos(event.atendimentos)
            }
            is SocketEvent.SenhaChamada -> {
                ultimaChamadaSenha = event.senha
                ultimaChamadaOperador = event.operadorNome
                ultimaChamadaOperadorFoto = event.operadorFoto
                when (event.tipo) {
                    "preferencial" -> {
                        ultimaPreferencialSenha = event.senha
                        ultimaPreferencialFoto = event.operadorFoto
                    }
                    "normal" -> {
                        ultimaNormalSenha = event.senha
                        ultimaNormalFoto = event.operadorFoto
                    }
                    else -> Unit
                }
                prependChamada(event)
                if (soundDeduplicator.isNewCall(event.senha, event.senhaId)) {
                    _callSoundEvents.trySend(Unit)
                }
            }
            is SocketEvent.TvConfigAtualizada -> {
                applyTvConfig(
                    layout = event.layoutTvWeb,
                    orientacao = event.orientacaoTv,
                    imgs = event.imagens,
                    intervalo = event.intervaloMs,
                )
            }
            else -> Unit
        }
    }

    override fun onCleared() {
        super.onCleared()
        rotationJob?.cancel()
        _callSoundEvents.close()
        SocketManager.disconnect()
    }
}
