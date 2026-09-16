package com.example.compuflow.data.remote.dto

import kotlinx.serialization.SerialName
import kotlinx.serialization.Serializable

/**
 * DTOs espelhando exatamente os payloads de `backend/blueprints/api_bp.py` e
 * dos `to_dict()` em `backend/models.py`. Nomes de campo são idênticos aos
 * do backend (snake_case), conforme `documentacao/REALTIME_PROTOCOL.md`.
 */

@Serializable
data class SetorDto(
    val id: Int,
    val nome: String,
    val descricao: String? = null,
    val modo_identificacao_operador: String = "foto",
    val propagandas_ativas: Boolean = false,
)

@Serializable
data class OperadorDto(
    val id: Int,
    val nome: String,
    val foto_perfil: String? = null,
    val setor_id: Int? = null,
    val tem_pin: Boolean = false,
)

@Serializable
data class SenhaDto(
    val id: Int,
    val senha: String,
    val tipo: String,
    val setor_id: Int? = null,
    val status: String? = null,
    val token_unico: String? = null,
    val tem_pedido: Boolean = false,
    val pedido: String? = null,
    val pedido_confirmado: Boolean = false,
)

@Serializable
data class AtendimentoDto(
    val operador_id: Int,
    val operador_nome: String,
    val operador_foto: String? = null,
    val senha: String,
    val tipo: String,
    val senha_id: Int? = null,
    val tem_pedido: Boolean = false,
    val pedido: String? = null,
    val pedido_confirmado: Boolean = false,
)

@Serializable
data class FilaDto(
    val setor_id: Int,
    val pendentes: List<SenhaDto> = emptyList(),
    val atendimentos: List<AtendimentoDto> = emptyList(),
)

@Serializable
data class AtendimentoAtualDto(
    val setor_id: Int? = null,
    val operador_id: Int? = null,
    val ticket_token: String? = null,
    val senha_id: Int? = null,
    val senha: String? = null,
    val tipo: String? = null,
    val operador_nome: String? = null,
    val operador_foto: String? = null,
    val tem_pedido: Boolean = false,
    val pedido: String? = null,
    val pedido_confirmado: Boolean = false,
    val alerta_preferenciais: Boolean = false,
)

@Serializable
data class PosicaoDto(
    val token_unico: String,
    val posicao: Int,
    val senha: String,
    val status: String,
    val setor_nome: String,
    val tem_pedido: Boolean = false,
    val pedido: String? = null,
    val pedido_confirmado: Boolean = false,
)

@Serializable
data class AvaliacaoPendenteDto(
    val senha_id: Int? = null,
    val senha: String? = null,
    val operador_id: Int? = null,
    val operador_nome: String? = null,
    val operador_foto: String? = null,
)

@Serializable
data class ChamarProximaResponseDto(
    val senha: SenhaDto? = null,
    val chamada_realizada: Boolean = senha != null,
    val mensagem: String? = null,
    val tipo_chamado: String? = null,
    val alerta_preferenciais: Boolean = false,
    val session_token: String? = null,
)

@Serializable
data class SuccessDto(val success: Boolean = true)

@Serializable
data class ErrorDto(val error: String? = null)

// --- Requests -----------------------------------------------------------------

@Serializable
data class SetorLoginRequest(val codigo_setor: String)

@Serializable
data class SetorLoginResponse(val session_token: String, val setor: SetorDto)

@Serializable
data class SelecionarPapelRequest(
    val role: String,
    val operador_id: Int? = null,
    val pin: String? = null,
)

@Serializable
data class SelecionarPapelResponse(
    val session_token: String,
    val operador: OperadorDto? = null,
)

@Serializable
data class OperadoresResponse(
    val operadores: List<OperadorDto> = emptyList(),
    val modo_identificacao_operador: String = "foto",
)

@Serializable
data class PropagandaImagemDto(
    val id: Int,
    val arquivo: String,
    val ordem: Int = 0,
    val tipo: String = "image",
)

@Serializable
data class TvConfigDto(
    val propagandas_ativas: Boolean = false,
    val layout_tv_web: String = "propaganda",
    val setor_nome: String? = null,
    val imagens: List<PropagandaImagemDto> = emptyList(),
    val intervalo_ms: Long = 15_000,
)

@Serializable
data class TvChamadaRecenteDto(
    val senha_id: Int,
    val senha: String,
    val tipo: String = "normal",
    val operador_id: Int? = null,
    val operador_nome: String? = null,
    val operador_foto: String? = null,
    val chamada_em: String? = null,
    val status: String = "finalizada",
)

@Serializable
data class TvChamadasRecentesResponse(
    val chamadas: List<TvChamadaRecenteDto> = emptyList(),
)

@Serializable
data class StreamingQueueItemDto(
    val path: String,
    val type: String = "image",
    val order: Int = 0,
    val duration: Long = 15_000,
)

@Serializable
data class StreamingDispositivoDto(
    val id: Int,
    val tipo: String = "streaming",
    val chave: String = "",
    val nome: String = "",
    val device_name: String = "",
    val is_online: Boolean = false,
    val setor_id: Int? = null,
    val propaganda_ids: List<Int> = emptyList(),
)

@Serializable
data class StreamingEntrarRequest(
    val device_id: String,
    val device_name: String = "Android",
)

@Serializable
data class StreamingEntrarResponse(
    val session_token: String,
    val dispositivo: StreamingDispositivoDto,
    val queue: List<StreamingQueueItemDto> = emptyList(),
    val intervalo_ms: Long = 15_000,
)

@Serializable
data class StreamingFilaResponse(
    val dispositivo: StreamingDispositivoDto? = null,
    val queue: List<StreamingQueueItemDto> = emptyList(),
    val intervalo_ms: Long = 15_000,
)

@Serializable
data class CriarSenhaRequest(val tipo: String)

@Serializable
data class SalvarPedidoRequest(val ticket_token: String, val pedido: String)

@Serializable
data class ChamarProximaRequest(val operador_id: Int? = null)

@Serializable
data class ChamarNovamenteRequest(val senha_id: Int)

@Serializable
data class ConfirmarPedidoRequest(val senha: String, val mensagem: String = "Pedido sendo preparado")

@Serializable
data class EnviarAvaliacaoRequest(val senha_id: Int, val operador_id: Int, val nota: Int)

/** Papéis possíveis do app, espelhando os valores aceitos por `POST /api/v1/sessao/papel`. */
enum class Papel(val valor: String) {
    CLIENTE("cliente"),
    OPERADOR("operador"),
    AVALIACAO("avaliacao"),
    TV("tv"),
    STREAMING("streaming"),
}
