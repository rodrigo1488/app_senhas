package com.example.compuflow.ui.tv

import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.setValue
import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.example.compuflow.AppGraph
import com.example.compuflow.data.remote.NetworkModule
import com.example.compuflow.data.remote.dto.AtendimentoDto
import com.example.compuflow.data.remote.dto.PropagandaImagemDto
import com.example.compuflow.data.remote.dto.SenhaDto
import com.example.compuflow.data.remote.dto.TvChamadaRecenteDto
import com.example.compuflow.data.remote.toUserMessage
import com.example.compuflow.realtime.SocketEvent
import com.example.compuflow.realtime.SocketManager
import kotlinx.coroutines.Job
import kotlinx.coroutines.channels.Channel
import kotlinx.coroutines.delay
import kotlinx.coroutines.flow.receiveAsFlow
import kotlinx.coroutines.isActive
import kotlinx.coroutines.launch

class TvViewModel : ViewModel() {
    private val sessionRepository = AppGraph.sessionRepository
    private val soundDeduplicator = CallSoundDeduplicator()
    private val _callSoundEvents = Channel<Unit>(capacity = Channel.CONFLATED)
    val callSoundEvents = _callSoundEvents.receiveAsFlow()

    var pendentes by mutableStateOf<List<SenhaDto>>(emptyList())
    var atendimentos by mutableStateOf<List<AtendimentoDto>>(emptyList())
    var chamadas by mutableStateOf<List<TvChamadaRecenteDto>>(emptyList())

    var ultimaChamadaSenha by mutableStateOf<String?>(null)
    var ultimaChamadaOperador by mutableStateOf<String?>(null)
    var ultimaChamadaOperadorFoto by mutableStateOf<String?>(null)

    var ultimaNormalSenha by mutableStateOf<String?>(null)
    var ultimaNormalFoto by mutableStateOf<String?>(null)
    var ultimaPreferencialSenha by mutableStateOf<String?>(null)
    var ultimaPreferencialFoto by mutableStateOf<String?>(null)

    private var ultimaChamadaEm: String? = null
    private var ultimaNormalEm: String? = null
    private var ultimaPreferencialEm: String? = null
    private var ultimaNormalId: Int? = null
    private var ultimaPreferencialId: Int? = null

    var layoutTvWeb by mutableStateOf("propaganda")
    var orientacaoTv by mutableStateOf("horizontal")
    var posicaoSenhasTv by mutableStateOf("superior")
    var somChamada by mutableStateOf<String?>(null)
    var imagens by mutableStateOf<List<PropagandaImagemDto>>(emptyList())
    var intervaloMs by mutableStateOf(15_000L)
    var imagemIndex by mutableStateOf(0)

    var errorMessage by mutableStateOf<String?>(null)

    private var rotationJob: Job? = null
    /** Playlist + intervalo. Poll/socket com o mesmo valor não reinicia o timer. */
    private var mediaFingerprint: String = ""
    private var lastAdvanceAtMs: Long = 0L

    val isFilaLayout: Boolean
        get() = layoutTvWeb == "fila"

    init {
        viewModelScope.launch {
            val token = sessionRepository.getSessionToken()
            if (token != null) {
                SocketManager.connectWithSessionToken(NetworkModule.currentHttpBaseUrl(), token)
            }
            refreshPainel(silent = false)
        }
        viewModelScope.launch {
            SocketManager.events.collect { event ->
                if (event is SocketEvent.Connected) {
                    refreshPainel(silent = true)
                } else {
                    handleEvent(event)
                }
            }
        }
        // Reserva se o socket não entregar fila/chamadas (túnel HTTPS).
        viewModelScope.launch {
            while (isActive) {
                delay(4_000)
                refreshFila(silent = true)
                refreshChamadas(silent = true)
            }
        }
        viewModelScope.launch {
            while (isActive) {
                delay(60_000)
                refreshConfig(silent = true)
            }
        }
    }

    private suspend fun refreshPainel(silent: Boolean) {
        refreshFila(silent)
        refreshConfig(silent)
        refreshChamadas(silent)
    }

    private suspend fun refreshFila(silent: Boolean) {
        try {
            val fila = NetworkModule.apiService().estadoFila()
            pendentes = fila.pendentes
            atendimentos = fila.atendimentos
            syncFromAtendimentos(fila.atendimentos)
            if (!silent) errorMessage = null
        } catch (e: Exception) {
            if (!silent) errorMessage = e.toUserMessage("Não foi possível carregar a fila.")
        }
    }

    private suspend fun refreshChamadas(silent: Boolean) {
        try {
            chamadas = mesclarChamadas(chamadas, NetworkModule.apiService().tvChamadasRecentes().chamadas)
        } catch (_: Exception) {
            if (!silent) {
                // Painel segue sem histórico até a primeira chamada ao vivo.
            }
        }
    }

