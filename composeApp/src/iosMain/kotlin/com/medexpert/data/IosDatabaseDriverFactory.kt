package com.medexpert.data

import app.cash.sqldelight.db.SqlDriver
import app.cash.sqldelight.driver.native.NativeSqliteDriver
import com.medexpert.db.MedExpertDatabase
import platform.Foundation.NSApplicationSupportDirectory
import platform.Foundation.NSSearchPathForDirectoriesInDomains
import platform.Foundation.NSUserDomainMask

/**
 * SQLiter (the SQLite engine behind SQLDelight's native driver) stores its
 * databases in `<Application Support>/databases`. The initializer writes the
 * bundled file to exactly the same path before the driver is opened.
 */
class IosDatabaseDriverFactory : DatabaseDriverFactory {

    override val databasePath: String
        get() {
            val applicationSupport = NSSearchPathForDirectoriesInDomains(
                directory = NSApplicationSupportDirectory,
                domainMask = NSUserDomainMask,
                expandTilde = true,
            ).first() as String

            return "$applicationSupport/databases/$DATABASE_NAME"
        }

    override fun createDriver(): SqlDriver =
        NativeSqliteDriver(
            schema = MedExpertDatabase.Schema,
            name = DATABASE_NAME,
        )

    private companion object {
        const val DATABASE_NAME = "med_expert.db"
    }
}
