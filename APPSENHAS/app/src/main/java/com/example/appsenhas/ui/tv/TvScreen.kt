package com.example.appsenhas.ui.tv

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.material3.Card
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.lifecycle.viewmodel.compose.viewModel
import com.example.appsenhas.data.remote.dto.SenhaDto

@Composable
fun TvScreen(viewModel: TvViewModel = viewModel()) {
    Surface(modifier = Modifier.fillMaxSize(), color = MaterialTheme.colorScheme.background) {
        Column(modifier = Modifier.fillMaxSize().padding(24.dp)) {
            Card(modifier = Modifier.fillMaxWidth()) {
                Column(
                    modifier = Modifier.fillMaxWidth().padding(32.dp),
                    horizontalAlignment = Alignment.CenterHorizontally,
                ) {
                    Text("Última chamada", style = MaterialTheme.typography.titleLarge)
                    Text(
                        text = viewModel.ultimaChamadaSenha ?: "-",
                        fontSize = 96.sp,
                        fontWeight = FontWeight.Bold,
                        color = MaterialTheme.colorScheme.primary,
                    )
                    viewModel.ultimaChamadaOperador?.let {
                        Text(text = it, style = MaterialTheme.typography.headlineSmall)
                    }
                }
            }

            Text(
                text = "Aguardando (${viewModel.pendentes.size})",
                style = MaterialTheme.typography.titleMedium,
                modifier = Modifier.padding(top = 24.dp, bottom = 8.dp),
            )
            LazyColumn(modifier = Modifier.weight(1f)) {
                items(viewModel.pendentes) { senha -> LinhaSenhaTv(senha) }
            }
        }
    }
}

@Composable
private fun LinhaSenhaTv(senha: SenhaDto) {
    Row(
        modifier = Modifier.fillMaxWidth().padding(vertical = 8.dp),
        horizontalArrangement = Arrangement.SpaceBetween,
    ) {
        Text(senha.senha, style = MaterialTheme.typography.headlineSmall, fontWeight = FontWeight.Bold)
        Text(
            text = if (senha.tipo == "preferencial") "Preferencial" else "Normal",
            style = MaterialTheme.typography.bodyLarge,
        )
    }
}
