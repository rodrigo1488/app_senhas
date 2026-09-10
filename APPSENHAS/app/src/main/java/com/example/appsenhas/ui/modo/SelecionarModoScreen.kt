package com.example.appsenhas.ui.modo

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.EmojiEvents
import androidx.compose.material.icons.filled.Person
import androidx.compose.material.icons.filled.SupportAgent
import androidx.compose.material.icons.filled.Tv
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.FilledTonalButton
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
import com.example.appsenhas.data.remote.dto.Papel

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun SelecionarModoScreen(
    setorNome: String,
    onSelecionarCliente: () -> Unit,
    onSelecionarOperador: () -> Unit,
    onSelecionarAvaliacao: () -> Unit,
    onSelecionarTv: () -> Unit,
    viewModel: SelecionarModoViewModel = viewModel(),
) {
    Scaffold(
        topBar = {
            TopAppBar(title = { Text(setorNome) })
        }
    ) { padding ->
        Column(
            modifier = Modifier
                .fillMaxSize()
                .padding(padding)
                .padding(24.dp),
            horizontalAlignment = Alignment.CenterHorizontally,
            verticalArrangement = Arrangement.Center,
        ) {
            Text(
                text = "Como você vai usar o app?",
                style = MaterialTheme.typography.titleLarge,
                modifier = Modifier.padding(bottom = 24.dp),
            )

            ModoButton(
                label = "Cliente — retirar senha",
                icon = Icons.Filled.Person,
                enabled = !viewModel.isLoading,
                onClick = { viewModel.selecionarPapelSimples(Papel.CLIENTE, onSelecionarCliente) },
            )
            ModoButton(
                label = "Operador — chamar senhas",
                icon = Icons.Filled.SupportAgent,
                enabled = !viewModel.isLoading,
                onClick = onSelecionarOperador,
            )
            ModoButton(
                label = "Avaliação de atendimento",
                icon = Icons.Filled.EmojiEvents,
                enabled = !viewModel.isLoading,
                onClick = onSelecionarAvaliacao,
            )
            ModoButton(
                label = "TV — painel de chamadas",
                icon = Icons.Filled.Tv,
                enabled = !viewModel.isLoading,
                onClick = { viewModel.selecionarPapelSimples(Papel.TV, onSelecionarTv) },
            )

            if (viewModel.isLoading) {
                CircularProgressIndicator(modifier = Modifier.padding(top = 16.dp))
            }

            viewModel.errorMessage?.let { message ->
                Text(
                    text = message,
                    color = MaterialTheme.colorScheme.error,
                    style = MaterialTheme.typography.bodySmall,
                    modifier = Modifier.padding(top = 12.dp),
                )
            }
        }
    }
}

@Composable
private fun ModoButton(
    label: String,
    icon: androidx.compose.ui.graphics.vector.ImageVector,
    enabled: Boolean,
    onClick: () -> Unit,
) {
    FilledTonalButton(
        onClick = onClick,
        enabled = enabled,
        modifier = Modifier
            .fillMaxWidth()
            .height(58.dp)
            .padding(vertical = 6.dp),
    ) {
        Icon(imageVector = icon, contentDescription = null, modifier = Modifier.padding(end = 12.dp))
        Text(label)
    }
}
