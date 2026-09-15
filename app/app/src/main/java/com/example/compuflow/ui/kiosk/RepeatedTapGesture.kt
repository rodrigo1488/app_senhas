package com.example.compuflow.ui.kiosk

import android.os.SystemClock
import androidx.activity.ComponentActivity
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.runtime.Composable
import androidx.compose.runtime.DisposableEffect
import androidx.compose.ui.Modifier
import androidx.compose.ui.input.pointer.PointerEventPass
import androidx.compose.ui.input.pointer.changedToUpIgnoreConsumed
import androidx.compose.ui.input.pointer.pointerInput
import androidx.compose.ui.platform.LocalContext

const val KIOSK_EXIT_TAPS = 5
const val KIOSK_EXIT_WINDOW_MS = 2_500L

fun Modifier.detectRepeatedTaps(
    tapsRequired: Int = KIOSK_EXIT_TAPS,
    windowMs: Long = KIOSK_EXIT_WINDOW_MS,
    onTriggered: () -> Unit,
): Modifier = pointerInput(tapsRequired, windowMs, onTriggered) {
    var count = 0
    var windowStart = 0L
    awaitPointerEventScope {
        while (true) {
            val event = awaitPointerEvent(PointerEventPass.Initial)
            if (event.changes.none { it.changedToUpIgnoreConsumed() }) continue
            val now = SystemClock.uptimeMillis()
            if (count == 0 || now - windowStart > windowMs) {
                count = 1
                windowStart = now
            } else {
                count++
            }
            if (count >= tapsRequired) {
                count = 0
                windowStart = 0L
                onTriggered()
            }
        }
    }
}

/**
 * Envolve telas de papel: imersivo suave (sem fixar o app no sistema) +
 * 5 toques rápidos para voltar ao menu de seleção.
 */
@Composable
fun SoftKioskHost(
    onExitToModeSelection: () -> Unit,
    content: @Composable () -> Unit,
) {
    val activity = LocalContext.current as? ComponentActivity
    DisposableEffect(activity) {
        activity?.enableSoftImmersive()
        onDispose { activity?.disableSoftImmersive() }
    }
    Box(
        modifier = Modifier
            .fillMaxSize()
            .detectRepeatedTaps(onTriggered = onExitToModeSelection),
    ) {
        content()
    }
}

internal fun registerTap(
    nowMs: Long,
    previousCount: Int,
    windowStartMs: Long,
    tapsRequired: Int,
    windowMs: Long,
): Triple<Int, Long, Boolean> {
    val count: Int
    val start: Long
    if (previousCount == 0 || nowMs - windowStartMs > windowMs) {
        count = 1
        start = nowMs
    } else {
        count = previousCount + 1
        start = windowStartMs
    }
    return if (count >= tapsRequired) {
        Triple(0, 0L, true)
    } else {
        Triple(count, start, false)
    }
}
