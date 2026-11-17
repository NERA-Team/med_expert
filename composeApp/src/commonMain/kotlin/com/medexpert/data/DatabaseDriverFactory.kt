package com.medexpert.data

import app.cash.sqldelight.db.SqlDriver

/**
 * Platform-specific description of where the bundled SQLite file lives and how
 * SQLDelight should open it. Implementations live in androidMain, iosMain and
 * desktopMain.
 */
interface DatabaseDriverFactory {
    /** Absolute path of `med_expert.db` inside the application sandbox. */
    val databasePath: String

    fun createDriver(): SqlDriver
}
