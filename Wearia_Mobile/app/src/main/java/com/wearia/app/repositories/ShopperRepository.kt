package com.wearia.app.repositories

import com.wearia.app.WeariaApplication
import com.wearia.app.data.remote.dto.ShopperPromptRequest
import com.wearia.app.data.remote.dto.ShopperResultResponse
import com.wearia.app.utils.Resource

class ShopperRepository {

    private val api = WeariaApplication.instance.apiService
    private val session = WeariaApplication.instance.sessionManager

    private fun authHeader(): String? = try {
        session.getAuthHeader()
    } catch (e: Exception) {
        null
    }

    suspend fun generateOutfits(prompt: String, budget: Float? = null, genre: String? = null): Resource<ShopperResultResponse> {
        return try {
            val userGenre = genre ?: session.getUserGenre()
            val request = ShopperPromptRequest(prompt = prompt, budget = budget, genre = userGenre)
            val header = authHeader()
            val response = api.generateShopperOutfits(header, request)

            if (response.isSuccessful && response.body() != null) {
                Resource.Success(response.body()!!)
            } else {
                val errorMsg = response.errorBody()?.string() ?: "Impossible d'interpréter la demande d'achat."
                Resource.Error("Erreur AI Shopper : $errorMsg")
            }
        } catch (e: Exception) {
            Resource.Error("Impossible de contacter le serveur AI Shopper (${e.localizedMessage ?: "Vérifiez votre connexion"}).")
        }
    }
}
