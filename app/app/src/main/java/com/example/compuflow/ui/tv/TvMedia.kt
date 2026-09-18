package com.example.compuflow.ui.tv

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.size
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Person
import androidx.compose.material3.Icon
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.DisposableEffect
import androidx.compose.runtime.remember
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.unit.Dp
import androidx.compose.ui.unit.dp
import androidx.compose.ui.viewinterop.AndroidView
import androidx.media3.common.C
import androidx.media3.common.MediaItem
import androidx.media3.common.PlaybackException
import androidx.media3.common.Player
import androidx.media3.exoplayer.DefaultLoadControl
import androidx.media3.exoplayer.ExoPlayer
import androidx.media3.ui.AspectRatioFrameLayout
import androidx.media3.ui.PlayerView
import coil.compose.AsyncImage
import coil.request.ImageRequest
import com.example.compuflow.data.remote.NetworkModule
import com.example.compuflow.data.remote.dto.PropagandaImagemDto

internal fun mediaUrl(path: String?): String? {
    val value = path?.trim()?.takeIf { it.isNotEmpty() } ?: return null
    if (value.startsWith("http://") || value.startsWith("https://")) return value
    val normalized = value.trimStart('/').removePrefix("uploads/")
    return "${NetworkModule.currentHttpBaseUrl().trimEnd('/')}/uploads/$normalized"
}

@Composable
internal fun TvOperatorPhoto(
    foto: String?,
    modifier: Modifier = Modifier,
    placeholderTint: Color,
    placeholderSize: Dp = 22.dp,
    decodeSizePx: Int = 128,
) {
    val photoUrl = mediaUrl(foto)
    if (photoUrl != null) {
        val context = LocalContext.current
        val request = remember(photoUrl, decodeSizePx, context) {
            ImageRequest.Builder(context)
                .data(photoUrl)
                .size(decodeSizePx, decodeSizePx)
                .crossfade(false)
                .allowRgb565(true)
                .build()
        }
        AsyncImage(
            model = request,
            contentDescription = null,
            contentScale = ContentScale.Crop,
            modifier = modifier,
        )
    } else {
        Icon(
            Icons.Filled.Person,
            contentDescription = null,
            tint = placeholderTint,
            modifier = Modifier.size(placeholderSize),
        )
    }
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
            else -> {
                val context = LocalContext.current
                val request = remember(mediaUrl, context) {
                    ImageRequest.Builder(context)
                        .data(mediaUrl)
                        .crossfade(false)
                        .allowRgb565(true)
                        .build()
                }
                AsyncImage(
                    model = request,
                    contentDescription = "Propaganda",
                    contentScale = contentScale,
                    modifier = Modifier.fillMaxSize(),
                )
            }
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
    val appContext = context.applicationContext
    val resizeMode = if (contentScale == ContentScale.Fit) {
        AspectRatioFrameLayout.RESIZE_MODE_FIT
    } else {
        AspectRatioFrameLayout.RESIZE_MODE_ZOOM
    }
    val exoPlayer = remember(url, loop) {
        val loadControl = DefaultLoadControl.Builder()
            .setBufferDurationsMs(1_500, 5_000, 1_000, 2_000)
            .build()
        ExoPlayer.Builder(appContext)
            .setLoadControl(loadControl)
            .build()
            .apply {
                setMediaItem(MediaItem.fromUri(url))
                volume = 0f
                trackSelectionParameters = trackSelectionParameters
                    .buildUpon()
                    .setTrackTypeDisabled(C.TRACK_TYPE_AUDIO, true)
                    .build()
                repeatMode = if (loop) Player.REPEAT_MODE_ONE else Player.REPEAT_MODE_OFF
                playWhenReady = true
                prepare()
            }
    }
    DisposableEffect(exoPlayer) {
        val listener = object : Player.Listener {
            private var advanced = false

            private fun advanceOnce() {
                if (advanced || loop) return
                advanced = true
                onEnded()
            }

            override fun onPlaybackStateChanged(playbackState: Int) {
                if (playbackState == Player.STATE_ENDED) advanceOnce()
            }

            override fun onPlayerError(error: PlaybackException) {
                advanceOnce()
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
                setKeepContentOnPlayerReset(true)
                player = exoPlayer
                this.resizeMode = resizeMode
            }
        },
        update = { view ->
            if (view.player !== exoPlayer) view.player = exoPlayer
            if (view.resizeMode != resizeMode) view.resizeMode = resizeMode
        },
        onRelease = { view ->
            view.player = null
        },
        modifier = modifier,
    )
}
