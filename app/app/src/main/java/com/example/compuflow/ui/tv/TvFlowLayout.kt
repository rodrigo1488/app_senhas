package com.example.compuflow.ui.tv

import androidx.compose.animation.AnimatedContent
import androidx.compose.animation.core.tween
import androidx.compose.animation.fadeIn
import androidx.compose.animation.fadeOut
import androidx.compose.animation.togetherWith
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.BoxWithConstraints
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxHeight
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.HorizontalDivider
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.key
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.draw.shadow
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.Dp
import androidx.compose.ui.unit.TextUnit
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.example.compuflow.data.remote.dto.PropagandaImagemDto
import com.example.compuflow.data.remote.dto.SenhaDto
import com.example.compuflow.data.remote.dto.TvChamadaRecenteDto

private val FilaBackground = Color(0xFFE7E3DC)
private val MediaPanel = Color(0xFFD9D6CF)
private val AsideBackground = Color(0xFFF4F1EA)
private val CurrentCall = Color(0xFFE85D04)
private val Ink = Color(0xFF1B1B1B)
private val PreferencialTint = Color(0xFF59388A)

private val QueueRefHeight = 720.dp

@Composable
fun TvFlowLayout(
    chamadas: List<TvChamadaRecenteDto>,
    pendentes: List<SenhaDto>,
    item: PropagandaImagemDto?,
    mediaUrl: String?,
    loop: Boolean,
    onEnded: () -> Unit,
    vertical: Boolean = false,
    modifier: Modifier = Modifier,
) {
    BoxWithConstraints(modifier = modifier.fillMaxSize()) {
        val scale = (maxHeight / QueueRefHeight).coerceIn(0.55f, 1.15f)
        val gap = (16f * scale).coerceIn(8f, 16f).dp
        val outerPad = (16f * scale).coerceIn(8f, 16f).dp

        // Em telas baixas, menos linhas para a chamada atual sempre caber.
        val maxAnteriores = when {
            vertical && maxHeight < 900.dp -> 3
            vertical -> 5
            maxHeight < 500.dp -> 2
            else -> 3
        }
        val maxProximas = when {
            vertical && maxHeight < 900.dp -> 4
            vertical -> 7
            maxHeight < 500.dp -> 3
            else -> 5
        }
        val atual = chamadas.firstOrNull()
        val anteriores = chamadas.drop(1).take(maxAnteriores)
        val proximas = pendentes.take(maxProximas)

        // Vertical: fila precisa de espaço mínimo; mídia cede se a tela for baixa.
        val queueWeight = if (vertical) {
            val minQueue = 320.dp
            (minQueue / maxHeight).coerceIn(0.42f, 0.55f)
        } else {
            1f
        }
        val mediaWeight = if (vertical) (1f - queueWeight).coerceAtLeast(0.40f) else 2.15f

        if (vertical) {
            Column(
                modifier = Modifier
                    .fillMaxSize()
                    .background(FilaBackground)
                    .padding(outerPad),
                verticalArrangement = Arrangement.spacedBy(gap),
            ) {
                MediaPane(
                    item = item,
                    mediaUrl = mediaUrl,
                    loop = loop,
                    onEnded = onEnded,
                    corner = (28f * scale).coerceIn(16f, 36f).dp,
                    modifier = Modifier.fillMaxWidth().weight(mediaWeight),
                )
                QueuePane(
                    atual = atual,
                    anteriores = anteriores,
                    proximas = proximas,
                    scale = scale,
                    modifier = Modifier.fillMaxWidth().weight(queueWeight),
                )
            }
        } else {
            Row(
                modifier = Modifier
                    .fillMaxSize()
                    .background(FilaBackground)
                    .padding(outerPad),
                horizontalArrangement = Arrangement.spacedBy(gap),
            ) {
                MediaPane(
                    item = item,
                    mediaUrl = mediaUrl,
                    loop = loop,
                    onEnded = onEnded,
                    corner = (28f * scale).coerceIn(16f, 36f).dp,
                    modifier = Modifier.weight(mediaWeight).fillMaxHeight(),
                )
                QueuePane(
                    atual = atual,
                    anteriores = anteriores,
                    proximas = proximas,
                    scale = scale,
                    modifier = Modifier.weight(1f).fillMaxHeight(),
                )
            }
        }
    }
}

