package com.example.appsenhas.data.remote

import com.example.appsenhas.data.session.AuthState
import okhttp3.Interceptor
import okhttp3.Response

/** Injeta `Authorization: Bearer <session_token>` em toda requisição, lendo
 * o token em memória (ver `AuthState`), conforme `backend/auth.py::get_bearer_token`. */
class AuthInterceptor : Interceptor {
    override fun intercept(chain: Interceptor.Chain): Response {
        val original = chain.request()
        val token = AuthState.sessionToken
        val request = if (token.isNullOrBlank() || original.header("Authorization") != null) {
            original
        } else {
            original.newBuilder().header("Authorization", "Bearer $token").build()
        }
        return chain.proceed(request)
    }
}
