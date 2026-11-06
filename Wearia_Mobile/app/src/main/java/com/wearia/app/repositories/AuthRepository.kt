package com.wearia.app.repositories

import com.wearia.app.WeariaApplication
import com.wearia.app.data.remote.dto.*
import com.wearia.app.utils.Resource

/**
 * AuthRepository : centralise les appels d'authentification vers FastAPI.
 * Retourne un sealed class Resource<T> pour exposer les états success/error/loading aux ViewModels.
 */
class AuthRepository {

    private val api = WeariaApplication.instance.apiService
    private val session = WeariaApplication.instance.sessionManager

    /**
     * Inscription (UC06, BR05) : nom, email unique, mot de passe >= 8 caractères.
     */
    suspend fun register(nom: String, email: String, password: String): Resource<UserResponse> {
        return try {
            val response = api.register(RegisterRequest(nom, email, password))
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
     * Connexion (UC07) : retourne le JWT et sauvegarde la session.
     */
    suspend fun login(email: String, password: String): Resource<TokenResponse> {
        return try {
            val response = api.login(LoginRequest(email, password))
            if (response.isSuccessful && response.body() != null) {
                val tokenResponse = response.body()!!

                // Charger le profil pour sauvegarder le nom dans la session
                val profileResponse = api.getProfile("Bearer ${tokenResponse.accessToken}")
                if (profileResponse.isSuccessful && profileResponse.body() != null) {
                    val user = profileResponse.body()!!
                    session.saveSession(
                        token = tokenResponse.accessToken,
                        userId = user.id,
                        name = user.nom,
                        email = user.email,
                        ville = user.ville
                    )
                } else {
                    // Session minimale sans profil
                    session.saveSession(tokenResponse.accessToken, -1, "", email)
                }
                Resource.Success(tokenResponse)
            } else {
                Resource.Error("Email ou mot de passe incorrect.")
            }
        } catch (e: Exception) {
            Resource.Error("Impossible de contacter le serveur (${e.localizedMessage ?: e.javaClass.simpleName}).")
        }
    }

    fun logout() {
        session.clearSession()
    }

    fun isLoggedIn() = session.isLoggedIn()

    private fun parseApiError(errorJson: String): String {
        // Extraire le message de l'erreur FastAPI (champ "detail")
        return try {
            val start = errorJson.indexOf("\"detail\":\"") + 10
            val end = errorJson.indexOf("\"", start)
            if (start > 10 && end > start) errorJson.substring(start, end) else "Erreur inconnue."
        } catch (e: Exception) {
            "Erreur du serveur."
        }
    }
}

