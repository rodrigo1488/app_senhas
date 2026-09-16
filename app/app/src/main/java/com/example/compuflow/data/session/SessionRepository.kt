package com.example.compuflow.data.session

import android.content.Context
import androidx.datastore.preferences.core.edit
import androidx.datastore.preferences.core.stringPreferencesKey
import androidx.datastore.preferences.preferencesDataStore
import com.example.compuflow.data.remote.dto.Papel
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.first
import kotlinx.coroutines.flow.map

private val Context.sessionDataStore by preferencesDataStore(name = "compuflow_session")

/**
 * Persiste localmente: URL do servidor, token de sessão (JWT), papel
 * escolhido e id do operador (quando papel = operador) — para reabrir o app
 * direto na tela certa sem precisar logar de novo enquanto o token for válido.
 */
class SessionRepository(private val context: Context) {

    private object Keys {
        val SERVER_URL = stringPreferencesKey("server_url")
        val SESSION_TOKEN = stringPreferencesKey("session_token")
        val SETOR_ID = stringPreferencesKey("setor_id")
        val SETOR_NOME = stringPreferencesKey("setor_nome")
        val PAPEL = stringPreferencesKey("papel")
        val OPERADOR_ID = stringPreferencesKey("operador_id")
        val OPERADOR_NOME = stringPreferencesKey("operador_nome")
        val DEVICE_ID = stringPreferencesKey("device_id")
        val AVALIACAO_IDLE_MODO = stringPreferencesKey("avaliacao_idle_modo")
    }

    val serverUrlFlow: Flow<String?> = context.sessionDataStore.data.map { it[Keys.SERVER_URL] }
    val sessionTokenFlow: Flow<String?> = context.sessionDataStore.data.map { it[Keys.SESSION_TOKEN] }
    val setorNomeFlow: Flow<String?> = context.sessionDataStore.data.map { it[Keys.SETOR_NOME] }
    val papelFlow: Flow<String?> = context.sessionDataStore.data.map { it[Keys.PAPEL] }
    val operadorIdFlow: Flow<String?> = context.sessionDataStore.data.map { it[Keys.OPERADOR_ID] }
    val operadorNomeFlow: Flow<String?> = context.sessionDataStore.data.map { it[Keys.OPERADOR_NOME] }

    suspend fun getServerUrl(): String? = serverUrlFlow.first()
    suspend fun getSessionToken(): String? = sessionTokenFlow.first()
    suspend fun getPapel(): String? = papelFlow.first()
    suspend fun getOperadorId(): Int? = operadorIdFlow.first()?.toIntOrNull()
    suspend fun getOperadorNome(): String? = operadorNomeFlow.first()
    suspend fun getSetorNome(): String? = setorNomeFlow.first()

    /** ID estável deste aparelho — reusa a mesma TV de propagandas ao reconectar. */
    suspend fun getOrCreateDeviceId(): String {
        val existing = context.sessionDataStore.data.map { it[Keys.DEVICE_ID] }.first()
        if (!existing.isNullOrBlank()) return existing
        val created = java.util.UUID.randomUUID().toString()
        context.sessionDataStore.edit { it[Keys.DEVICE_ID] = created }
        return created
    }

    /** Idle da avaliação: "propaganda" (carrossel) ou "estatica" (1ª imagem / fundo). */
    suspend fun getAvaliacaoIdleModo(): String =
        context.sessionDataStore.data.map { it[Keys.AVALIACAO_IDLE_MODO] }.first() ?: "propaganda"

    suspend fun saveAvaliacaoIdleModo(modo: String) {
        context.sessionDataStore.edit { it[Keys.AVALIACAO_IDLE_MODO] = modo }
    }

    suspend fun saveServerUrl(url: String) {
        context.sessionDataStore.edit { it[Keys.SERVER_URL] = url }
        AuthState.serverUrl = url
    }

    suspend fun saveLoginSetor(token: String, setorId: Int, setorNome: String) {
        context.sessionDataStore.edit {
            it[Keys.SESSION_TOKEN] = token
            it[Keys.SETOR_ID] = setorId.toString()
            it[Keys.SETOR_NOME] = setorNome
            it.remove(Keys.PAPEL)
            it.remove(Keys.OPERADOR_ID)
            it.remove(Keys.OPERADOR_NOME)
        }
        AuthState.sessionToken = token
    }

    suspend fun savePapel(token: String, papel: Papel, operadorId: Int? = null, operadorNome: String? = null) {
        context.sessionDataStore.edit {
            it[Keys.SESSION_TOKEN] = token
            it[Keys.PAPEL] = papel.valor
            if (operadorId != null) it[Keys.OPERADOR_ID] = operadorId.toString() else it.remove(Keys.OPERADOR_ID)
            if (operadorNome != null) it[Keys.OPERADOR_NOME] = operadorNome else it.remove(Keys.OPERADOR_NOME)
        }
        AuthState.sessionToken = token
    }

    suspend fun saveGenericSession(token: String) {
        context.sessionDataStore.edit {
            it[Keys.SESSION_TOKEN] = token
            it.remove(Keys.PAPEL)
            it.remove(Keys.OPERADOR_ID)
            it.remove(Keys.OPERADOR_NOME)
        }
        AuthState.sessionToken = token
    }

    /** Remove só o papel/operador, mantendo o login do setor (volta ao menu). */
    suspend fun clearPapel() {
        context.sessionDataStore.edit {
            it.remove(Keys.PAPEL)
            it.remove(Keys.OPERADOR_ID)
            it.remove(Keys.OPERADOR_NOME)
        }
    }

    suspend fun logout() {
        context.sessionDataStore.edit {
            it.remove(Keys.SESSION_TOKEN)
            it.remove(Keys.SETOR_ID)
            it.remove(Keys.SETOR_NOME)
            it.remove(Keys.PAPEL)
            it.remove(Keys.OPERADOR_ID)
            it.remove(Keys.OPERADOR_NOME)
        }
        AuthState.sessionToken = null
    }

    /** Carrega o token/URL persistidos para a memória (usado no boot do app,
     * já que o interceptor HTTP e o SocketManager leem de forma síncrona). */
    suspend fun warmUpAuthState() {
        AuthState.serverUrl = getServerUrl()
        AuthState.sessionToken = getSessionToken()
    }
}

/**
 * Cache em memória do token/URL atuais, para acesso síncrono pelo
 * `AuthInterceptor` (OkHttp) e pelo `SocketManager`, sem precisar suspender
 * em toda requisição.
 */
object AuthState {
    @Volatile var serverUrl: String? = null
    @Volatile var sessionToken: String? = null
}
