package com.wearia.app.repositories

import com.wearia.app.WeariaApplication
import com.wearia.app.BuildConfig
import com.wearia.app.data.remote.dto.ShopperPromptRequest
import com.wearia.app.data.remote.dto.ShopperResultResponse
import com.wearia.app.utils.Resource

class ShopperRepository {

    private val api = WeariaApplication.instance.apiService
    private val session = WeariaApplication.instance.sessionManager

    private fun authHeader(): String? = try {
        val token = session.getToken()
        if (token.isNullOrEmpty()) null else "Bearer $token"
    } catch (e: Exception) {
        null
    }

    suspend fun generateOutfits(request: ShopperPromptRequest): Resource<ShopperResultResponse> {
        return try {
            val header = authHeader()
            val response = api.generateShopperOutfits(header, request)

            if (response.isSuccessful && response.body() != null) {
                Resource.Success(response.body()!!)
            } else {
                val errorMsg = response.errorBody()?.string() ?: "Impossible d'interpréter la demande d'achat."
                Resource.Error("Erreur AI Shopper : $errorMsg")
            }
        } catch (e: Exception) {
            val cause = e.localizedMessage ?: e.javaClass.simpleName
            Resource.Error(
                "Le serveur AI Shopper ne répond pas ($cause). Vérifiez qu’il est démarré et que l’adresse " +
                    "réseau Android correspond à votre appareil (${BuildConfig.BASE_URL})."
            )
        }
    }
}
