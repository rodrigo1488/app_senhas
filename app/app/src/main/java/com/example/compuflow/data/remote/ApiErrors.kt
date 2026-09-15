package com.example.compuflow.data.remote

import kotlinx.serialization.json.Json
import okhttp3.ResponseBody
import retrofit2.HttpException

/** Extrai a mensagem `{"error": "..."}` do corpo de erro das rotas de
 * `backend/blueprints/api_bp.py`, com uma mensagem genérica de fallback. */
fun Throwable.toUserMessage(fallback: String = "Não foi possível completar a operação"): String {
    if (this is HttpException) {
        val body: ResponseBody? = response()?.errorBody()
        val raw = body?.string()
        if (!raw.isNullOrBlank()) {
            runCatching {
                val json = Json { ignoreUnknownKeys = true }
                val obj = json.parseToJsonElement(raw).let { it as? kotlinx.serialization.json.JsonObject }
                val msg = obj?.get("error")?.let { (it as? kotlinx.serialization.json.JsonPrimitive)?.content }
                if (!msg.isNullOrBlank()) return msg
            }
        }
    }
    return this.message?.takeIf { it.isNotBlank() } ?: fallback
}
