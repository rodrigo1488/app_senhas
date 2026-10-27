package com.example.compuflow

import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.activity.enableEdgeToEdge
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import com.example.compuflow.ui.navigation.AppNavGraph
import com.example.compuflow.ui.theme.CompuFlowTheme
import com.example.compuflow.update.AppUpdateController

class MainActivity : ComponentActivity() {
    private val atualizacao by lazy { AppUpdateController(this) }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        AppGraph.init(applicationContext)
        enableEdgeToEdge()
        atualizacao
        setContent {
            CompuFlowTheme {
                AppNavGraph()
                if (atualizacao.mostrarDialogo) {
                    AlertDialog(
                        onDismissRequest = { atualizacao.agoraNao() },
                        title = { Text("Nova versão") },
                        text = {
                            Text("Há uma versão nova deste aplicativo. Deseja instalar agora?")
                        },
                        confirmButton = {
                            TextButton(onClick = { atualizacao.instalar() }) {
                                Text("Instalar")
                            }
                        },
                        dismissButton = {
                            TextButton(onClick = { atualizacao.agoraNao() }) {
                                Text("Agora não")
                            }
                        },
                    )
                }
            }
        }
        atualizacao.iniciar()
    }

    override fun onResume() {
        super.onResume()
        atualizacao.aoRetomar()
    }
}
