package com.example.appsenhas.ui.operador

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.PhoneCallback
import androidx.compose.material.icons.filled.Person
import androidx.compose.material.icons.filled.PlayArrow
import androidx.compose.material.icons.filled.Receipt
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.Icon
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text
import androidx.compose.material3.TopAppBar
import androidx.compose.material3.TopAppBarDefaults
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.lifecycle.viewmodel.compose.viewModel
import coil.compose.AsyncImage
import com.example.appsenhas.data.remote.NetworkModule
import com.example.appsenhas.data.remote.dto.SenhaDto
import com.example.appsenhas.ui.theme.FundoOperadorClaro
import com.example.appsenhas.ui.theme.GradienteConfirmar
import com.example.appsenhas.ui.theme.GradienteHeroOperador
import com.example.appsenhas.ui.theme.GradienteVerPedido
import com.example.appsenhas.ui.theme.IndigoApp
import com.example.appsenhas.ui.theme.VermelhoPreferencial

/** Réplica visual de `templates/senhas_pendentes.html`: hero roxo em
 * gradiente com a senha atual + foto do operador, botão de ação principal
 * e lista de senhas pendentes abaixo. */
@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun OperadorScreen(viewModel: OperadorViewModel = viewModel()) {
    Scaffold(
        topBar = {
            TopAppBar(
                title = { Text(viewModel.meuOperadorNome ?: "Operador", fontWeight = FontWeight.Bold) },
                colors = TopAppBarDefaults.topAppBarColors(containerColor = IndigoApp, titleContentColor = Color.White),
            )
        },
        containerColor = FundoOperadorClaro,
    ) { padding ->
        Column(modifier = Modifier.fillMaxSize().padding(padding).padding(16.dp)) {

            SenhaAtualHero(viewModel)

            viewModel.errorMessage?.let {
                Text(it, color = MaterialTheme.colorScheme.error, modifier = Modifier.padding(top = 8.dp))
            }

            Button(
                onClick = { viewModel.chamarProxima() },
                enabled = !viewModel.isLoading,
                shape = RoundedCornerShape(50),
                colors = ButtonDefaults.buttonColors(containerColor = VermelhoPreferencial),
                modifier = Modifier.fillMaxWidth().height(54.dp).padding(top = 16.dp),
            ) {
                Icon(Icons.Filled.PlayArrow, contentDescription = null, modifier = Modifier.padding(end = 8.dp))
                Text("Chamar Próxima Senha", fontWeight = FontWeight.Bold)
            }

            Text(
                text = "Fila de espera (${viewModel.pendentes.size})",
                style = MaterialTheme.typography.titleMedium,
                fontWeight = FontWeight.Bold,
                color = Color(0xFF333333),
                modifier = Modifier.padding(top = 20.dp, bottom = 8.dp),
            )
            LazyColumn(modifier = Modifier.fillMaxSize()) {
                items(viewModel.pendentes) { senha -> PendenteRow(senha) }
            }
        }
    }
}