    private suspend fun refreshConfig(silent: Boolean) {
        try {
            val config = NetworkModule.apiService().tvConfig()
            applyTvConfig(
                layout = config.layout_tv_web,
                orientacao = config.orientacao_tv,
                posicao = config.posicao_senhas_tv,
                imgs = config.imagens,
                intervalo = config.intervalo_ms.coerceAtLeast(1_000L),
                som = config.som_chamada,
            )
        } catch (_: Exception) {
            if (!silent) {
                // Sem config de propaganda, mantém layout padrão.
            }
        }
    }

    private fun applyTvConfig(
        layout: String,
        orientacao: String,
        posicao: String,
        imgs: List<PropagandaImagemDto>,
        intervalo: Long,
        som: String? = null,
    ) {
        layoutTvWeb = if (layout == "fila") "fila" else "propaganda"
        orientacaoTv = if (orientacao == "vertical") "vertical" else "horizontal"
        posicaoSenhasTv = if (posicao == "inferior") "inferior" else "superior"
        somChamada = som?.trim()?.takeIf { it.isNotEmpty() }
        val fingerprint = buildString {
            append(intervalo)
            imgs.forEach { item ->
                append('|')
                append(item.id)
                append(':')
                append(item.arquivo)
                append(':')
                append(item.tipo)
            }
        }
        if (fingerprint == mediaFingerprint) return
        mediaFingerprint = fingerprint
        imagens = imgs
        intervaloMs = intervalo
        if (imgs.isEmpty()) {
            imagemIndex = 0
            rotationJob?.cancel()
            rotationJob = null
            return
        }
        if (imagemIndex >= imgs.size) imagemIndex = 0
        restartRotation()
    }

    private fun restartRotation() {
        rotationJob?.cancel()
        if (imagens.isEmpty()) return
        val atual = imagens.getOrNull(imagemIndex) ?: return
        if (atual.tipo.equals("video", ignoreCase = true)) return
        if (imagens.size <= 1) return
        rotationJob = viewModelScope.launch {
            delay(intervaloMs)
            imagemIndex = (imagemIndex + 1) % imagens.size
            restartRotation()
        }
    }

    fun onMediaEnded() {
        if (imagens.size <= 1) return
        val now = System.currentTimeMillis()
        if (now - lastAdvanceAtMs < 800L) return
        lastAdvanceAtMs = now
        imagemIndex = (imagemIndex + 1) % imagens.size
        restartRotation()
    }

    private fun syncFromAtendimentos(lista: List<AtendimentoDto>) {
        // Última chamada do setor: horário + ordem de solicitação (atendimento_id),
        // nunca o id da senha (preferencial pode ter id maior e “ganhar” indevido).
        val porChamada = compareBy<AtendimentoDto>(
            { it.chamada_em.orEmpty() },
            { it.atendimento_id ?: 0 },
        )
        val maisRecente = lista.maxWithOrNull(porChamada)
        if (
            maisRecente != null &&
            deveAtualizarChamada(
                atualSenha = ultimaChamadaSenha,
                atualEm = ultimaChamadaEm,
                incoming = maisRecente,
                atualFoto = ultimaChamadaOperadorFoto,
                atualOperador = ultimaChamadaOperador,
                atualAtendimentoId = null,
            )
        ) {
            ultimaChamadaSenha = maisRecente.senha
            ultimaChamadaOperador = maisRecente.operador_nome
            ultimaChamadaOperadorFoto = maisRecente.operador_foto
            ultimaChamadaEm = maisRecente.chamada_em
        }
        lista.filter { it.tipo == "normal" }
            .maxWithOrNull(porChamada)
            ?.let { aplicarTipoSeMaisNova("normal", it) }
        lista.filter { it.tipo == "preferencial" }
            .maxWithOrNull(porChamada)
            ?.let { aplicarTipoSeMaisNova("preferencial", it) }
    }

    private fun aplicarTipoSeMaisNova(tipo: String, incoming: AtendimentoDto) {
        val atualSenha = if (tipo == "preferencial") ultimaPreferencialSenha else ultimaNormalSenha
        val atualEm = if (tipo == "preferencial") ultimaPreferencialEm else ultimaNormalEm
        val atualId = if (tipo == "preferencial") ultimaPreferencialId else ultimaNormalId
        val atualFoto = if (tipo == "preferencial") ultimaPreferencialFoto else ultimaNormalFoto
        if (
            atualSenha != null &&
            !deveAtualizarChamada(
                atualSenha = atualSenha,
                atualEm = atualEm,
                incoming = incoming,
                atualId = atualId,
                atualFoto = atualFoto,
                atualAtendimentoId = null,
            )
        ) {
            return
        }
        if (tipo == "preferencial") {
            ultimaPreferencialSenha = incoming.senha
            ultimaPreferencialFoto = incoming.operador_foto
            ultimaPreferencialEm = incoming.chamada_em
            ultimaPreferencialId = incoming.senha_id
        } else {
            ultimaNormalSenha = incoming.senha
            ultimaNormalFoto = incoming.operador_foto
            ultimaNormalEm = incoming.chamada_em
            ultimaNormalId = incoming.senha_id
        }
    }

