package com.example.compuflow.ui.operador

import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.compose.ui.window.Dialog
import com.example.compuflow.ui.theme.AppCard
import com.example.compuflow.ui.theme.AppForeground
import com.example.compuflow.ui.theme.AppMutedForeground
import com.example.compuflow.ui.theme.AppPrimary
import com.example.compuflow.ui.theme.AppPrimaryForeground

@Composable
fun ConfiguracaoOperadorDialog(
    modo: String,
    onSelecionar: (String) -> Unit,
    onDismiss: () -> Unit,
) {
    Dialog(onDismissRequest = onDismiss) {
        Card(
            shape = RoundedCornerShape(22.dp),
            colors = CardDefaults.cardColors(containerColor = AppCard),
            modifier = Modifier.fillMaxWidth(),
        ) {
            Column(modifier = Modifier.padding(22.dp)) {
                Text(
                    "Configuração do operador",
                    color = AppForeground,
                    fontWeight = FontWeight.Bold,
                    fontSize = 21.sp,
                )
                Text(
                    "Escolha como o atendente se identifica neste aparelho ao chamar a senha.",
                    color = AppMutedForeground,
                    fontSize = 13.sp,
                    modifier = Modifier.padding(top = 6.dp, bottom = 16.dp),
                )
                OpcaoIdentificacao(
                    titulo = "Usar senha",
                    detalhe = "O operador digita a senha de 4 números.",
                    selecionada = modo == "pin",
                    onClick = { onSelecionar("pin") },
                )
                OpcaoIdentificacao(
                    titulo = "Escolher o nome",
                    detalhe = "O operador escolhe o nome no momento de chamar a senha.",
                    selecionada = modo == "nome",
                    onClick = { onSelecionar("nome") },
                    modifier = Modifier.padding(top = 10.dp),
                )
                TextButton(onClick = onDismiss, modifier = Modifier.align(androidx.compose.ui.Alignment.End).padding(top = 8.dp)) {
                    Text("Fechar")
                }
            }
        }
    }
}

@Composable
private fun OpcaoIdentificacao(
    titulo: String,
    detalhe: String,
    selecionada: Boolean,
    onClick: () -> Unit,
    modifier: Modifier = Modifier,
) {
    if (selecionada) {
        Button(
            onClick = onClick,
            shape = RoundedCornerShape(14.dp),
            colors = ButtonDefaults.buttonColors(containerColor = AppPrimary, contentColor = AppPrimaryForeground),
            modifier = modifier.fillMaxWidth(),
        ) {
            Column(modifier = Modifier.padding(vertical = 6.dp)) {
                Text(titulo, fontWeight = FontWeight.Bold)
                Text(detalhe, fontSize = 12.sp)
            }
        }
    } else {
        OutlinedButton(
            onClick = onClick,
            shape = RoundedCornerShape(14.dp),
            modifier = modifier.fillMaxWidth(),
        ) {
            Column(modifier = Modifier.padding(vertical = 6.dp)) {
                Text(titulo, fontWeight = FontWeight.Bold, color = AppForeground)
                Text(detalhe, fontSize = 12.sp, color = AppMutedForeground)
            }
        }
    }
}
