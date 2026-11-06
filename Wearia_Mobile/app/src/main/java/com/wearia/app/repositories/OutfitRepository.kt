package com.wearia.app.repositories

import com.google.gson.Gson
import com.wearia.app.WeariaApplication
import com.wearia.app.data.local.entity.TenueFavoriteEntity
import com.wearia.app.data.remote.dto.*
import com.wearia.app.utils.Resource

/**
 * OutfitRepository : recommandations de tenues, favoris et feedback.
 */
class OutfitRepository {

    private val api = WeariaApplication.instance.apiService
    private val session = WeariaApplication.instance.sessionManager
    private val outfitDao = WeariaApplication.instance.database.outfitDao()
    private val gson = Gson()

    private fun authHeader() = session.getAuthHeader()

    /**
     * Génère une recommandation de tenue via le moteur BR01-BR09 du backend.
     * Si manual_temp et manual_precip sont fournis, la météo OpenWeatherMap est ignorée.
     */
    suspend fun getRecommendation(
        occasion: String? = null,
        manualTemp: Float? = null,
        manualPrecip: Boolean? = null
    ): Resource<RecommendationResponse> {
        return try {
            val request = RecommendationRequest(
                occasion = occasion,
                temperature = manualTemp,
                precipitations = manualPrecip
            )
            val response = api.getRecommendation(authHeader(), request)
            if (response.isSuccessful && response.body() != null) {
                Resource.Success(response.body()!!)
            } else {
                val errorBody = response.errorBody()?.string() ?: ""
                val msg = if ("disponible" in errorBody.lowercase() || "garde-robe" in errorBody.lowercase()) {
                    "Votre dressing ne contient aucun vêtement disponible. Ajoutez des vêtements d'abord."
                } else {
                    "Impossible de générer une recommandation pour le moment."
                }
                Resource.Error(msg)
            }
        } catch (e: Exception) {
            Resource.Error("Impossible de contacter le serveur.")
        }
    }

    suspend fun getOutfits(favorisOnly: Boolean = false): Resource<List<TenueResponse>> {
        return try {
            val response = api.getOutfits(authHeader(), favorisOnly)
            if (response.isSuccessful && response.body() != null) {
                Resource.Success(response.body()!!)
            } else {
                Resource.Error("Impossible de charger les tenues.")
            }
        } catch (e: Exception) {
            Resource.Error("Mode hors-ligne : favoris locaux affichés.")
        }
    }

    suspend fun toggleFavorite(outfitId: Int, isFavorite: Boolean): Resource<TenueResponse> {
        return try {
            val response = api.updateOutfit(authHeader(), outfitId, estFavorite = isFavorite)
            if (response.isSuccessful && response.body() != null) {
                val tenue = response.body()!!
                if (isFavorite) {
                    // Sauvegarder en local pour le mode hors-ligne
                    outfitDao.insertFavorite(tenue.toLocalEntity())
                } else {
                    outfitDao.deleteFavoriteById(outfitId)
                }
                Resource.Success(tenue)
            } else {
                Resource.Error("Erreur lors de la mise à jour du favori.")
            }
        } catch (e: Exception) {
            Resource.Error("Impossible de contacter le serveur.")
        }
    }

    suspend fun submitFeedback(outfitId: Int, appreciation: String, motifRejet: String?): Resource<FeedbackResponse> {
        return try {
            val response = api.submitFeedback(
                authHeader(), outfitId,
                FeedbackRequest(appreciation = appreciation, motifRejet = motifRejet)
            )
            if (response.isSuccessful && response.body() != null) {
                Resource.Success(response.body()!!)
            } else {
                Resource.Error("Erreur lors de l'enregistrement de l'avis.")
            }
        } catch (e: Exception) {
            Resource.Error("Impossible de contacter le serveur.")
        }
    }

    fun getLocalFavorites() = outfitDao.getAllFavorites()

    private fun TenueResponse.toLocalEntity() = TenueFavoriteEntity(
        id = id,
        occasion = occasion,
        temperature = temperatureCelsius,
        weather = descriptionMeteo,
        score = scoreCompatibilite,
        explanation = explication ?: "",
        itemsJson = gson.toJson(vetements.map { it.nom })
    )
}

