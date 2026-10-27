package com.example.compuflow.data.remote

import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.async
import kotlinx.coroutines.awaitAll
import kotlinx.coroutines.coroutineScope
import kotlinx.coroutines.ensureActive
import kotlinx.coroutines.sync.Semaphore
import kotlinx.coroutines.sync.withPermit
import kotlinx.coroutines.withContext
import okhttp3.OkHttpClient
import okhttp3.Request
import java.net.Inet4Address
import java.net.NetworkInterface
import java.util.concurrent.TimeUnit
import kotlin.coroutines.coroutineContext

/** Varre a LAN em busca do Flask em `/api/v1/health`. */
object ServerDiscovery {

    const val DEFAULT_PORT = 5000

    private val probeClient: OkHttpClient by lazy {
        OkHttpClient.Builder()
            .connectTimeout(400, TimeUnit.MILLISECONDS)
            .readTimeout(400, TimeUnit.MILLISECONDS)
            .callTimeout(900, TimeUnit.MILLISECONDS)
            .followRedirects(false)
            .retryOnConnectionFailure(false)
            .build()
    }

    suspend fun scan(ports: List<Int> = listOf(DEFAULT_PORT)): List<String> = withContext(Dispatchers.IO) {
        val prefixes = localIpv4Prefixes()
        if (prefixes.isEmpty()) return@withContext emptyList()
        val selfHosts = localIpv4Hosts()
        val hosts = prefixes.flatMap { prefix ->
            (1..254).map { "$prefix.$it" }
        }.filterNot { it in selfHosts }.distinct()

        val semaphore = Semaphore(32)
        coroutineScope {
            hosts.flatMap { host ->
                ports.map { port ->
                    async {
                        semaphore.withPermit {
                            coroutineContext.ensureActive()
                            if (isCompuflowServer(host, port)) displayUrl(host, port) else null
                        }
                    }
                }
            }.awaitAll().filterNotNull().distinct().sorted()
        }
    }

    fun displayUrl(host: String, port: Int = DEFAULT_PORT): String = "http://$host:$port"

    internal fun isCompuflowHealthBody(body: String): Boolean {
        val text = body.lowercase()
        return text.contains("\"status\"") && text.contains("ok")
    }

    private fun isCompuflowServer(host: String, port: Int): Boolean {
        val request = Request.Builder()
            .url("http://$host:$port/api/v1/health")
            .get()
            .build()
        return runCatching {
            probeClient.newCall(request).execute().use { response ->
                response.isSuccessful && isCompuflowHealthBody(response.body?.string().orEmpty())
            }
        }.getOrDefault(false)
    }

    private fun localIpv4Hosts(): Set<String> {
        val hosts = mutableSetOf<String>()
        forEachLocalIpv4 { hosts.add(it) }
        return hosts
    }

    private fun localIpv4Prefixes(): List<String> {
        val prefixes = linkedSetOf<String>()
        forEachLocalIpv4 { host ->
            val parts = host.split('.')
            if (parts.size == 4) prefixes.add(parts.take(3).joinToString("."))
        }
        return prefixes.toList()
    }

    private fun forEachLocalIpv4(block: (String) -> Unit) {
        val interfaces = runCatching { NetworkInterface.getNetworkInterfaces()?.toList().orEmpty() }
            .getOrDefault(emptyList())
        for (nif in interfaces) {
            val usable = runCatching { nif.isUp && !nif.isLoopback }.getOrDefault(false)
            if (!usable) continue
            val addresses = runCatching { nif.inetAddresses.toList() }.getOrDefault(emptyList())
            for (address in addresses) {
                if (address !is Inet4Address || address.isLoopbackAddress) continue
                val host = address.hostAddress ?: continue
                if (host.startsWith("169.254.")) continue
                block(host)
            }
        }
    }
}
