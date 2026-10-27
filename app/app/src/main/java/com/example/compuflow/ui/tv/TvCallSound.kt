package com.example.compuflow.ui.tv

import android.content.Context
import android.media.AudioAttributes
import android.media.MediaPlayer
import android.media.SoundPool
import com.example.compuflow.R

/**
 * Evita eco quando o socket entrega a mesma chamada duas vezes em sequência,
 * mas permite "chamar novamente" depois de um intervalo curto.
 */
internal class CallSoundDeduplicator(
    private val minIntervalMs: Long = 800L,
    private val nowMs: () -> Long = { System.nanoTime() / 1_000_000L },
) {
    private var lastKey: String? = null
    private var lastAtMs: Long = 0L

    fun isNewCall(password: String, senhaId: Int? = null): Boolean {
        val normalized = password.trim()
        if (normalized.isEmpty()) return false
        val key = senhaId?.let { "id:$it" } ?: "s:$normalized"
        val now = nowMs()
        if (key == lastKey && now - lastAtMs < minIntervalMs) return false
        lastKey = key
        lastAtMs = now
        return true
    }
}

/**
 * Som curto de chamada. SoundPool pré-carrega o MP3 padrão; se o setor tiver
 * áudio próprio, MediaPlayer reproduz a URL do servidor.
 */
internal class TvCallSoundPlayer(context: Context) {
    private val appContext = context.applicationContext
    private val soundPool: SoundPool = SoundPool.Builder()
        .setMaxStreams(1)
        .setAudioAttributes(sonificationAttrs())
        .build()
    private val soundId: Int = soundPool.load(appContext, R.raw.call_chime, 1)
    private var loaded = false
    private var customUrl: String? = null
    private var customPlayer: MediaPlayer? = null
    private var customReady = false

    init {
        soundPool.setOnLoadCompleteListener { _, sampleId, status ->
            if (sampleId == soundId && status == 0) loaded = true
        }
    }

    fun setCustomUrl(url: String?) {
        val next = url?.trim()?.takeIf { it.isNotEmpty() }
        if (next == customUrl) return
        customUrl = next
        releaseCustom()
        if (next == null) return
        val player = MediaPlayer()
        customPlayer = player
        runCatching {
            player.setAudioAttributes(sonificationAttrs())
            player.setDataSource(next)
            player.setOnPreparedListener { customReady = true }
            player.setOnErrorListener { _, _, _ ->
                customReady = false
                true
            }
            player.prepareAsync()
        }.onFailure {
            releaseCustom()
        }
    }

    fun play() {
        val player = customPlayer
        if (player != null && customReady) {
            runCatching {
                player.seekTo(0)
                player.start()
            }
            return
        }
        if (!loaded || soundId == 0) return
        runCatching { soundPool.play(soundId, 1f, 1f, 1, 0, 1f) }
    }

    fun release() {
        loaded = false
        releaseCustom()
        runCatching { soundPool.release() }
    }

    private fun releaseCustom() {
        customReady = false
        customPlayer?.let { player ->
            runCatching { player.release() }
        }
        customPlayer = null
    }

    private fun sonificationAttrs(): AudioAttributes =
        AudioAttributes.Builder()
            .setUsage(AudioAttributes.USAGE_ASSISTANCE_SONIFICATION)
            .setContentType(AudioAttributes.CONTENT_TYPE_SONIFICATION)
            .build()
}
