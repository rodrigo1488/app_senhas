package com.example.compuflow.data.remote

import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

class ServerDiscoveryTest {
    @Test
    fun reconheceHealthDoCompuflow() {
        assertTrue(ServerDiscovery.isCompuflowHealthBody("""{"status":"ok"}"""))
        assertTrue(ServerDiscovery.isCompuflowHealthBody("""{ "status" : "OK" }"""))
        assertFalse(ServerDiscovery.isCompuflowHealthBody("""{"status":"down"}"""))
        assertFalse(ServerDiscovery.isCompuflowHealthBody("<html>ok</html>"))
    }
}
