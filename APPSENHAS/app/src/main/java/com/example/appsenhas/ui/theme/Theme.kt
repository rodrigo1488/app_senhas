package com.example.appsenhas.ui.theme

import android.app.Activity
import android.os.Build
import androidx.compose.foundation.isSystemInDarkTheme
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.darkColorScheme
import androidx.compose.material3.dynamicDarkColorScheme
import androidx.compose.material3.dynamicLightColorScheme
import androidx.compose.material3.lightColorScheme
import androidx.compose.runtime.Composable
import androidx.compose.ui.platform.LocalContext

// Esquema de cores próprio (não o roxo genérico do template do Android
// Studio) — usa o Indigo do painel admin/login.html como cor de marca, para
// que o app tenha uma identidade visual consistente com o resto do sistema
// (cada tela então sobrepõe suas próprias cores vindas dos templates web
// legados — ver AppSenhasColors.kt — por cima deste tema base).
private val DarkColorScheme = darkColorScheme(
    primary = IndigoAppClaro,
    secondary = VerdeSenhaNormal,
    tertiary = DouradoEstrela,
)

private val LightColorScheme = lightColorScheme(
    primary = IndigoApp,
    secondary = VerdeSenhaNormal,
    tertiary = DouradoEstrela,
)

@Composable
fun APPSENHASTheme(
    darkTheme: Boolean = isSystemInDarkTheme(),
    // Dynamic color (Material You) desligado por padrão: queremos a MESMA
    // identidade visual em qualquer aparelho, igual ao kiosk web, em vez de
    // cores que variam com o papel de parede do usuário.
    dynamicColor: Boolean = false,
    content: @Composable () -> Unit
) {
    val colorScheme = when {
        dynamicColor && Build.VERSION.SDK_INT >= Build.VERSION_CODES.S -> {
            val context = LocalContext.current
            if (darkTheme) dynamicDarkColorScheme(context) else dynamicLightColorScheme(context)
        }

        darkTheme -> DarkColorScheme
        else -> LightColorScheme
    }

    MaterialTheme(
        colorScheme = colorScheme,
        typography = Typography,
        content = content
    )
}