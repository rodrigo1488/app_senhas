package com.example.appsenhas.ui.tv

import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.setValue
import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.example.appsenhas.AppGraph
import com.example.appsenhas.data.remote.NetworkModule
import com.example.appsenhas.data.remote.dto.AtendimentoDto
import com.example.appsenhas.data.remote.dto.PropagandaImagemDto
import com.example.appsenhas.data.remote.dto.SenhaDto
import com.example.appsenhas.data.remote.toUserMessage
import com.example.appsenhas.realtime.SocketEvent
import com.example.appsenhas.realtime.SocketManager
import kotlinx.coroutines.Job
import kotlinx.coroutines.channels.Channel
import kotlinx.coroutines.delay
import kotlinx.coroutines.flow.receiveAsFlow
import kotlinx.coroutines.isActive
import kotlinx.coroutines.launch

class TvViewModel : ViewModel() {
    private val sessionRepository = AppGraph.sessionRepository
    private val soundDeduplicator = CallSoundDeduplicator()
    private val _callSoundEvents = Channel<Unit>(capacity = Channel.BUFFERED)
    val callSoundEvents = _callSoundEvents.receiveAsFlow()

    var pendentes by mutableStateOf<List<SenhaDto>>(emptyList())
    var atendimentos by mutableStateOf<List<AtendimentoDto>>(emptyList())

    var ultimaChamadaSenha by mutableStateOf<String?>(null)
    var ultimaChamadaOperador by mutableStateOf<String?>(null)
    var ultimaChamadaOperadorFoto by mutableStateOf<String?>(null)

    var ultimaNormalSenha by mutableStateOf<String?>(null)
    var ultimaPreferencialSenha by mutableStateOf<String?>(null)

    var propagandasAtivas by mutableStateOf(false)
    var imagens by mutableStateOf<List<PropagandaImagemDto>>(emptyList())
    var intervaloMs by mutableStateOf(15_000L)
    var imagemIndex by mutableStateOf(0)

    var errorMessage by mutableStateOf<String?>(null)

    private var rotationJob: Job? = null

    val showPropagandaLayout: Boolean
        get() = propagandasAtivas && imagens.isNotEmpty()

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
                syncFromAtendimentos(atendimentos)
            } catch (e: Exception) {
                errorMessage = e.toUserMessage("Não foi possível carregar a fila.")
            }
            try {
                val config = NetworkModule.apiService().tvConfig()
                applyTvConfig(
                    ativas = config.propagandas_ativas,
                    imgs = config.imagens,
                    intervalo = config.intervalo_ms.coerceAtLeast(1_000L),
                )
            } catch (_: Exception) {
                // Sem config de propaganda, mantém layout padrão.
            }
        }
        viewModelScope.launch {
            SocketManager.events.collect { event -> handleEvent(event) }
        }
    }

    private fun applyTvConfig(
        ativas: Boolean,
        imgs: List<PropagandaImagemDto>,
        intervalo: Long,
    ) {
        propagandasAtivas = ativas
        imagens = imgs
        intervaloMs = intervalo
        imagemIndex = 0
        restartRotation()
    }

    private fun restartRotation() {
        rotationJob?.cancel()
        if (!showPropagandaLayout) return
        rotationJob = viewModelScope.launch {
            while (isActive && imagens.size > 1) {
                delay(intervaloMs)
                imagemIndex = (imagemIndex + 1) % imagens.size
            }
        }
    }

    private fun syncFromAtendimentos(lista: List<AtendimentoDto>) {
        ultimaChamadaSenha = lista.firstOrNull()?.senha
        ultimaChamadaOperador = lista.firstOrNull()?.operador_nome
        ultimaChamadaOperadorFoto = lista.firstOrNull()?.operador_foto
        lista.firstOrNull { it.tipo == "normal" }?.let {
            ultimaNormalSenha = it.senha
        }
        lista.firstOrNull { it.tipo == "preferencial" }?.let {
            ultimaPreferencialSenha = it.senha
        }
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
                    "preferencial" -> ultimaPreferencialSenha = event.senha
                    "normal" -> ultimaNormalSenha = event.senha
                    else -> Unit
                }
                if (soundDeduplicator.isNewCall(event.senha)) {
                    _callSoundEvents.trySend(Unit)
                }
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
