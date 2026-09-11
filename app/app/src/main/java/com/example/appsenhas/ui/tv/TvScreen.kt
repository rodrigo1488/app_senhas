package com.example.appsenhas.ui.tv

import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxHeight
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Person
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.Icon
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.DisposableEffect
import androidx.compose.runtime.LaunchedEffect
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
import coil.compose.AsyncImage
import com.example.appsenhas.data.remote.NetworkModule
import com.example.appsenhas.data.remote.dto.SenhaDto

private val PreferencialPanel = Color(0xFF1A1A1A)
private val PreferencialOnPanel = Color(0xFFF5F5F5)
private val NormalPanel = Color(0xFFE85D04)
private val NormalOnPanel = Color(0xFFFFFFFF)

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

    Surface(color = MaterialTheme.colorScheme.background, modifier = Modifier.fillMaxSize()) {
        if (viewModel.showPropagandaLayout) {
            PropagandaTvLayout(
                imageUrl = mediaUrl(viewModel.imagens.getOrNull(viewModel.imagemIndex)?.arquivo),
                preferencialSenha = viewModel.ultimaPreferencialSenha,
                normalSenha = viewModel.ultimaNormalSenha,
            )
        } else {
            Row(
                modifier = Modifier.fillMaxSize().padding(32.dp),
                horizontalArrangement = Arrangement.spacedBy(24.dp),
            ) {
                CurrentCallCard(
                    senha = viewModel.ultimaChamadaSenha,
                    operadorNome = viewModel.ultimaChamadaOperador,
                    operadorFoto = viewModel.ultimaChamadaOperadorFoto,
                    modifier = Modifier.weight(1.65f).fillMaxSize(),
                )
                QueueCard(
                    pendentes = viewModel.pendentes,
                    errorMessage = viewModel.errorMessage,
                    modifier = Modifier.weight(1f).fillMaxSize(),
                )
            }
        }
    }
}

@Composable
private fun PropagandaTvLayout(
    imageUrl: String?,
    preferencialSenha: String?,
    normalSenha: String?,
) {
    Column(modifier = Modifier.fillMaxSize()) {
        Box(
            modifier = Modifier
                .fillMaxWidth()
                .weight(0.78f)
                .background(Color.Black),
            contentAlignment = Alignment.Center,
        ) {
            if (imageUrl != null) {
                AsyncImage(
                    model = imageUrl,
                    contentDescription = "Propaganda",
                    contentScale = ContentScale.Crop,
                    modifier = Modifier.fillMaxSize(),
                )
            }
        }
        Row(
            modifier = Modifier
                .fillMaxWidth()
                .weight(0.22f),
        ) {
            TipoSenhaPanel(
                titulo = "PREFERENCIAL",
                senha = preferencialSenha,
                background = PreferencialPanel,
                foreground = PreferencialOnPanel,
                modifier = Modifier.weight(1f).fillMaxHeight(),
            )
            TipoSenhaPanel(
                titulo = "NORMAL",
                senha = normalSenha,
                background = NormalPanel,
                foreground = NormalOnPanel,
                modifier = Modifier.weight(1f).fillMaxHeight(),
            )
        }
    }
}

@Composable
private fun TipoSenhaPanel(
    titulo: String,
    senha: String?,
    background: Color,
    foreground: Color,
    modifier: Modifier,
) {
    Column(
        modifier = modifier.background(background).padding(horizontal = 24.dp, vertical = 16.dp),
        horizontalAlignment = Alignment.CenterHorizontally,
        verticalArrangement = Arrangement.Center,
    ) {
        Text(
            text = titulo,
            color = foreground.copy(alpha = 0.85f),
            fontSize = 22.sp,
            fontWeight = FontWeight.SemiBold,
            letterSpacing = 2.sp,
        )
        Text(
            text = senha ?: "—",
            color = foreground,
            fontSize = if (senha == null) 48.sp else 72.sp,
            fontWeight = FontWeight.Black,
            textAlign = TextAlign.Center,
            modifier = Modifier.padding(top = 4.dp),
        )
    }
}

@Composable
private fun CurrentCallCard(
    senha: String?,
    operadorNome: String?,
    operadorFoto: String?,
    modifier: Modifier,
) {
    Card(
        modifier = modifier.border(1.dp, MaterialTheme.colorScheme.outline, RoundedCornerShape(24.dp)),
        shape = RoundedCornerShape(24.dp),
        colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface),
        elevation = CardDefaults.cardElevation(defaultElevation = 3.dp),
    ) {
        Column(
            modifier = Modifier.fillMaxSize().padding(36.dp),
            horizontalAlignment = Alignment.CenterHorizontally,
            verticalArrangement = Arrangement.Center,
        ) {
            Text(
                text = "SENHA ATUAL",
                color = MaterialTheme.colorScheme.primary,
                fontSize = 24.sp,
                fontWeight = FontWeight.SemiBold,
                letterSpacing = 3.sp,
            )
            Text(
                text = senha ?: "Aguardando",
                color = MaterialTheme.colorScheme.onSurface,
                fontSize = if (senha == null) 52.sp else 104.sp,
                lineHeight = if (senha == null) 60.sp else 112.sp,
                fontWeight = FontWeight.Black,
                textAlign = TextAlign.Center,
                modifier = Modifier.padding(vertical = 22.dp),
            )
            if (operadorNome != null) {
                OperatorCard(nome = operadorNome, foto = operadorFoto)
            } else {
                Text(
                    text = "A próxima chamada aparecerá aqui",
                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                    fontSize = 22.sp,
                )
            }
        }
    }
}

