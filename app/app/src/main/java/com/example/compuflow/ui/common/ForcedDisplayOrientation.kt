package com.example.compuflow.ui.common

import android.app.Activity
import android.content.Context
import android.content.ContextWrapper
import android.content.pm.ActivityInfo
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.BoxWithConstraints
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.requiredHeight
import androidx.compose.foundation.layout.requiredWidth
import androidx.compose.runtime.Composable
import androidx.compose.runtime.DisposableEffect
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.graphicsLayer
import androidx.compose.ui.platform.LocalContext

/**
 * Aplica rotação física da TV: 0 | 90 | 180 | 270.
 *
 * Em TV boxes que ignoram a orientação do sistema (framebuffer landscape),
 * usa [graphicsLayer] para girar o conteúdo e preencher o monitor.
 *
 * Compat: [portrait] true ≡ 90°, false ≡ 0° (painéis de senha).
 */
@Composable
fun ForcedDisplayOrientation(
    portrait: Boolean,
    content: @Composable () -> Unit,
) {
    ForcedDisplayOrientation(rotationDegrees = if (portrait) 90 else 0, content = content)
}

@Composable
fun ForcedDisplayOrientation(
    rotationDegrees: Int,
    content: @Composable () -> Unit,
) {
    val rotation = normalizeRotation(rotationDegrees)
    val context = LocalContext.current
    DisposableEffect(rotation) {
        val activity = context.findActivity()
        val previous = activity?.requestedOrientation
        activity?.requestedOrientation = when (rotation) {
            90, 270 -> ActivityInfo.SCREEN_ORIENTATION_PORTRAIT
            else -> ActivityInfo.SCREEN_ORIENTATION_UNSPECIFIED
        }
        onDispose {
            activity?.requestedOrientation =
                previous ?: ActivityInfo.SCREEN_ORIENTATION_UNSPECIFIED
        }
    }

    if (rotation == 0) {
        content()
        return
    }

    BoxWithConstraints(modifier = Modifier.fillMaxSize()) {
        val windowIsLandscape = maxWidth > maxHeight
        val needsSwap = rotation == 90 || rotation == 270

        // Se o SO já aplicou retrato e pedimos 90°, desenha sem transform extra.
        if (needsSwap && !windowIsLandscape && rotation == 90) {
            content()
            return@BoxWithConstraints
        }

        val layerRotation = when (rotation) {
            90 -> -90f // montagem CW típica (igual ao portrait legado)
            180 -> 180f
            270 -> 90f
            else -> 0f
        }

        if (needsSwap) {
            Box(
                modifier = Modifier
                    .requiredWidth(maxHeight)
                    .requiredHeight(maxWidth)
                    .align(Alignment.Center)
                    .graphicsLayer { rotationZ = layerRotation },
            ) {
                content()
            }
        } else {
            Box(
                modifier = Modifier
                    .fillMaxSize()
                    .graphicsLayer { rotationZ = layerRotation },
            ) {
                content()
            }
        }
    }
}

fun normalizeRotation(degrees: Int): Int {
    val mod = ((degrees % 360) + 360) % 360
    return when (mod) {
        90, 180, 270 -> mod
        else -> 0
    }
}

private tailrec fun Context.findActivity(): Activity? = when (this) {
    is Activity -> this
    is ContextWrapper -> baseContext.findActivity()
    else -> null
}