@Composable
private fun MediaPane(
    item: PropagandaImagemDto?,
    mediaUrl: String?,
    loop: Boolean,
    onEnded: () -> Unit,
    corner: Dp = 36.dp,
    modifier: Modifier = Modifier,
) {
    Box(
        modifier = modifier
            .clip(RoundedCornerShape(corner))
            .background(MediaPanel)
            .border(1.dp, Color.Black.copy(alpha = 0.10f), RoundedCornerShape(corner)),
    ) {
        key(item?.id, item?.arquivo, item?.tipo) {
            TvMediaSlide(
                item = item,
                mediaUrl = mediaUrl,
                loop = loop,
                onEnded = onEnded,
                emptyLabel = "Espaço de mídia",
                emptyBackground = MediaPanel,
                contentScale = ContentScale.Fit,
                modifier = Modifier.fillMaxSize(),
            )
        }
    }
}

@Composable
private fun QueuePane(
    atual: TvChamadaRecenteDto?,
    anteriores: List<TvChamadaRecenteDto>,
    proximas: List<SenhaDto>,
    scale: Float,
    modifier: Modifier = Modifier,
) {
    val corner = (28f * scale).coerceIn(16f, 36f).dp
    val hPad = (18f * scale).coerceIn(12f, 22f).dp
    val vPad = (18f * scale).coerceIn(12f, 24f).dp

    Column(
        modifier = modifier
            .shadow(6.dp, RoundedCornerShape(corner), clip = false)
            .clip(RoundedCornerShape(corner))
            .background(AsideBackground)
            .verticalScroll(rememberScrollState())
            .padding(horizontal = hPad, vertical = vPad),
    ) {
        GroupLabel("Chamadas anteriores", scale)
        CallTable(headers = listOf("Senha", "Tipo", "Atendente"), scale = scale) {
            if (anteriores.isEmpty()) {
                EmptyLine("Nenhuma chamada anterior", scale)
            } else {
                anteriores.forEachIndexed { index, call ->
                    PreviousRow(call = call, index = index, scale = scale)
                }
            }
        }

        AnimatedContent(
            targetState = atual,
            contentKey = { it?.let { call -> "${call.senha_id}:${call.chamada_em}" } ?: "none" },
            transitionSpec = {
                fadeIn(tween(160)) togetherWith fadeOut(tween(100))
            },
            label = "chamada-atual",
            modifier = Modifier.padding(vertical = (12f * scale).coerceIn(8f, 16f).dp),
        ) { chamada ->
            CurrentCallCard(chamada, scale)
        }

        GroupLabel("Próximas senhas", scale)
        CallTable(headers = listOf("#", "Senha", "Tipo"), scale = scale) {
            if (proximas.isEmpty()) {
                EmptyLine("Não há senhas aguardando", scale)
            } else {
                proximas.forEachIndexed { index, senha ->
                    NextRow(senha = senha, position = index + 1, scale = scale)
                }
            }
        }
    }
}

@Composable
private fun GroupLabel(text: String, scale: Float) {
    Text(
        text = text.uppercase(),
        color = Ink.copy(alpha = 0.45f),
        fontSize = scaledSp(11f, scale, 9f, 11f),
        fontWeight = FontWeight.Bold,
        letterSpacing = scaledSp(2.4f, scale, 1.2f, 2.4f),
        modifier = Modifier.padding(bottom = (6f * scale).coerceIn(4f, 8f).dp),
    )
}

@Composable
private fun CurrentCallCard(atual: TvChamadaRecenteDto?, scale: Float) {
    val corner = (22f * scale).coerceIn(14f, 28f).dp
    val hPad = (16f * scale).coerceIn(12f, 20f).dp
    val vPad = (16f * scale).coerceIn(12f, 22f).dp

    Column(
        modifier = Modifier
            .fillMaxWidth()
            .clip(RoundedCornerShape(corner))
            .background(CurrentCall)
            .padding(horizontal = hPad, vertical = vPad),
    ) {
        Text(
            text = "CHAMANDO AGORA",
            color = Color.White.copy(alpha = 0.70f),
            fontSize = scaledSp(12f, scale, 9f, 12f),
            fontWeight = FontWeight.Bold,
            letterSpacing = scaledSp(3f, scale, 1.5f, 3f),
            maxLines = 1,
            overflow = TextOverflow.Ellipsis,
        )
        if (atual == null) {
            Text(
                text = "Aguardando chamada",
                color = Color.White,
                fontSize = scaledSp(28f, scale, 18f, 28f),
                fontWeight = FontWeight.Bold,
                modifier = Modifier.padding(vertical = (12f * scale).coerceIn(8f, 18f).dp),
            )
        } else {
            Row(
                modifier = Modifier.fillMaxWidth().padding(top = 4.dp),
                verticalAlignment = Alignment.Bottom,
                horizontalArrangement = Arrangement.SpaceBetween,
            ) {
                Text(
                    text = atual.senha,
                    color = Color.White,
                    fontSize = scaledSp(72f, scale, 36f, 72f),
                    fontWeight = FontWeight.Black,
                    letterSpacing = (-3).sp,
                    lineHeight = scaledSp(76f, scale, 40f, 76f),
                    maxLines = 1,
                    overflow = TextOverflow.Ellipsis,
                    modifier = Modifier.weight(1f, fill = false),
                )
                Text(
                    text = if (atual.tipo == "preferencial") "Preferencial" else "Normal",
                    color = Color.White,
                    fontSize = scaledSp(13f, scale, 10f, 13f),
                    fontWeight = FontWeight.Bold,
                    letterSpacing = 1.sp,
                    modifier = Modifier.padding(bottom = (8f * scale).coerceIn(4f, 10f).dp),
                )
            }
            OperatorRow(nome = atual.operador_nome, foto = atual.operador_foto, scale = scale)
        }
    }
}

