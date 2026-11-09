package com.example.compuflow.data.remote

import org.junit.Assert.assertEquals
import org.junit.Assert.assertNull
import org.junit.Test

class LocalIpv4Test {
    @Test
    fun `prefere wifi ou ethernet e ignora interface virtual`() {
        assertEquals(
            "192.168.0.21",
            escolherIpv4(
                listOf(
                    ParEndereco("docker0", "172.17.0.1"),
                    ParEndereco("wlan0", "192.168.0.21"),
                    ParEndereco("tun0", "10.8.0.2"),
                ),
            ),
        )
        assertEquals(
            "10.0.0.4",
            escolherIpv4(listOf(ParEndereco("rmnet0", "10.0.0.4"))),
        )
        assertNull(escolherIpv4(listOf(ParEndereco("lo", "127.0.0.1"))))
    }
}
