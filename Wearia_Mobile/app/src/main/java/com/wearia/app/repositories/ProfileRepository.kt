package com.wearia.app.repositories

import com.wearia.app.WeariaApplication
import com.wearia.app.data.remote.dto.*
import com.wearia.app.utils.Resource

class ProfileRepository {
    private val api = WeariaApplication.instance.apiService
    private val session = WeariaApplication.instance.sessionManager
    private fun authHeader() = session.getAuthHeader()

    suspend fun getProfile(): Resource<UserResponse> {
        return try {
            val response = api.getProfile(authHeader())
            if (response.isSuccessful && response.body() != null) {
                val user = response.body()!!
                user.genre?.let { session.saveUserGenre(it) }
                if (user.hauteurCm != null && user.poidsKg != null) {
                    session.saveUserMorphology(user.hauteurCm, user.poidsKg)
                }
                Resource.Success(user)
            } else Resource.Error("Impossible de charger le profil.")
        } catch (e: Exception) {
            Resource.Error("Impossible de contacter le serveur.")
        }
    }

    suspend fun updateProfile(request: UserUpdateRequest): Resource<UserResponse> {
        return try {
            val response = api.updateProfile(authHeader(), request)
            if (response.isSuccessful && response.body() != null) {
                val user = response.body()!!
                session.saveSession(
                    session.getToken() ?: "",
                    user.id,
                    user.nom,
                    user.email,
                    user.ville,
                    user.genre
                )
                request.hauteurCm?.let { h ->
                    request.poidsKg?.let { p ->
                        session.saveUserMorphology(h, p)
                    }
                }
                Resource.Success(user)
            } else {
                val errorMsg = response.errorBody()?.string() ?: "Erreur HTTP ${response.code()}"
                android.util.Log.e("WeariaProfile", "Erreur updateProfile: $errorMsg")
                Resource.Error("Impossible de mettre à jour le profil.")
            }
        } catch (e: Exception) {
            android.util.Log.e("WeariaProfile", "Exception updateProfile", e)
            Resource.Error("Impossible de contacter le serveur.")
        }
    }

    suspend fun updateColorPreferences(
        likedColorIds: List<Int>,
        avoidedColorIds: List<Int> = emptyList()
    ): Resource<List<PreferenceCouleurResponse>> {
        return try {
            val response = api.updateColorPreferences(
                authHeader(),
                ColorPreferencesBatchRequest(likedColorIds = likedColorIds, avoidedColorIds = avoidedColorIds)
            )
            if (response.isSuccessful && response.body() != null) {
                Resource.Success(response.body()!!)
            } else Resource.Error("Impossible d'enregistrer les préférences de couleurs.")
        } catch (e: Exception) {
            Resource.Error("Impossible de contacter le serveur.")
        }
    }

    suspend fun updateStylePreferences(styleIds: List<Int>): Resource<List<PreferenceStyleResponse>> {
        return try {
            val response = api.updateStylePreferences(
                authHeader(),
                StylePreferencesBatchRequest(styleIds = styleIds)
            )
            if (response.isSuccessful && response.body() != null) {
                Resource.Success(response.body()!!)
            } else Resource.Error("Impossible d'enregistrer les styles.")
        } catch (e: Exception) {
            Resource.Error("Impossible de contacter le serveur.")
        }
    }

    suspend fun getCategories(): Resource<List<CategorieResponse>> {
        return try {
            val response = api.getCategories()
            if (response.isSuccessful) Resource.Success(response.body() ?: emptyList())
            else Resource.Error("Impossible de charger les catégories.")
        } catch (e: Exception) { Resource.Error("Hors-ligne.") }
    }

    suspend fun getTypes(genre: String? = null): Resource<List<TypeVetementResponse>> {
        return try {
            val response = api.getTypes(genre)
            if (response.isSuccessful) Resource.Success(response.body() ?: emptyList())
            else Resource.Error("Impossible de charger les types.")
        } catch (e: Exception) { Resource.Error("Hors-ligne.") }
    }

    suspend fun getColors(): Resource<List<CouleurResponse>> {
        return try {
            val response = api.getColors()
            if (response.isSuccessful) Resource.Success(response.body() ?: emptyList())
            else Resource.Error("Impossible de charger les couleurs.")
        } catch (e: Exception) { Resource.Error("Hors-ligne.") }
    }

    suspend fun getStyles(): Resource<List<StyleVestimentaireResponse>> {
        return try {
            val response = api.getStyles()
            if (response.isSuccessful) Resource.Success(response.body() ?: emptyList())
            else Resource.Error("Impossible de charger les styles.")
        } catch (e: Exception) { Resource.Error("Hors-ligne.") }
    }

    suspend fun getRoutines(): Resource<List<RoutineHebdomadaireResponse>> {
        return try {
            val response = api.getRoutines(authHeader())
            if (response.isSuccessful) Resource.Success(response.body() ?: emptyList())
            else Resource.Error("Impossible de charger les routines.")
        } catch (e: Exception) { Resource.Error("Hors-ligne.") }
    }

    suspend fun createRoutine(jour: String, occasion: String): Resource<RoutineHebdomadaireResponse> {
        return try {
            val response = api.createRoutine(authHeader(), RoutineHebdomadaireRequest(jour, occasion))
            if (response.isSuccessful && response.body() != null) Resource.Success(response.body()!!)
            else Resource.Error("Erreur lors de la création de la routine.")
        } catch (e: Exception) { Resource.Error("Impossible de contacter le serveur.") }
    }

    suspend fun deleteRoutine(id: Int): Resource<Unit> {
        return try {
            val response = api.deleteRoutine(authHeader(), id)
            if (response.isSuccessful) Resource.Success(Unit)
            else Resource.Error("Erreur lors de la suppression de la routine.")
        } catch (e: Exception) { Resource.Error("Impossible de contacter le serveur.") }
    }

    suspend fun getShoppingSuggestions(besoin: String? = null): Resource<List<ArticleCatalogueResponse>> {
        return try {
            val response = api.getShoppingSuggestions(authHeader(), besoin)
            if (response.isSuccessful) Resource.Success(response.body() ?: emptyList())
            else Resource.Error("Impossible de charger les suggestions.")
        } catch (e: Exception) { Resource.Error("Hors-ligne.") }
    }
}