@Composable
private fun OperatorRow(nome: String?, foto: String?, scale: Float) {
    HorizontalDivider(
        color = Color.White.copy(alpha = 0.25f),
        modifier = Modifier.padding(
            top = (10f * scale).coerceIn(6f, 14f).dp,
            bottom = (8f * scale).coerceIn(6f, 12f).dp,
        ),
    )
    Row(
        modifier = Modifier.fillMaxWidth(),
        verticalAlignment = Alignment.CenterVertically,
    ) {
        val photoSize = (36f * scale).coerceIn(28f, 42f).dp
        Box(
            modifier = Modifier
                .size(photoSize)
                .clip(RoundedCornerShape((10f * scale).coerceIn(8f, 12f).dp))
                .background(Color.White.copy(alpha = 0.15f)),
            contentAlignment = Alignment.Center,
        ) {
            TvOperatorPhoto(
                foto = foto,
                placeholderTint = Color.White.copy(alpha = 0.75f),
                placeholderSize = (photoSize.value * 0.52f).dp,
                decodeSizePx = 96,
                modifier = Modifier.fillMaxSize(),
            )
        }
        Column(modifier = Modifier.padding(start = (10f * scale).coerceIn(8f, 12f).dp)) {
            Text(
                text = "DIRIJA-SE AO ATENDIMENTO",
                color = Color.White.copy(alpha = 0.65f),
                fontSize = scaledSp(10f, scale, 8f, 10f),
                fontWeight = FontWeight.SemiBold,
                letterSpacing = scaledSp(1.6f, scale, 0.8f, 1.6f),
                maxLines = 1,
                overflow = TextOverflow.Ellipsis,
            )
            Text(
                text = nome?.takeIf { it.isNotBlank() } ?: "Operador",
                color = Color.White,
                fontSize = scaledSp(18f, scale, 13f, 18f),
                fontWeight = FontWeight.Bold,
                maxLines = 1,
                overflow = TextOverflow.Ellipsis,
            )
        }
    }
}

@Composable
private fun CallTable(
    headers: List<String>,
    scale: Float,
    content: @Composable () -> Unit,
) {
    val corner = (12f * scale).coerceIn(10f, 16f).dp
    Column(
        modifier = Modifier
            .fillMaxWidth()
            .clip(RoundedCornerShape(corner))
            .background(Color.White.copy(alpha = 0.55f))
            .border(1.dp, Color.Black.copy(alpha = 0.10f), RoundedCornerShape(corner)),
    ) {
        Row(
            modifier = Modifier
                .fillMaxWidth()
                .background(Color.Black.copy(alpha = 0.035f))
                .padding(
                    horizontal = (12f * scale).coerceIn(10f, 14f).dp,
                    vertical = (6f * scale).coerceIn(4f, 8f).dp,
                ),
        ) {
            headers.forEach { header ->
                Text(
                    text = header.uppercase(),
                    color = Ink.copy(alpha = 0.40f),
                    fontSize = scaledSp(11f, scale, 9f, 11f),
                    fontWeight = FontWeight.Bold,
                    letterSpacing = scaledSp(1.4f, scale, 0.8f, 1.4f),
                    modifier = Modifier.weight(1f),
                    maxLines = 1,
                    overflow = TextOverflow.Ellipsis,
                )
            }
        }
        content()
    }
}

