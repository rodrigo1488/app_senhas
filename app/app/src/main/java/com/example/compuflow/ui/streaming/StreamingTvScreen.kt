package com.example.compuflow.ui.streaming

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.sp
import androidx.lifecycle.viewmodel.compose.viewModel
import com.example.compuflow.data.remote.NetworkModule
import com.example.compuflow.data.remote.dto.PropagandaImagemDto
import com.example.compuflow.data.remote.dto.StreamingQueueItemDto
import com.example.compuflow.ui.tv.TvMediaSlide

@Composable
fun StreamingTvScreen(viewModel: StreamingTvViewModel = viewModel()) {
    val item = viewModel.currentItem
    Box(
        modifier = Modifier
            .fillMaxSize()
            .background(Color.Black),
        contentAlignment = Alignment.Center,
    ) {
        when {
            viewModel.errorMessage != null && viewModel.queue.isEmpty() -> {
                Text(
                    text = viewModel.errorMessage ?: "",
                    color = Color.White.copy(alpha = 0.8f),
                    fontSize = 20.sp,
                    textAlign = TextAlign.Center,
                )
            }
            item == null -> {
                Text(
                    text = if (viewModel.tvNome.isNotBlank()) {
                        "TV ${viewModel.tvNome}\nAguardando mídias do admin…"
                    } else {
                        "Aguardando mídias do admin…"
                    },
                    color = Color.White.copy(alpha = 0.55f),
                    fontSize = 22.sp,
                    textAlign = TextAlign.Center,
                )
            }
            else -> {
                val slide = item.toPropagandaDto()
                TvMediaSlide(
                    item = slide,
                    mediaUrl = streamingMediaUrl(item.path),
                    loop = false,
                    onEnded = { viewModel.onMediaEnded() },
                    emptyLabel = "Sem mídia",
                    modifier = Modifier.fillMaxSize(),
                )
            }
        }
    }
}

private fun StreamingQueueItemDto.toPropagandaDto(): PropagandaImagemDto =
    PropagandaImagemDto(
        id = order,
        arquivo = path,
        ordem = order,
        tipo = if (type.equals("video", ignoreCase = true)) "video" else "image",
    )

internal fun streamingMediaUrl(path: String?): String? {
    val value = path?.trim()?.takeIf { it.isNotEmpty() } ?: return null
    if (value.startsWith("http://") || value.startsWith("https://")) return value
    val base = NetworkModule.currentHttpBaseUrl().trimEnd('/')
    return if (value.startsWith("/")) "$base$value" else "$base/$value"
}
