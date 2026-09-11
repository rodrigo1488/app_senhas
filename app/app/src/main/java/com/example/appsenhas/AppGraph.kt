package com.example.appsenhas

import android.content.Context
import com.example.appsenhas.data.session.SessionRepository

/**
 * Pequeno "container" de dependências manual (sem DI framework, escopo do
 * app é pequeno). `sessionRepository` é o único estado compartilhado entre
 * telas — tudo o mais (Retrofit, Socket) é acessado via singletons próprios
 * (`NetworkModule`, `SocketManager`) que leem o token em `AuthState`.
 */
object AppGraph {
    lateinit var sessionRepository: SessionRepository
        private set

    private var initialized = false

    fun init(context: Context) {
        if (initialized) return
        sessionRepository = SessionRepository(context.applicationContext)
        initialized = true
    }
}
