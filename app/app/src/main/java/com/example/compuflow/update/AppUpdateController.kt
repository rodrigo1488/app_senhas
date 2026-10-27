package com.example.compuflow.update

import android.content.ClipData
import android.content.Context
import android.content.Intent
import android.net.Uri
import android.os.Build
import android.provider.Settings
import android.util.Log
import androidx.activity.ComponentActivity
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.setValue
import androidx.core.content.FileProvider
import androidx.lifecycle.lifecycleScope
import com.example.compuflow.BuildConfig
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext
import org.json.JSONObject
import java.io.File
import java.io.FileOutputStream
import java.net.HttpURLConnection
import java.net.URL
import java.security.MessageDigest

class AppUpdateController(private val activity: ComponentActivity) {
    var mostrarDialogo by mutableStateOf(false)
        private set

    var verificando by mutableStateOf(false)
        private set

    var mensagem by mutableStateOf<String?>(null)
        private set

    private var arquivoBaixado: File? = null
    private var aguardandoPermissao = false

    init {
        atual = this
    }

    fun iniciar() {
        consultar(manual = false)
    }

    fun verificarAgora() {
        consultar(manual = true)
    }

    private fun consultar(manual: Boolean) {
        val hash = BuildConfig.UTILITY_UPDATE_HASH.trim()
        if (hash.isEmpty()) {
            if (manual) mensagem = "Atualização não configurada neste aplicativo."
            return
        }
        if (verificando) {
            if (manual) mensagem = "Verificação já em andamento."
            return
        }
        verificando = true
        if (manual) mensagem = "Verificando versão…"
        activity.lifecycleScope.launch(Dispatchers.IO) {
            val resultado = runCatching { preparar(activity.applicationContext, hash) }
            withContext(Dispatchers.Main) {
                verificando = false
                resultado.onSuccess { arquivo ->
                    if (arquivo != null && !activity.isFinishing) {
                        arquivoBaixado = arquivo
                        mostrarDialogo = true
                        if (manual) mensagem = "Há uma versão nova pronta para instalar."
                    } else if (manual) {
                        mensagem = "Este aplicativo já está na versão mais recente."
                    }
                }.onFailure {
                    Log.w(TAG, "Falha ao consultar atualização", it)
                    if (manual) mensagem = "Não foi possível consultar a atualização."
                }
            }
        }
    }

    fun agoraNao() {
        arquivoBaixado = null
        mostrarDialogo = false
    }

    fun instalar() {
        val arquivo = arquivoBaixado ?: return
        if (!podeInstalar(activity)) {
            aguardandoPermissao = true
            mostrarDialogo = false
            val destino = Intent(
                Settings.ACTION_MANAGE_UNKNOWN_APP_SOURCES,
                Uri.parse("package:${activity.packageName}"),
            )
            runCatching { activity.startActivity(destino) }
                .onFailure {
                    aguardandoPermissao = false
                    mostrarDialogo = true
                    Log.w(TAG, "Não abriu a permissão de instalação", it)
                }
            return
        }
        mostrarDialogo = false
        abrirInstalador(arquivo)
    }

    fun aoRetomar() {
        if (!aguardandoPermissao) return
        aguardandoPermissao = false
        val arquivo = arquivoBaixado ?: return
        if (podeInstalar(activity)) {
            abrirInstalador(arquivo)
        } else {
            mostrarDialogo = true
        }
    }

