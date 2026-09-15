package com.example.compuflow

import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.activity.enableEdgeToEdge
import com.example.compuflow.ui.navigation.AppNavGraph
import com.example.compuflow.ui.theme.CompuFlowTheme

class MainActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        AppGraph.init(applicationContext)
        enableEdgeToEdge()
        setContent {
            CompuFlowTheme {
                AppNavGraph()
            }
        }
    }
}
