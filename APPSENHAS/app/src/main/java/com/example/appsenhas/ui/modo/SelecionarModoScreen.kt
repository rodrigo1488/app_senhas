package com.example.appsenhas.ui.modo

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.ui.draw.clip
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.EmojiEvents
import androidx.compose.material.icons.filled.Person
import androidx.compose.material.icons.filled.SupportAgent
import androidx.compose.material.icons.filled.Tv
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.Icon
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.foundation.clickable
import androidx.lifecycle.viewmodel.compose.viewModel
import com.example.appsenhas.data.remote.dto.Papel
import com.example.appsenhas.ui.theme.FundoModoClaroFim
import com.example.appsenhas.ui.theme.FundoModoClaroInicio
import com.example.appsenhas.ui.theme.GradienteAvaliacao
import com.example.appsenhas.ui.theme.GradienteCliente
import com.example.appsenhas.ui.theme.GradienteOperador
import com.example.appsenhas.ui.theme.GradienteTv

/**
 * Réplica do fluxo/visual de `templates/setor_opcoes.html`: mesmo card
 * branco central, mesmos 4 botões em gradiente (cores e rótulos idênticos).
 */
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
    Box(
        modifier = Modifier
            .fillMaxSize()
            .background(Brush.linearGradient(listOf(FundoModoClaroInicio, FundoModoClaroFim))),
        contentAlignment = Alignment.Center,
    ) {
        Card(
            shape = RoundedCornerShape(24.dp),
            colors = CardDefaults.cardColors(containerColor = Color.White),
            elevation = CardDefaults.cardElevation(defaultElevation = 8.dp),
            modifier = Modifier
                .fillMaxWidth()
                .padding(28.dp),
        ) {
            Column(
                modifier = Modifier
                    .fillMaxWidth()
                    .padding(32.dp),
                horizontalAlignment = Alignment.CenterHorizontally,
            ) {
                Text(
                    text = setorNome,
                    style = MaterialTheme.typography.labelLarge,
                    color = Color(0xFF888888),
                )
                Text(
                    text = "Opções do Setor",
                    style = MaterialTheme.typography.headlineSmall,
                    fontWeight = FontWeight.Bold,
                    color = Color(0xFF222222),
                    modifier = Modifier.padding(top = 4.dp, bottom = 28.dp),
                )

                ModoGradienteButton(
                    label = "CLIENTE",
                    icon = Icons.Filled.Person,
                    gradiente = GradienteCliente,
                    enabled = !viewModel.isLoading,
                    onClick = { viewModel.selecionarPapelSimples(Papel.CLIENTE, onSelecionarCliente) },
                )
                ModoGradienteButton(
                    label = "OPERADOR",
                    icon = Icons.Filled.SupportAgent,
                    gradiente = GradienteOperador,
                    enabled = !viewModel.isLoading,
                    onClick = onSelecionarOperador,
                )
                ModoGradienteButton(
                    label = "PAINEL (TV)",
                    icon = Icons.Filled.Tv,
                    gradiente = GradienteTv,
                    textoEscuro = true,
                    enabled = !viewModel.isLoading,
                    onClick = { viewModel.selecionarPapelSimples(Papel.TV, onSelecionarTv) },
                )
                ModoGradienteButton(
                    label = "AVALIAÇÃO",
                    icon = Icons.Filled.EmojiEvents,
                    gradiente = GradienteAvaliacao,
                    enabled = !viewModel.isLoading,
                    onClick = onSelecionarAvaliacao,
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
}

@Composable
private fun ModoGradienteButton(
    label: String,
    icon: ImageVector,
    gradiente: Brush,
    enabled: Boolean,
    onClick: () -> Unit,
    textoEscuro: Boolean = false,
) {
    val corTexto = if (textoEscuro) Color(0xFF333333) else Color.White
    Box(
        modifier = Modifier
            .fillMaxWidth()
            .padding(vertical = 8.dp)
            .height(64.dp)
            .clip(RoundedCornerShape(18.dp))
            .background(gradiente)
            .clickable(enabled = enabled) { onClick() },
        contentAlignment = Alignment.Center,
    ) {
        Row(verticalAlignment = Alignment.CenterVertically) {
            Icon(imageVector = icon, contentDescription = null, tint = corTexto, modifier = Modifier.padding(end = 10.dp))
            Text(
                text = label,
                color = corTexto,
                fontWeight = FontWeight.Bold,
                style = MaterialTheme.typography.titleMedium,
            )
        }
    }
}
