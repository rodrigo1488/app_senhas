package com.example.appsenhas.ui.avaliacao

import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.StarOutline
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.Icon
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text
import androidx.compose.material3.TopAppBar
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import androidx.lifecycle.viewmodel.compose.viewModel

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun AvaliacaoScreen(viewModel: AvaliacaoViewModel = viewModel()) {
    Scaffold(topBar = { TopAppBar(title = { Text("Avaliação — ${viewModel.operadorNome ?: ""}") }) }) { padding ->
        Column(
            modifier = Modifier.fillMaxSize().padding(padding).padding(24.dp),
            horizontalAlignment = Alignment.CenterHorizontally,
            verticalArrangement = Arrangement.Center,
        ) {
            when {
                viewModel.isLoading -> CircularProgressIndicator()
                viewModel.enviado -> {
                    Text("Obrigado pela avaliação!", style = MaterialTheme.typography.headlineSmall)
                }
                viewModel.senhaId == null -> {
                    Text(
                        "Nenhum atendimento pendente de avaliação.",
                        style = MaterialTheme.typography.titleMedium,
                    )
                }
                else -> {
                    Text("Como foi o atendimento da senha ${viewModel.senha ?: ""}?", style = MaterialTheme.typography.titleMedium)
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
private fun EstrelasAvaliacao(onSelecionar: (Int) -> Unit) {
    Row(modifier = Modifier.padding(top = 24.dp)) {
        for (nota in 1..5) {
            Icon(
                imageVector = Icons.Filled.StarOutline,
                contentDescription = "$nota estrelas",
                tint = MaterialTheme.colorScheme.primary,
                modifier = Modifier
                    .size(40.dp)
                    .padding(4.dp)
                    .clickable { onSelecionar(nota) },
            )
        }
    }
}
