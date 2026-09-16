package com.example.compuflow.ui.modo

import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.setValue
import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.example.compuflow.AppGraph
import com.example.compuflow.data.remote.NetworkModule
import com.example.compuflow.data.remote.dto.Papel
import com.example.compuflow.data.remote.dto.SelecionarPapelRequest
import com.example.compuflow.data.remote.dto.StreamingEntrarRequest
import com.example.compuflow.data.remote.toUserMessage
import kotlinx.coroutines.launch

class SelecionarModoViewModel : ViewModel() {
    private val sessionRepository = AppGraph.sessionRepository

    var isLoading by mutableStateOf(false)
    var errorMessage by mutableStateOf<String?>(null)

    /** Usado por Cliente, TV e Avaliação (tablet do setor, sem escolher operador). */
    fun selecionarPapelSimples(papel: Papel, onSuccess: () -> Unit) {
        errorMessage = null
        isLoading = true
        viewModelScope.launch {
            try {
                val response = NetworkModule.apiService().selecionarPapel(SelecionarPapelRequest(role = papel.valor))
                sessionRepository.savePapel(response.session_token, papel)
                onSuccess()
            } catch (e: Exception) {
                errorMessage = e.toUserMessage("Não foi possível continuar.")
            } finally {
                isLoading = false
            }
        }
    }

    /** Registra TV de propagandas com nome do setor (ou '2 Nome', '3 Nome'…). */
    fun entrarTvPropagandas(onSuccess: () -> Unit) {
        errorMessage = null
        isLoading = true
        viewModelScope.launch {
            try {
                val deviceId = sessionRepository.getOrCreateDeviceId()
                val response = NetworkModule.apiService().tvStreamingEntrar(
                    StreamingEntrarRequest(
                        device_id = deviceId,
                        device_name = "Android",
                    ),
                )
                sessionRepository.savePapel(response.session_token, Papel.STREAMING)
                onSuccess()
            } catch (e: Exception) {
                errorMessage = e.toUserMessage("Não foi possível abrir a TV de propagandas.")
            } finally {
                isLoading = false
            }
        }
    }
}
