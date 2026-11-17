package com.medexpert.android

import android.app.Application
import com.medexpert.data.AndroidDatabaseDriverFactory
import com.medexpert.di.initKoin

class MedExpertApplication : Application() {
    override fun onCreate() {
        super.onCreate()
        initKoin(AndroidDatabaseDriverFactory(applicationContext))
    }
}
