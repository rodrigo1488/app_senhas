package com.example.compuflow.ui.operador

import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.lazy.grid.GridCells
import androidx.compose.foundation.lazy.grid.LazyVerticalGrid
import androidx.compose.foundation.lazy.grid.items
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Person
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.Icon
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text
import androidx.compose.material3.TopAppBar
import androidx.compose.material3.TopAppBarDefaults
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
import androidx.lifecycle.viewmodel.compose.viewModel
import coil.compose.AsyncImage
import com.example.compuflow.data.remote.dto.OperadorDto
import com.example.compuflow.data.remote.dto.Papel
import com.example.compuflow.ui.theme.IndigoApp

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun IdentificarOperadorScreen(
    papel: Papel,
    fotoBaseUrl: String,
    onSelecionado: () -> Unit,
    viewModel: IdentificarOperadorViewModel = viewModel(),
) {
    val titulo = if (papel == Papel.AVALIACAO) "Quem está avaliando?" else "Quem é você?"

    Scaffold(
        topBar = {
            TopAppBar(
                title = { Text(titulo, fontWeight = FontWeight.Bold) },
                colors = TopAppBarDefaults.topAppBarColors(
                    containerColor = IndigoApp,
                    titleContentColor = Color.White,
                ),
            )
        },
        containerColor = Color(0xFFF4F4F4),
    ) { padding ->
        Box(modifier = Modifier.fillMaxSize().padding(padding)) {
            when {
                viewModel.isLoading -> {
                    CircularProgressIndicator(modifier = Modifier.align(Alignment.Center), color = IndigoApp)
                }
                papel == Papel.OPERADOR && viewModel.modoIdentificacao == "pin" -> {
                    PinIdentification(
                        enabled = !viewModel.isSubmitting,
                        onConfirm = { pin -> viewModel.identificarPorPin(pin, onSelecionado) },
                        modifier = Modifier.align(Alignment.Center),
                    )
                }
                viewModel.operadores.isEmpty() -> {
                    Text(
                        text = "Nenhum operador cadastrado para este setor.",
                        modifier = Modifier.align(Alignment.Center).padding(24.dp),
                        textAlign = TextAlign.Center,
                    )
                }
                else -> {
                    LazyVerticalGrid(
                        columns = GridCells.Fixed(2),
                        contentPadding = PaddingValues(20.dp),
                        horizontalArrangement = Arrangement.spacedBy(16.dp),
                        verticalArrangement = Arrangement.spacedBy(16.dp),
                    ) {
                        items(viewModel.operadores) { operador ->
                            OperadorAvatarCard(
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
                    Text(text = message, color = MaterialTheme.colorScheme.error, textAlign = TextAlign.Center)
                }
            }
        }
    }
}

@Composable
private fun PinIdentification(
    enabled: Boolean,
    onConfirm: (String) -> Unit,
    modifier: Modifier = Modifier,
) {
    var pin by remember { mutableStateOf("") }
    Column(
        modifier = modifier.padding(24.dp),
        horizontalAlignment = Alignment.CenterHorizontally,
    ) {
        Text("Digite seu PIN", style = MaterialTheme.typography.headlineSmall, fontWeight = FontWeight.Bold)
        Text(
            text = if (pin.isEmpty()) "○ ○ ○ ○" else "● ".repeat(pin.length).trim(),
            style = MaterialTheme.typography.headlineMedium,
            color = IndigoApp,
            modifier = Modifier.padding(vertical = 20.dp),
        )
        listOf(
            listOf("1", "2", "3"),
            listOf("4", "5", "6"),
            listOf("7", "8", "9"),
            listOf("Limpar", "0", "⌫"),
        ).forEach { linha ->
            Row(horizontalArrangement = Arrangement.spacedBy(10.dp), modifier = Modifier.padding(vertical = 5.dp)) {
                linha.forEach { tecla ->
                    Button(
                        onClick = {
                            val result = processPinKey(pin, tecla, OperadorViewModel.PIN_LENGTH)
                            pin = result.displayedPin
                            result.submittedPin?.let(onConfirm)
                        },
                        enabled = enabled,
                        colors = ButtonDefaults.buttonColors(containerColor = IndigoApp),
                        modifier = Modifier.size(width = 88.dp, height = 54.dp),
                    ) {
                        Text(tecla, fontWeight = FontWeight.Bold)
                    }
                }
            }
        }
    }
}

@Composable
private fun OperadorAvatarCard(
    operador: OperadorDto,
    fotoBaseUrl: String,
    enabled: Boolean,
    onClick: () -> Unit,
) {
    Card(
        shape = RoundedCornerShape(20.dp),
        colors = CardDefaults.cardColors(containerColor = Color.White),
        elevation = CardDefaults.cardElevation(defaultElevation = 3.dp),
        modifier = Modifier
            .fillMaxWidth()
            .clickable(enabled = enabled) { onClick() },
    ) {
        Column(
            modifier = Modifier.fillMaxWidth().padding(vertical = 20.dp, horizontal = 12.dp),
            horizontalAlignment = Alignment.CenterHorizontally,
        ) {
            Box(
                modifier = Modifier
                    .size(72.dp)
                    .clip(CircleShape)
                    .background(IndigoApp.copy(alpha = 0.12f)),
                contentAlignment = Alignment.Center,
            ) {
                if (operador.foto_perfil != null) {
                    AsyncImage(
                        model = "$fotoBaseUrl/uploads/${operador.foto_perfil}",
                        contentDescription = operador.nome,
                        modifier = Modifier.size(72.dp).clip(CircleShape),
                    )
                } else {
                    Icon(
                        imageVector = Icons.Filled.Person,
                        contentDescription = null,
                        tint = IndigoApp,
                        modifier = Modifier.size(36.dp),
                    )
                }
            }
            Text(
                text = operador.nome,
                style = MaterialTheme.typography.titleSmall,
                fontWeight = FontWeight.Bold,
                textAlign = TextAlign.Center,
                modifier = Modifier.padding(top = 12.dp),
            )
        }
    }
}
