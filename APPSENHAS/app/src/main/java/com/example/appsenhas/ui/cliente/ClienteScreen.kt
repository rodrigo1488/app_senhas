package com.example.appsenhas.ui.cliente

import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.AccessibilityNew
import androidx.compose.material.icons.filled.CheckCircle
import androidx.compose.material.icons.filled.Groups
import androidx.compose.material.icons.filled.Person
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.Icon
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.OutlinedTextFieldDefaults
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
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
import com.example.appsenhas.data.remote.NetworkModule
import com.example.appsenhas.ui.theme.FundoClienteEscuro
import com.example.appsenhas.ui.theme.VerdeSenhaNormal
import com.example.appsenhas.ui.theme.VermelhoPreferencial

/** Réplica visual de `templates/senhas.html` (fundo escuro, botões grandes
 * verde/vermelho) e do painel de acompanhamento inspirado em
 * `templates/senha_atual.html` (card com a senha em destaque). */
@Composable
fun ClienteScreen(viewModel: ClienteViewModel = viewModel()) {
    Box(
        modifier = Modifier
            .fillMaxSize()
            .background(FundoClienteEscuro),
    ) {
        if (viewModel.ticketToken == null) {
            SelecaoTipoSenha(viewModel)
        } else {
            AcompanharSenha(viewModel)
        }
    }
}

@Composable
private fun SelecaoTipoSenha(viewModel: ClienteViewModel) {
    Column(
        modifier = Modifier.fillMaxSize().padding(28.dp),
        horizontalAlignment = Alignment.CenterHorizontally,
        verticalArrangement = Arrangement.Center,
    ) {
        Text(
            text = "Bem-vindo",
            style = MaterialTheme.typography.headlineMedium,
            fontWeight = FontWeight.Bold,
            color = Color.White,
        )
        Text(
            text = "Retire uma senha:",
            style = MaterialTheme.typography.titleMedium,
            color = Color.White.copy(alpha = 0.85f),
            modifier = Modifier.padding(top = 6.dp, bottom = 36.dp),
        )

        PillButton(
            label = "Senha Normal",
            icon = Icons.Filled.Groups,
            color = VerdeSenhaNormal,
            enabled = !viewModel.isLoading,
            onClick = { viewModel.criarSenha("normal") },
        )
        PillButton(
            label = "Senha Preferencial",
            icon = Icons.Filled.AccessibilityNew,
            color = VermelhoPreferencial,
            enabled = !viewModel.isLoading,
            onClick = { viewModel.criarSenha("preferencial") },
        )

        if (viewModel.isLoading) {
            CircularProgressIndicator(color = Color.White, modifier = Modifier.padding(top = 24.dp))
        }
        viewModel.errorMessage?.let {
            Text(it, color = MaterialTheme.colorScheme.error, modifier = Modifier.padding(top = 16.dp))
        }
    }
}

@Composable
private fun PillButton(
    label: String,
    icon: androidx.compose.ui.graphics.vector.ImageVector,
    color: Color,
    enabled: Boolean,
    onClick: () -> Unit,
) {
    Button(
        onClick = onClick,
        enabled = enabled,
        shape = RoundedCornerShape(50),
        colors = ButtonDefaults.buttonColors(containerColor = color, contentColor = Color.White),
        modifier = Modifier
            .fillMaxWidth()
            .height(64.dp)
            .padding(vertical = 8.dp),
    ) {
        Icon(icon, contentDescription = null, modifier = Modifier.padding(end = 10.dp))
        Text(label, style = MaterialTheme.typography.titleMedium, fontWeight = FontWeight.Bold)
    }
}

