package com.example.appsenhas.ui.operador

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.material3.Button
import androidx.compose.material3.Card
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.HorizontalDivider
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text
import androidx.compose.material3.TopAppBar
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.lifecycle.viewmodel.compose.viewModel
import com.example.appsenhas.data.remote.dto.SenhaDto

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun OperadorScreen(viewModel: OperadorViewModel = viewModel()) {
    Scaffold(
        topBar = { TopAppBar(title = { Text(viewModel.meuOperadorNome ?: "Operador") }) },
    ) { padding ->
        Column(modifier = Modifier.fillMaxSize().padding(padding).padding(16.dp)) {

            Card(modifier = Modifier.fillMaxWidth()) {
                Column(modifier = Modifier.fillMaxWidth().padding(16.dp)) {
                    Text("Atendimento atual", style = MaterialTheme.typography.titleMedium)
                    val chamada = viewModel.senhaChamadaAtual ?: viewModel.meuAtendimento?.senha
                    Text(
                        text = chamada ?: "Nenhuma senha chamada",
                        style = MaterialTheme.typography.headlineMedium,
                        fontWeight = FontWeight.Bold,
                    )
                    if (viewModel.temPedidoAtual) {
                        Text("Pedido: ${viewModel.pedidoAtual ?: ""}")
                        Button(onClick = { viewModel.confirmarPedido() }, modifier = Modifier.padding(top = 8.dp)) {
                            Text("Confirmar pedido")
                        }
                    }
                    Row(modifier = Modifier.padding(top = 12.dp)) {
                        Button(onClick = { viewModel.chamarProxima() }, enabled = !viewModel.isLoading) {
                            Text("Chamar próxima")
                        }
                        val idParaChamarNovamente = viewModel.meuAtendimento?.senha_id
                        if (idParaChamarNovamente != null) {
                            OutlinedButton(
                                onClick = { viewModel.chamarNovamente(idParaChamarNovamente) },
                                modifier = Modifier.padding(start = 8.dp),
                            ) {
                                Text("Chamar novamente")
                            }
                        }
                    }
                }
            }

            viewModel.errorMessage?.let {
                Text(it, color = MaterialTheme.colorScheme.error, modifier = Modifier.padding(top = 8.dp))
            }

            Text(
                text = "Fila de espera (${viewModel.pendentes.size})",
                style = MaterialTheme.typography.titleMedium,
                modifier = Modifier.padding(top = 20.dp, bottom = 8.dp),
            )
            HorizontalDivider()
            LazyColumn(modifier = Modifier.fillMaxSize()) {
                items(viewModel.pendentes) { senha -> PendenteRow(senha) }
            }
        }
    }
}

@Composable
private fun PendenteRow(senha: SenhaDto) {
    Row(
        modifier = Modifier.fillMaxWidth().padding(vertical = 10.dp),
        horizontalArrangement = Arrangement.SpaceBetween,
    ) {
        Text(senha.senha, fontWeight = FontWeight.Bold)
        Text(if (senha.tipo == "preferencial") "Preferencial" else "Normal")
    }
}
