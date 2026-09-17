package com.example.compuflow.ui.tv

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.DisposableEffect
import androidx.compose.runtime.remember
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.viewinterop.AndroidView
import androidx.media3.common.MediaItem
import androidx.media3.common.PlaybackException
import androidx.media3.common.Player
import androidx.media3.exoplayer.ExoPlayer
import androidx.media3.ui.AspectRatioFrameLayout
import androidx.media3.ui.PlayerView
import coil.compose.AsyncImage
import com.example.compuflow.data.remote.NetworkModule
import com.example.compuflow.data.remote.dto.PropagandaImagemDto

internal fun mediaUrl(path: String?): String? {
    val value = path?.trim()?.takeIf { it.isNotEmpty() } ?: return null
    if (value.startsWith("http://") || value.startsWith("https://")) return value
    val normalized = value.trimStart('/').removePrefix("uploads/")
    return "${NetworkModule.currentHttpBaseUrl().trimEnd('/')}/uploads/$normalized"
}

@Composable
internal fun TvMediaSlide(
    item: PropagandaImagemDto?,
    mediaUrl: String?,
    loop: Boolean,
    onEnded: () -> Unit,
    emptyLabel: String,
    modifier: Modifier = Modifier,
    emptyBackground: Color = Color(0xFF09090B),
    contentScale: ContentScale = ContentScale.Crop,
) {
    Box(
        modifier = modifier.background(emptyBackground),
        contentAlignment = Alignment.Center,
    ) {
        when {
            mediaUrl == null || item == null -> {
                Text(text = emptyLabel, color = Color.White.copy(alpha = 0.4f))
            }
            item.tipo == "video" -> MutedVideoPlayer(
                url = mediaUrl,
                loop = loop,
                onEnded = onEnded,
                contentScale = contentScale,
                modifier = Modifier.fillMaxSize(),
            )
            else -> AsyncImage(
                model = mediaUrl,
                contentDescription = "Propaganda",
                contentScale = contentScale,
                modifier = Modifier.fillMaxSize(),
            )
        }
    }
}

@Composable
private fun MutedVideoPlayer(
    url: String,
    loop: Boolean,
    onEnded: () -> Unit,
    contentScale: ContentScale = ContentScale.Crop,
    modifier: Modifier = Modifier,
) {
    val context = LocalContext.current
    val resizeMode = if (contentScale == ContentScale.Fit) {
        AspectRatioFrameLayout.RESIZE_MODE_FIT
    } else {
        AspectRatioFrameLayout.RESIZE_MODE_ZOOM
    }
    val exoPlayer = remember(url, loop) {
        ExoPlayer.Builder(context).build().apply {
            setMediaItem(MediaItem.fromUri(url))
            volume = 0f
            repeatMode = if (loop) Player.REPEAT_MODE_ONE else Player.REPEAT_MODE_OFF
            playWhenReady = true
            prepare()
        }
    }
    DisposableEffect(exoPlayer) {
        val listener = object : Player.Listener {
            override fun onPlaybackStateChanged(playbackState: Int) {
                if (playbackState == Player.STATE_ENDED && !loop) onEnded()
            }

            override fun onPlayerError(error: PlaybackException) {
                onEnded()
            }
        }
        exoPlayer.addListener(listener)
        onDispose {
            exoPlayer.removeListener(listener)
            exoPlayer.release()
        }
    }
    AndroidView(
        factory = { ctx ->
            PlayerView(ctx).apply {
                useController = false
                this.resizeMode = resizeMode
            }
        },
        update = { view ->
            view.player = exoPlayer
            view.resizeMode = resizeMode
        },
        modifier = modifier,
    )
}
