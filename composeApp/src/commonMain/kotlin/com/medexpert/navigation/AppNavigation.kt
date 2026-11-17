package com.medexpert.navigation

import androidx.compose.runtime.Composable
import androidx.compose.runtime.remember
import cafe.adriel.voyager.core.screen.Screen
import cafe.adriel.voyager.core.screen.ScreenKey
import cafe.adriel.voyager.navigator.CurrentScreen
import cafe.adriel.voyager.navigator.LocalNavigator
import cafe.adriel.voyager.navigator.Navigator
import cafe.adriel.voyager.navigator.currentOrThrow
import com.medexpert.presentation.DrugDetailsViewModel
import com.medexpert.presentation.SearchViewModel
import com.medexpert.presentation.screens.DrugDetailsScreen
import com.medexpert.presentation.screens.SearchScreen
import org.koin.mp.KoinPlatform

@Composable
fun AppNavigation() {
    Navigator(SearchRoute) {
        CurrentScreen()
    }
}

private object SearchRoute : Screen {
    @Composable
    override fun Content() {
        val navigator = LocalNavigator.currentOrThrow
        val viewModel = remember { KoinPlatform.getKoin().get<SearchViewModel>() }

        SearchScreen(
            viewModel = viewModel,
            onDrugClick = { drugId -> navigator.push(DrugDetailsRoute(drugId)) },
        )
    }
}

private data class DrugDetailsRoute(
    val drugId: Long,
) : Screen {
    override val key: ScreenKey
        get() = "drug-details-$drugId"

    @Composable
    override fun Content() {
        val navigator = LocalNavigator.currentOrThrow
        val viewModel = remember { KoinPlatform.getKoin().get<DrugDetailsViewModel>() }

        DrugDetailsScreen(
            viewModel = viewModel,
            drugId = drugId,
            onBack = { navigator.pop() },
        )
    }
}
