package com.example.appsenhas.ui.operador

import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.setValue
import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.example.appsenhas.AppGraph
import com.example.appsenhas.data.remote.NetworkModule
import com.example.appsenhas.data.remote.dto.OperadorDto
import com.example.appsenhas.data.remote.dto.Papel
import com.example.appsenhas.data.remote.dto.SelecionarPapelRequest
import com.example.appsenhas.data.remote.toUserMessage
import kotlinx.coroutines.launch

/** Tela compartilhada por Operador e Avaliação: "quem é você?" dentro do setor. */
class IdentificarOperadorViewModel : ViewModel() {
    private val sessionRepository = AppGraph.sessionRepository

    var operadores by mutableStateOf<List<OperadorDto>>(emptyList())
    var isLoading by mutableStateOf(true)
    var isSubmitting by mutableStateOf(false)
    var errorMessage by mutableStateOf<String?>(null)

    init {
        carregarOperadores()
    }

    private fun carregarOperadores() {
        isLoading = true
        viewModelScope.launch {
            try {
                operadores = NetworkModule.apiService().listarOperadores().operadores
            } catch (e: Exception) {
                errorMessage = e.toUserMessage("Não foi possível carregar os operadores.")
            } finally {
                isLoading = false
            }
        }
    }

    fun selecionarOperador(operador: OperadorDto, papel: Papel, onSuccess: () -> Unit) {
        errorMessage = null
        isSubmitting = true
        viewModelScope.launch {
            try {
                val response = NetworkModule.apiService().selecionarPapel(
                    SelecionarPapelRequest(role = papel.valor, operador_id = operador.id)
                )
                sessionRepository.savePapel(response.session_token, papel, operador.id, operador.nome)
                onSuccess()
            } catch (e: Exception) {
                errorMessage = e.toUserMessage("Não foi possível continuar.")
            } finally {
                isSubmitting = false
            }
        }
    }
}
