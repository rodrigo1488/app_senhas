package com.example.compuflow.ui.tv

import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

class TvCallSoundTest {
    @Test
    fun `toca apenas quando a chamada muda`() {
        var now = 0L
        val deduplicator = CallSoundDeduplicator(minIntervalMs = 800L, nowMs = { now })

        assertTrue(deduplicator.isNewCall("N1001"))
        assertFalse(deduplicator.isNewCall("N1001"))
        assertFalse(deduplicator.isNewCall(" N1001 "))
        assertTrue(deduplicator.isNewCall("P1002"))
        assertTrue(deduplicator.isNewCall("N1001"))
    }

    @Test
    fun `ignora chamada sem senha`() {
        val deduplicator = CallSoundDeduplicator()

        assertFalse(deduplicator.isNewCall(""))
        assertFalse(deduplicator.isNewCall("   "))
    }

    @Test
    fun `permite chamar novamente depois do intervalo`() {
        var now = 0L
        val deduplicator = CallSoundDeduplicator(minIntervalMs = 800L, nowMs = { now })

        assertTrue(deduplicator.isNewCall("N1001", senhaId = 10))
        assertFalse(deduplicator.isNewCall("N1001", senhaId = 10))
        now = 801L
        assertTrue(deduplicator.isNewCall("N1001", senhaId = 10))
    }
}
