package com.medexpert

import androidx.compose.runtime.Composable
import com.medexpert.navigation.AppNavigation
import com.medexpert.presentation.theme.MedExpertTheme

@Composable
fun App() {
    MedExpertTheme {
        AppNavigation()
    }
}
