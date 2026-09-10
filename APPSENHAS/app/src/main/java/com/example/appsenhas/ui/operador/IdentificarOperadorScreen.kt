package com.example.appsenhas.ui.operador

import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Person
import androidx.compose.material3.Card
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.Icon
import androidx.compose.material3.ListItem
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text
import androidx.compose.material3.TopAppBar
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.unit.dp
import androidx.lifecycle.viewmodel.compose.viewModel
import coil.compose.AsyncImage
import com.example.appsenhas.data.remote.dto.OperadorDto
import com.example.appsenhas.data.remote.dto.Papel

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun IdentificarOperadorScreen(
    papel: Papel,
    fotoBaseUrl: String,
    onSelecionado: () -> Unit,
    viewModel: IdentificarOperadorViewModel = viewModel(),
) {
    val titulo = if (papel == Papel.AVALIACAO) "Quem está avaliando?" else "Quem é você?"

    Scaffold(topBar = { TopAppBar(title = { Text(titulo) }) }) { padding ->
        Box(modifier = Modifier.fillMaxSize().padding(padding)) {
            when {
                viewModel.isLoading -> {
                    CircularProgressIndicator(modifier = Modifier.align(Alignment.Center))
                }
                viewModel.operadores.isEmpty() -> {
                    Text(
                        text = "Nenhum operador cadastrado para este setor.",
                        modifier = Modifier.align(Alignment.Center).padding(24.dp),
                    )
                }
                else -> {
                    LazyColumn(contentPadding = PaddingValues(16.dp)) {
                        items(viewModel.operadores) { operador ->
                            OperadorRow(
                                operador = operador,
                                fotoBaseUrl = fotoBaseUrl,
                                enabled = !viewModel.isSubmitting,
                                onClick = { viewModel.selecionarOperador(operador, papel, onSelecionado) },
                            )
                        }
                    }
                }
            }

            viewModel.errorMessage?.let { message ->
                Column(modifier = Modifier.align(Alignment.BottomCenter).padding(16.dp)) {
                    Text(text = message, color = MaterialTheme.colorScheme.error)
                }
            }
        }
    }
}

@Composable
private fun OperadorRow(
    operador: OperadorDto,
    fotoBaseUrl: String,
    enabled: Boolean,
    onClick: () -> Unit,
) {
    Card(
        modifier = Modifier
            .fillMaxWidth()
            .padding(vertical = 6.dp)
            .clickable(enabled = enabled) { onClick() },
    ) {
        ListItem(
            headlineContent = { Text(operador.nome) },
            leadingContent = {
                if (operador.foto_perfil != null) {
                    AsyncImage(
                        model = "$fotoBaseUrl/uploads/${operador.foto_perfil}",
                        contentDescription = operador.nome,
                        modifier = Modifier.size(48.dp).clip(CircleShape),
                    )
                } else {
                    Icon(
                        imageVector = Icons.Filled.Person,
                        contentDescription = null,
                        modifier = Modifier.size(48.dp),
                    )
                }
            },
        )
    }
}
