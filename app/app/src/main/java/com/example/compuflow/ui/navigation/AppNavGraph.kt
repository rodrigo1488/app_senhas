package com.example.compuflow.ui.navigation

import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.navigation.NavType
import androidx.navigation.compose.NavHost
import androidx.navigation.compose.composable
import androidx.navigation.compose.rememberNavController
import androidx.navigation.navArgument
import com.example.compuflow.AppGraph
import com.example.compuflow.data.remote.NetworkModule
import com.example.compuflow.data.remote.dto.Papel
import com.example.compuflow.ui.avaliacao.AvaliacaoScreen
import com.example.compuflow.ui.cliente.ClienteScreen
import com.example.compuflow.ui.kiosk.SoftKioskHost
import com.example.compuflow.ui.login.LoginScreen
import com.example.compuflow.ui.modo.SelecionarModoScreen
import com.example.compuflow.ui.operador.IdentificarOperadorScreen
import com.example.compuflow.ui.operador.OperadorScreen
import com.example.compuflow.ui.streaming.StreamingTvScreen
import com.example.compuflow.ui.tv.TvScreen
import kotlinx.coroutines.launch

/**
 * Grafo de navegação do app: `login -> modo -> (identificar_operador ->) tela do papel`.
 * A tela inicial é decidida em tempo de execução (`BootRoute`) a partir do que
 * estiver persistido em `SessionRepository`, para reabrir o app direto na
 * tela certa enquanto a sessão continuar válida.
 */
@Composable
fun AppNavGraph() {
    val navController = rememberNavController()
    val scope = rememberCoroutineScope()
    var setorNome by remember { mutableStateOf("") }

    fun voltarAoMenuSelecao() {
        scope.launch {
            val sessionRepository = AppGraph.sessionRepository
            try {
                val livre = NetworkModule.apiService().liberarOperador()
                sessionRepository.saveGenericSession(livre.session_token)
            } catch (_: Exception) {
                sessionRepository.clearPapel()
            }
            setorNome = sessionRepository.getSetorNome() ?: setorNome
            navController.navigate(Routes.MODO) {
                popUpTo(navController.graph.id) { inclusive = true }
                launchSingleTop = true
            }
        }
    }

    fun trocarSetor() {
        scope.launch {
            AppGraph.sessionRepository.logout()
            setorNome = ""
            navController.navigate(Routes.LOGIN) {
                popUpTo(navController.graph.id) { inclusive = true }
                launchSingleTop = true
            }
        }
    }

    NavHost(navController = navController, startDestination = Routes.BOOT) {
        composable(Routes.BOOT) {
            BootRoute(
                onIrParaLogin = {
                    navController.navigate(Routes.LOGIN) { popUpTo(Routes.BOOT) { inclusive = true } }
                },
                onIrParaModo = { nome ->
                    setorNome = nome
                    navController.navigate(Routes.MODO) { popUpTo(Routes.BOOT) { inclusive = true } }
                },
                onIrParaPapel = { papel ->
                    val destino = rotaDoPapel(papel)
                    navController.navigate(destino) { popUpTo(Routes.BOOT) { inclusive = true } }
                },
            )
        }

        composable(Routes.LOGIN) {
            LoginScreen(onLoginSuccess = { nome ->
                setorNome = nome
                navController.navigate(Routes.MODO) { popUpTo(Routes.LOGIN) { inclusive = true } }
            })
        }

        composable(Routes.MODO) {
            SelecionarModoScreen(
                setorNome = setorNome,
                onSelecionarCliente = {
                    navController.navigate(Routes.CLIENTE) { popUpTo(Routes.MODO) { inclusive = true } }
                },
                onSelecionarOperador = {
                    navController.navigate(Routes.OPERADOR) { popUpTo(Routes.MODO) { inclusive = true } }
                },
                onSelecionarAvaliacao = {
                    navController.navigate(Routes.AVALIACAO) { popUpTo(Routes.MODO) { inclusive = true } }
                },
                onSelecionarTv = {
                    navController.navigate(Routes.TV) { popUpTo(Routes.MODO) { inclusive = true } }
                },
                onSelecionarTvPropagandas = {
                    navController.navigate(Routes.TV_STREAMING) { popUpTo(Routes.MODO) { inclusive = true } }
                },
                onTrocarSetor = ::trocarSetor,
            )
        }

        composable(
            route = Routes.IDENTIFICAR_OPERADOR,
            arguments = listOf(navArgument("finalidade") { type = NavType.StringType }),
        ) { backStackEntry ->
            val finalidade = backStackEntry.arguments?.getString("finalidade") ?: Routes.FINALIDADE_OPERADOR
            val papel = if (finalidade == Routes.FINALIDADE_AVALIACAO) Papel.AVALIACAO else Papel.OPERADOR
            SoftKioskHost(onExitToModeSelection = ::voltarAoMenuSelecao) {
                IdentificarOperadorScreen(
                    papel = papel,
                    fotoBaseUrl = NetworkModule.currentHttpBaseUrl().trimEnd('/'),
                    onSelecionado = {
                        val destino = if (papel == Papel.AVALIACAO) Routes.AVALIACAO else Routes.OPERADOR
                        navController.navigate(destino) { popUpTo(Routes.MODO) { inclusive = true } }
                    },
                )
            }
        }

        composable(Routes.CLIENTE) {
            SoftKioskHost(onExitToModeSelection = ::voltarAoMenuSelecao) {
                ClienteScreen()
            }
        }
        composable(Routes.OPERADOR) {
            SoftKioskHost(onExitToModeSelection = ::voltarAoMenuSelecao) {
                OperadorScreen()
            }
        }
        composable(Routes.AVALIACAO) {
            SoftKioskHost(onExitToModeSelection = ::voltarAoMenuSelecao) {
                AvaliacaoScreen()
            }
        }
        composable(Routes.TV) {
            SoftKioskHost(onExitToModeSelection = ::voltarAoMenuSelecao) {
                TvScreen()
            }
        }
        composable(Routes.TV_STREAMING) {
            SoftKioskHost(onExitToModeSelection = ::voltarAoMenuSelecao) {
                StreamingTvScreen()
            }
        }
    }
}

private fun rotaDoPapel(papel: Papel): String = when (papel) {
    Papel.CLIENTE -> Routes.CLIENTE
    Papel.OPERADOR -> Routes.OPERADOR
    Papel.AVALIACAO -> Routes.AVALIACAO
    Papel.TV -> Routes.TV
    Papel.STREAMING -> Routes.TV_STREAMING
}

@Composable
private fun BootRoute(
    onIrParaLogin: () -> Unit,
    onIrParaModo: (setorNome: String) -> Unit,
    onIrParaPapel: (Papel) -> Unit,
) {
    LaunchedEffect(Unit) {
        val sessionRepository = AppGraph.sessionRepository
        val serverUrl = sessionRepository.getServerUrl()
        val token = sessionRepository.getSessionToken()
        if (serverUrl != null) {
            com.example.compuflow.data.session.AuthState.serverUrl = serverUrl
        }
        if (token == null) {
            onIrParaLogin()
            return@LaunchedEffect
        }
        com.example.compuflow.data.session.AuthState.sessionToken = token
        val papelSalvo = sessionRepository.getPapel()
        val papel = Papel.entries.firstOrNull { it.valor == papelSalvo }
        if (papel == null) {
            onIrParaModo(sessionRepository.getSetorNome() ?: "")
        } else {
            onIrParaPapel(papel)
        }
    }

    Box(modifier = Modifier.fillMaxSize()) {
        CircularProgressIndicator(modifier = Modifier.align(Alignment.Center))
    }
}
