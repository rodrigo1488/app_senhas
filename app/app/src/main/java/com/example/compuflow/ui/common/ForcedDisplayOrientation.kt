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
 * Trava a Activity na orientação pedida e, se o TV box ignorar a rotação do
 * sistema (comum: framebuffer continua landscape), gira o conteúdo em Compose
 * para a tela fisicamente vertical/horizontal bater com o layout.
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
        // Travado (não SENSOR): TV box costuma não ter acelerômetro.
        activity?.requestedOrientation = if (portrait) {
            ActivityInfo.SCREEN_ORIENTATION_PORTRAIT
        } else {
            ActivityInfo.SCREEN_ORIENTATION_LANDSCAPE
        }
        onDispose {
            activity?.requestedOrientation =
                previous ?: ActivityInfo.SCREEN_ORIENTATION_UNSPECIFIED
        }
    }

    BoxWithConstraints(modifier = Modifier.fillMaxSize()) {
        val windowIsPortrait = maxHeight >= maxWidth
        val needsSoftwareRotate = portrait != windowIsPortrait
        if (!needsSoftwareRotate) {
            content()
            return@BoxWithConstraints
        }

        // Monitor em pé + SO em landscape: gira o UI -90° para o "topo" do
        // layout apontar para o topo físico do monitor (montagem CW típica).
        val rotation = if (portrait) -90f else 90f
        Box(
            modifier = Modifier
                .requiredWidth(maxHeight)
                .requiredHeight(maxWidth)
                .align(Alignment.Center)
                .graphicsLayer { rotationZ = rotation },
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