@Composable
private fun OperatorCard(nome: String, foto: String?) {
    Row(
        modifier = Modifier
            .clip(RoundedCornerShape(18.dp))
            .background(MaterialTheme.colorScheme.secondary)
            .padding(horizontal = 20.dp, vertical = 14.dp),
        verticalAlignment = Alignment.CenterVertically,
    ) {
        Box(
            modifier = Modifier.size(64.dp).clip(CircleShape)
                .background(MaterialTheme.colorScheme.surface)
                .border(2.dp, MaterialTheme.colorScheme.primary, CircleShape),
            contentAlignment = Alignment.Center,
        ) {
            val photoUrl = mediaUrl(foto)
            if (photoUrl != null) {
                AsyncImage(
                    model = photoUrl,
                    contentDescription = "Foto de $nome",
                    contentScale = ContentScale.Crop,
                    modifier = Modifier.fillMaxSize(),
                )
            } else {
                Icon(
                    Icons.Filled.Person,
                    contentDescription = null,
                    tint = MaterialTheme.colorScheme.primary,
                    modifier = Modifier.size(36.dp),
                )
            }
        }
        Column(modifier = Modifier.padding(start = 16.dp)) {
            Text("DIRIJA-SE A", color = MaterialTheme.colorScheme.onSurfaceVariant, fontSize = 14.sp)
            Text(nome, color = MaterialTheme.colorScheme.onSurface, fontSize = 27.sp, fontWeight = FontWeight.Bold)
        }
    }
}

@Composable
private fun QueueCard(pendentes: List<SenhaDto>, errorMessage: String?, modifier: Modifier) {
    Card(
        modifier = modifier.border(1.dp, MaterialTheme.colorScheme.outline, RoundedCornerShape(24.dp)),
        shape = RoundedCornerShape(24.dp),
        colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface),
    ) {
        Column(modifier = Modifier.fillMaxSize().padding(24.dp)) {
            Text("FILA DE ESPERA", color = MaterialTheme.colorScheme.onSurface, fontSize = 26.sp, fontWeight = FontWeight.Bold)
            Text(
                "${pendentes.size} ${if (pendentes.size == 1) "senha aguardando" else "senhas aguardando"}",
                color = MaterialTheme.colorScheme.onSurfaceVariant,
                fontSize = 18.sp,
                modifier = Modifier.padding(top = 4.dp, bottom = 18.dp),
            )
            LazyColumn(
                modifier = Modifier.weight(1f),
                verticalArrangement = Arrangement.spacedBy(10.dp),
            ) {
                items(pendentes, key = { it.id }) { senha -> QueueRow(senha) }
            }
            errorMessage?.let {
                Text(it, color = MaterialTheme.colorScheme.error, modifier = Modifier.padding(top = 12.dp))
            }
        }
    }
}

@Composable
private fun QueueRow(senha: SenhaDto) {
    val preferential = senha.tipo == "preferencial"
    Row(
        modifier = Modifier.fillMaxWidth().clip(RoundedCornerShape(14.dp))
            .background(MaterialTheme.colorScheme.secondary)
            .padding(horizontal = 18.dp, vertical = 14.dp),
        horizontalArrangement = Arrangement.SpaceBetween,
        verticalAlignment = Alignment.CenterVertically,
    ) {
        Text(senha.senha, color = MaterialTheme.colorScheme.onSurface, fontSize = 27.sp, fontWeight = FontWeight.Bold)
        Text(
            text = if (preferential) "PREFERENCIAL" else "NORMAL",
            color = if (preferential) MaterialTheme.colorScheme.error else MaterialTheme.colorScheme.primary,
            fontSize = 14.sp,
            fontWeight = FontWeight.Bold,
        )
    }
}

private fun mediaUrl(path: String?): String? {
    val value = path?.trim()?.takeIf { it.isNotEmpty() } ?: return null
    if (value.startsWith("http://") || value.startsWith("https://")) return value
    val normalized = value.trimStart('/').removePrefix("uploads/")
    return "${NetworkModule.currentHttpBaseUrl().trimEnd('/')}/uploads/$normalized"
}
