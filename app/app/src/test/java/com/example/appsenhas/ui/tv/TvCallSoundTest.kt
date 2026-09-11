package com.example.appsenhas.ui.tv

import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

class TvCallSoundTest {
    @Test
    fun `toca apenas quando a chamada muda`() {
        val deduplicator = CallSoundDeduplicator()

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
}
