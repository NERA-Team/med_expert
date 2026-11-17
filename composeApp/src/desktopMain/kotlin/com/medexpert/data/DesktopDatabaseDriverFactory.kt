package com.medexpert.data

import app.cash.sqldelight.db.SqlDriver
import app.cash.sqldelight.driver.jdbc.sqlite.JdbcSqliteDriver
import java.io.File

/**
 * Desktop data directory:
 * - macOS: ~/Library/Application Support/MedExpert
 * - Windows: %APPDATA%\MedExpert
 * - Linux: $XDG_DATA_HOME/MedExpert (or ~/.local/share/MedExpert)
 */
class DesktopDatabaseDriverFactory : DatabaseDriverFactory {

    override val databasePath: String = resolveDatabasePath()

    override fun createDriver(): SqlDriver = JdbcSqliteDriver("jdbc:sqlite:$databasePath")

    private fun resolveDatabasePath(): String {
        val home = System.getProperty("user.home")
        val osName = System.getProperty("os.name").lowercase()

        val directory = when {
            osName.contains("mac") || osName.contains("darwin") ->
                "$home/Library/Application Support/MedExpert"

            osName.contains("win") -> {
                val appData = System.getenv("APPDATA") ?: "$home\\AppData\\Roaming"
                "$appData\\MedExpert"
            }

            else -> {
                val dataHome = System.getenv("XDG_DATA_HOME") ?: "$home/.local/share"
                "$dataHome/MedExpert"
            }
        }

        return File(directory, DATABASE_NAME).absolutePath
    }

    private companion object {
        const val DATABASE_NAME = "med_expert.db"
    }
}
