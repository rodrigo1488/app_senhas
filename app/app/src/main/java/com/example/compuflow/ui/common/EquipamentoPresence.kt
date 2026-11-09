package com.example.compuflow.ui.common

import android.os.Build
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import com.example.compuflow.AppGraph
import com.example.compuflow.data.remote.NetworkModule
import com.example.compuflow.data.remote.dto.PresencaEquipamentoRequest
import com.example.compuflow.data.remote.ipv4Local
import kotlinx.coroutines.delay

/** Envia o IP deste aparelho ao administrador enquanto houver um papel ativo. */
@Composable
fun EquipamentoPresence() {
    val papel by AppGraph.sessionRepository.papelFlow.collectAsStateWithLifecycle(initialValue = null)
    LaunchedEffect(papel) {
        if (!papel.isNullOrBlank()) enviarPresenca()
    }
    LaunchedEffect(Unit) {
        while (true) {
            delay(15_000)
            enviarPresenca()
        }
    }
}

private suspend fun enviarPresenca() {
    val session = AppGraph.sessionRepository
    val papel = session.getPapel() ?: return
    if (session.getSessionToken().isNullOrBlank()) return
    try {
        NetworkModule.apiService().registrarPresenca(
            PresencaEquipamentoRequest(
                device_id = session.getOrCreateDeviceId(),
                papel = papel,
                ip = ipv4Local(),
                nome = Build.MODEL,
            ),
        )
    } catch (_: Exception) {
        /* presença é complementar; a tela segue sem o IP */
    }
}
