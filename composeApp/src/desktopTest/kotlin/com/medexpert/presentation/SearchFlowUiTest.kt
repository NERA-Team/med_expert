package com.medexpert.presentation

import androidx.compose.ui.test.ExperimentalTestApi
import androidx.compose.ui.test.assertExists
import androidx.compose.ui.test.hasScrollAction
import androidx.compose.ui.test.hasSetTextAction
import androidx.compose.ui.test.hasText
import androidx.compose.ui.test.onAllNodesWithText
import androidx.compose.ui.test.onNode
import androidx.compose.ui.test.onNodeWithTag
import androidx.compose.ui.test.onNodeWithText
import androidx.compose.ui.test.performClick
import androidx.compose.ui.test.performScrollToNode
import androidx.compose.ui.test.performTextInput
import androidx.compose.ui.test.runComposeUiTest
import app.cash.sqldelight.db.SqlDriver
import app.cash.sqldelight.driver.jdbc.sqlite.JdbcSqliteDriver
import com.medexpert.App
import com.medexpert.data.DatabaseDriverFactory
import com.medexpert.di.initKoin
import org.koin.mp.KoinPlatform
import java.nio.file.Files
import kotlin.test.AfterTest
import kotlin.test.Test

/**
 * Drives the real Compose UI: installs the bundled database, types a query,
 * checks trade-name results and opens a card with several age regimens.
 */
@OptIn(ExperimentalTestApi::class)
class SearchFlowUiTest {

    private val directory: java.nio.file.Path =
        Files.createTempDirectory("medexpert-ui-test")

    @AfterTest
    fun tearDown() {
        KoinPlatform.getKoinOrNull()?.close()
        directory.toFile().deleteRecursively()
    }

    @Test
    fun searchesByTradeNameAndOpensMultiRegimenDetails() = runComposeUiTest {
        initKoin(TestDriverFactory(directory.resolve("med_expert.db").toString()))
        setContent { App() }

        waitUntil(15_000) {
            onAllNodesWithText("Все препараты").fetchSemanticsNodes().isNotEmpty()
        }

        onNode(hasSetTextAction()).performTextInput("Амоксициллин")

        val viewModel = KoinPlatform.getKoin().get<SearchViewModel>()
        waitUntil(15_000) {
            val state = viewModel.uiState.value
            !state.isLoading &&
                state.results.size == 6 &&
                state.results.all { it.tradeName == "Амоксициллин" }
        }

        onNodeWithText("Результаты поиска").assertExists()

        // Seed row 2: Amoxicillin 500 mg tablets with five age-specific regimens.
        onNodeWithTag("drug-2").performClick()

        waitUntil(15_000) {
            onAllNodesWithText("Режимы дозирования").fetchSemanticsNodes().isNotEmpty()
        }

        onNodeWithText("с 12 лет").assertExists()
        onAllNodesWithText("5–7 дней").fetchSemanticsNodes().isNotEmpty()
        onAllNodesWithText("Курс лечения: 5–7 дней").fetchSemanticsNodes().isNotEmpty()

        onNode(hasScrollAction()).performScrollToNode(hasText("3–6 лет"))
        onNodeWithText("3–6 лет").assertExists()
    }

    private class TestDriverFactory(
        override val databasePath: String,
    ) : DatabaseDriverFactory {
        override fun createDriver(): SqlDriver = JdbcSqliteDriver("jdbc:sqlite:$databasePath")
    }
}
