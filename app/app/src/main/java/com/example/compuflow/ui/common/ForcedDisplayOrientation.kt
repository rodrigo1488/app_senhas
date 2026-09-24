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
 * Quando [portrait] é true: tenta travar a Activity em retrato e, se o TV box
 * ignorar a rotação do sistema (framebuffer continua landscape), gira o
 * conteúdo em Compose −90° para preencher o monitor em pé.
 *
 * Quando [portrait] é false: não força landscape (em vários TV boxes isso
 * cortava a tela) — só libera qualquer travamento anterior e desenha em
 * tela cheia como antes.
 */
@Composable
fun ForcedDisplayOrientation(
    portrait: Boolean,
    content: @Composable () -> Unit,
) {
    val context = LocalContext.current
    DisposableEffect(portrait) {
        val activity = context.findActivity()
        val previous = activity?.requestedOrientation
        if (portrait) {
            activity?.requestedOrientation = ActivityInfo.SCREEN_ORIENTATION_PORTRAIT
        } else {
            activity?.requestedOrientation = ActivityInfo.SCREEN_ORIENTATION_UNSPECIFIED
        }
        onDispose {
            activity?.requestedOrientation =
                previous ?: ActivityInfo.SCREEN_ORIENTATION_UNSPECIFIED
        }
    }

    if (!portrait) {
        content()
        return
    }

    BoxWithConstraints(modifier = Modifier.fillMaxSize()) {
        val windowIsLandscape = maxWidth > maxHeight
        if (!windowIsLandscape) {
            content()
            return@BoxWithConstraints
        }

        // Monitor em pé + SO em landscape: gira o UI −90° (montagem CW típica).
        Box(
            modifier = Modifier
                .requiredWidth(maxHeight)
                .requiredHeight(maxWidth)
                .align(Alignment.Center)
                .graphicsLayer { rotationZ = -90f },
        ) {
            content()
        }
    }
}

private tailrec fun Context.findActivity(): Activity? = when (this) {
    is Activity -> this
    is ContextWrapper -> baseContext.findActivity()
    else -> null
}
