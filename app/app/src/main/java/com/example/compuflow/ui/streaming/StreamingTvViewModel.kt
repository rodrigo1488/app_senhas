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
    var errorMessage by mutableStateOf<String?>(null)

    private var rotationJob: Job? = null

    val currentItem: StreamingQueueItemDto?
        get() = queue.getOrNull(imagemIndex)

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
                        applyQueue(event.queue)
                    }
                    else -> Unit
                }
            }
        }
        viewModelScope.launch {
            while (isActive) {
                delay(8_000)
                refreshFila(silent = true)
            }
        }
    }

    private suspend fun refreshFila(silent: Boolean = false) {
        try {
            val response = NetworkModule.apiService().tvStreamingFila()
            tvNome = response.dispositivo?.nome.orEmpty().ifBlank { tvNome }
            intervaloMs = response.intervalo_ms.coerceAtLeast(1_000L)
            applyQueue(response.queue)
            errorMessage = null
        } catch (e: Exception) {
            if (!silent) {
                errorMessage = e.toUserMessage("Não foi possível carregar as mídias.")
            }
        }
    }

    private fun applyQueue(items: List<StreamingQueueItemDto>) {
        queue = items.sortedBy { it.order }
        if (queue.isEmpty()) {
            imagemIndex = 0
            rotationJob?.cancel()
            return
        }
        if (imagemIndex >= queue.size) {
            imagemIndex = 0
        }
        restartRotation()
    }

    fun onMediaEnded() {
        advance()
    }

    private fun advance() {
        if (queue.isEmpty()) return
        imagemIndex = (imagemIndex + 1) % queue.size
        restartRotation()
    }

    private fun restartRotation() {
        rotationJob?.cancel()
        val item = currentItem ?: return
        if (item.type.equals("video", ignoreCase = true)) {
            // Vídeo avança no onEnded do player.
            return
        }
        val duration = item.duration.takeIf { it > 0 } ?: intervaloMs
        rotationJob = viewModelScope.launch {
            delay(duration)
            advance()
        }
    }

    override fun onCleared() {
        super.onCleared()
        rotationJob?.cancel()
        SocketManager.disconnect()
    }
}