@Composable
private fun AcompanharSenha(viewModel: ClienteViewModel) {
    var pedidoInput by remember { mutableStateOf("") }

    Column(
        modifier = Modifier.fillMaxSize().padding(24.dp),
        horizontalAlignment = Alignment.CenterHorizontally,
        verticalArrangement = Arrangement.Center,
    ) {
        Card(
            shape = RoundedCornerShape(24.dp),
            colors = CardDefaults.cardColors(containerColor = Color(0xFF1E1E1E)),
            modifier = Modifier.fillMaxWidth(),
        ) {
            Column(
                modifier = Modifier.fillMaxWidth().padding(28.dp),
                horizontalAlignment = Alignment.CenterHorizontally,
            ) {
                Text("Sua senha", style = MaterialTheme.typography.titleMedium, color = Color.White.copy(alpha = 0.7f))
                Text(
                    text = viewModel.senha ?: "-",
                    fontSize = 64.sp,
                    fontWeight = FontWeight.Bold,
                    color = VerdeSenhaNormal,
                )

                when {
                    viewModel.finalizada -> {
                        Icon(Icons.Filled.CheckCircle, contentDescription = null, tint = VerdeSenhaNormal, modifier = Modifier.size(40.dp).padding(top = 8.dp))
                        Text(
                            "Atendimento finalizado. Obrigado!",
                            style = MaterialTheme.typography.bodyLarge,
                            color = Color.White,
                            textAlign = TextAlign.Center,
                        )
                    }
                    viewModel.chamada -> {
                        Text(
                            "Você foi chamado!",
                            style = MaterialTheme.typography.headlineSmall,
                            fontWeight = FontWeight.Bold,
                            color = VerdeSenhaNormal,
                            modifier = Modifier.padding(top = 8.dp),
                        )
                        if (viewModel.operadorNome != null) {
                            OperadorMiniCard(nome = viewModel.operadorNome!!, foto = viewModel.operadorFoto)
                        }
                    }
                    viewModel.posicao != null -> {
                        Text(
                            "Posição na fila: ${viewModel.posicao}",
                            style = MaterialTheme.typography.bodyLarge,
                            color = Color.White,
                        )
                    }
                    else -> {
                        Text("Aguardando confirmação...", style = MaterialTheme.typography.bodyLarge, color = Color.White.copy(alpha = 0.8f))
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
                colors = OutlinedTextFieldDefaults.colors(
                    focusedTextColor = Color.White,
                    unfocusedTextColor = Color.White,
                    focusedBorderColor = VerdeSenhaNormal,
                    focusedLabelColor = VerdeSenhaNormal,
                ),
                modifier = Modifier.fillMaxWidth().padding(top = 20.dp),
            )
            Button(
                onClick = { viewModel.enviarPedido(pedidoInput) },
                enabled = pedidoInput.isNotBlank(),
                colors = ButtonDefaults.buttonColors(containerColor = VerdeSenhaNormal),
                shape = RoundedCornerShape(50),
                modifier = Modifier.fillMaxWidth().padding(top = 8.dp),
            ) {
                Text("Enviar pedido")
            }
        } else if (viewModel.temPedido) {
            Text(
                text = "Pedido: ${viewModel.pedidoTexto ?: ""}",
                color = Color.White.copy(alpha = 0.85f),
                modifier = Modifier.padding(top = 16.dp),
            )
        }

        if (viewModel.finalizada) {
            Button(
                onClick = { viewModel.novaSenha() },
                colors = ButtonDefaults.buttonColors(containerColor = VerdeSenhaNormal),
                shape = RoundedCornerShape(50),
                modifier = Modifier.fillMaxWidth().padding(top = 20.dp),
            ) {
                Text("Retirar nova senha")
            }
        }

        viewModel.errorMessage?.let {
            Text(it, color = MaterialTheme.colorScheme.error, modifier = Modifier.padding(top = 12.dp))
        }
    }
}

@Composable
private fun OperadorMiniCard(nome: String, foto: String?) {
    Row(
        verticalAlignment = Alignment.CenterVertically,
        modifier = Modifier.padding(top = 14.dp),
    ) {
        Box(
            modifier = Modifier
                .size(44.dp)
                .clip(CircleShape)
                .background(VerdeSenhaNormal.copy(alpha = 0.2f)),
            contentAlignment = Alignment.Center,
        ) {
            if (foto != null) {
                AsyncImage(
                    model = "${NetworkModule.currentHttpBaseUrl()}uploads/$foto",
                    contentDescription = nome,
                    modifier = Modifier.size(44.dp).clip(CircleShape),
                )
            } else {
                Icon(Icons.Filled.Person, contentDescription = null, tint = VerdeSenhaNormal)
            }
        }
        Text(
            text = nome,
            color = Color.White,
            fontWeight = FontWeight.Bold,
            modifier = Modifier.padding(start = 10.dp),
        )
    }
}
