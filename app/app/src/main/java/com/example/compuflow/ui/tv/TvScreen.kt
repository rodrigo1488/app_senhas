package com.example.compuflow.ui.tv

import android.app.Activity
import android.content.pm.ActivityInfo
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxHeight
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.DisposableEffect
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.key
import androidx.compose.runtime.remember
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.lifecycle.viewmodel.compose.viewModel
import com.example.compuflow.data.remote.dto.PropagandaImagemDto

private val PreferencialPanel = Color(0xFF120B1E)
private val NormalPanel = Color(0xFFE85D04)

@Composable
fun TvScreen(viewModel: TvViewModel = viewModel()) {
    val context = LocalContext.current
    val soundPlayer = remember(context.applicationContext) { TvCallSoundPlayer(context) }

    LaunchedEffect(viewModel, soundPlayer) {
        viewModel.callSoundEvents.collect { soundPlayer.play() }
    }
    DisposableEffect(soundPlayer) {
        onDispose { soundPlayer.release() }
    }

    val atual = viewModel.imagens.getOrNull(viewModel.imagemIndex)
    val url = mediaUrl(atual?.arquivo)
    val loop = viewModel.imagens.size <= 1
    val vertical = viewModel.orientacaoTv == "vertical"

    DisposableEffect(vertical) {
        val activity = context as? Activity
        val previous = activity?.requestedOrientation
        activity?.requestedOrientation = if (vertical) {
            ActivityInfo.SCREEN_ORIENTATION_SENSOR_PORTRAIT
        } else {
            ActivityInfo.SCREEN_ORIENTATION_SENSOR_LANDSCAPE
        }
        onDispose {
            activity?.requestedOrientation = previous ?: ActivityInfo.SCREEN_ORIENTATION_UNSPECIFIED
        }
    }

    Surface(
        color = if (viewModel.isFilaLayout) Color(0xFFE7E3DC) else Color.Black,
        modifier = Modifier.fillMaxSize(),
    ) {
        if (viewModel.isFilaLayout) {
            TvFlowLayout(
                chamadas = viewModel.chamadas,
                pendentes = viewModel.pendentes,
                item = atual,
                mediaUrl = url,
                loop = loop,
                onEnded = viewModel::onMediaEnded,
                vertical = vertical,
            )
        } else {
            PropagandaTvLayout(
                item = atual,
                mediaUrl = url,
                loop = loop,
                onEnded = viewModel::onMediaEnded,
                preferencialSenha = viewModel.ultimaPreferencialSenha,
                preferencialFoto = viewModel.ultimaPreferencialFoto,
                normalSenha = viewModel.ultimaNormalSenha,
                normalFoto = viewModel.ultimaNormalFoto,
                vertical = vertical,
            )
        }
    }
}

@Composable
private fun PropagandaTvLayout(
    item: PropagandaImagemDto?,
    mediaUrl: String?,
    loop: Boolean,
    onEnded: () -> Unit,
    preferencialSenha: String?,
    preferencialFoto: String?,
    normalSenha: String?,
    normalFoto: String?,
    vertical: Boolean = false,
) {
        Column(modifier = Modifier.fillMaxSize()) {
        Box(
            modifier = Modifier
                .fillMaxWidth()
                .weight(if (vertical) 0.62f else 0.78f),
        ) {
            key(item?.id, item?.arquivo, item?.tipo) {
                TvMediaSlide(
                    item = item,
                    mediaUrl = mediaUrl,
                    loop = loop,
                    onEnded = onEnded,
                    emptyLabel = "Sem mídia de propaganda",
                    contentScale = ContentScale.Fit,
                    modifier = Modifier.fillMaxSize(),
                )
            }
        }
        if (vertical) {
            Column(
                modifier = Modifier
                    .fillMaxWidth()
                    .weight(0.38f),
            ) {
                TipoSenhaPanel(
                    titulo = "PREFERENCIAL",
                    senha = preferencialSenha,
                    foto = preferencialFoto,
                    background = PreferencialPanel,
                    modifier = Modifier.weight(1f).fillMaxWidth(),
                )
                TipoSenhaPanel(
                    titulo = "NORMAL",
                    senha = normalSenha,
                    foto = normalFoto,
                    background = NormalPanel,
                    modifier = Modifier.weight(1f).fillMaxWidth(),
                )
            }
        } else {
            Row(
                modifier = Modifier
                    .fillMaxWidth()
                    .weight(0.22f),
            ) {
                TipoSenhaPanel(
                    titulo = "PREFERENCIAL",
                    senha = preferencialSenha,
                    foto = preferencialFoto,
                    background = PreferencialPanel,
                    modifier = Modifier.weight(1f).fillMaxHeight(),
                )
                TipoSenhaPanel(
                    titulo = "NORMAL",
                    senha = normalSenha,
                    foto = normalFoto,
                    background = NormalPanel,
                    modifier = Modifier.weight(1f).fillMaxHeight(),
                )
            }
        }
    }
}

@Composable
private fun TipoSenhaPanel(
    titulo: String,
    senha: String?,
    foto: String?,
    background: Color,
    modifier: Modifier,
) {
    Column(
        modifier = modifier.background(background).padding(horizontal = 24.dp, vertical = 12.dp),
        horizontalAlignment = Alignment.CenterHorizontally,
        verticalArrangement = Arrangement.Center,
    ) {
        Text(
            text = titulo,
            color = Color.White.copy(alpha = 0.90f),
            fontSize = 22.sp,
            fontWeight = FontWeight.Bold,
            letterSpacing = 3.sp,
        )
        Row(
            modifier = Modifier.padding(top = 8.dp),
            verticalAlignment = Alignment.CenterVertically,
            horizontalArrangement = Arrangement.spacedBy(16.dp),
        ) {
            Box(
                modifier = Modifier
                    .size(72.dp)
                    .clip(CircleShape)
                    .background(Color.White.copy(alpha = 0.15f)),
                contentAlignment = Alignment.Center,
            ) {
                TvOperatorPhoto(
                    foto = foto,
                    placeholderTint = Color.White.copy(alpha = 0.80f),
                    placeholderSize = 36.dp,
                    decodeSizePx = 160,
                    modifier = Modifier.fillMaxSize(),
                )
            }
            Text(
                text = senha ?: "—",
                color = Color.White,
                fontSize = if (senha == null) 48.sp else 72.sp,
                fontWeight = FontWeight.Black,
                textAlign = TextAlign.Center,
            )
        }
    }
}
