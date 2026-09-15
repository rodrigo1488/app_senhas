package com.example.compuflow.ui.login

import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.setValue
import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.example.compuflow.AppGraph
import com.example.compuflow.data.remote.NetworkModule
import com.example.compuflow.data.remote.dto.SetorLoginRequest
import com.example.compuflow.data.remote.toUserMessage
import kotlinx.coroutines.launch

class LoginViewModel : ViewModel() {
    private val sessionRepository = AppGraph.sessionRepository

    var serverUrl by mutableStateOf(NetworkModule.DEFAULT_BASE_URL)
    var codigoSetor by mutableStateOf("")
    var isLoading by mutableStateOf(false)
    var errorMessage by mutableStateOf<String?>(null)

    init {
        viewModelScope.launch {
            sessionRepository.getServerUrl()?.let { serverUrl = it }
        }
    }

    fun login(onSuccess: (setorNome: String) -> Unit) {
        if (codigoSetor.isBlank()) {
            errorMessage = "Digite o código do setor"
            return
        }
        if (serverUrl.isBlank()) {
            errorMessage = "Digite o endereço do servidor"
            return
        }
        errorMessage = null
        isLoading = true
        viewModelScope.launch {
            try {
                sessionRepository.saveServerUrl(serverUrl.trim())
                val response = NetworkModule.apiService().setorLogin(SetorLoginRequest(codigoSetor.trim()))
                sessionRepository.saveLoginSetor(
                    token = response.session_token,
                    setorId = response.setor.id,
                    setorNome = response.setor.nome,
                )
                onSuccess(response.setor.nome)
            } catch (e: Exception) {
                errorMessage = e.toUserMessage("Não foi possível entrar. Verifique o endereço do servidor e o código do setor.")
            } finally {
                isLoading = false
            }
        }
    }
}
