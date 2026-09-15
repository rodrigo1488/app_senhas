package com.example.compuflow.ui.operador

import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.setValue
import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.example.compuflow.AppGraph
import com.example.compuflow.data.remote.NetworkModule
import com.example.compuflow.data.remote.dto.AtendimentoDto
import com.example.compuflow.data.remote.dto.ChamarNovamenteRequest
import com.example.compuflow.data.remote.dto.ChamarProximaRequest
import com.example.compuflow.data.remote.dto.ConfirmarPedidoRequest
import com.example.compuflow.data.remote.dto.OperadorDto
import com.example.compuflow.data.remote.dto.Papel
import com.example.compuflow.data.remote.dto.SelecionarPapelRequest
import com.example.compuflow.data.remote.dto.SenhaDto
import com.example.compuflow.data.session.AuthState
import com.example.compuflow.data.remote.toUserMessage
import com.example.compuflow.realtime.SocketEvent
import com.example.compuflow.realtime.SocketManager
import kotlinx.coroutines.launch

class OperadorViewModel : ViewModel() {
    private val sessionRepository = AppGraph.sessionRepository

    var operadores by mutableStateOf<List<OperadorDto>>(emptyList())
        private set
    var modoIdentificacao by mutableStateOf("foto")
        private set

    var pendentes by mutableStateOf<List<SenhaDto>>(emptyList())
    var atendimentos by mutableStateOf<List<AtendimentoDto>>(emptyList())

    var atendimentoAtual by mutableStateOf<AtendimentoDto?>(null)
        private set
    var senhaPedidoSelecionada by mutableStateOf<SenhaDto?>(null)
        private set
    var identificacaoVisible by mutableStateOf(false)
        private set
    var pedidoDialogVisible by mutableStateOf(false)
        private set

    var isLoading by mutableStateOf(true)
    var errorMessage by mutableStateOf<String?>(null)
    var successMessage by mutableStateOf<String?>(null)
        private set
    private var tokenDoAtendimento: String? = null

    init {
        prepararTela()
        viewModelScope.launch {
            SocketManager.events.collect { event -> handleEvent(event) }
        }
    }

    private fun prepararTela() {
        viewModelScope.launch {
            try {
                if (sessionRepository.getOperadorId() != null) {
                    val livre = NetworkModule.apiService().liberarOperador()
                    sessionRepository.savePapel(livre.session_token, Papel.OPERADOR)
                }
                val operadoresResponse = NetworkModule.apiService().listarOperadores()
                operadores = operadoresResponse.operadores
                modoIdentificacao = operadoresResponse.modo_identificacao_operador
                val fila = NetworkModule.apiService().estadoFila()
                pendentes = fila.pendentes
                atendimentos = fila.atendimentos
                conectarSocketDaTela()
            } catch (e: Exception) {
                errorMessage = e.toUserMessage("Não foi possível carregar a fila.")
            } finally {
                isLoading = false
            }
        }
    }

    private suspend fun conectarSocketDaTela() {
        sessionRepository.getSessionToken()?.let { token ->
            SocketManager.connectWithSessionToken(NetworkModule.currentHttpBaseUrl(), token)
        }
    }

    private fun handleEvent(event: SocketEvent) {
        when (event) {
            is SocketEvent.FilaAtualizada -> {
                pendentes = event.pendentes
                atendimentos = event.atendimentos
            }
            else -> Unit
        }
    }

    fun abrirIdentificacao() {
        errorMessage = null
        successMessage = null
        identificacaoVisible = true
    }

    fun fecharIdentificacao() {
        if (!isLoading) identificacaoVisible = false
    }

    fun identificarPorFoto(operador: OperadorDto) {
        identificarEChamar(SelecionarPapelRequest(role = Papel.OPERADOR.valor, operador_id = operador.id))
    }

    fun identificarPorPin(pin: String) {
        if (pin.length != PIN_LENGTH) {
            errorMessage = "Digite um PIN de 4 números."
            return
        }
        identificarEChamar(SelecionarPapelRequest(role = Papel.OPERADOR.valor, pin = pin))
    }

