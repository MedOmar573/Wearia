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
        private const val KEY_AVATAR_URI = "user_avatar_uri"
        private const val KEY_PREFERRED_COLORS = "preferred_colors"
        private const val KEY_AVOIDED_COLORS = "avoided_colors"
        private const val KEY_USER_SHOULDERS = "user_shoulders"
        private const val KEY_USER_CHEST = "user_chest"
        private const val KEY_USER_WAIST = "user_waist"
        private const val KEY_USER_HIPS = "user_hips"
    }

    fun saveSession(
        token: String, 
        userId: Int, 
        name: String, 
        email: String, 
        ville: String = "Tunis",
        genre: String? = null,
        hauteurCm: Int? = null,
        poidsKg: Float? = null,
        profileCompleted: Boolean = false
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
            if (hauteurCm != null && hauteurCm > 0) {
                putInt(KEY_USER_HEIGHT, hauteurCm)
            }
            if (poidsKg != null && poidsKg > 0) {
                putFloat(KEY_USER_WEIGHT, poidsKg)
            }
            if (profileCompleted || (hauteurCm != null && hauteurCm > 0 && poidsKg != null && poidsKg > 0)) {
                putBoolean(KEY_PROFILE_COMPLETED, true)
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

    fun saveOptionalMeasurements(shoulders: Float?, chest: Float?, waist: Float?, hips: Float?) {
        prefs.edit().apply {
            if (shoulders != null && shoulders > 0) putFloat(KEY_USER_SHOULDERS, shoulders) else remove(KEY_USER_SHOULDERS)
            if (chest != null && chest > 0) putFloat(KEY_USER_CHEST, chest) else remove(KEY_USER_CHEST)
            if (waist != null && waist > 0) putFloat(KEY_USER_WAIST, waist) else remove(KEY_USER_WAIST)
            if (hips != null && hips > 0) putFloat(KEY_USER_HIPS, hips) else remove(KEY_USER_HIPS)
            apply()
        }
    }

    fun getUserShoulders(): Float? = if (prefs.contains(KEY_USER_SHOULDERS)) prefs.getFloat(KEY_USER_SHOULDERS, 0f) else null
    fun getUserChest(): Float? = if (prefs.contains(KEY_USER_CHEST)) prefs.getFloat(KEY_USER_CHEST, 0f) else null
    fun getUserWaist(): Float? = if (prefs.contains(KEY_USER_WAIST)) prefs.getFloat(KEY_USER_WAIST, 0f) else null
    fun getUserHips(): Float? = if (prefs.contains(KEY_USER_HIPS)) prefs.getFloat(KEY_USER_HIPS, 0f) else null

    fun getUserHeight(): Int = prefs.getInt(KEY_USER_HEIGHT, 175)

    fun getUserWeight(): Float = prefs.getFloat(KEY_USER_WEIGHT, 70f)

    fun saveAvatarUri(uri: String) {
        prefs.edit().putString(KEY_AVATAR_URI, uri).apply()
    }

    fun getAvatarUri(): String? = prefs.getString(KEY_AVATAR_URI, null)

    fun isLoggedIn(): Boolean = !getToken().isNullOrEmpty()

    fun isOnboardingCompleted(): Boolean = prefs.getBoolean(KEY_ONBOARDING_DONE, false)

    fun setOnboardingCompleted(completed: Boolean = true) {
        prefs.edit().putBoolean(KEY_ONBOARDING_DONE, completed).apply()
    }

    fun isProfileCompleted(): Boolean {
        if (prefs.getBoolean(KEY_PROFILE_COMPLETED, false)) return true
        val h = prefs.getInt(KEY_USER_HEIGHT, -1)
        val w = prefs.getFloat(KEY_USER_WEIGHT, -1f)
        return (h > 0 && w > 0)
    }

    fun setProfileCompleted(completed: Boolean = true) {
        prefs.edit().putBoolean(KEY_PROFILE_COMPLETED, completed).apply()
    }

    fun savePreferredColors(colors: Set<String>) {
        prefs.edit().putStringSet(KEY_PREFERRED_COLORS, colors).apply()
    }

    fun getPreferredColors(): Set<String> {
        return prefs.getStringSet(KEY_PREFERRED_COLORS, emptySet()) ?: emptySet()
    }

    fun saveAvoidedColors(colors: Set<String>) {
        prefs.edit().putStringSet(KEY_AVOIDED_COLORS, colors).apply()
    }

    fun getAvoidedColors(): Set<String> {
        return prefs.getStringSet(KEY_AVOIDED_COLORS, emptySet()) ?: emptySet()
    }

    fun clearSession() {
        prefs.edit().clear().apply()
    }
}
