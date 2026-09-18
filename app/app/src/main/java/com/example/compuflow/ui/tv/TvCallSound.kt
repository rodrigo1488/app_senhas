package com.example.compuflow.ui.tv

import android.content.Context
import android.media.AudioAttributes
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
 * Som curto de chamada. SoundPool pré-carrega o MP3 e toca sem abrir um
 * decoder novo — MediaPlayer.create() na thread da UI travava TVs baratas
 * e ainda brigava pelo foco de áudio com o ExoPlayer da propaganda.
 */
internal class TvCallSoundPlayer(context: Context) {
    private val soundPool: SoundPool = SoundPool.Builder()
        .setMaxStreams(1)
        .setAudioAttributes(
            AudioAttributes.Builder()
                .setUsage(AudioAttributes.USAGE_ASSISTANCE_SONIFICATION)
                .setContentType(AudioAttributes.CONTENT_TYPE_SONIFICATION)
                .build(),
        )
        .build()
    private val soundId: Int = soundPool.load(context.applicationContext, R.raw.call_chime, 1)
    private var loaded = false

    init {
        soundPool.setOnLoadCompleteListener { _, sampleId, status ->
            if (sampleId == soundId && status == 0) loaded = true
        }
    }

    fun play() {
        if (!loaded || soundId == 0) return
        runCatching { soundPool.play(soundId, 1f, 1f, 1, 0, 1f) }
    }

    fun release() {
        loaded = false
        runCatching { soundPool.release() }
    }
}
