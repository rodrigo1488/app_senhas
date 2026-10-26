package com.example.compuflow.ui.login

import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.setValue
import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.example.compuflow.AppGraph
import com.example.compuflow.data.remote.NetworkModule
import com.example.compuflow.data.remote.ServerDiscovery
import com.example.compuflow.data.remote.dto.SetorLoginRequest
import com.example.compuflow.data.remote.toUserMessage
import kotlinx.coroutines.Job
import kotlinx.coroutines.launch

class LoginViewModel : ViewModel() {
    private val sessionRepository = AppGraph.sessionRepository
    private var scanJob: Job? = null

    var serverUrl by mutableStateOf(NetworkModule.DEFAULT_BASE_URL)
    var codigoSetor by mutableStateOf("")
    var isLoading by mutableStateOf(false)
    var isScanning by mutableStateOf(false)
    var isConnecting by mutableStateOf(false)
    var errorMessage by mutableStateOf<String?>(null)
    var statusMessage by mutableStateOf<String?>(null)
    var servidoresEncontrados by mutableStateOf<List<String>>(emptyList())

    init {
        viewModelScope.launch {
            val saved = sessionRepository.getServerUrl()?.trim().orEmpty()
            val antigoPadrao =
                saved.startsWith("http://192.168.0.100") ||
                    saved == "192.168.0.100:5000" ||
                    saved.contains("senhas.compuchat.space")
            if (saved.isNotBlank() && !antigoPadrao) {
                serverUrl = saved
            }
        }
    }

    fun escanearRede() {
        if (isScanning || isLoading || isConnecting) return
        errorMessage = null
        statusMessage = "Procurando o servidor na rede…"
        isScanning = true
        scanJob?.cancel()
        scanJob = viewModelScope.launch {
            try {
                val encontrados = ServerDiscovery.scan()
                servidoresEncontrados = encontrados
                when {
                    encontrados.isEmpty() -> {
                        statusMessage = null
                        errorMessage = "Nenhum servidor encontrado na rede. Confira se o aparelho está no mesmo Wi‑Fi."
                    }
                    encontrados.size == 1 -> {
                        serverUrl = encontrados.first()
                        statusMessage = "Servidor encontrado. Toque em Conectar."
                    }
                    else -> {
                        serverUrl = encontrados.first()
                        statusMessage = "${encontrados.size} servidores encontrados. Escolha um e toque em Conectar."
                    }
                }
            } catch (e: Exception) {
                statusMessage = null
                errorMessage = e.toUserMessage("Não foi possível escanear a rede.")
            } finally {
                isScanning = false
            }
        }
    }

    fun conectar() {
        if (serverUrl.isBlank()) {
            errorMessage = "Digite o endereço do servidor ou escaneie a rede"
            return
        }
        if (isConnecting || isLoading || isScanning) return
        errorMessage = null
        statusMessage = "Conectando…"
        isConnecting = true
        viewModelScope.launch {
            try {
                sessionRepository.saveServerUrl(serverUrl.trim())
                val health = NetworkModule.apiService().health()
                if (!health.status.equals("ok", ignoreCase = true)) {
                    throw IllegalStateException("Resposta inesperada do servidor")
                }
                statusMessage = "Conectado. Informe o código do setor para entrar."
            } catch (e: Exception) {
                statusMessage = null
                errorMessage = e.toUserMessage("Não foi possível conectar ao servidor.")
            } finally {
                isConnecting = false
            }
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
        statusMessage = null
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
