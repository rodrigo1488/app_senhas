package com.example.compuflow.ui.operador

import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Test

class OperadorUiLogicTest {
    @Test
    fun `badge reflete o estado real do pedido`() {
        assertNull(pedidoBadgeLabel(temPedido = false, confirmado = false))
        assertEquals("COM PEDIDO", pedidoBadgeLabel(temPedido = true, confirmado = false))
        assertEquals("PEDIDO CONFIRMADO", pedidoBadgeLabel(temPedido = true, confirmado = true))
    }

    @Test
    fun `confirmacao so e permitida para atendimento atual nao confirmado`() {
        assertTrue(podeConfirmarPedido("N1000", "N1000", pedidoConfirmado = false))
        assertFalse(podeConfirmarPedido("N1000", "N1001", pedidoConfirmado = false))
        assertFalse(podeConfirmarPedido("N1000", "N1000", pedidoConfirmado = true))
    }

    @Test
    fun `foto do operador aceita caminho local e url absoluta`() {
        assertNull(operatorPhotoUrl("https://api.exemplo.com", null))
        assertEquals(
            "https://api.exemplo.com/uploads/fotos/ana.jpg",
            operatorPhotoUrl("https://api.exemplo.com/", "/uploads/fotos/ana.jpg"),
        )
        assertEquals(
            "https://cdn.exemplo.com/ana.jpg",
            operatorPhotoUrl("https://api.exemplo.com", "https://cdn.exemplo.com/ana.jpg"),
        )
    }

    @Test
    fun `quarto digito autoenvia pin sem confirmacao`() {
        assertEquals(PinKeyResult("1"), processPinKey("", "1"))
        assertEquals(PinKeyResult("12"), processPinKey("1", "2"))
        assertEquals(PinKeyResult("123"), processPinKey("12", "3"))
        assertEquals(PinKeyResult("", submittedPin = "1234"), processPinKey("123", "4"))
        assertEquals(PinKeyResult("12"), processPinKey("123", "⌫"))
    }
}
