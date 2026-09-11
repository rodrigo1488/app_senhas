package com.example.appsenhas.ui.operador

import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.LazyRow
import androidx.compose.foundation.lazy.grid.GridCells
import androidx.compose.foundation.lazy.grid.LazyVerticalGrid
import androidx.compose.foundation.lazy.grid.items
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.PhoneCallback
import androidx.compose.material.icons.filled.ConfirmationNumber
import androidx.compose.material.icons.filled.Person
import androidx.compose.material.icons.filled.PlayArrow
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.Icon
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
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
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.compose.ui.window.Dialog
import androidx.lifecycle.viewmodel.compose.viewModel
import coil.compose.AsyncImage
import com.example.appsenhas.data.remote.NetworkModule
import com.example.appsenhas.data.remote.dto.AtendimentoDto
import com.example.appsenhas.data.remote.dto.OperadorDto
import com.example.appsenhas.data.remote.dto.SenhaDto
import com.example.appsenhas.ui.theme.AppBorder
import com.example.appsenhas.ui.theme.AppCard
import com.example.appsenhas.ui.theme.AppForeground
import com.example.appsenhas.ui.theme.AppMutedForeground
import com.example.appsenhas.ui.theme.AppPrimary
import com.example.appsenhas.ui.theme.AppPrimaryForeground
import com.example.appsenhas.ui.theme.AppSecondary
import com.example.appsenhas.ui.theme.FundoOperadorClaro
import com.example.appsenhas.ui.theme.VermelhoPreferencial

private val TextoPrincipal = AppForeground
private val TextoSecundario = AppMutedForeground
private val Borda = AppBorder
private val VerdePedido = Color(0xFF15803D)

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun OperadorScreen(viewModel: OperadorViewModel = viewModel()) {
    if (viewModel.identificacaoVisible) {
        IdentificacaoDialog(viewModel)
    }
    if (viewModel.pedidoDialogVisible) {
        PedidoDialog(viewModel)
    }

    Scaffold(
        topBar = {
            TopAppBar(
                title = {
                    Column {
                        Text("Operador", fontWeight = FontWeight.Bold)
                        Text("Fila do setor", fontSize = 12.sp, color = TextoSecundario)
                    }
                },
                colors = TopAppBarDefaults.topAppBarColors(
                    containerColor = AppCard,
                    titleContentColor = TextoPrincipal,
                ),
            )
        },
        containerColor = FundoOperadorClaro,
    ) { scaffoldPadding ->
        Column(
            modifier = Modifier
                .fillMaxSize()
                .padding(scaffoldPadding)
                .padding(horizontal = 16.dp),
        ) {
            Button(
                onClick = viewModel::abrirIdentificacao,
                enabled = !viewModel.isLoading,
                shape = RoundedCornerShape(14.dp),
                colors = ButtonDefaults.buttonColors(
                    containerColor = AppPrimary,
                    contentColor = AppPrimaryForeground,
                ),
                elevation = ButtonDefaults.buttonElevation(defaultElevation = 4.dp),
                modifier = Modifier.fillMaxWidth().padding(top = 16.dp).height(58.dp),
            ) {
                if (viewModel.isLoading) {
                    CircularProgressIndicator(color = AppPrimaryForeground, modifier = Modifier.size(22.dp), strokeWidth = 2.dp)
                } else {
                    Icon(Icons.Filled.PlayArrow, contentDescription = null)
                    Text("CHAMAR SENHA", fontWeight = FontWeight.ExtraBold, modifier = Modifier.padding(start = 8.dp))
                }
            }

            viewModel.errorMessage?.let {
                Text(it, color = MaterialTheme.colorScheme.error, modifier = Modifier.padding(top = 10.dp))
            }
            viewModel.successMessage?.let {
                Text(it, color = VerdePedido, modifier = Modifier.padding(top = 10.dp))
            }

            LazyColumn(
                modifier = Modifier.weight(1f),
                contentPadding = PaddingValues(bottom = 20.dp),
                verticalArrangement = Arrangement.spacedBy(10.dp),
            ) {
                if (viewModel.atendimentos.isNotEmpty()) {
                    item {
                        Column(Modifier.padding(top = 20.dp)) {
                            Text("Atendimentos atuais", color = TextoPrincipal, fontWeight = FontWeight.Bold, fontSize = 20.sp)
                            Text("Todos os operadores em atendimento", color = TextoSecundario, fontSize = 13.sp)
                        }
                    }
                    item {
                        LazyRow(
                            horizontalArrangement = Arrangement.spacedBy(10.dp),
                            contentPadding = PaddingValues(vertical = 4.dp),
                        ) {
                            items(
                                viewModel.atendimentos,
                                key = { "${it.operador_id}-${it.senha_id}-${it.senha}" },
                            ) { atendimento ->
                                val atendimentoLocal = viewModel.atendimentoAtual
                                    ?.takeIf { it.operador_id == atendimento.operador_id && it.senha == atendimento.senha }
                                AtendimentoAgoraCard(
                                    atendimento = atendimento,
                                    onRepetir = atendimentoLocal?.senha_id?.let { senhaId ->
                                        { viewModel.chamarNovamente(senhaId) }
                                    },
                                    onVerPedido = { viewModel.verPedido(atendimento) },
                                )
                            }
                        }
                    }
                }
                item {
                    Row(
                        modifier = Modifier.fillMaxWidth().padding(top = 10.dp),
                        horizontalArrangement = Arrangement.SpaceBetween,
                        verticalAlignment = Alignment.CenterVertically,
                    ) {
                        Column {
                            Text("Senhas pendentes", color = TextoPrincipal, fontWeight = FontWeight.Bold, fontSize = 20.sp)
                            Text("Ordem atual de atendimento", color = TextoSecundario, fontSize = 13.sp)
                        }
                        Text(
                            "${viewModel.pendentes.size}",
                            color = AppPrimary,
                            fontWeight = FontWeight.Bold,
                            modifier = Modifier
                                .clip(CircleShape)
                                .background(AppSecondary)
                                .padding(horizontal = 12.dp, vertical = 6.dp),
                        )
                    }
                }
                if (!viewModel.isLoading && viewModel.pendentes.isEmpty()) {
                    item { EmptyQueue() }
                } else {
                    items(viewModel.pendentes, key = { it.id }) { senha ->
                        PendenteCard(senha = senha, onVerPedido = { viewModel.verPedido(senha) })
                    }
                }
            }
        }
    }
}

