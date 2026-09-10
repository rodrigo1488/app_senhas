package com.example.appsenhas.ui.navigation

/** Rotas do Navigation Compose. `IdentificarOperador` é compartilhada pelos
 * papéis Operador e Avaliação (ambos precisam saber "qual operador é você"). */
object Routes {
    const val BOOT = "boot"
    const val LOGIN = "login"
    const val MODO = "modo"
    const val IDENTIFICAR_OPERADOR = "identificar_operador/{finalidade}"
    const val CLIENTE = "cliente"
    const val OPERADOR = "operador"
    const val AVALIACAO = "avaliacao"
    const val TV = "tv"

    fun identificarOperador(finalidade: String) = "identificar_operador/$finalidade"

    const val FINALIDADE_OPERADOR = "operador"
    const val FINALIDADE_AVALIACAO = "avaliacao"
}
