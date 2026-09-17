package com.example.compuflow.ui.tv

import androidx.compose.animation.AnimatedContent
import androidx.compose.animation.fadeIn
import androidx.compose.animation.fadeOut
import androidx.compose.animation.slideInVertically
import androidx.compose.animation.togetherWith
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
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
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Person
import androidx.compose.material3.HorizontalDivider
import androidx.compose.material3.Icon
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.draw.shadow
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import coil.compose.AsyncImage
import com.example.compuflow.data.remote.dto.PropagandaImagemDto
import com.example.compuflow.data.remote.dto.SenhaDto
import com.example.compuflow.data.remote.dto.TvChamadaRecenteDto

private val FilaBackground = Color(0xFFE7E3DC)
private val MediaPanel = Color(0xFFD9D6CF)
private val AsideBackground = Color(0xFFF4F1EA)
private val CurrentCall = Color(0xFFE85D04)
private val Ink = Color(0xFF1B1B1B)
private val PreferencialTint = Color(0xFF59388A)

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
    val atual = chamadas.firstOrNull()
    val anteriores = chamadas.drop(1).take(if (vertical) 5 else 3)
    val proximas = pendentes.take(if (vertical) 7 else 5)

    if (vertical) {
        Column(
            modifier = modifier
                .fillMaxSize()
                .background(FilaBackground)
                .padding(16.dp),
            verticalArrangement = Arrangement.spacedBy(16.dp),
        ) {
            MediaPane(
                item = item,
                mediaUrl = mediaUrl,
                loop = loop,
                onEnded = onEnded,
                modifier = Modifier.fillMaxWidth().weight(1.05f),
            )
            QueuePane(
                atual = atual,
                anteriores = anteriores,
                proximas = proximas,
                modifier = Modifier.fillMaxWidth().weight(1f),
            )
        }
    } else {
        Row(
            modifier = modifier
                .fillMaxSize()
                .background(FilaBackground)
                .padding(16.dp),
            horizontalArrangement = Arrangement.spacedBy(16.dp),
        ) {
            MediaPane(
                item = item,
                mediaUrl = mediaUrl,
                loop = loop,
                onEnded = onEnded,
                modifier = Modifier.weight(2.15f).fillMaxHeight(),
            )
            QueuePane(
                atual = atual,
                anteriores = anteriores,
                proximas = proximas,
                modifier = Modifier.weight(1f).fillMaxHeight(),
            )
        }
    }
}