    private fun abrirInstalador(arquivo: File) {
        val uri = FileProvider.getUriForFile(
            activity,
            "${activity.packageName}.fileprovider",
            arquivo,
        )
        val intent = Intent(Intent.ACTION_VIEW).apply {
            setDataAndType(uri, MIME_APK)
            addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION)
            clipData = ClipData.newRawUri("", uri)
        }
        runCatching { activity.startActivity(intent) }
            .onFailure {
                mostrarDialogo = true
                Log.w(TAG, "Não abriu o instalador", it)
            }
    }

    private fun preparar(context: Context, hash: String): File? {
        val prefs = context.getSharedPreferences(PREFS, Context.MODE_PRIVATE)
        val versaoLocal = prefs.getInt(KEY_VERSION, 0)
        val shaGuardado = prefs.getString(KEY_SHA, "").orEmpty()
        val manifesto = baixarManifesto(hash, versaoLocal)
        if (manifesto.sha256.isEmpty()) error("Resposta sem sha256")
        if (shaGuardado.equals(manifesto.sha256, ignoreCase = true)) return null

        val instalado = File(context.applicationInfo.sourceDir)
        if (sha256(instalado).equals(manifesto.sha256, ignoreCase = true)) {
            gravarAplicado(context, manifesto)
            return null
        }

        val pasta = File(context.filesDir, "updates")
        pasta.mkdirs()
        val destino = File(pasta, "update.apk")
        if (!destino.isFile || !sha256(destino).equals(manifesto.sha256, ignoreCase = true)) {
            val parcial = File(pasta, "update.apk.part")
            try {
                baixarArquivo(manifesto.downloadUrl, parcial)
            } catch (e: Exception) {
                parcial.delete()
                throw e
            }
            if (!sha256(parcial).equals(manifesto.sha256, ignoreCase = true)) {
                parcial.delete()
                return null
            }
            if (destino.exists()) destino.delete()
            if (!parcial.renameTo(destino)) {
                parcial.copyTo(destino, overwrite = true)
                parcial.delete()
            }
        }
        if (!sha256(destino).equals(manifesto.sha256, ignoreCase = true)) {
            destino.delete()
            return null
        }
        return destino
    }

    private fun gravarAplicado(context: Context, manifesto: Manifesto) {
        context.getSharedPreferences(PREFS, Context.MODE_PRIVATE)
            .edit()
            .putString(KEY_SHA, manifesto.sha256.lowercase())
            .putInt(KEY_VERSION, manifesto.version)
            .apply()
    }

    private fun baixarManifesto(hash: String, versaoLocal: Int): Manifesto {
        val endereco = BuildConfig.UTILITY_UPDATE_BASE.trimEnd('/') +
            "/utilitarios/atualizacao/$hash?version=$versaoLocal"
        val conn = abrir(endereco, LEITURA_MANIFESTO)
        try {
            if (conn.responseCode != 200) error("HTTP ${conn.responseCode}")
            val json = JSONObject(conn.inputStream.bufferedReader().use { it.readText() })
            val sha = json.optString("sha256").trim()
            val versao = json.optInt("version", 0)
            var download = json.optString("download_url").trim()
            if (download.isEmpty()) {
                download = BuildConfig.UTILITY_UPDATE_BASE.trimEnd('/') +
                    "/utilitarios/arquivo/hash/$hash"
            }
            return Manifesto(versao, sha, download)
        } finally {
            conn.disconnect()
        }
    }

    private fun baixarArquivo(endereco: String, destino: File) {
        val conn = abrir(endereco, LEITURA_APK)
        try {
            if (conn.responseCode != 200) error("HTTP ${conn.responseCode}")
            conn.inputStream.use { entrada ->
                FileOutputStream(destino).use { saida ->
                    entrada.copyTo(saida)
                }
            }
        } finally {
            conn.disconnect()
        }
    }

    private fun abrir(endereco: String, leituraMs: Int): HttpURLConnection {
        val conn = URL(endereco).openConnection() as HttpURLConnection
        conn.connectTimeout = CONEXAO_MS
        conn.readTimeout = leituraMs
        conn.instanceFollowRedirects = true
        conn.useCaches = false
        conn.setRequestProperty("Accept", "application/json")
        conn.setRequestProperty("User-Agent", "ComputicketAppUpdate")
        return conn
    }

    private data class Manifesto(val version: Int, val sha256: String, val downloadUrl: String)

    companion object {
        var atual: AppUpdateController? = null
            private set

        private const val TAG = "AppUpdate"
        private const val PREFS = "utility_update"
        private const val KEY_SHA = "sha256"
        private const val KEY_VERSION = "version"
        private const val MIME_APK = "application/vnd.android.package-archive"
        private const val CONEXAO_MS = 15_000
        private const val LEITURA_MANIFESTO = 20_000
        private const val LEITURA_APK = 300_000

        fun podeInstalar(context: Context): Boolean {
            if (Build.VERSION.SDK_INT < Build.VERSION_CODES.O) return true
            return context.packageManager.canRequestPackageInstalls()
        }

        fun sha256(arquivo: File): String {
            val digest = MessageDigest.getInstance("SHA-256")
            arquivo.inputStream().use { entrada ->
                val buffer = ByteArray(8192)
                while (true) {
                    val lido = entrada.read(buffer)
                    if (lido < 0) break
                    digest.update(buffer, 0, lido)
                }
            }
            return digest.digest().joinToString("") { "%02x".format(it.toInt() and 0xff) }
        }
    }
}
