package com.medexpert

import androidx.compose.ui.unit.dp
import androidx.compose.ui.window.Window
import androidx.compose.ui.window.application
import androidx.compose.ui.window.rememberWindowState
import com.medexpert.data.DesktopDatabaseDriverFactory
import com.medexpert.di.initKoin
import java.awt.Dimension

fun main() {
    System.setProperty("apple.awt.application.name", "MedExpert")

    initKoin(DesktopDatabaseDriverFactory())

    application {
        Window(
            onCloseRequest = ::exitApplication,
            title = "MedExpert — справочник лекарственных препаратов",
            state = rememberWindowState(
                width = 1120.dp,
                height = 840.dp,
            ),
        ) {
            window.minimumSize = Dimension(420, 620)
            App()
        }
    }
}
