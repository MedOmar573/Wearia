package com.wearia.app.data.remote

import android.content.Context
import com.wearia.app.BuildConfig
import okhttp3.OkHttpClient
import okhttp3.logging.HttpLoggingInterceptor
import retrofit2.Retrofit
import retrofit2.converter.gson.GsonConverterFactory
import java.util.concurrent.TimeUnit

/**
 * Singleton Retrofit : crée et configure le client HTTP pour le backend FastAPI Wearia.
 *
 * URL de base :
 *  - Émulateur Android Studio : http://10.0.2.2:8000/ (PIÈGE DE DÉMO : ne pas mettre localhost !)
 *  - Téléphone physique (Wi-Fi) : http://192.168.X.X:8000/ (remplacer par l'IP de votre PC)
 *
 * L'URL est définie dans app/build.gradle.kts via BuildConfig.BASE_URL
 */
object RetrofitClient {

    private var retrofitInstance: Retrofit? = null

    fun create(context: Context): ApiService {
        val logging = HttpLoggingInterceptor().apply {
            level = if (BuildConfig.DEBUG) HttpLoggingInterceptor.Level.HEADERS else HttpLoggingInterceptor.Level.NONE
        }

        val okHttpClient = OkHttpClient.Builder()
            .addInterceptor(logging)
            .connectTimeout(30, TimeUnit.SECONDS)
            .readTimeout(60, TimeUnit.SECONDS)
            .writeTimeout(60, TimeUnit.SECONDS)
            .retryOnConnectionFailure(true)
            .build()

        if (retrofitInstance == null) {
            retrofitInstance = Retrofit.Builder()
                .baseUrl(BuildConfig.BASE_URL)
                .client(okHttpClient)
                .addConverterFactory(GsonConverterFactory.create())
                .build()
        }

        return retrofitInstance!!.create(ApiService::class.java)
    }
}

