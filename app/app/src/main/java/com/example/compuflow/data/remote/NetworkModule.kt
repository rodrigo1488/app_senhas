package com.example.compuflow.data.remote

import com.example.compuflow.data.session.AuthState
import kotlinx.serialization.json.Json
import okhttp3.MediaType.Companion.toMediaType
import okhttp3.OkHttpClient
import okhttp3.logging.HttpLoggingInterceptor
import retrofit2.Retrofit
import retrofit2.converter.kotlinx.serialization.asConverterFactory
import java.util.concurrent.TimeUnit

/**
 * Constrói o `ApiService` sob demanda. A URL base é definida pelo usuário na
 * tela de login (IP local do servidor Flask ou URL do ngrok) e persistida via
 * `SessionRepository`; como pode mudar em runtime, o Retrofit é reconstruído
 * sempre que a URL muda (é uma app de uso interno, custo irrelevante).
 */
object NetworkModule {

    const val DEFAULT_BASE_URL = "http://192.168.0.100:5000/"

    private val json = Json {
        ignoreUnknownKeys = true
        isLenient = true
        explicitNulls = false
        encodeDefaults = true
    }

    @Volatile private var cachedBaseUrl: String? = null
    @Volatile private var cachedApiService: ApiService? = null

    private val okHttpClient: OkHttpClient by lazy {
        val logging = HttpLoggingInterceptor().apply { level = HttpLoggingInterceptor.Level.BASIC }
        OkHttpClient.Builder()
            .connectTimeout(15, TimeUnit.SECONDS)
            .readTimeout(20, TimeUnit.SECONDS)
            .writeTimeout(20, TimeUnit.SECONDS)
            .addInterceptor(AuthInterceptor())
            .addInterceptor(logging)
            .build()
    }

    fun apiService(): ApiService {
        val baseUrl = normalizeBaseUrl(AuthState.serverUrl ?: DEFAULT_BASE_URL)
        val cached = cachedApiService
        if (cached != null && cachedBaseUrl == baseUrl) return cached

        val retrofit = Retrofit.Builder()
            .baseUrl(baseUrl)
            .client(okHttpClient)
            .addConverterFactory(json.asConverterFactory("application/json".toMediaType()))
            .build()

        return retrofit.create(ApiService::class.java).also {
            cachedApiService = it
            cachedBaseUrl = baseUrl
        }
    }

    /** URL base "http://host:porta/" usada para montar a conexão do socket. */
    fun currentHttpBaseUrl(): String = normalizeBaseUrl(AuthState.serverUrl ?: DEFAULT_BASE_URL)

    private fun normalizeBaseUrl(raw: String): String {
        var url = raw.trim()
        if (!url.startsWith("http://") && !url.startsWith("https://")) url = "http://$url"
        if (!url.endsWith("/")) url = "$url/"
        return url
    }
}
