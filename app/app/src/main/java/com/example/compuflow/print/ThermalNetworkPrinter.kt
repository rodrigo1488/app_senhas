package com.example.compuflow.print

import android.util.Base64
import android.util.Log
import com.example.compuflow.data.remote.dto.ImpressaoClienteDto
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import java.io.IOException
import java.net.InetSocketAddress
import java.net.Socket

/**
 * Encaminha bytes ESC/POS gerados pelo servidor para a impressora térmica
 * na LAN do tablet (porta típica 9100). Usado quando o setor tem
 * `impressao_via_cliente` — a API atrás do túnel não alcança a impressora.
 */
object ThermalNetworkPrinter {
    private const val TAG = "ThermalPrinter"
    private const val CONNECT_TIMEOUT_MS = 4_000
    private const val SO_TIMEOUT_MS = 8_000

    suspend fun enviarSeNecessario(impressao: ImpressaoClienteDto?): Result<Unit> {
        if (impressao == null || !impressao.via_cliente) {
            return Result.success(Unit)
        }
        val erroPayload = impressao.erro?.trim()?.takeIf { it.isNotEmpty() }
        if (erroPayload != null) {
            return Result.failure(IOException(erroPayload))
        }
        val ip = impressao.impressora_ip?.trim().orEmpty()
        val rawB64 = impressao.escpos_base64?.trim().orEmpty()
        if (ip.isEmpty() || rawB64.isEmpty()) {
            return Result.failure(IOException("Dados de impressão incompletos"))
        }
        val porta = impressao.impressora_porta.takeIf { it in 1..65535 } ?: 9100
        val bytes = try {
            Base64.decode(rawB64, Base64.DEFAULT)
        } catch (e: IllegalArgumentException) {
            return Result.failure(IOException("Cupom inválido", e))
        }
        if (bytes.isEmpty()) {
            return Result.failure(IOException("Cupom vazio"))
        }
        return withContext(Dispatchers.IO) {
            enviarBytes(ip, porta, bytes)
        }
    }

    private fun enviarBytes(host: String, porta: Int, payload: ByteArray): Result<Unit> {
        return try {
            Socket().use { socket ->
                socket.tcpNoDelay = true
                socket.soTimeout = SO_TIMEOUT_MS
                socket.connect(InetSocketAddress(host, porta), CONNECT_TIMEOUT_MS)
                socket.getOutputStream().use { out ->
                    out.write(payload)
                    out.flush()
                }
            }
            Result.success(Unit)
        } catch (e: Exception) {
            Log.w(TAG, "Falha ao imprimir em $host:$porta", e)
            Result.failure(IOException("Não foi possível imprimir em $host:$porta", e))
        }
    }
}