@Composable
private fun AtendimentoAgoraCard(
    atendimento: AtendimentoDto,
    onRepetir: (() -> Unit)?,
    onVerPedido: () -> Unit,
) {
    Card(
        shape = RoundedCornerShape(14.dp),
        colors = CardDefaults.cardColors(containerColor = AppCard),
        border = BorderStroke(1.dp, Borda),
        elevation = CardDefaults.cardElevation(defaultElevation = 1.dp),
        modifier = Modifier.width(238.dp),
    ) {
        Column(modifier = Modifier.padding(12.dp)) {
            Text("ATENDENDO AGORA", color = AppPrimary, fontWeight = FontWeight.Bold, fontSize = 10.sp)
            Row(
                modifier = Modifier.fillMaxWidth().padding(top = 7.dp),
                horizontalArrangement = Arrangement.SpaceBetween,
                verticalAlignment = Alignment.CenterVertically,
            ) {
                Row(verticalAlignment = Alignment.CenterVertically, modifier = Modifier.weight(1f)) {
                    OperatorPhoto(atendimento.operador_foto, atendimento.operador_nome, 38)
                    Text(
                        atendimento.operador_nome,
                        color = TextoPrincipal,
                        fontWeight = FontWeight.Bold,
                        fontSize = 13.sp,
                        maxLines = 2,
                        modifier = Modifier.padding(start = 8.dp),
                    )
                }
                Text(
                    atendimento.senha,
                    color = TextoPrincipal,
                    fontSize = 24.sp,
                    fontWeight = FontWeight.ExtraBold,
                    modifier = Modifier.padding(start = 8.dp),
                )
            }
            Row(modifier = Modifier.padding(top = 8.dp), horizontalArrangement = Arrangement.spacedBy(6.dp)) {
                if (onRepetir != null) {
                    OutlinedButton(
                        onClick = onRepetir,
                        border = BorderStroke(1.dp, Borda),
                        colors = ButtonDefaults.outlinedButtonColors(contentColor = AppPrimary),
                        contentPadding = PaddingValues(horizontal = 8.dp, vertical = 2.dp),
                        modifier = Modifier.height(32.dp),
                    ) {
                        Icon(Icons.AutoMirrored.Filled.PhoneCallback, null, modifier = Modifier.size(14.dp))
                        Text("Repetir", modifier = Modifier.padding(start = 4.dp), fontSize = 11.sp)
                    }
                }
                if (atendimento.tem_pedido) {
                    PedidoBadge(
                        confirmado = atendimento.pedido_confirmado,
                        onClick = onVerPedido,
                        modifier = Modifier.align(Alignment.CenterVertically),
                    )
                }
            }
        }
    }
}

