package com.wearia.app.utils

import android.content.Context
import android.content.SharedPreferences

/**
 * SessionManager : stockage sécurisé du JWT et des infos de session utilisateur.
 * Utilise SharedPreferences pour persister la session entre les lancements.
 */
class SessionManager(context: Context) {

    private val prefs: SharedPreferences =
        context.getSharedPreferences("wearia_session", Context.MODE_PRIVATE)

    companion object {
        private const val KEY_TOKEN = "jwt_token"
        private const val KEY_USER_ID = "user_id"
        private const val KEY_USER_NAME = "user_name"
        private const val KEY_USER_EMAIL = "user_email"
        private const val KEY_USER_VILLE = "user_ville"
        private const val KEY_USER_GENRE = "user_genre"
        private const val KEY_USER_HEIGHT = "user_height"
        private const val KEY_USER_WEIGHT = "user_weight"
        private const val KEY_ONBOARDING_DONE = "onboarding_done"
        private const val KEY_PROFILE_COMPLETED = "profile_completed"
    }

    fun saveSession(
        token: String, 
        userId: Int, 
        name: String, 
        email: String, 
        ville: String = "Tunis",
        genre: String? = null
    ) {
        prefs.edit().apply {
            putString(KEY_TOKEN, token)
            putInt(KEY_USER_ID, userId)
            putString(KEY_USER_NAME, name)
            putString(KEY_USER_EMAIL, email)
            putString(KEY_USER_VILLE, ville)
            if (!genre.isNullOrEmpty()) {
                putString(KEY_USER_GENRE, genre.uppercase())
            }
            apply()
        }
    }

    fun getToken(): String? = prefs.getString(KEY_TOKEN, null)

    fun getAuthHeader(): String = "Bearer ${getToken() ?: ""}"

    fun getUserId(): Int = prefs.getInt(KEY_USER_ID, -1)

    fun getUserName(): String = prefs.getString(KEY_USER_NAME, "") ?: ""

    fun getUserEmail(): String = prefs.getString(KEY_USER_EMAIL, "") ?: ""

    fun getUserVille(): String = prefs.getString(KEY_USER_VILLE, "Tunis") ?: "Tunis"

    fun saveUserGenre(genre: String) {
        prefs.edit().putString(KEY_USER_GENRE, genre.uppercase()).apply()
    }

    fun getUserGenre(): String = prefs.getString(KEY_USER_GENRE, "HOMME") ?: "HOMME"

    fun saveUserMorphology(height: Int, weight: Float) {
        prefs.edit().putInt(KEY_USER_HEIGHT, height).putFloat(KEY_USER_WEIGHT, weight).apply()
    }

    fun getUserHeight(): Int = prefs.getInt(KEY_USER_HEIGHT, 175)

    fun getUserWeight(): Float = prefs.getFloat(KEY_USER_WEIGHT, 70f)

    fun isLoggedIn(): Boolean = !getToken().isNullOrEmpty()

    fun isOnboardingCompleted(): Boolean = prefs.getBoolean(KEY_ONBOARDING_DONE, false)

    fun setOnboardingCompleted(completed: Boolean = true) {
        prefs.edit().putBoolean(KEY_ONBOARDING_DONE, completed).apply()
    }

    fun isProfileCompleted(): Boolean = prefs.getBoolean(KEY_PROFILE_COMPLETED, false)

    fun setProfileCompleted(completed: Boolean = true) {
        prefs.edit().putBoolean(KEY_PROFILE_COMPLETED, completed).apply()
    }

    fun clearSession() {
        prefs.edit().clear().apply()
    }
}
