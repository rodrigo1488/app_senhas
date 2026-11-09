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