@Composable
private fun PendenteCard(senha: SenhaDto, onVerPedido: () -> Unit) {
    Card(
        shape = RoundedCornerShape(14.dp),
        colors = CardDefaults.cardColors(containerColor = AppCard),
        border = BorderStroke(1.dp, Borda),
        elevation = CardDefaults.cardElevation(defaultElevation = 1.dp),
        modifier = Modifier.fillMaxWidth(),
    ) {
        Row(
            modifier = Modifier.fillMaxWidth().padding(16.dp),
            horizontalArrangement = Arrangement.SpaceBetween,
            verticalAlignment = Alignment.CenterVertically,
        ) {
            Row(verticalAlignment = Alignment.CenterVertically) {
                Box(
                    modifier = Modifier.size(46.dp).clip(RoundedCornerShape(12.dp)).background(AppSecondary),
                    contentAlignment = Alignment.Center,
                ) {
                    Icon(Icons.Filled.ConfirmationNumber, null, tint = AppPrimary)
                }
                Column(modifier = Modifier.padding(start = 12.dp)) {
                    Text(senha.senha, color = TextoPrincipal, fontWeight = FontWeight.ExtraBold, fontSize = 20.sp)
                    Text(
                        if (senha.tipo == "preferencial") "Preferencial" else "Normal",
                        color = if (senha.tipo == "preferencial") VermelhoPreferencial else TextoSecundario,
                        fontSize = 12.sp,
                    )
                }
            }
            if (senha.tem_pedido) {
                PedidoBadge(senha.pedido_confirmado, onVerPedido)
            }
        }
    }
}

@Composable
private fun PedidoBadge(confirmado: Boolean, onClick: () -> Unit, modifier: Modifier = Modifier) {
    Text(
        text = pedidoBadgeLabel(temPedido = true, confirmado = confirmado).orEmpty(),
        color = if (confirmado) AppPrimary else VerdePedido,
        fontWeight = FontWeight.Bold,
        fontSize = 10.sp,
        textAlign = TextAlign.Center,
        modifier = modifier
            .clip(RoundedCornerShape(50))
            .background(if (confirmado) AppSecondary else Color(0xFFDCFCE7))
            .clickable(onClick = onClick)
            .padding(horizontal = 10.dp, vertical = 7.dp),
    )
}

@Composable
private fun EmptyQueue() {
    Card(
        colors = CardDefaults.cardColors(containerColor = AppCard),
        border = BorderStroke(1.dp, Borda),
        modifier = Modifier.fillMaxWidth(),
    ) {
        Text(
            "Nenhuma senha pendente",
            color = TextoSecundario,
            textAlign = TextAlign.Center,
            modifier = Modifier.fillMaxWidth().padding(28.dp),
        )
    }
}

@Composable
private fun IdentificacaoDialog(viewModel: OperadorViewModel) {
    Dialog(onDismissRequest = viewModel::fecharIdentificacao) {
        Card(
            shape = RoundedCornerShape(22.dp),
            colors = CardDefaults.cardColors(containerColor = AppCard),
            modifier = Modifier.fillMaxWidth(),
        ) {
            Column(modifier = Modifier.padding(22.dp)) {
                Text("Identifique-se para chamar", color = TextoPrincipal, fontWeight = FontWeight.Bold, fontSize = 21.sp)
                Text(
                    if (viewModel.modoIdentificacao == "pin") "Digite seu PIN. A próxima senha será chamada imediatamente."
                    else "Toque na sua foto. A próxima senha será chamada imediatamente.",
                    color = TextoSecundario,
                    fontSize = 13.sp,
                    modifier = Modifier.padding(top = 5.dp, bottom = 16.dp),
                )
                if (viewModel.modoIdentificacao == "pin") {
                    PinPad(enabled = !viewModel.isLoading, onConfirm = viewModel::identificarPorPin)
                } else {
                    LazyVerticalGrid(
                        columns = GridCells.Fixed(2),
                        modifier = Modifier.height(330.dp),
                        horizontalArrangement = Arrangement.spacedBy(10.dp),
                        verticalArrangement = Arrangement.spacedBy(10.dp),
                    ) {
                        items(viewModel.operadores, key = { it.id }) { operador ->
                            OperatorChoice(operador, !viewModel.isLoading) { viewModel.identificarPorFoto(operador) }
                        }
                    }
                }
                viewModel.errorMessage?.let {
                    Text(it, color = MaterialTheme.colorScheme.error, fontSize = 12.sp, modifier = Modifier.padding(top = 10.dp))
                }
                TextButton(onClick = viewModel::fecharIdentificacao, enabled = !viewModel.isLoading, modifier = Modifier.align(Alignment.End)) {
                    Text("Cancelar")
                }
            }
        }
    }
}

