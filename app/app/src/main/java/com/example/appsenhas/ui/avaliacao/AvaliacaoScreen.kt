package com.example.appsenhas.ui.avaliacao

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
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.Icon
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text
import androidx.compose.material3.TopAppBar
import androidx.compose.material3.TopAppBarDefaults
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
import androidx.lifecycle.viewmodel.compose.viewModel
import coil.compose.AsyncImage
import com.example.appsenhas.data.remote.NetworkModule
import com.example.appsenhas.ui.theme.AzulAvaliacaoCard
import com.example.appsenhas.ui.theme.CinzaEstrelaVazia
import com.example.appsenhas.ui.theme.DouradoEstrela
import com.example.appsenhas.ui.theme.IndigoApp

/** Réplica visual de `templates/avaliacao.html`: card azulado com foto do
 * operador e as mesmas 5 estrelas douradas para avaliar o atendimento. */
@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun AvaliacaoScreen(viewModel: AvaliacaoViewModel = viewModel()) {
    Scaffold(
        topBar = {
            TopAppBar(
                title = { Text("Avaliação de Atendimento", fontWeight = FontWeight.Bold) },
                colors = TopAppBarDefaults.topAppBarColors(containerColor = IndigoApp, titleContentColor = Color.White),
            )
        },
    ) { padding ->
        Column(
            modifier = Modifier.fillMaxSize().padding(padding).padding(24.dp),
            horizontalAlignment = Alignment.CenterHorizontally,
            verticalArrangement = Arrangement.Center,
        ) {
            when {
                viewModel.isLoading -> CircularProgressIndicator(color = IndigoApp)
                viewModel.enviado -> {
                    Icon(Icons.Filled.CheckCircle, contentDescription = null, tint = Color(0xFF28A745), modifier = Modifier.size(64.dp))
                    Text(
                        "Obrigado pela avaliação!",
                        style = MaterialTheme.typography.headlineSmall,
                        fontWeight = FontWeight.Bold,
                        modifier = Modifier.padding(top = 16.dp),
                    )
                }
                viewModel.senhaId == null -> {
                    Text(
                        "Nenhum atendimento pendente de avaliação.",
                        style = MaterialTheme.typography.titleMedium,
                        textAlign = TextAlign.Center,
                    )
                }
                else -> {
                    Text(
                        text = "Como foi o atendimento da senha ${viewModel.senha ?: ""}?",
                        style = MaterialTheme.typography.titleMedium,
                        fontWeight = FontWeight.Bold,
                        textAlign = TextAlign.Center,
                    )

                    if (viewModel.operadorNome != null) {
                        OperadorCardAvaliacao(nome = viewModel.operadorNome!!, foto = viewModel.operadorFoto)
                    }

                    EstrelasAvaliacao(onSelecionar = { nota -> viewModel.enviarAvaliacao(nota) })
                }
            }

            viewModel.errorMessage?.let {
                Text(it, color = MaterialTheme.colorScheme.error, modifier = Modifier.padding(top = 16.dp))
            }
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
                        model = "${NetworkModule.currentHttpBaseUrl()}uploads/$foto",
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
                    .size(48.dp)
                    .padding(4.dp)
                    .clickable {
                        notaSelecionada = nota
                        onSelecionar(nota)
                    },
            )
        }
    }
}
