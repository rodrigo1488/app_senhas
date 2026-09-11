package com.example.appsenhas.ui.tv

import android.content.Context
import android.media.AudioAttributes
import android.media.MediaPlayer
import com.example.appsenhas.R

internal class CallSoundDeduplicator {
    private var lastPassword: String? = null

    fun isNewCall(password: String): Boolean {
        val normalized = password.trim()
        if (normalized.isEmpty() || normalized == lastPassword) return false
        lastPassword = normalized
        return true
    }
}

internal class TvCallSoundPlayer(context: Context) {
    private val appContext = context.applicationContext
    private var player: MediaPlayer? = null

    fun play() {
        runCatching {
            val current = player ?: createPlayer().also { player = it }
            if (current.isPlaying) current.seekTo(0)
            current.start()
        }.onFailure {
            release()
            runCatching {
                createPlayer().also { player = it }.start()
            }
        }
    }

    private fun createPlayer(): MediaPlayer {
        val attributes = AudioAttributes.Builder()
            .setUsage(AudioAttributes.USAGE_MEDIA)
            .setContentType(AudioAttributes.CONTENT_TYPE_SONIFICATION)
            .build()

        return MediaPlayer.create(appContext, R.raw.call_chime, attributes, 0)
            ?: error("Não foi possível carregar o som de chamada")
    }

    fun release() {
        player?.release()
        player = null
    }
}
