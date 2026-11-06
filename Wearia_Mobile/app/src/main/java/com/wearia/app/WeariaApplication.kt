package com.wearia.app

import android.app.Application
import com.wearia.app.data.local.WeariaDatabase
import com.wearia.app.data.remote.RetrofitClient
import com.wearia.app.utils.SessionManager

/**
 * Application singleton : point d'entrée global.
 * Initialise les singletons (Retrofit, Room, SessionManager).
 * Évite Hilt/Koin pour rester simple (architectures demandée par le cahier).
 */
class WeariaApplication : Application() {

    // Instances accessibles globalement sans injection de dépendances
    val database: WeariaDatabase by lazy { WeariaDatabase.getInstance(this) }
    val apiService by lazy { RetrofitClient.create(this) }
    val sessionManager: SessionManager by lazy { SessionManager(this) }

    override fun onCreate() {
        super.onCreate()
        instance = this
    }

    companion object {
        lateinit var instance: WeariaApplication
            private set
    }
}

