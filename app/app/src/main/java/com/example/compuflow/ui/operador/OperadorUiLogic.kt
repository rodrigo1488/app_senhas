package com.example.compuflow.ui.operador

/** "pin" ou "foto". Preferência do aparelho ("pin"/"nome") vence o padrão do setor. */
internal fun modoIdentificacaoEfetivo(preferenciaAparelho: String?, modoSetor: String): String {
    return when (preferenciaAparelho) {
        "pin" -> "pin"
        "nome" -> "foto"
        else -> if (modoSetor == "pin") "pin" else "foto"
    }
}

internal fun pedidoBadgeLabel(temPedido: Boolean, confirmado: Boolean): String? = when {
    !temPedido -> null
    confirmado -> "PEDIDO CONFIRMADO"
    else -> "COM PEDIDO"
}

internal fun podeConfirmarPedido(
    senhaEmAtendimento: String?,
    senhaSelecionada: String,
    pedidoConfirmado: Boolean,
): Boolean = senhaEmAtendimento == senhaSelecionada && !pedidoConfirmado

internal fun operatorPhotoUrl(baseUrl: String, path: String?): String? {
    val value = path?.trim()?.takeIf { it.isNotEmpty() } ?: return null
    if (value.startsWith("http://") || value.startsWith("https://")) return value
    val normalized = value.trimStart('/').removePrefix("uploads/")
    return "${baseUrl.trimEnd('/')}/uploads/$normalized"
}

internal data class GradeOperadores(val colunas: Int, val linhas: Int)

/** Grade que cabe todos os operadores na área, priorizando o card mais quadrado. */
internal fun gradeParaCaberTodos(
    quantidade: Int,
    largura: Float,
    altura: Float,
    espaco: Float,
): GradeOperadores {
    if (quantidade <= 1) return GradeOperadores(1, 1)
    var melhor = GradeOperadores(1, quantidade)
    var melhorLado = -1f
    for (colunas in 1..quantidade) {
        val linhas = (quantidade + colunas - 1) / colunas
        val larguraCelula = (largura - espaco * (colunas - 1)) / colunas
        val alturaCelula = (altura - espaco * (linhas - 1)) / linhas
        if (larguraCelula <= 0f || alturaCelula <= 0f) continue
        val lado = minOf(larguraCelula, alturaCelula)
        if (lado > melhorLado) {
            melhorLado = lado
            melhor = GradeOperadores(colunas, linhas)
        }
    }
    return melhor
}

internal data class PinKeyResult(val displayedPin: String, val submittedPin: String? = null)

internal fun processPinKey(current: String, key: String, length: Int = 4): PinKeyResult {
    val updated = when (key) {
        "Limpar" -> ""
        "⌫" -> current.dropLast(1)
        else -> if (key.length == 1 && key[0].isDigit() && current.length < length) current + key else current
    }
    return if (updated.length == length && key.length == 1 && key[0].isDigit()) {
        PinKeyResult(displayedPin = "", submittedPin = updated)
    } else {
        PinKeyResult(displayedPin = updated)
    }
}
