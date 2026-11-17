package com.medexpert.di

import com.medexpert.data.DatabaseDriverFactory
import com.medexpert.data.DatabaseProvider
import com.medexpert.data.DrugRepositoryImpl
import com.medexpert.data.FirstLaunchInitializer
import com.medexpert.domain.DrugRepository
import com.medexpert.presentation.DrugDetailsViewModel
import com.medexpert.presentation.SearchViewModel
import kotlinx.serialization.json.Json
import org.koin.core.context.startKoin
import org.koin.core.module.Module
import org.koin.dsl.module
import org.koin.mp.KoinPlatform

fun appModule(driverFactory: DatabaseDriverFactory): Module = module {
    single<DatabaseDriverFactory> { driverFactory }
    single {
        Json {
            ignoreUnknownKeys = true
            isLenient = true
        }
    }
    single { FirstLaunchInitializer(get()) }
    single { DatabaseProvider(get(), get()) }
    single<DrugRepository> { DrugRepositoryImpl(get(), get()) }

    // The app is a single-window reference book, so its presentation state
    // holders live for the whole Koin container.
    single { SearchViewModel(get()) }
    single { DrugDetailsViewModel(get()) }
}

/**
 * Idempotent so Android activity recreation and repeated iOS view-controller
 * creation cannot start Koin twice.
 */
fun initKoin(driverFactory: DatabaseDriverFactory) {
    if (KoinPlatform.getKoinOrNull() != null) return

    startKoin {
        modules(appModule(driverFactory))
    }
}
