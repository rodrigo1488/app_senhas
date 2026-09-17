package com.example.compuflow.ui.cliente

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.AccessibilityNew
import androidx.compose.material.icons.filled.Groups
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.Icon
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.lifecycle.viewmodel.compose.viewModel
import com.example.compuflow.ui.theme.FundoClienteEscuro
import com.example.compuflow.ui.theme.VerdeSenhaNormal
import com.example.compuflow.ui.theme.VermelhoPreferencial
import com.example.compuflow.ui.tv.TvMediaSlide
import com.example.compuflow.ui.tv.mediaUrl

/** Totem de retirada: emite, imprime no servidor e fica pronto para a próxima pessoa. */
@Composable
fun ClienteScreen(viewModel: ClienteViewModel = viewModel()) {
    Box(
        modifier = Modifier
            .fillMaxSize()
            .background(FundoClienteEscuro),
    ) {
        val item = viewModel.currentItem
        if (item != null) {
            TvMediaSlide(
                item = item,
                mediaUrl = mediaUrl(item.arquivo),
                loop = viewModel.imagens.size <= 1,
                onEnded = { viewModel.onMediaEnded() },
                emptyLabel = "",
                modifier = Modifier.fillMaxSize(),
                emptyBackground = FundoClienteEscuro,
            )
            Box(
                modifier = Modifier
                    .fillMaxSize()
                    .background(Color.Black.copy(alpha = 0.45f)),
            )
        }
        SelecaoTipoSenha(viewModel)
    }
}

@Composable
private fun SelecaoTipoSenha(viewModel: ClienteViewModel) {
    Column(
        modifier = Modifier.fillMaxSize().padding(horizontal = 32.dp, vertical = 28.dp),
        horizontalAlignment = Alignment.CenterHorizontally,
        verticalArrangement = Arrangement.Center,
    ) {
        Text(
            text = "Bem-vindo",
            style = MaterialTheme.typography.headlineLarge,
            fontWeight = FontWeight.Bold,
            color = Color.White,
        )
        Text(
            text = "Retire uma senha:",
            style = MaterialTheme.typography.titleLarge,
            color = Color.White.copy(alpha = 0.85f),
            modifier = Modifier.padding(top = 8.dp, bottom = 40.dp),
        )

        PillButton(
            label = "Senha Normal",
            icon = Icons.Filled.Groups,
            color = VerdeSenhaNormal,
            enabled = !viewModel.isLoading,
            onClick = { viewModel.criarSenha("normal") },
        )
        Spacer(modifier = Modifier.height(20.dp))
        PillButton(
            label = "Senha Preferencial",
            icon = Icons.Filled.AccessibilityNew,
            color = VermelhoPreferencial,
            enabled = !viewModel.isLoading,
            onClick = { viewModel.criarSenha("preferencial") },
        )

        if (viewModel.isLoading) {
            CircularProgressIndicator(color = Color.White, modifier = Modifier.padding(top = 32.dp))
        }
        viewModel.errorMessage?.let {
            Text(it, color = MaterialTheme.colorScheme.error, modifier = Modifier.padding(top = 20.dp))
        }
    }
}

@Composable
private fun PillButton(
    label: String,
    icon: ImageVector,
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
            .height(112.dp),
    ) {
        Icon(
            icon,
            contentDescription = null,
            modifier = Modifier
                .padding(end = 14.dp)
                .size(36.dp),
        )
        Text(
            label,
            fontSize = 26.sp,
            fontWeight = FontWeight.Bold,
        )
    }
}
