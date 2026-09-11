package com.example.appsenhas

import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.activity.enableEdgeToEdge
import com.example.appsenhas.ui.navigation.AppNavGraph
import com.example.appsenhas.ui.theme.APPSENHASTheme

class MainActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        AppGraph.init(applicationContext)
        enableEdgeToEdge()
        setContent {
            APPSENHASTheme {
                AppNavGraph()
            }
        }
    }
}
