package com.medexpert.data

import com.medexpert.resources.Res
import kotlinx.coroutines.sync.Mutex
import kotlinx.coroutines.sync.withLock
import okio.FileSystem
import okio.Path
import okio.Path.Companion.toPath
import org.jetbrains.compose.resources.ExperimentalResourceApi

/**
 * Installs or refreshes the prepared database from Compose resources in the
 * platform sandbox before the SQLite driver is opened.
 *
 * SQLDelight never creates or seeds the schema on desktop/iOS: the application
 * always opens the bundled file. This keeps the reference data identical on
 * every platform.
 */
class FirstLaunchInitializer(
    private val driverFactory: DatabaseDriverFactory,
    private val fileSystem: FileSystem = FileSystem.SYSTEM,
) {
    private val mutex = Mutex()

    suspend fun ensureDatabaseInstalled() {
        val target = driverFactory.databasePath.toPath()
        mutex.withLock {
            @OptIn(ExperimentalResourceApi::class)
            val databaseBytes = Res.readBytes(DATABASE_RESOURCE_PATH)

            if (isCurrent(target, databaseBytes)) return

            val parent = target.parent
            if (parent != null) {
                fileSystem.createDirectories(parent)
            }

            val temporary = parent?.resolve("${target.name}.installing")
                ?: "${target}.installing".toPath()

            fileSystem.write(temporary) { write(databaseBytes) }
            try {
                // Replace outdated or corrupt copies only after the new bundled
                // database has been fully written to the staging file.
                fileSystem.atomicMove(temporary, target)
            } finally {
                if (fileSystem.exists(temporary)) {
                    fileSystem.delete(temporary)
                }
            }
        }
    }

    private fun isCurrent(path: Path, bundledBytes: ByteArray): Boolean {
        if (!fileSystem.exists(path)) return false
        if ((fileSystem.metadata(path).size ?: 0L) != bundledBytes.size.toLong()) return false
        return fileSystem.read(path) { readByteArray().contentEquals(bundledBytes) }
    }

    private companion object {
        const val DATABASE_RESOURCE_PATH = "files/med_expert.db"
    }
}
