package com.example.appsenhas.ui.tv

import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Person
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.Icon
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.Shadow
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.lifecycle.viewmodel.compose.viewModel
import coil.compose.AsyncImage
import com.example.appsenhas.data.remote.NetworkModule
import com.example.appsenhas.data.remote.dto.SenhaDto
import com.example.appsenhas.ui.theme.CianoNeonTv
import com.example.appsenhas.ui.theme.GradienteTvFundo
import com.example.appsenhas.ui.theme.VerdeNeonTv
import com.example.appsenhas.ui.theme.VermelhoPreferencial

/** Réplica visual de `templates/senha_atual.html`: painel escuro tipo TV
 * com brilho neon verde na senha chamada e card do operador com foto. */
@Composable
fun TvScreen(viewModel: TvViewModel = viewModel()) {
    Box(
        modifier = Modifier
            .fillMaxSize()
            .background(GradienteTvFundo),
    ) {
        Column(modifier = Modifier.fillMaxSize().padding(28.dp)) {
            Column(
                modifier = Modifier.fillMaxWidth(),
                horizontalAlignment = Alignment.CenterHorizontally,
            ) {
                Card(
                    shape = RoundedCornerShape(28.dp),
                    colors = CardDefaults.cardColors(containerColor = Color(0xFF121212).copy(alpha = 0.85f)),
                    elevation = CardDefaults.cardElevation(defaultElevation = 12.dp),
                    modifier = Modifier
                        .fillMaxWidth()
                        .border(1.dp, VerdeNeonTv.copy(alpha = 0.25f), RoundedCornerShape(28.dp)),
                ) {
                    Column(
                        modifier = Modifier.fillMaxWidth().padding(36.dp),
                        horizontalAlignment = Alignment.CenterHorizontally,
                    ) {
                        Text(
                            text = "SENHA ATUAL",
                            style = MaterialTheme.typography.titleLarge,
                            color = VerdeNeonTv,
                            fontWeight = FontWeight.Light,
                            letterSpacing = 4.sp,
                        )
                        Text(
                            text = viewModel.ultimaChamadaSenha ?: "Aguardando próxima senha...",
                            fontSize = if ((viewModel.ultimaChamadaSenha?.length ?: 0) > 0) 90.sp else 34.sp,
                            fontWeight = FontWeight.Bold,
                            fontFamily = FontFamily.Monospace,
                            color = Color.White,
                            textAlign = TextAlign.Center,
                            letterSpacing = 4.sp,
                            style = MaterialTheme.typography.displayLarge.copy(
                                shadow = Shadow(color = VerdeNeonTv.copy(alpha = 0.8f), offset = Offset(0f, 0f), blurRadius = 40f),
                            ),
                            modifier = Modifier.padding(top = 16.dp, bottom = 8.dp),
                        )

                        if (viewModel.ultimaChamadaOperador != null) {
                            OperadorCardTv(
                                nome = viewModel.ultimaChamadaOperador!!,
                                foto = viewModel.ultimaChamadaOperadorFoto,
                            )
                        }
                    }
                }
            }

            Text(
                text = "Aguardando (${viewModel.pendentes.size})",
                style = MaterialTheme.typography.titleMedium,
                color = Color.White.copy(alpha = 0.7f),
                modifier = Modifier.padding(top = 28.dp, bottom = 8.dp),
            )
            LazyColumn(modifier = Modifier.weight(1f)) {
                items(viewModel.pendentes) { senha -> LinhaSenhaTv(senha) }
            }

            viewModel.errorMessage?.let {
                Text(it, color = MaterialTheme.colorScheme.error, modifier = Modifier.padding(top = 8.dp))
            }
        }
    }
}

@Composable
private fun OperadorCardTv(nome: String, foto: String?) {
    Row(
        verticalAlignment = Alignment.CenterVertically,
        modifier = Modifier
            .padding(top = 24.dp)
            .clip(RoundedCornerShape(50))
            .background(VerdeNeonTv.copy(alpha = 0.1f))
            .border(1.dp, VerdeNeonTv.copy(alpha = 0.3f), RoundedCornerShape(50))
            .padding(horizontal = 20.dp, vertical = 10.dp),
    ) {
        Box(
            modifier = Modifier
                .size(48.dp)
                .clip(CircleShape)
                .background(VerdeNeonTv.copy(alpha = 0.15f))
                .border(2.dp, VerdeNeonTv.copy(alpha = 0.5f), CircleShape),
            contentAlignment = Alignment.Center,
        ) {
            if (foto != null) {
                AsyncImage(
                    model = "${NetworkModule.currentHttpBaseUrl()}uploads/$foto",
                    contentDescription = nome,
                    modifier = Modifier.size(48.dp).clip(CircleShape),
                )
            } else {
                Icon(Icons.Filled.Person, contentDescription = null, tint = VerdeNeonTv)
            }
        }
        Column(modifier = Modifier.padding(start = 12.dp)) {
            Text(text = nome, color = VerdeNeonTv, fontWeight = FontWeight.Bold)
            Text(text = "Atendendo agora", color = CianoNeonTv, style = MaterialTheme.typography.labelSmall)
        }
    }
}

@Composable
private fun LinhaSenhaTv(senha: SenhaDto) {
    val preferencial = senha.tipo == "preferencial"
    Row(
        modifier = Modifier.fillMaxWidth().padding(vertical = 8.dp),
        horizontalArrangement = Arrangement.SpaceBetween,
    ) {
        Text(
            senha.senha,
            style = MaterialTheme.typography.headlineSmall,
            fontWeight = FontWeight.Bold,
            fontFamily = FontFamily.Monospace,
            color = Color.White,
        )
        Text(
            text = if (preferencial) "Preferencial" else "Normal",
            style = MaterialTheme.typography.bodyLarge,
            color = if (preferencial) VermelhoPreferencial else VerdeNeonTv,
        )
    }
}
