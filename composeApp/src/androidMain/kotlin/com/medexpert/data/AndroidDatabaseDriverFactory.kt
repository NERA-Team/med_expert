package com.medexpert.data

import android.content.Context
import app.cash.sqldelight.driver.android.AndroidSqliteDriver
import app.cash.sqldelight.db.SqlDriver
import com.medexpert.db.MedExpertDatabase

class AndroidDatabaseDriverFactory(
    private val context: Context,
) : DatabaseDriverFactory {

    override val databasePath: String
        get() = context.getDatabasePath(DATABASE_NAME).absolutePath

    override fun createDriver(): SqlDriver =
        AndroidSqliteDriver(
            schema = MedExpertDatabase.Schema,
            context = context,
            name = DATABASE_NAME,
        )

    private companion object {
        const val DATABASE_NAME = "med_expert.db"
    }
}