@Composable
private fun SenhaAtualHero(viewModel: OperadorViewModel) {
    val senhaAtual = viewModel.senhaChamadaAtual ?: viewModel.meuAtendimento?.senha
    val fotoOperador = viewModel.meuAtendimento?.operador_foto

    Card(
        shape = RoundedCornerShape(20.dp),
        colors = CardDefaults.cardColors(containerColor = Color.Transparent),
        elevation = CardDefaults.cardElevation(defaultElevation = 6.dp),
        modifier = Modifier.fillMaxWidth(),
    ) {
        Box(modifier = Modifier.background(GradienteHeroOperador).fillMaxWidth().padding(24.dp)) {
            Column {
                Row(
                    verticalAlignment = Alignment.CenterVertically,
                    horizontalArrangement = Arrangement.SpaceBetween,
                    modifier = Modifier.fillMaxWidth(),
                ) {
                    Row(verticalAlignment = Alignment.CenterVertically) {
                        Box(
                            modifier = Modifier
                                .size(56.dp)
                                .clip(CircleShape)
                                .background(Color.White.copy(alpha = 0.25f)),
                            contentAlignment = Alignment.Center,
                        ) {
                            if (fotoOperador != null) {
                                AsyncImage(
                                    model = "${NetworkModule.currentHttpBaseUrl()}uploads/$fotoOperador",
                                    contentDescription = null,
                                    modifier = Modifier.size(56.dp).clip(CircleShape),
                                )
                            } else {
                                Icon(Icons.Filled.Person, contentDescription = null, tint = Color.White)
                            }
                        }
                        Column(modifier = Modifier.padding(start = 12.dp)) {
                            Text(
                                text = viewModel.meuOperadorNome ?: "Operador",
                                color = Color.White,
                                fontWeight = FontWeight.Bold,
                            )
                            Box(
                                modifier = Modifier
                                    .clip(RoundedCornerShape(50))
                                    .background(Color.White.copy(alpha = 0.2f))
                                    .padding(horizontal = 10.dp, vertical = 2.dp),
                            ) {
                                Text("Atendendo agora", color = Color.White, fontSize = 11.sp)
                            }
                        }
                    }
                    Column(horizontalAlignment = Alignment.End) {
                        Text(
                            text = "SENHA ATUAL",
                            color = Color.White.copy(alpha = 0.8f),
                            fontSize = 11.sp,
                        )
                        Text(
                            text = senhaAtual ?: "Nenhuma senha chamada",
                            color = Color.White,
                            fontSize = if (senhaAtual != null) 40.sp else 16.sp,
                            fontWeight = FontWeight.Bold,
                        )
                    }
                }

                if (viewModel.temPedidoAtual) {
                    Button(
                        onClick = { viewModel.confirmarPedido() },
                        shape = RoundedCornerShape(50),
                        colors = ButtonDefaults.buttonColors(containerColor = Color.Transparent),
                        contentPadding = androidx.compose.foundation.layout.PaddingValues(0.dp),
                        modifier = Modifier.padding(top = 16.dp),
                    ) {
                        Box(
                            modifier = Modifier
                                .background(GradienteVerPedido, RoundedCornerShape(50))
                                .padding(horizontal = 20.dp, vertical = 10.dp),
                        ) {
                            Row(verticalAlignment = Alignment.CenterVertically) {
                                Icon(Icons.Filled.Receipt, contentDescription = null, tint = Color.White, modifier = Modifier.size(18.dp))
                                Text(
                                    "  Ver Pedido: ${viewModel.pedidoAtual ?: ""}",
                                    color = Color.White,
                                    fontWeight = FontWeight.Bold,
                                    style = MaterialTheme.typography.bodySmall,
                                )
                            }
                        }
                    }
                }

                val idParaChamarNovamente = viewModel.meuAtendimento?.senha_id
                if (idParaChamarNovamente != null) {
                    OutlinedButton(
                        onClick = { viewModel.chamarNovamente(idParaChamarNovamente) },
                        colors = ButtonDefaults.outlinedButtonColors(contentColor = Color.White),
                        border = androidx.compose.foundation.BorderStroke(1.dp, Color.White.copy(alpha = 0.6f)),
                        shape = RoundedCornerShape(50),
                        modifier = Modifier.padding(top = 10.dp),
                    ) {
                        Icon(Icons.AutoMirrored.Filled.PhoneCallback, contentDescription = null, modifier = Modifier.size(16.dp).padding(end = 6.dp))
                        Text("Chamar novamente")
                    }
                }
            }
        }
    }
}

@Composable
private fun PendenteRow(senha: SenhaDto) {
    val preferencial = senha.tipo == "preferencial"
    Card(
        shape = RoundedCornerShape(14.dp),
        colors = CardDefaults.cardColors(containerColor = Color.White),
        elevation = CardDefaults.cardElevation(defaultElevation = 1.dp),
        modifier = Modifier.fillMaxWidth().padding(vertical = 5.dp),
    ) {
        Row(
            modifier = Modifier.fillMaxWidth().padding(horizontal = 18.dp, vertical = 14.dp),
            horizontalArrangement = Arrangement.SpaceBetween,
            verticalAlignment = Alignment.CenterVertically,
        ) {
            Text(senha.senha, fontWeight = FontWeight.Bold, style = MaterialTheme.typography.titleMedium)
            Box(
                modifier = Modifier
                    .clip(RoundedCornerShape(50))
                    .background(if (preferencial) VermelhoPreferencial.copy(alpha = 0.12f) else Color(0xFF4CAF50).copy(alpha = 0.12f))
                    .padding(horizontal = 12.dp, vertical = 4.dp),
            ) {
                Text(
                    text = if (preferencial) "Preferencial" else "Normal",
                    color = if (preferencial) VermelhoPreferencial else Color(0xFF4CAF50),
                    fontWeight = FontWeight.Bold,
                    style = MaterialTheme.typography.labelMedium,
                )
            }
        }
    }
}
