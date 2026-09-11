package com.example.appsenhas.ui.cliente

import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.setValue
import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.example.appsenhas.data.remote.NetworkModule
import com.example.appsenhas.data.remote.dto.CriarSenhaRequest
import com.example.appsenhas.data.remote.toUserMessage
import kotlinx.coroutines.delay
import kotlinx.coroutines.launch

class ClienteViewModel : ViewModel() {
    var isLoading by mutableStateOf(false)
        private set
    var errorMessage by mutableStateOf<String?>(null)
        private set
    var senhaEmitida by mutableStateOf<String?>(null)
        private set

    fun criarSenha(tipoSenha: String) {
        if (isLoading) return
        errorMessage = null
        isLoading = true
        viewModelScope.launch {
            try {
                val senhaCriada = NetworkModule.apiService().criarSenha(CriarSenhaRequest(tipoSenha))
                val senha = senhaCriada.senha
                senhaEmitida = senha
                isLoading = false
                delay(2_500)
                if (senhaEmitida == senha) senhaEmitida = null
            } catch (e: Exception) {
                errorMessage = e.toUserMessage("Não foi possível retirar a senha.")
            } finally {
                isLoading = false
            }
        }
    }
}