@Composable
private fun PreviousRow(call: TvChamadaRecenteDto, index: Int, scale: Float) {
    Row(
        modifier = Modifier
            .fillMaxWidth()
            .padding(
                horizontal = (12f * scale).coerceIn(10f, 14f).dp,
                vertical = (8f * scale).coerceIn(6f, 10f).dp,
            ),
        verticalAlignment = Alignment.CenterVertically,
    ) {
        Row(
            modifier = Modifier.weight(1f),
            verticalAlignment = Alignment.CenterVertically,
        ) {
            OperatorPhoto(foto = call.operador_foto, scale = scale)
            Spacer(Modifier.width((6f * scale).coerceIn(4f, 8f).dp))
            Text(
                text = call.senha,
                color = Ink.copy(alpha = (0.78f - index * 0.12f).coerceAtLeast(0.40f)),
                fontSize = scaledSp(24f, scale, 16f, 24f),
                fontWeight = FontWeight.Bold,
                maxLines = 1,
                overflow = TextOverflow.Ellipsis,
            )
        }
        Box(modifier = Modifier.weight(1f)) {
            TicketType(tipo = call.tipo, scale = scale)
        }
        Text(
            text = call.operador_nome?.takeIf { it.isNotBlank() } ?: "—",
            color = Ink.copy(alpha = 0.55f),
            fontSize = scaledSp(13f, scale, 11f, 13f),
            maxLines = 1,
            overflow = TextOverflow.Ellipsis,
            modifier = Modifier.weight(1f),
        )
    }
}

@Composable
private fun NextRow(senha: SenhaDto, position: Int, scale: Float) {
    Row(
        modifier = Modifier
            .fillMaxWidth()
            .padding(
                horizontal = (12f * scale).coerceIn(10f, 14f).dp,
                vertical = (8f * scale).coerceIn(6f, 10f).dp,
            ),
        verticalAlignment = Alignment.CenterVertically,
    ) {
        Text(
            text = position.toString().padStart(2, '0'),
            color = Ink.copy(alpha = 0.35f),
            fontSize = scaledSp(12f, scale, 10f, 12f),
            fontWeight = FontWeight.SemiBold,
            modifier = Modifier.weight(1f),
        )
        Text(
            text = senha.senha,
            color = Ink,
            fontSize = scaledSp(24f, scale, 16f, 24f),
            fontWeight = FontWeight.Bold,
            modifier = Modifier.weight(1f),
            maxLines = 1,
            overflow = TextOverflow.Ellipsis,
        )
        Box(modifier = Modifier.weight(1f)) {
            TicketType(tipo = senha.tipo, scale = scale)
        }
    }
}

@Composable
private fun TicketType(tipo: String?, scale: Float) {
    val preferencial = tipo == "preferencial"
    Text(
        text = if (preferencial) "Pref." else "Normal",
        color = if (preferencial) PreferencialTint else Ink.copy(alpha = 0.45f),
        fontSize = scaledSp(11f, scale, 9f, 11f),
        fontWeight = FontWeight.Bold,
        letterSpacing = scaledSp(1.2f, scale, 0.6f, 1.2f),
    )
}

@Composable
private fun OperatorPhoto(foto: String?, scale: Float) {
    val size = (30f * scale).coerceIn(24f, 34f).dp
    Box(
        modifier = Modifier
            .size(size)
            .clip(CircleShape)
            .background(Color.Black.copy(alpha = 0.10f)),
        contentAlignment = Alignment.Center,
    ) {
        TvOperatorPhoto(
            foto = foto,
            placeholderTint = Ink.copy(alpha = 0.35f),
            placeholderSize = (size.value * 0.47f).dp,
            decodeSizePx = 72,
            modifier = Modifier.fillMaxSize(),
        )
    }
}

@Composable
private fun EmptyLine(text: String, scale: Float) {
    Box(
        modifier = Modifier
            .fillMaxWidth()
            .clip(RoundedCornerShape((10f * scale).coerceIn(8f, 12f).dp))
            .border(1.dp, Color.Black.copy(alpha = 0.15f), RoundedCornerShape((10f * scale).coerceIn(8f, 12f).dp))
            .padding(
                horizontal = (12f * scale).coerceIn(10f, 16f).dp,
                vertical = (8f * scale).coerceIn(6f, 12f).dp,
            ),
        contentAlignment = Alignment.Center,
    ) {
        Text(
            text = text,
            color = Ink.copy(alpha = 0.35f),
            fontSize = scaledSp(13f, scale, 11f, 13f),
            textAlign = TextAlign.Center,
        )
    }
}

private fun scaledSp(base: Float, scale: Float, min: Float, max: Float): TextUnit =
    (base * scale).coerceIn(min, max).sp
