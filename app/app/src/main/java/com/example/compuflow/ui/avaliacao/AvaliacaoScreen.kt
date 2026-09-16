package com.example.compuflow.ui.avaliacao

import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.CheckCircle
import androidx.compose.material.icons.filled.Person
import androidx.compose.material.icons.filled.Star
import androidx.compose.material.icons.filled.StarOutline
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.Icon
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableIntStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.lifecycle.viewmodel.compose.viewModel
import coil.compose.AsyncImage
import com.example.compuflow.data.remote.NetworkModule
import com.example.compuflow.ui.theme.AzulAvaliacaoCard
import com.example.compuflow.ui.theme.CinzaEstrelaVazia
import com.example.compuflow.ui.theme.DouradoEstrela
import com.example.compuflow.ui.tv.TvMediaSlide
import com.example.compuflow.ui.tv.mediaUrl

@Composable
fun AvaliacaoScreen(viewModel: AvaliacaoViewModel = viewModel()) {
    Box(modifier = Modifier.fillMaxSize().background(Color.Black)) {
        when {
            viewModel.isLoading -> {
                CircularProgressIndicator(
                    color = Color.White,
                    modifier = Modifier.align(Alignment.Center),
                )
            }
            viewModel.fase == AvaliacaoFase.RATING -> {
                RatingOverlay(viewModel)
            }
            viewModel.fase == AvaliacaoFase.THANKS -> {
                ThanksOverlay()
            }
            else -> {
                IdleMediaLayer(viewModel)
            }
        }
    }
}

@Composable
private fun IdleMediaLayer(viewModel: AvaliacaoViewModel) {
    Box(modifier = Modifier.fillMaxSize()) {
        val item = viewModel.currentIdleItem
        TvMediaSlide(
            item = item,
            mediaUrl = mediaUrl(item?.arquivo),
            loop = viewModel.idleModo == "estatica",
            onEnded = { viewModel.onIdleMediaEnded() },
            emptyLabel = "Aguardando avaliação…\nConfigure mídias do setor no admin",
            modifier = Modifier.fillMaxSize(),
        )

        // Seletor discreto no rodapé (toques repetidos do kiosk ainda permitem sair).
        Surface(
            color = Color.Black.copy(alpha = 0.45f),
            modifier = Modifier
                .align(Alignment.BottomCenter)
                .fillMaxWidth(),
        ) {
            Row(
                modifier = Modifier
                    .fillMaxWidth()
                    .padding(horizontal = 12.dp, vertical = 8.dp),
                horizontalArrangement = Arrangement.SpaceEvenly,
                verticalAlignment = Alignment.CenterVertically,
            ) {
                TextButton(onClick = { viewModel.definirIdleModo("propaganda") }) {
                    Text(
                        text = "Propagandas",
                        color = if (viewModel.idleModo == "propaganda") Color.White else Color.White.copy(alpha = 0.5f),
                        fontWeight = if (viewModel.idleModo == "propaganda") FontWeight.Bold else FontWeight.Normal,
                    )
                }
                TextButton(onClick = { viewModel.definirIdleModo("estatica") }) {
                    Text(
                        text = "Imagem estática",
                        color = if (viewModel.idleModo == "estatica") Color.White else Color.White.copy(alpha = 0.5f),
                        fontWeight = if (viewModel.idleModo == "estatica") FontWeight.Bold else FontWeight.Normal,
                    )
                }
            }
        }
    }
}