    private fun deveAtualizarChamada(
        atualSenha: String?,
        atualEm: String?,
        incoming: AtendimentoDto,
        atualId: Int? = null,
        atualFoto: String? = null,
        atualOperador: String? = null,
        atualAtendimentoId: Int? = null,
    ): Boolean {
        if (atualSenha.isNullOrBlank()) return true
        if (atualSenha == incoming.senha) {
            val fotoMudou = atualFoto != incoming.operador_foto
            val operadorMudou = atualOperador != null && atualOperador != incoming.operador_nome
            val faltaHorario = atualEm.isNullOrBlank() && !incoming.chamada_em.isNullOrBlank()
            return fotoMudou || operadorMudou || faltaHorario
        }
        val atual = atualEm.orEmpty()
        val nova = incoming.chamada_em.orEmpty()
        if (atual.isNotEmpty() && nova.isNotEmpty()) {
            if (nova < atual) return false
            if (nova > atual) return true
            val atualAtt = atualAtendimentoId ?: 0
            val novoAtt = incoming.atendimento_id ?: 0
            if (atualAtt > 0 && novoAtt > 0 && novoAtt < atualAtt) return false
        }
        if (nova.isEmpty() && atualId != null && incoming.senha_id != null && incoming.senha_id < atualId) {
            return false
        }
        return true
    }

    private fun mesclarChamadas(
        locais: List<TvChamadaRecenteDto>,
        remotas: List<TvChamadaRecenteDto>,
    ): List<TvChamadaRecenteDto> {
        fun ehMaisNova(a: TvChamadaRecenteDto, b: TvChamadaRecenteDto): Boolean {
            val emA = a.chamada_em.orEmpty()
            val emB = b.chamada_em.orEmpty()
            if (emA != emB) return emA > emB
            return (a.atendimento_id ?: 0) >= (b.atendimento_id ?: 0)
        }

        val porId = linkedMapOf<Int, TvChamadaRecenteDto>()
        for (item in remotas + locais) {
            val existente = porId[item.senha_id]
            if (existente == null || ehMaisNova(item, existente)) {
                porId[item.senha_id] = item
            }
        }
        return porId.values.sortedWith(
            compareByDescending<TvChamadaRecenteDto> { it.chamada_em.orEmpty() }
                .thenByDescending { it.atendimento_id ?: 0 },
        ).take(8)
    }

    private fun prependChamada(event: SocketEvent.SenhaChamada) {
        val next = TvChamadaRecenteDto(
            senha_id = event.senhaId ?: (System.currentTimeMillis() and 0x7fffffff).toInt(),
            senha = event.senha,
            tipo = event.tipo ?: "normal",
            operador_id = event.operadorId,
            operador_nome = event.operadorNome,
            operador_foto = event.operadorFoto,
            chamada_em = event.chamadaEm,
            atendimento_id = null,
            status = "atual",
        )
        // Sempre a última solicitação do setor fica no topo ("Chamando agora").
        chamadas = listOf(next) + chamadas.filter { item ->
            if (event.senhaId != null) item.senha_id != event.senhaId else item.senha != event.senha
        }.take(7)
    }

    private fun handleEvent(event: SocketEvent) {
        when (event) {
            is SocketEvent.FilaAtualizada -> {
                pendentes = event.pendentes
                atendimentos = event.atendimentos
                syncFromAtendimentos(event.atendimentos)
            }
            is SocketEvent.SenhaChamada -> {
                val agora = event.chamadaEm
                ultimaChamadaSenha = event.senha
                ultimaChamadaOperador = event.operadorNome
                ultimaChamadaOperadorFoto = event.operadorFoto
                ultimaChamadaEm = agora
                when (event.tipo) {
                    "preferencial" -> {
                        ultimaPreferencialSenha = event.senha
                        ultimaPreferencialFoto = event.operadorFoto
                        ultimaPreferencialEm = agora
                        ultimaPreferencialId = event.senhaId
                    }
                    "normal" -> {
                        ultimaNormalSenha = event.senha
                        ultimaNormalFoto = event.operadorFoto
                        ultimaNormalEm = agora
                        ultimaNormalId = event.senhaId
                    }
                    else -> Unit
                }
                prependChamada(event)
                if (soundDeduplicator.isNewCall(event.senha, event.senhaId)) {
                    _callSoundEvents.trySend(Unit)
                }
            }
            is SocketEvent.TvConfigAtualizada -> {
                applyTvConfig(
                    layout = event.layoutTvWeb,
                    orientacao = event.orientacaoTv,
                    posicao = event.posicaoSenhasTv,
                    imgs = event.imagens,
                    intervalo = event.intervaloMs,
                    som = event.somChamada,
                )
            }
            else -> Unit
        }
    }

    override fun onCleared() {
        super.onCleared()
        rotationJob?.cancel()
        _callSoundEvents.close()
        SocketManager.disconnect()
    }
}