    private fun identificarEChamar(identificacao: SelecionarPapelRequest) {
        errorMessage = null
        successMessage = null
        isLoading = true
        viewModelScope.launch {
            var tokenVinculado: String? = null
            val tokenLivre = sessionRepository.getSessionToken()
            try {
                val sessao = NetworkModule.apiService().selecionarPapel(identificacao)
                val operador = sessao.operador
                    ?: throw IllegalStateException("Operador não retornado pelo servidor")
                tokenVinculado = sessao.session_token
                AuthState.sessionToken = tokenVinculado
                val response = NetworkModule.apiService().chamarProxima(ChamarProximaRequest())
                val tokenAtivo = response.session_token ?: tokenVinculado
                AuthState.sessionToken = tokenAtivo
                identificacaoVisible = false
                successMessage = response.mensagem

                val senhaChamada = response.senha
                if (response.chamada_realizada) {
                    checkNotNull(senhaChamada) {
                        "Resposta inválida: chamada realizada sem dados da senha"
                    }
                    tokenDoAtendimento = tokenVinculado
                    val novoAtendimento = AtendimentoDto(
                        operador_id = operador.id,
                        operador_nome = operador.nome,
                        operador_foto = operador.foto_perfil,
                        senha = senhaChamada.senha,
                        tipo = senhaChamada.tipo,
                        senha_id = senhaChamada.id,
                        tem_pedido = senhaChamada.tem_pedido,
                        pedido = senhaChamada.pedido,
                        pedido_confirmado = senhaChamada.pedido_confirmado,
                    )
                    atendimentoAtual = novoAtendimento
                    atendimentos = listOf(novoAtendimento) +
                        atendimentos.filterNot { it.operador_id == operador.id }
                    pendentes = pendentes.filterNot { it.id == senhaChamada.id }
                } else {
                    check(senhaChamada == null) {
                        "Resposta inválida: senha retornada sem chamada realizada"
                    }
                    tokenDoAtendimento = null
                    atendimentoAtual = atendimentoAtual?.takeUnless {
                        it.operador_id == operador.id
                    }
                    atendimentos = atendimentos.filterNot { it.operador_id == operador.id }
                }

                sessionRepository.savePapel(tokenAtivo, Papel.OPERADOR)
                conectarSocketDaTela()
            } catch (e: Exception) {
                errorMessage = e.toUserMessage("Não foi possível chamar a próxima senha.")
                if (tokenVinculado != null) {
                    try {
                        val livre = NetworkModule.apiService().liberarOperador()
                        sessionRepository.savePapel(livre.session_token, Papel.OPERADOR)
                        conectarSocketDaTela()
                    } catch (_: Exception) {
                        AuthState.sessionToken = tokenLivre
                        conectarSocketDaTela()
                    }
                }
            } finally {
                isLoading = false
            }
        }
    }

    fun chamarNovamente(senhaId: Int) {
        val token = tokenDoAtendimento ?: return
        viewModelScope.launch {
            try {
                NetworkModule.apiService().chamarNovamente(
                    ChamarNovamenteRequest(senhaId),
                    "Bearer $token",
                )
            } catch (e: Exception) {
                errorMessage = e.toUserMessage("Não foi possível chamar novamente.")
            }
        }
    }

    fun verPedido(senha: SenhaDto) {
        if (!senha.tem_pedido) return
        senhaPedidoSelecionada = senha
        pedidoDialogVisible = true
    }

    fun verPedidoAtual() {
        val atual = atendimentoAtual ?: return
        verPedido(atual)
    }

    fun verPedido(atendimento: AtendimentoDto) {
        val atual = atendimento
        if (!atual.tem_pedido) return
        senhaPedidoSelecionada = SenhaDto(
            id = atual.senha_id ?: 0,
            senha = atual.senha,
            tipo = atual.tipo,
            tem_pedido = atual.tem_pedido,
            pedido = atual.pedido,
            pedido_confirmado = atual.pedido_confirmado,
        )
        pedidoDialogVisible = true
    }

    fun fecharPedido() {
        pedidoDialogVisible = false
        senhaPedidoSelecionada = null
    }

    fun confirmarPedido() {
        val selecionada = senhaPedidoSelecionada ?: return
        val atual = atendimentoAtual ?: return
        val token = tokenDoAtendimento ?: return
        if (selecionada.senha != atual.senha) return
        viewModelScope.launch {
            try {
                NetworkModule.apiService().confirmarPedido(
                    ConfirmarPedidoRequest(selecionada.senha),
                    "Bearer $token",
                )
                atendimentoAtual = atual.copy(pedido_confirmado = true)
                atendimentos = atendimentos.map {
                    if (it.senha_id == selecionada.id || it.senha == selecionada.senha) {
                        it.copy(pedido_confirmado = true)
                    } else {
                        it
                    }
                }
                fecharPedido()
            } catch (e: Exception) {
                errorMessage = e.toUserMessage("Não foi possível confirmar o pedido.")
            }
        }
    }

    override fun onCleared() {
        super.onCleared()
        SocketManager.disconnect()
    }

    companion object {
        const val PIN_LENGTH = 4
    }
}
