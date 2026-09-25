package com.example.compuflow.ui.streaming

import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableIntStateOf
import androidx.compose.runtime.mutableLongStateOf
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.setValue
import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.example.compuflow.AppGraph
import com.example.compuflow.data.remote.NetworkModule
import com.example.compuflow.data.remote.dto.StreamingQueueItemDto
import com.example.compuflow.data.remote.toUserMessage
import com.example.compuflow.realtime.SocketEvent
import com.example.compuflow.realtime.SocketManager
import com.example.compuflow.ui.common.normalizeRotation
import kotlinx.coroutines.Job
import kotlinx.coroutines.delay
import kotlinx.coroutines.isActive
import kotlinx.coroutines.launch

class StreamingTvViewModel : ViewModel() {
    private val sessionRepository = AppGraph.sessionRepository

    var tvNome by mutableStateOf("")
    var queue by mutableStateOf<List<StreamingQueueItemDto>>(emptyList())
    var intervaloMs by mutableLongStateOf(15_000L)
    var imagemIndex by mutableIntStateOf(0)
    var rotacaoTv by mutableIntStateOf(0)
    var previewItem by mutableStateOf<StreamingQueueItemDto?>(null)
    var errorMessage by mutableStateOf<String?>(null)

    private var rotationJob: Job? = null
    private var previewJob: Job? = null
    /** Evita reiniciar o timer a cada poll (travava na 1ª mídia). */
    private var queueFingerprint: String = ""

    val currentItem: StreamingQueueItemDto?
        get() = previewItem ?: queue.getOrNull(imagemIndex)

    init {
        viewModelScope.launch {
            val token = sessionRepository.getSessionToken()
            if (token != null) {
                SocketManager.connectWithSessionToken(NetworkModule.currentHttpBaseUrl(), token)
            }
            refreshFila()
        }
        viewModelScope.launch {
            SocketManager.events.collect { event ->
                when (event) {
                    is SocketEvent.QueueUpdated -> {
                        applyRotacao(event.rotacaoTv, event.orientacaoTv)
                        applyQueue(event.queue)
                    }
                    is SocketEvent.MediaPreview -> {
                        applyRotacao(event.rotacaoTv, event.orientacaoTv)
                        showPreview(event.item, event.durationMs)
                    }
                    is SocketEvent.Connected -> refreshFila(silent = true)
                    else -> Unit
                }
            }
        }
        // Poll de reserva se o socket não entregar queue_updated.
        viewModelScope.launch {
            while (isActive) {
                delay(5_000)
                refreshFila(silent = true)
            }
        }
    }

    private suspend fun refreshFila(silent: Boolean = false) {
        try {
            val response = NetworkModule.apiService().tvStreamingFila()
            tvNome = response.dispositivo?.nome.orEmpty().ifBlank { tvNome }
            intervaloMs = response.intervalo_ms.coerceAtLeast(1_000L)
            applyRotacao(response.rotacao_tv, response.orientacao_tv)
            applyQueue(response.queue)
            errorMessage = null
        } catch (e: Exception) {
            if (!silent) {
                errorMessage = e.toUserMessage("Não foi possível carregar as mídias.")
            }
        }
    }

    private fun applyRotacao(rotacao: Int?, orientacao: String?) {
        val normalized = normalizeRotation(rotacao ?: 0)
        // APIs antigas sem rotacao_tv: kotlinx defaulta 0; vertical legado → 90.
        rotacaoTv = if (normalized == 0 && orientacao.equals("vertical", ignoreCase = true)) {
            90
        } else {
            normalized
        }
    }

    private fun showPreview(item: StreamingQueueItemDto, durationMs: Long) {
        previewJob?.cancel()
        rotationJob?.cancel()
        previewItem = item
        val duration = durationMs.coerceAtLeast(3_000L)
        if (item.type.equals("video", ignoreCase = true)) {
            // Vídeo encerra no onEnded do player; timeout de segurança.
            previewJob = viewModelScope.launch {
                delay(duration.coerceAtMost(120_000L))
                clearPreview()
            }
            return
        }
        previewJob = viewModelScope.launch {
            delay(duration)
            clearPreview()
        }
    }

    fun onPreviewEnded() {
        clearPreview()
    }

    private fun clearPreview() {
        previewJob?.cancel()
        previewJob = null
        if (previewItem == null) return
        previewItem = null
        restartRotation()
    }

    private fun applyQueue(items: List<StreamingQueueItemDto>) {
        val sorted = items.sortedBy { it.order }
        val fingerprint = sorted.joinToString("|") { "${it.path}\u0000${it.type}\u0000${it.duration}" }
        val changed = fingerprint != queueFingerprint

        queue = sorted

        if (sorted.isEmpty()) {
            queueFingerprint = ""
            imagemIndex = 0
            if (previewItem == null) {
                rotationJob?.cancel()
                rotationJob = null
            }
            return
        }

        if (changed) {
            queueFingerprint = fingerprint
            imagemIndex = 0
            if (previewItem == null) restartRotation()
            return
        }

        if (imagemIndex >= sorted.size) {
            imagemIndex = 0
            if (previewItem == null) restartRotation()
        }
    }

    fun onMediaEnded() {
        if (previewItem != null) {
            clearPreview()
            return
        }
        advance()
    }

    private fun advance() {
        if (queue.isEmpty()) return
        imagemIndex = (imagemIndex + 1) % queue.size
        restartRotation()
    }

    private fun restartRotation() {
        rotationJob?.cancel()
        if (previewItem != null) return
        val item = queue.getOrNull(imagemIndex) ?: return
        if (item.type.equals("video", ignoreCase = true)) {
            return
        }
        if (queue.size <= 1) return
        val duration = item.duration.takeIf { it > 0 } ?: intervaloMs
        rotationJob = viewModelScope.launch {
            delay(duration.coerceAtLeast(1_000L))
            advance()
        }
    }

    override fun onCleared() {
        super.onCleared()
        rotationJob?.cancel()
        previewJob?.cancel()
        SocketManager.disconnect()
    }
}