@Composable
private fun RatingOverlay(viewModel: AvaliacaoViewModel) {
    Box(
        modifier = Modifier
            .fillMaxSize()
            .background(Color(0xCC0B1220)),
        contentAlignment = Alignment.Center,
    ) {
        Card(
            shape = RoundedCornerShape(24.dp),
            colors = CardDefaults.cardColors(containerColor = Color.White),
            modifier = Modifier
                .fillMaxWidth()
                .padding(28.dp),
        ) {
            Column(
                modifier = Modifier
                    .fillMaxWidth()
                    .padding(28.dp),
                horizontalAlignment = Alignment.CenterHorizontally,
            ) {
                Text(
                    text = "Como foi o atendimento da senha ${viewModel.senha ?: ""}?",
                    style = MaterialTheme.typography.titleLarge,
                    fontWeight = FontWeight.Bold,
                    textAlign = TextAlign.Center,
                    color = Color(0xFF222222),
                )
                if (viewModel.operadorNome != null) {
                    OperadorCardAvaliacao(
                        nome = viewModel.operadorNome!!,
                        foto = viewModel.operadorFoto,
                    )
                }
                EstrelasAvaliacao(onSelecionar = { nota -> viewModel.enviarAvaliacao(nota) })
                viewModel.errorMessage?.let {
                    Text(
                        it,
                        color = MaterialTheme.colorScheme.error,
                        modifier = Modifier.padding(top = 16.dp),
                        textAlign = TextAlign.Center,
                    )
                }
            }
        }
    }
}

@Composable
private fun ThanksOverlay() {
    Box(
        modifier = Modifier
            .fillMaxSize()
            .background(Color(0xCC0B1220)),
        contentAlignment = Alignment.Center,
    ) {
        Column(horizontalAlignment = Alignment.CenterHorizontally) {
            Icon(
                Icons.Filled.CheckCircle,
                contentDescription = null,
                tint = Color(0xFF28A745),
                modifier = Modifier.size(88.dp),
            )
            Text(
                "Obrigado pela avaliação!",
                color = Color.White,
                fontSize = 28.sp,
                fontWeight = FontWeight.Bold,
                modifier = Modifier.padding(top = 16.dp),
            )
        }
    }
}

@Composable
private fun OperadorCardAvaliacao(nome: String, foto: String?) {
    Card(
        shape = RoundedCornerShape(16.dp),
        colors = CardDefaults.cardColors(containerColor = AzulAvaliacaoCard.copy(alpha = 0.08f)),
        modifier = Modifier.fillMaxWidth().padding(top = 20.dp, bottom = 8.dp),
    ) {
        Row(
            modifier = Modifier.fillMaxWidth().padding(16.dp),
            verticalAlignment = Alignment.CenterVertically,
            horizontalArrangement = Arrangement.Center,
        ) {
            Box(
                modifier = Modifier
                    .size(56.dp)
                    .clip(CircleShape)
                    .background(AzulAvaliacaoCard.copy(alpha = 0.12f)),
                contentAlignment = Alignment.Center,
            ) {
                if (foto != null) {
                    AsyncImage(
                        model = "${NetworkModule.currentHttpBaseUrl().trimEnd('/')}/uploads/$foto",
                        contentDescription = nome,
                        modifier = Modifier.size(56.dp).clip(CircleShape),
                    )
                } else {
                    Icon(Icons.Filled.Person, contentDescription = null, tint = AzulAvaliacaoCard)
                }
            }
            Column(modifier = Modifier.padding(start = 14.dp)) {
                Text(text = nome, fontWeight = FontWeight.Bold, color = AzulAvaliacaoCard)
                Text(
                    text = "Atendente",
                    style = MaterialTheme.typography.labelMedium,
                    color = AzulAvaliacaoCard.copy(alpha = 0.8f),
                )
            }
        }
    }
}

@Composable
private fun EstrelasAvaliacao(onSelecionar: (Int) -> Unit) {
    var notaSelecionada by remember { mutableIntStateOf(0) }
    Row(modifier = Modifier.padding(top = 20.dp)) {
        for (nota in 1..5) {
            val preenchida = nota <= notaSelecionada
            Icon(
                imageVector = if (preenchida) Icons.Filled.Star else Icons.Filled.StarOutline,
                contentDescription = "$nota estrelas",
                tint = if (preenchida) DouradoEstrela else CinzaEstrelaVazia,
                modifier = Modifier
                    .size(56.dp)
                    .padding(4.dp)
                    .clickable {
                        notaSelecionada = nota
                        onSelecionar(nota)
                    },
            )
        }
    }
}
