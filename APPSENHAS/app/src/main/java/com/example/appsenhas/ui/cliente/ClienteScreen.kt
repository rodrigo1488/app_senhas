package com.example.appsenhas.ui.cliente

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.AccessibilityNew
import androidx.compose.material.icons.filled.Groups
import androidx.compose.material3.Button
import androidx.compose.material3.Card
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.Icon
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text
import androidx.compose.material3.TopAppBar
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.lifecycle.viewmodel.compose.viewModel

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun ClienteScreen(viewModel: ClienteViewModel = viewModel()) {
    Scaffold(topBar = { TopAppBar(title = { Text("Retirar senha") }) }) { padding ->
        Column(
            modifier = Modifier.fillMaxSize().padding(padding).padding(20.dp),
            horizontalAlignment = Alignment.CenterHorizontally,
        ) {
            if (viewModel.ticketToken == null) {
                SelecaoTipoSenha(viewModel)
            } else {
                AcompanharSenha(viewModel)
            }
        }
    }
}

@Composable
private fun SelecaoTipoSenha(viewModel: ClienteViewModel) {
    Column(
        modifier = Modifier.fillMaxSize(),
        horizontalAlignment = Alignment.CenterHorizontally,
        verticalArrangement = Arrangement.Center,
    ) {
        Text("Escolha o tipo de atendimento", style = MaterialTheme.typography.titleMedium)

        Button(
            onClick = { viewModel.criarSenha("normal") },
            enabled = !viewModel.isLoading,
            modifier = Modifier.fillMaxWidth().padding(top = 24.dp),
        ) {
            Icon(Icons.Filled.Groups, contentDescription = null, modifier = Modifier.padding(end = 8.dp))
            Text("Senha normal")
        }

        OutlinedButton(
            onClick = { viewModel.criarSenha("preferencial") },
            enabled = !viewModel.isLoading,
            modifier = Modifier.fillMaxWidth().padding(top = 12.dp),
        ) {
            Icon(Icons.Filled.AccessibilityNew, contentDescription = null, modifier = Modifier.padding(end = 8.dp))
            Text("Senha preferencial")
        }

        if (viewModel.isLoading) {
            CircularProgressIndicator(modifier = Modifier.padding(top = 20.dp))
        }
        viewModel.errorMessage?.let {
            Text(it, color = MaterialTheme.colorScheme.error, modifier = Modifier.padding(top = 16.dp))
        }
    }
}

@Composable
private fun AcompanharSenha(viewModel: ClienteViewModel) {
    var pedidoInput by remember { mutableStateOf("") }

    Column(
        modifier = Modifier.fillMaxSize(),
        horizontalAlignment = Alignment.CenterHorizontally,
        verticalArrangement = Arrangement.Center,
    ) {
        Card(modifier = Modifier.fillMaxWidth()) {
            Column(modifier = Modifier.fillMaxWidth().padding(24.dp), horizontalAlignment = Alignment.CenterHorizontally) {
                Text("Sua senha", style = MaterialTheme.typography.titleMedium)
                Text(
                    text = viewModel.senha ?: "-",
                    fontSize = 56.sp,
                    fontWeight = FontWeight.Bold,
                    color = MaterialTheme.colorScheme.primary,
                )

                when {
                    viewModel.finalizada -> Text("Atendimento finalizado. Obrigado!", style = MaterialTheme.typography.bodyLarge)
                    viewModel.chamada -> {
                        Text("Você foi chamado!", style = MaterialTheme.typography.headlineSmall, color = MaterialTheme.colorScheme.primary)
                        viewModel.operadorNome?.let { Text("Atendente: $it") }
                    }
                    viewModel.posicao != null -> {
                        Text("Posição na fila: ${viewModel.posicao}", style = MaterialTheme.typography.bodyLarge)
                    }
                    else -> {
                        Text("Aguardando confirmação...", style = MaterialTheme.typography.bodyLarge)
                    }
                }

                viewModel.pedidoStatusMensagem?.let {
                    Text(it, color = MaterialTheme.colorScheme.tertiary, modifier = Modifier.padding(top = 8.dp))
                }
            }
        }

        if (!viewModel.temPedido && !viewModel.finalizada) {
            OutlinedTextField(
                value = pedidoInput,
                onValueChange = { pedidoInput = it },
                label = { Text("Deseja fazer um pedido? (opcional)") },
                modifier = Modifier.fillMaxWidth().padding(top = 20.dp),
            )
            Button(
                onClick = { viewModel.enviarPedido(pedidoInput) },
                enabled = pedidoInput.isNotBlank(),
                modifier = Modifier.fillMaxWidth().padding(top = 8.dp),
            ) {
                Text("Enviar pedido")
            }
        } else if (viewModel.temPedido) {
            Text(
                text = "Pedido: ${viewModel.pedidoTexto ?: ""}",
                modifier = Modifier.padding(top = 16.dp),
            )
        }

        if (viewModel.finalizada) {
            Button(onClick = { viewModel.novaSenha() }, modifier = Modifier.fillMaxWidth().padding(top = 20.dp)) {
                Text("Retirar nova senha")
            }
        }

        viewModel.errorMessage?.let {
            Text(it, color = MaterialTheme.colorScheme.error, modifier = Modifier.padding(top = 12.dp))
        }
    }
}
