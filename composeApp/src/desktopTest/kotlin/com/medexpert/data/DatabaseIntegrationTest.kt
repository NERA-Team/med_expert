package com.medexpert.data

import app.cash.sqldelight.db.SqlDriver
import app.cash.sqldelight.driver.jdbc.sqlite.JdbcSqliteDriver
import com.medexpert.domain.DrugRepository
import com.medexpert.domain.SearchMode
import kotlinx.coroutines.test.runTest
import kotlinx.serialization.json.Json
import java.nio.file.Files
import kotlin.test.AfterTest
import kotlin.test.Test
import kotlin.test.assertEquals
import kotlin.test.assertNotNull
import kotlin.test.assertTrue

/**
 * End-to-end checks for the pre-built database: first-launch installation,
 * SQL search in both modes, and decoding of the age-specific regimens.
 */
class DatabaseIntegrationTest {

    private val temporaryDirectories = mutableListOf<java.nio.file.Path>()

    @AfterTest
    fun cleanUp() {
        temporaryDirectories.forEach { directory ->
            directory.toFile().deleteRecursively()
        }
    }

    @Test
    fun installsBundledDatabaseAndSearchesByTradeName() = runTest {
        val repository = createRepository()

        val results = repository.search("амоксициллин", SearchMode.TradeName)

        assertEquals(7, results.size, "All parsed Amoxicillin dosage forms should be found")
        assertTrue(results.all { it.tradeName == "Амоксициллин" })
        assertTrue(results.any { it.strengthLabel == "500 мг" })
        assertTrue(results.first().activeSubstances.contains("Амоксициллин"))
    }

    @Test
    fun searchesByMnnAndFindsRelatedTradeNames() = runTest {
        val repository = createRepository()

        val results = repository.search("Амоксициллин", SearchMode.Mnn)
        val tradeNames = results.map { it.tradeName }.toSet()

        assertEquals(36, results.size)
        assertTrue("Амоксициллин" in tradeNames)
        assertTrue("Оспамокс" in tradeNames)
        assertTrue("Флемоксин Солютаб" in tradeNames)
    }

    @Test
    fun opensDetailsWithSeveralAgeSpecificRegimens() = runTest {
        val repository = createRepository()
        val summary = repository.search("Амоксициллин", SearchMode.TradeName)
            .first { it.dosageForm == "Таблетки" && it.strengthLabel == "500 мг" }

        val drug = repository.getDrug(summary.id)

        assertNotNull(drug)
        assertEquals("Амоксициллин", drug.tradeName)
        assertEquals("Пенициллины", drug.groupName)
        assertTrue(drug.regimens.isNotEmpty())
        assertTrue(drug.regimens.all { it.regimenText.isNotBlank() })
        assertTrue(drug.regimens.any { !it.courseNote.isNullOrBlank() })
        assertTrue(drug.activeSubstances.any { it.nameRu == "Амоксициллин" })
    }

    @Test
    fun doesNotReinstallDatabaseOnSecondLaunch() = runTest {
        val directory = createTemporaryDirectory()
        val path = directory.resolve("med_expert.db")
        val factory = TestDriverFactory(path.toString())
        val initializer = FirstLaunchInitializer(factory)

        initializer.ensureDatabaseInstalled()
        val installedSize = Files.size(path)
        val markerTime = 1_000_000_000_000L
        Files.setLastModifiedTime(path, java.nio.file.attribute.FileTime.fromMillis(markerTime))

        initializer.ensureDatabaseInstalled()

        assertEquals(installedSize, Files.size(path))
        assertEquals(
            markerTime,
            Files.getLastModifiedTime(path).toMillis(),
            "The existing database must be left untouched",
        )
    }

    @Test
    fun replacesOutdatedDatabaseWithBundledCopy() = runTest {
        val directory = createTemporaryDirectory()
        val path = directory.resolve("med_expert.db")
        val previousVersion = "outdated bundled database".toByteArray()
        Files.write(path, previousVersion)
        val factory = TestDriverFactory(path.toString())
        val initializer = FirstLaunchInitializer(factory)

        initializer.ensureDatabaseInstalled()

        assertTrue(!Files.readAllBytes(path).contentEquals(previousVersion))
        assertTrue(Files.size(path) > previousVersion.size)
    }

    private suspend fun createRepository(): DrugRepository {
        val directory = createTemporaryDirectory()
        val factory = TestDriverFactory(directory.resolve("med_expert.db").toString())
        val initializer = FirstLaunchInitializer(factory)
        val provider = DatabaseProvider(factory, initializer)
        val json = Json {
            ignoreUnknownKeys = true
            isLenient = true
        }

        // Force installation before the first repository call so the test
        // covers the same ordering as Application startup.
        provider.get()

        return DrugRepositoryImpl(provider, json)
    }

    private fun createTemporaryDirectory(): java.nio.file.Path =
        Files.createTempDirectory("medexpert-test").also { temporaryDirectories.add(it) }

    private class TestDriverFactory(
        override val databasePath: String,
    ) : DatabaseDriverFactory {
        override fun createDriver(): SqlDriver =
            JdbcSqliteDriver("jdbc:sqlite:$databasePath")
    }
}
