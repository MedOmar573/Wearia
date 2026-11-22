package com.wearia.app.repositories

import com.wearia.app.WeariaApplication
import com.wearia.app.data.remote.dto.*
import com.wearia.app.utils.Resource

/**
 * AuthRepository : centralise les appels d'authentification et validation OTP vers FastAPI.
 * Retourne un sealed class Resource<T> pour exposer les états success/error/loading aux ViewModels.
 */
class AuthRepository {

    private val api = WeariaApplication.instance.apiService
    private val session = WeariaApplication.instance.sessionManager

    /**
     * Étape 1 Inscription (UC06, BR05) :
     * Envoie nom, email et mot de passe, déclenche l'envoi de l'OTP par email.
     */
    suspend fun register(
        nom: String, 
        email: String, 
        password: String,
        hauteurCm: Int? = null,
        poidsKg: Float? = null,
        genre: String? = null
    ): Resource<AuthStepResponse> {
        return try {
            val response = api.register(RegisterRequest(nom, email, password, hauteurCm, poidsKg, genre))
            if (response.isSuccessful && response.body() != null) {
                Resource.Success(response.body()!!)
            } else {
                val errorMsg = response.errorBody()?.string() ?: "Erreur d'inscription"
                Resource.Error(parseApiError(errorMsg))
            }
        } catch (e: Exception) {
            Resource.Error("Impossible de contacter le serveur (${e.localizedMessage ?: e.javaClass.simpleName}).")
        }
    }

    /**
     * Étape 1 Connexion (UC07) :
     * Vérifie les identifiants et déclenche l'envoi de l'OTP de sécurité par email.
     */
    suspend fun login(email: String, password: String): Resource<AuthStepResponse> {
        return try {
            val response = api.login(LoginRequest(email, password))
            if (response.isSuccessful && response.body() != null) {
                Resource.Success(response.body()!!)
            } else {
                val errorMsg = response.errorBody()?.string() ?: "Email ou mot de passe incorrect."
                Resource.Error(parseApiError(errorMsg))
            }
        } catch (e: Exception) {
            Resource.Error("Impossible de contacter le serveur (${e.localizedMessage ?: e.javaClass.simpleName}).")
        }
    }

    /**
     * Étape 2 Validation OTP (Inscription et Connexion) :
     * Valide le code à 6 chiffres reçu par email et enregistre le token JWT en session.
     */
    suspend fun verifyOtp(email: String, code: String, purpose: String): Resource<TokenResponse> {
        return try {
            val previousUserId = session.getUserId()
            val response = api.verifyOtp(VerifyOtpRequest(email, code, purpose))
            if (response.isSuccessful && response.body() != null) {
                val tokenResponse = response.body()!!
                var resolvedUserId = tokenResponse.userId ?: -1

                // Charger le profil pour initialiser le nom, la ville, le genre, la morphologie et les couleurs
                try {
                    val profileResponse = api.getProfile("Bearer ${tokenResponse.accessToken}")
                    if (profileResponse.isSuccessful && profileResponse.body() != null) {
                        val user = profileResponse.body()!!
                        resolvedUserId = user.id
                        if (previousUserId != -1 && previousUserId != resolvedUserId) {
                            clearLocalUserCaches()
                        }
                        val hasMorphology = (user.hauteurCm != null && user.hauteurCm > 0 && user.poidsKg != null && user.poidsKg > 0)
                        session.saveSession(
                            token = tokenResponse.accessToken,
                            userId = user.id,
                            name = user.nom,
                            email = user.email,
                            ville = user.ville,
                            genre = user.genre,
                            hauteurCm = user.hauteurCm,
                            poidsKg = user.poidsKg,
                            profileCompleted = hasMorphology
                        )

                        // Sauvegarder les couleurs préférées dans la session
                        val likedHexes = user.preferencesCouleur
                            .filter { it.typePreference.equals("AIME", ignoreCase = true) }
                            .map { it.couleur.nom }
                            .toSet()
                        val avoidedNames = user.preferencesCouleur
                            .filter { it.typePreference.equals("EVITE", ignoreCase = true) }
                            .map { it.couleur.nom }
                            .toSet()
                        session.savePreferredColors(likedHexes)
                        session.saveAvoidedColors(avoidedNames)
                    } else {
                        if (previousUserId != -1 && previousUserId != resolvedUserId) {
                            clearLocalUserCaches()
                        }
                        session.saveSession(
                            token = tokenResponse.accessToken,
                            userId = resolvedUserId,
                            name = tokenResponse.nom ?: "",
                            email = tokenResponse.email ?: email,
                            genre = tokenResponse.genre,
                            hauteurCm = tokenResponse.hauteurCm,
                            poidsKg = tokenResponse.poidsKg,
                            profileCompleted = tokenResponse.isProfileCompleted
                        )
                    }
                } catch (e: Exception) {
                    if (previousUserId != -1 && previousUserId != resolvedUserId) {
                        clearLocalUserCaches()
                    }
                    session.saveSession(
                        token = tokenResponse.accessToken,
                        userId = resolvedUserId,
                        name = tokenResponse.nom ?: "",
                        email = tokenResponse.email ?: email,
                        genre = tokenResponse.genre,
                        hauteurCm = tokenResponse.hauteurCm,
                        poidsKg = tokenResponse.poidsKg,
                        profileCompleted = tokenResponse.isProfileCompleted
                    )
                }

                Resource.Success(tokenResponse)
            } else {
                val errorMsg = response.errorBody()?.string() ?: "Code de vérification invalide."
                Resource.Error(parseApiError(errorMsg))
            }
        } catch (e: Exception) {
            Resource.Error("Impossible de contacter le serveur (${e.localizedMessage ?: e.javaClass.simpleName}).")
        }
    }

    /**
     * Renvoi d'un nouveau code OTP par email.
     */
    suspend fun resendOtp(email: String, purpose: String): Resource<String> {
        return try {
            val response = api.resendOtp(ResendOtpRequest(email, purpose))
            if (response.isSuccessful) {
                val msg = response.body()?.get("message")?.toString() ?: "Nouveau code envoyé avec succès."
                Resource.Success(msg)
            } else {
                val errorMsg = response.errorBody()?.string() ?: "Erreur lors du renvoi du code."
                Resource.Error(parseApiError(errorMsg))
            }
        } catch (e: Exception) {
            Resource.Error("Impossible de contacter le serveur (${e.localizedMessage ?: e.javaClass.simpleName}).")
        }
    }

    suspend fun clearLocalUserCaches() {
        try {
            val db = WeariaApplication.instance.database
            db.outfitDao().clearAllFavorites()
            db.clothingDao().clearAll()
        } catch (_: Exception) {
            // Nettoyage best-effort
        }
    }

    suspend fun logoutAndClearCaches() {
        clearLocalUserCaches()
        session.clearSession()
    }

    fun logout() {
        session.clearSession()
    }

    fun isLoggedIn() = session.isLoggedIn()

    private fun parseApiError(errorJson: String): String {
        return try {
            val start = errorJson.indexOf("\"detail\":\"") + 10
            if (start >= 10) {
                val end = errorJson.indexOf("\"", start)
                if (end > start) errorJson.substring(start, end) else "Une erreur est survenue."
            } else {
                "Une erreur est survenue."
            }
        } catch (e: Exception) {
            "Une erreur est survenue."
        }
    }
}