@Composable
private fun PinPad(enabled: Boolean, onConfirm: (String) -> Unit) {
    var pin by remember { mutableStateOf("") }
    Column(horizontalAlignment = Alignment.CenterHorizontally, modifier = Modifier.fillMaxWidth()) {
        Text(
            if (pin.isEmpty()) "○ ○ ○ ○" else "● ".repeat(pin.length).trim(),
            color = AppPrimary,
            fontSize = 27.sp,
            fontWeight = FontWeight.Bold,
            modifier = Modifier.padding(bottom = 10.dp),
        )
        listOf(listOf("1", "2", "3"), listOf("4", "5", "6"), listOf("7", "8", "9"), listOf("Limpar", "0", "⌫")).forEach { row ->
            Row(horizontalArrangement = Arrangement.spacedBy(8.dp), modifier = Modifier.padding(vertical = 4.dp)) {
                row.forEach { key ->
                    OutlinedButton(
                        onClick = {
                            val result = processPinKey(pin, key, OperadorViewModel.PIN_LENGTH)
                            pin = result.displayedPin
                            result.submittedPin?.let(onConfirm)
                        },
                        enabled = enabled,
                        modifier = Modifier.size(width = 78.dp, height = 48.dp),
                        contentPadding = PaddingValues(2.dp),
                    ) { Text(key, fontWeight = FontWeight.Bold, fontSize = if (key == "Limpar") 11.sp else 16.sp) }
                }
            }
        }
    }
}

@Composable
private fun OperatorChoice(operador: OperadorDto, enabled: Boolean, onClick: () -> Unit) {
    Card(
        shape = RoundedCornerShape(14.dp),
        colors = CardDefaults.cardColors(containerColor = Color(0xFFF8FAFC)),
        border = BorderStroke(1.dp, Borda),
        modifier = Modifier.fillMaxWidth().clickable(enabled = enabled, onClick = onClick),
    ) {
        Column(
            horizontalAlignment = Alignment.CenterHorizontally,
            modifier = Modifier.fillMaxWidth().padding(14.dp),
        ) {
            OperatorPhoto(operador.foto_perfil, operador.nome, 60)
            Text(operador.nome, color = TextoPrincipal, fontWeight = FontWeight.Bold, textAlign = TextAlign.Center, modifier = Modifier.padding(top = 8.dp))
        }
    }
}

@Composable
private fun OperatorPhoto(path: String?, name: String, size: Int) {
    Box(
        modifier = Modifier.size(size.dp).clip(CircleShape).background(AppSecondary),
        contentAlignment = Alignment.Center,
    ) {
        if (path != null) {
            AsyncImage(
                model = operatorPhotoUrl(NetworkModule.currentHttpBaseUrl(), path),
                contentDescription = "Foto de $name",
                modifier = Modifier.fillMaxSize().clip(CircleShape),
                contentScale = ContentScale.Crop,
            )
        } else {
            Icon(Icons.Filled.Person, contentDescription = null, tint = AppPrimary, modifier = Modifier.size((size / 2).dp))
        }
    }
}

@Composable
private fun PedidoDialog(viewModel: OperadorViewModel) {
    val senha = viewModel.senhaPedidoSelecionada ?: return
    val podeConfirmar = podeConfirmarPedido(
        senhaEmAtendimento = viewModel.atendimentoAtual?.senha,
        senhaSelecionada = senha.senha,
        pedidoConfirmado = senha.pedido_confirmado,
    )
    AlertDialog(
        onDismissRequest = viewModel::fecharPedido,
        containerColor = AppCard,
        titleContentColor = AppForeground,
        textContentColor = AppForeground,
        title = { Text("Pedido da senha ${senha.senha}", color = AppForeground, fontWeight = FontWeight.Bold) },
        text = {
            Column {
                Text(
                    pedidoBadgeLabel(senha.tem_pedido, senha.pedido_confirmado).orEmpty(),
                    color = if (senha.pedido_confirmado) AppPrimary else VerdePedido,
                    fontWeight = FontWeight.Bold,
                )
                Spacer(Modifier.height(10.dp))
                Text(senha.pedido ?: "Pedido não informado", color = TextoPrincipal)
            }
        },
        confirmButton = {
            if (podeConfirmar) {
                Button(onClick = viewModel::confirmarPedido, colors = ButtonDefaults.buttonColors(containerColor = VerdePedido)) {
                    Text("Confirmar pedido")
                }
            } else {
                TextButton(onClick = viewModel::fecharPedido, colors = ButtonDefaults.textButtonColors(contentColor = AppForeground)) {
                    Text("Fechar")
                }
            }
        },
        dismissButton = {
            if (podeConfirmar) {
                TextButton(onClick = viewModel::fecharPedido, colors = ButtonDefaults.textButtonColors(contentColor = AppForeground)) {
                    Text("Agora não")
                }
            }
        },
    )
}