@Composable
private fun MediaPane(
    item: PropagandaImagemDto?,
    mediaUrl: String?,
    loop: Boolean,
    onEnded: () -> Unit,
    modifier: Modifier = Modifier,
) {
    Box(
        modifier = modifier
            .clip(RoundedCornerShape(36.dp))
            .background(MediaPanel)
            .border(1.dp, Color.Black.copy(alpha = 0.10f), RoundedCornerShape(36.dp)),
    ) {
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

@Composable
private fun QueuePane(
    atual: TvChamadaRecenteDto?,
    anteriores: List<TvChamadaRecenteDto>,
    proximas: List<SenhaDto>,
    modifier: Modifier = Modifier,
) {
    Column(
        modifier = modifier
            .shadow(18.dp, RoundedCornerShape(36.dp), clip = false)
            .clip(RoundedCornerShape(36.dp))
            .background(AsideBackground)
            .verticalScroll(rememberScrollState())
            .padding(horizontal = 22.dp, vertical = 24.dp),
    ) {
        GroupLabel("Chamadas anteriores")
        CallTable(headers = listOf("Senha", "Tipo", "Atendente")) {
            if (anteriores.isEmpty()) {
                EmptyLine("Nenhuma chamada anterior")
            } else {
                anteriores.forEachIndexed { index, call ->
                    PreviousRow(call = call, index = index)
                }
            }
        }

        AnimatedContent(
            targetState = atual,
            contentKey = { it?.senha_id ?: 0 },
            transitionSpec = {
                (fadeIn() + slideInVertically { it / 2 }) togetherWith fadeOut()
            },
            label = "chamada-atual",
            modifier = Modifier.padding(vertical = 16.dp),
        ) { chamada ->
            CurrentCallCard(chamada)
        }

        GroupLabel("Próximas senhas")
        CallTable(headers = listOf("#", "Senha", "Tipo")) {
            if (proximas.isEmpty()) {
                EmptyLine("Não há senhas aguardando")
            } else {
                proximas.forEachIndexed { index, senha ->
                    NextRow(senha = senha, position = index + 1)
                }
            }
        }
    }
}

@Composable
private fun GroupLabel(text: String) {
    Text(
        text = text.uppercase(),
        color = Ink.copy(alpha = 0.45f),
        fontSize = 11.sp,
        fontWeight = FontWeight.Bold,
        letterSpacing = 2.4.sp,
        modifier = Modifier.padding(bottom = 8.dp),
    )
}

@Composable
private fun CurrentCallCard(atual: TvChamadaRecenteDto?) {
    Column(
        modifier = Modifier
            .fillMaxWidth()
            .clip(RoundedCornerShape(28.dp))
            .background(CurrentCall)
            .padding(horizontal = 20.dp, vertical = 22.dp),
    ) {
        Text(
            text = "CHAMANDO AGORA",
            color = Color.White.copy(alpha = 0.70f),
            fontSize = 12.sp,
            fontWeight = FontWeight.Bold,
            letterSpacing = 3.sp,
        )
        if (atual == null) {
            Text(
                text = "Aguardando chamada",
                color = Color.White,
                fontSize = 28.sp,
                fontWeight = FontWeight.Bold,
                modifier = Modifier.padding(vertical = 18.dp),
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
                    fontSize = 72.sp,
                    fontWeight = FontWeight.Black,
                    letterSpacing = (-3).sp,
                    lineHeight = 76.sp,
                )
                Text(
                    text = if (atual.tipo == "preferencial") "Preferencial" else "Normal",
                    color = Color.White,
                    fontSize = 13.sp,
                    fontWeight = FontWeight.Bold,
                    letterSpacing = 1.sp,
                    modifier = Modifier.padding(bottom = 10.dp),
                )
            }
            OperatorRow(nome = atual.operador_nome, foto = atual.operador_foto)
        }
    }
}

@Composable
private fun OperatorRow(nome: String?, foto: String?) {
    HorizontalDivider(
        color = Color.White.copy(alpha = 0.25f),
        modifier = Modifier.padding(top = 14.dp, bottom = 12.dp),
    )
    Row(
        modifier = Modifier.fillMaxWidth(),
        verticalAlignment = Alignment.CenterVertically,
    ) {
        Box(
            modifier = Modifier
                .size(42.dp)
                .clip(RoundedCornerShape(12.dp))
                .background(Color.White.copy(alpha = 0.15f)),
            contentAlignment = Alignment.Center,
        ) {
            val photoUrl = mediaUrl(foto)
            if (photoUrl != null) {
                AsyncImage(
                    model = photoUrl,
                    contentDescription = null,
                    contentScale = ContentScale.Crop,
                    modifier = Modifier.fillMaxSize(),
                )
            } else {
                Icon(
                    Icons.Filled.Person,
                    contentDescription = null,
                    tint = Color.White.copy(alpha = 0.75f),
                    modifier = Modifier.size(22.dp),
                )
            }
        }
        Column(modifier = Modifier.padding(start = 12.dp)) {
            Text(
                text = "DIRIJA-SE AO ATENDIMENTO",
                color = Color.White.copy(alpha = 0.65f),
                fontSize = 10.sp,
                fontWeight = FontWeight.SemiBold,
                letterSpacing = 1.6.sp,
            )
            Text(
                text = nome?.takeIf { it.isNotBlank() } ?: "Operador",
                color = Color.White,
                fontSize = 18.sp,
                fontWeight = FontWeight.Bold,
            )
        }
    }
}

@Composable
private fun CallTable(
    headers: List<String>,
    content: @Composable () -> Unit,
) {
    Column(
        modifier = Modifier
            .fillMaxWidth()
            .clip(RoundedCornerShape(16.dp))
            .background(Color.White.copy(alpha = 0.55f))
            .border(1.dp, Color.Black.copy(alpha = 0.10f), RoundedCornerShape(16.dp)),
    ) {
        Row(
            modifier = Modifier
                .fillMaxWidth()
                .background(Color.Black.copy(alpha = 0.035f))
                .padding(horizontal = 14.dp, vertical = 8.dp),
        ) {
            headers.forEach { header ->
                Text(
                    text = header.uppercase(),
                    color = Ink.copy(alpha = 0.40f),
                    fontSize = 11.sp,
                    fontWeight = FontWeight.Bold,
                    letterSpacing = 1.4.sp,
                    modifier = Modifier.weight(1f),
                )
            }
        }
        content()
    }
}

@Composable
private fun PreviousRow(call: TvChamadaRecenteDto, index: Int) {
    Row(
        modifier = Modifier
            .fillMaxWidth()
            .padding(horizontal = 14.dp, vertical = 10.dp),
        verticalAlignment = Alignment.CenterVertically,
    ) {
        Row(
            modifier = Modifier.weight(1f),
            verticalAlignment = Alignment.CenterVertically,
        ) {
            OperatorPhoto(foto = call.operador_foto)
            Spacer(Modifier.width(8.dp))
            Text(
                text = call.senha,
                color = Ink.copy(alpha = (0.78f - index * 0.12f).coerceAtLeast(0.40f)),
                fontSize = 24.sp,
                fontWeight = FontWeight.Bold,
            )
        }
        Box(modifier = Modifier.weight(1f)) {
            TicketType(tipo = call.tipo)
        }
        Text(
            text = call.operador_nome?.takeIf { it.isNotBlank() } ?: "—",
            color = Ink.copy(alpha = 0.55f),
            fontSize = 13.sp,
            maxLines = 1,
            overflow = TextOverflow.Ellipsis,
            modifier = Modifier.weight(1f),
        )
    }
}

@Composable
private fun NextRow(senha: SenhaDto, position: Int) {
    Row(
        modifier = Modifier
            .fillMaxWidth()
            .padding(horizontal = 14.dp, vertical = 10.dp),
        verticalAlignment = Alignment.CenterVertically,
    ) {
        Text(
            text = position.toString().padStart(2, '0'),
            color = Ink.copy(alpha = 0.35f),
            fontSize = 12.sp,
            fontWeight = FontWeight.SemiBold,
            modifier = Modifier.weight(1f),
        )
        Text(
            text = senha.senha,
            color = Ink,
            fontSize = 24.sp,
            fontWeight = FontWeight.Bold,
            modifier = Modifier.weight(1f),
        )
        Box(modifier = Modifier.weight(1f)) {
            TicketType(tipo = senha.tipo)
        }
    }
}

@Composable
private fun TicketType(tipo: String?) {
    val preferencial = tipo == "preferencial"
    Text(
        text = if (preferencial) "Pref." else "Normal",
        color = if (preferencial) PreferencialTint else Ink.copy(alpha = 0.45f),
        fontSize = 11.sp,
        fontWeight = FontWeight.Bold,
        letterSpacing = 1.2.sp,
    )
}

@Composable
private fun OperatorPhoto(foto: String?) {
    Box(
        modifier = Modifier
            .size(34.dp)
            .clip(CircleShape)
            .background(Color.Black.copy(alpha = 0.10f)),
        contentAlignment = Alignment.Center,
    ) {
        val photoUrl = mediaUrl(foto)
        if (photoUrl != null) {
            AsyncImage(
                model = photoUrl,
                contentDescription = null,
                contentScale = ContentScale.Crop,
                modifier = Modifier.fillMaxSize(),
            )
        } else {
            Icon(
                Icons.Filled.Person,
                contentDescription = null,
                tint = Ink.copy(alpha = 0.35f),
                modifier = Modifier.size(16.dp),
            )
        }
    }
}

@Composable
private fun EmptyLine(text: String) {
    Box(
        modifier = Modifier
            .fillMaxWidth()
            .clip(RoundedCornerShape(12.dp))
            .border(1.dp, Color.Black.copy(alpha = 0.15f), RoundedCornerShape(12.dp))
            .padding(horizontal = 16.dp, vertical = 12.dp),
        contentAlignment = Alignment.Center,
    ) {
        Text(
            text = text,
            color = Ink.copy(alpha = 0.35f),
            fontSize = 13.sp,
            textAlign = TextAlign.Center,
        )
    }
}
