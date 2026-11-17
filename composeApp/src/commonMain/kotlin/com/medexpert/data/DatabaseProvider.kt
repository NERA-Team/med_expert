package com.medexpert.data

import com.medexpert.db.MedExpertDatabase
import kotlinx.coroutines.sync.Mutex
import kotlinx.coroutines.sync.withLock
import kotlin.concurrent.Volatile

/**
 * Lazily installs and opens the SQLite database exactly once per process.
 */
class DatabaseProvider(
    private val driverFactory: DatabaseDriverFactory,
    private val initializer: FirstLaunchInitializer,
) {
    private val mutex = Mutex()

    @Volatile
    private var database: MedExpertDatabase? = null

    suspend fun get(): MedExpertDatabase {
        database?.let { return it }

        return mutex.withLock {
            database ?: run {
                initializer.ensureDatabaseInstalled()
                MedExpertDatabase(driverFactory.createDriver()).also { database = it }
            }
        }
    }
}
