package com.example.compuflow.data.remote

import java.net.Inet4Address
import java.net.NetworkInterface

data class ParEndereco(val iface: String, val ip: String)

private val interfacesIgnoradas = listOf("dummy", "tun", "docker", "vbox", "vmnet", "bluetooth")

/** Escolhe o IPv4 de LAN do aparelho (Wi-Fi ou Ethernet antes de interfaces virtuais). */
fun escolherIpv4(candidatos: List<ParEndereco>): String? {
    val uteis = candidatos.filter { par ->
        val nome = par.iface.lowercase()
        par.ip.isNotBlank() &&
            par.ip != "127.0.0.1" &&
            interfacesIgnoradas.none { nome.contains(it) }
    }
    val preferida = uteis.firstOrNull { par ->
        val nome = par.iface.lowercase()
        nome.startsWith("wlan") || nome.startsWith("eth") || nome.startsWith("en") || nome.startsWith("wifi")
    }
    return (preferida ?: uteis.firstOrNull())?.ip
}

fun ipv4Local(): String? {
    val interfaces = NetworkInterface.getNetworkInterfaces() ?: return null
    val candidatos = mutableListOf<ParEndereco>()
    for (iface in interfaces) {
        if (!iface.isUp || iface.isLoopback) continue
        for (addr in iface.inetAddresses) {
            if (addr is Inet4Address && !addr.isLoopbackAddress) {
                val host = addr.hostAddress ?: continue
                candidatos += ParEndereco(iface.name.orEmpty(), host.substringBefore('%'))
            }
        }
    }
    return escolherIpv4(candidatos)
}
