package com.example.compuflow.ui.tv

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.BoxWithConstraints
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
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.Dp
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.lifecycle.viewmodel.compose.viewModel
import com.example.compuflow.data.remote.dto.PropagandaImagemDto
import com.example.compuflow.ui.common.ForcedDisplayOrientation

private val PreferencialPanel = Color(0xFF120B1E)
private val NormalPanel = Color(0xFFE85D04)

/** Altura de referência do painel Preferencial/Normal no design original. */
private val PanelRefHeight = 140.dp

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

    ForcedDisplayOrientation(portrait = vertical) {
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
                    senhasNoTopo = viewModel.posicaoSenhasTv != "inferior",
                )
            }
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
    senhasNoTopo: Boolean = true,
) {
    Column(modifier = Modifier.fillMaxSize()) {
        if (senhasNoTopo) {
            SenhasFaixa(
                modifier = Modifier
                    .fillMaxWidth()
                    .weight(if (vertical) 0.38f else 0.22f),
                vertical = vertical,
                preferencialSenha = preferencialSenha,
                preferencialFoto = preferencialFoto,
                normalSenha = normalSenha,
                normalFoto = normalFoto,
            )
        }
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
        if (!senhasNoTopo) {
            SenhasFaixa(
                modifier = Modifier
                    .fillMaxWidth()
                    .weight(if (vertical) 0.38f else 0.22f),
                vertical = vertical,
                preferencialSenha = preferencialSenha,
                preferencialFoto = preferencialFoto,
                normalSenha = normalSenha,
                normalFoto = normalFoto,
            )
        }
    }
}

@Composable
private fun SenhasFaixa(
    modifier: Modifier,
    vertical: Boolean,
    preferencialSenha: String?,
    preferencialFoto: String?,
    normalSenha: String?,
    normalFoto: String?,
) {
    if (vertical) {
        Column(
            modifier = modifier,
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
            modifier = modifier,
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

@Composable
private fun TipoSenhaPanel(
    titulo: String,
    senha: String?,
    foto: String?,
    background: Color,
    modifier: Modifier,
) {
    BoxWithConstraints(modifier = modifier.background(background)) {
        val scale = (maxHeight / PanelRefHeight).coerceIn(0.40f, 1.15f)
        val compact = maxHeight < 100.dp
        val panelMaxWidth = maxWidth
        val titleSp = (18f * scale).coerceIn(11f, 22f).sp
        val senhaSp = (
            if (senha == null) 36f * scale else 64f * scale
            ).coerceIn(22f, if (senha == null) 48f else 72f).sp
        val photoDp = (64f * scale).coerceIn(28f, 72f).dp
        val hPad = (16f * scale).coerceIn(8f, 24f).dp
        val vPad = (8f * scale).coerceIn(4f, 12f).dp
        val gap = (10f * scale).coerceIn(4f, 16f).dp
        val letterSp = (2.2f * scale).coerceIn(1f, 3f).sp

        Column(
            modifier = Modifier
                .fillMaxSize()
                .padding(horizontal = hPad, vertical = vPad),
            horizontalAlignment = Alignment.CenterHorizontally,
            verticalArrangement = Arrangement.Center,
        ) {
            Text(
                text = titulo,
                color = Color.White.copy(alpha = 0.90f),
                fontSize = titleSp,
                fontWeight = FontWeight.Bold,
                letterSpacing = letterSp,
                maxLines = 1,
                overflow = TextOverflow.Ellipsis,
            )
            Row(
                modifier = Modifier.padding(top = if (compact) 2.dp else gap * 0.6f),
                verticalAlignment = Alignment.CenterVertically,
                horizontalArrangement = Arrangement.spacedBy(gap),
            ) {
                if (!compact || panelMaxWidth > 280.dp) {
                    Box(
                        modifier = Modifier
                            .size(photoDp)
                            .clip(CircleShape)
                            .background(Color.White.copy(alpha = 0.15f)),
                        contentAlignment = Alignment.Center,
                    ) {
                        TvOperatorPhoto(
                            foto = foto,
                            placeholderTint = Color.White.copy(alpha = 0.80f),
                            placeholderSize = (photoDp.value * 0.5f).dp,
                            decodeSizePx = 160,
                            modifier = Modifier.fillMaxSize(),
                        )
                    }
                }
                Text(
                    text = senha ?: "—",
                    color = Color.White,
                    fontSize = senhaSp,
                    fontWeight = FontWeight.Black,
                    textAlign = TextAlign.Center,
                    maxLines = 1,
                    overflow = TextOverflow.Ellipsis,
                )
            }
        }
    }
}
