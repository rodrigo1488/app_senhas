package com.example.appsenhas.data.remote

import com.example.appsenhas.data.remote.dto.AtendimentoAtualDto
import com.example.appsenhas.data.remote.dto.AvaliacaoPendenteDto
import com.example.appsenhas.data.remote.dto.ChamarNovamenteRequest
import com.example.appsenhas.data.remote.dto.ChamarProximaRequest
import com.example.appsenhas.data.remote.dto.ChamarProximaResponseDto
import com.example.appsenhas.data.remote.dto.ConfirmarPedidoRequest
import com.example.appsenhas.data.remote.dto.CriarSenhaRequest
import com.example.appsenhas.data.remote.dto.EnviarAvaliacaoRequest
import com.example.appsenhas.data.remote.dto.FilaDto
import com.example.appsenhas.data.remote.dto.OperadoresResponse
import com.example.appsenhas.data.remote.dto.PosicaoDto
import com.example.appsenhas.data.remote.dto.SalvarPedidoRequest
import com.example.appsenhas.data.remote.dto.SelecionarPapelRequest
import com.example.appsenhas.data.remote.dto.SelecionarPapelResponse
import com.example.appsenhas.data.remote.dto.SenhaDto
import com.example.appsenhas.data.remote.dto.SetorLoginRequest
import com.example.appsenhas.data.remote.dto.SetorLoginResponse
import com.example.appsenhas.data.remote.dto.SuccessDto
import retrofit2.http.Body
import retrofit2.http.GET
import retrofit2.http.POST
import retrofit2.http.Path
import retrofit2.http.Query

/**
 * Espelha 1:1 as rotas de `backend/blueprints/api_bp.py` (prefixo `/api/v1`).
 * Todas as rotas (exceto login/health) exigem `Authorization: Bearer <token>`,
 * injetado automaticamente pelo `AuthInterceptor` (ver `NetworkModule.kt`).
 */
interface ApiService {

    @GET("api/v1/health")
    suspend fun health(): SuccessDto

    @POST("api/v1/setor/login")
    suspend fun setorLogin(@Body body: SetorLoginRequest): SetorLoginResponse

    @POST("api/v1/sessao/papel")
    suspend fun selecionarPapel(@Body body: SelecionarPapelRequest): SelecionarPapelResponse

    @POST("api/v1/sessao/liberar_operador")
    suspend fun liberarOperador(): SelecionarPapelResponse

    @GET("api/v1/setor/operadores")
    suspend fun listarOperadores(): OperadoresResponse

    @GET("api/v1/setor/fila")
    suspend fun estadoFila(): FilaDto

    @GET("api/v1/setor/atendimento_atual")
    suspend fun atendimentoAtual(): AtendimentoAtualDto

    @POST("api/v1/senha")
    suspend fun criarSenha(@Body body: CriarSenhaRequest): SenhaDto

    @POST("api/v1/senha/pedido")
    suspend fun salvarPedido(@Body body: SalvarPedidoRequest): SuccessDto

    @GET("api/v1/senha/{token}/posicao")
    suspend fun posicaoNaFila(@Path("token") token: String): PosicaoDto

    @POST("api/v1/operador/chamar_proxima")
    suspend fun chamarProxima(@Body body: ChamarProximaRequest): ChamarProximaResponseDto

    @POST("api/v1/operador/chamar_novamente")
    suspend fun chamarNovamente(@Body body: ChamarNovamenteRequest): SuccessDto

    @POST("api/v1/operador/confirmar_pedido")
    suspend fun confirmarPedido(@Body body: ConfirmarPedidoRequest): SuccessDto

    @GET("api/v1/avaliacao/pendente")
    suspend fun avaliacaoPendente(@Query("operador_id") operadorId: Int? = null): AvaliacaoPendenteDto

    @POST("api/v1/avaliacao")
    suspend fun enviarAvaliacao(@Body body: EnviarAvaliacaoRequest): SuccessDto
}
