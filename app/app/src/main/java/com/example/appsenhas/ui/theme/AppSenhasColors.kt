package com.example.appsenhas.ui.theme

import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color

/**
 * Paleta e gradientes extraídos dos templates web legados (pasta
 * "templates" com os arquivos senhas.html, setor_opcoes.html,
 * senha_atual.html, senhas_pendentes.html e avaliacao.html), para que o
 * app Android tenha a MESMA identidade visual e fluxo do kiosk web em vez
 * do Material genérico padrão.
 */

// Tela de login/identidade do app
val IndigoApp = Color(0xFF4F46E5)
val IndigoAppClaro = Color(0xFF6366F1)

// Cliente (retirar senha) — ver templates/senhas.html
val FundoClienteEscuro = Color(0xFF121212)
val VerdeSenhaNormal = Color(0xFF4CAF50)
val VermelhoPreferencial = Color(0xFFFF5733)

// Seleção de papel (Cliente/Operador/Avaliação/TV) — ver templates/setor_opcoes.html
val FundoModoClaroInicio = Color(0xFFF8FAFC)
val FundoModoClaroFim = Color(0xFFE0E7EF)
val GradienteCliente = Brush.horizontalGradient(listOf(Color(0xFF2196F3), Color(0xFF21CBF3)))
val GradienteOperador = Brush.horizontalGradient(listOf(Color(0xFF43E97B), Color(0xFF38F9D7)))
val GradienteTv = Brush.horizontalGradient(listOf(Color(0xFFF7971E), Color(0xFFFFD200)))
val GradienteAvaliacao = Brush.horizontalGradient(listOf(Color(0xFFF85032), Color(0xFFE73827)))

// Operador (fila/atendimento) — ver templates/senhas_pendentes.html
val FundoOperadorClaro = Color(0xFFF4F4F4)
val GradienteHeroOperador = Brush.linearGradient(listOf(Color(0xFF667EEA), Color(0xFF764BA2)))
val GradienteVerPedido = Brush.horizontalGradient(listOf(Color(0xFFFF6B6B), Color(0xFFEE5A24)))
val GradienteConfirmar = Brush.horizontalGradient(listOf(Color(0xFF28A745), Color(0xFF20C997)))
val AmareloAlertaPreferenciais = Color(0xFFFFEB3B)
val VermelhoAlertaPreferenciais = Color(0xFFB71C1C)

// TV / painel de chamadas — ver templates/senha_atual.html
val FundoTvInicio = Color(0xFF0C0C0C)
val FundoTvMeio = Color(0xFF1A1A1A)
val GradienteTvFundo = Brush.linearGradient(listOf(FundoTvInicio, FundoTvMeio, FundoTvInicio))
val VerdeNeonTv = Color(0xFF00E676)
val CianoNeonTv = Color(0xFF00BCD4)

// Avaliação — ver templates/avaliacao.html
val AzulAvaliacaoCard = Color(0xFF007BFF)
val DouradoEstrela = Color(0xFFFFD700)
val CinzaEstrelaVazia = Color(0xFFCCCCCC)
