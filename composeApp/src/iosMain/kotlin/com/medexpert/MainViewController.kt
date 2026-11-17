package com.medexpert

import androidx.compose.ui.window.ComposeUIViewController
import com.medexpert.data.IosDatabaseDriverFactory
import com.medexpert.di.initKoin
import platform.UIKit.UIViewController

@Suppress("FunctionName", "unused")
fun MainViewController(): UIViewController {
    initKoin(IosDatabaseDriverFactory())

    return ComposeUIViewController {
        App()
    }
}
