package com.example.appsenhas.ui.cliente

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.AccessibilityNew
import androidx.compose.material.icons.filled.CheckCircle
import androidx.compose.material.icons.filled.Groups
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.Icon
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import androidx.lifecycle.viewmodel.compose.viewModel
import com.example.appsenhas.ui.theme.FundoClienteEscuro
import com.example.appsenhas.ui.theme.VerdeSenhaNormal
import com.example.appsenhas.ui.theme.VermelhoPreferencial

/** Totem de retirada: emite, imprime no servidor e fica pronto para a próxima pessoa. */
@Composable
fun ClienteScreen(viewModel: ClienteViewModel = viewModel()) {
    Box(
        modifier = Modifier
            .fillMaxSize()
            .background(FundoClienteEscuro),
    ) {
        SelecaoTipoSenha(viewModel)
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
        viewModel.senhaEmitida?.let { senha ->
            Card(
                shape = RoundedCornerShape(20.dp),
                colors = CardDefaults.cardColors(containerColor = Color(0xFF1E1E1E)),
                modifier = Modifier.fillMaxWidth().padding(top = 20.dp),
            ) {
                Column(
                    modifier = Modifier.fillMaxWidth().padding(18.dp),
                    horizontalAlignment = Alignment.CenterHorizontally,
                ) {
                    Icon(Icons.Filled.CheckCircle, contentDescription = null, tint = VerdeSenhaNormal)
                    Text(
                        text = "Senha $senha emitida e enviada para impressão",
                        color = Color.White,
                        fontWeight = FontWeight.Bold,
                        textAlign = TextAlign.Center,
                        modifier = Modifier.padding(top = 8.dp),
                    )
                    Text(
                        text = "O próximo cliente já pode retirar uma senha.",
                        color = Color.White.copy(alpha = 0.75f),
                        textAlign = TextAlign.Center,
                    )
                }
            }
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
