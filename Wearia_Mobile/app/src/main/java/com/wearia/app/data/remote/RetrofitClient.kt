package com.wearia.app.data.remote

import android.content.Context
import com.wearia.app.BuildConfig
import okhttp3.Interceptor
import okhttp3.OkHttpClient
import okhttp3.Response
import okhttp3.logging.HttpLoggingInterceptor
import retrofit2.Retrofit
import retrofit2.converter.gson.GsonConverterFactory
import java.io.IOException
import java.util.concurrent.TimeUnit

/**
 * Singleton Retrofit : crée et configure le client HTTP pour le backend FastAPI Wearia.
 *
 * URL de base :
 *  - Émulateur Android Studio : http://10.0.2.2:8000/
 *  - Téléphone physique (Wi-Fi) : http://10.95.88.235:8000/
 *  - Câble USB (ADB reverse)    : http://127.0.0.1:8000/
 */
object RetrofitClient {

    private var retrofitInstance: Retrofit? = null

    fun create(context: Context): ApiService {
        val logging = HttpLoggingInterceptor().apply {
            level = if (BuildConfig.DEBUG) HttpLoggingInterceptor.Level.HEADERS else HttpLoggingInterceptor.Level.NONE
        }

        // Intercepteur de basculement automatique Wi-Fi <-> USB ADB (127.0.0.1)
        val networkFallbackInterceptor = Interceptor { chain ->
            val request = chain.request()
            try {
                chain.proceed(request)
            } catch (e: IOException) {
                val originalUrl = request.url
                val fallbackHost = if (originalUrl.host == "127.0.0.1" || originalUrl.host == "localhost") {
                    "10.95.88.235"
                } else {
                    "127.0.0.1"
                }
                if (originalUrl.host != fallbackHost) {
                    val newUrl = originalUrl.newBuilder().host(fallbackHost).build()
                    val newRequest = request.newBuilder().url(newUrl).build()
                    try {
                        chain.proceed(newRequest)
                    } catch (e2: IOException) {
                        throw e
                    }
                } else {
                    throw e
                }
            }
        }

        val okHttpClient = OkHttpClient.Builder()
            .addInterceptor(networkFallbackInterceptor)
            .addInterceptor(logging)
            .connectTimeout(15, TimeUnit.SECONDS)
            // La première recherche peut synchroniser des fiches produit publiques.
            .readTimeout(180, TimeUnit.SECONDS)
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
