package com.example.appsenhas.ui.modo

import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.setValue
import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.example.appsenhas.AppGraph
import com.example.appsenhas.data.remote.NetworkModule
import com.example.appsenhas.data.remote.dto.Papel
import com.example.appsenhas.data.remote.dto.SelecionarPapelRequest
import com.example.appsenhas.data.remote.toUserMessage
import kotlinx.coroutines.launch

class SelecionarModoViewModel : ViewModel() {
    private val sessionRepository = AppGraph.sessionRepository

    var isLoading by mutableStateOf(false)
    var errorMessage by mutableStateOf<String?>(null)

    /** Usado por Cliente e TV, que não precisam identificar um operador antes. */
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
}
