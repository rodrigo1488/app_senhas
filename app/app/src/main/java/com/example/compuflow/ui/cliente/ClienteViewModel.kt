package com.example.compuflow.ui.cliente

import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.setValue
import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.example.compuflow.data.remote.NetworkModule
import com.example.compuflow.data.remote.dto.CriarSenhaRequest
import com.example.compuflow.data.remote.toUserMessage
import kotlinx.coroutines.launch

class ClienteViewModel : ViewModel() {
    var isLoading by mutableStateOf(false)
        private set
    var errorMessage by mutableStateOf<String?>(null)
        private set

    fun criarSenha(tipoSenha: String) {
        if (isLoading) return
        errorMessage = null
        isLoading = true
        viewModelScope.launch {
            try {
                NetworkModule.apiService().criarSenha(CriarSenhaRequest(tipoSenha))
            } catch (e: Exception) {
                errorMessage = e.toUserMessage("Não foi possível retirar a senha.")
            } finally {
                isLoading = false
            }
        }
    }
}
