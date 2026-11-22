package com.wearia.app.repositories

import androidx.room.withTransaction
import com.wearia.app.WeariaApplication
import com.wearia.app.data.local.entity.VetementCacheEntity
import com.wearia.app.data.remote.dto.*
import com.wearia.app.utils.Resource
import okhttp3.MediaType.Companion.toMediaTypeOrNull
import okhttp3.MultipartBody
import okhttp3.RequestBody.Companion.asRequestBody
import java.io.File

/**
 * ClothingRepository : gestion du dressing (CRUD vêtements) et classification IA.
 */
class ClothingRepository {

    private val api = WeariaApplication.instance.apiService
    private val session = WeariaApplication.instance.sessionManager
    private val clothingDao = WeariaApplication.instance.database.clothingDao()

    private fun authHeader() = session.getAuthHeader()
    private fun currentUserId() = session.getUserId()

    suspend fun getClothes(
        categorieId: Int? = null,
        couleurId: Int? = null,
        statut: String? = null,
        search: String? = null
    ): Resource<List<VetementResponse>> {
        return try {
            val response = api.getClothes(authHeader(), categorieId, couleurId, statut, search)
            if (response.isSuccessful && response.body() != null) {
                val list = response.body()!!
                val uid = currentUserId()
                if (uid > 0) {
                    val isUnfiltered = categorieId == null && couleurId == null && statut == null && search.isNullOrBlank()
                    if (isUnfiltered) {
                        val entities = list.map { it.toCacheEntity(uid) }
                        WeariaApplication.instance.database.withTransaction {
                            clothingDao.clearClothesForUser(uid)
                            if (entities.isNotEmpty()) {
                                clothingDao.insertAll(entities)
                            }
                        }
                    } else {
                        clothingDao.insertAll(list.map { it.toCacheEntity(uid) })
                    }
                }
                Resource.Success(list)
            } else {
                Resource.Error("Erreur lors du chargement des vêtements.")
            }
        } catch (e: Exception) {
            Resource.Error("Mode hors-ligne : données du cache affichées.")
        }
    }

    suspend fun addClothing(request: VetementCreateRequest): Resource<VetementResponse> {
        return try {
            val response = api.addClothing(authHeader(), request)
            if (response.isSuccessful && response.body() != null) {
                Resource.Success(response.body()!!)
            } else {
                Resource.Error("Erreur lors de l'ajout du vêtement.")
            }
        } catch (e: Exception) {
            Resource.Error("Impossible de contacter le serveur.")
        }
    }

    suspend fun updateClothing(id: Int, request: VetementUpdateRequest): Resource<VetementResponse> {
        return try {
            val response = api.updateClothing(authHeader(), id, request)
            if (response.isSuccessful && response.body() != null) {
                Resource.Success(response.body()!!)
            } else {
                Resource.Error("Erreur lors de la modification.")
            }
        } catch (e: Exception) {
            Resource.Error("Impossible de contacter le serveur.")
        }
    }

    suspend fun deleteClothing(id: Int): Resource<Unit> {
        return try {
            val response = api.deleteClothing(authHeader(), id)
            if (response.isSuccessful) {
                val uid = currentUserId()
                if (uid > 0) {
                    clothingDao.getByIdForUser(id, uid)?.let {
                        clothingDao.clearClothesForUser(uid)
                    }
                }
                Resource.Success(Unit)
            } else {
                Resource.Error("Erreur lors de la suppression.")
            }
        } catch (e: Exception) {
            Resource.Error("Impossible de contacter le serveur.")
        }
    }

    /**
     * Envoie une photo au backend pour classification KNN + détection de couleur OpenCV.
     * Utilise multipart/form-data comme spécifié dans le cahier (API /ai/classify).
     */
    suspend fun classifyClothing(imageFile: File): Resource<ClassifyResponse> {
        return try {
            val requestFile = imageFile.asRequestBody("image/jpeg".toMediaTypeOrNull())
            val body = MultipartBody.Part.createFormData("file", imageFile.name, requestFile)
            val response = api.classifyClothing(authHeader(), body)
            if (response.isSuccessful && response.body() != null) {
                Resource.Success(response.body()!!)
            } else {
                val err = response.errorBody()?.string() ?: "Code HTTP ${response.code()}"
                android.util.Log.e("WeariaAI", "Erreur HTTP classification: $err")
                Resource.Error("Erreur serveur lors de la classification : $err")
            }
        } catch (e: Exception) {
            android.util.Log.e("WeariaAI", "Exception classifyClothing", e)
            val errorMsg = when (e) {
                is java.net.ConnectException -> "Connexion au serveur refusée. Vérifiez que le serveur est démarré et le port inversé (adb reverse)."
                is java.net.SocketTimeoutException -> "Délai d'attente dépassé lors de l'analyse."
                is java.net.UnknownHostException -> "Serveur introuvable. Vérifiez votre connexion."
                else -> e.localizedMessage ?: "Erreur réseau inconnue"
            }
            Resource.Error("Impossible d'analyser l'image : $errorMsg")
        }
    }

    suspend fun deleteTempUpload(imageUrl: String) {
        if (imageUrl.isBlank()) return
        try {
            api.deleteTempUpload(authHeader(), imageUrl)
        } catch (_: Exception) {
            // Nettoyage best-effort
        }
    }

    fun getLocalClothes() = clothingDao.getClothesForUser(currentUserId())

    private fun VetementResponse.toCacheEntity(userId: Int = currentUserId()) = VetementCacheEntity(
        id = id,
        userId = userId,
        nom = nom,
        photoUrl = photoUrl,
        categorie = typeVetement.categorieId.toString(),
        couleur = couleur.nom,
        couleurHex = couleur.codeHex,
        statut = statut
    )
}

