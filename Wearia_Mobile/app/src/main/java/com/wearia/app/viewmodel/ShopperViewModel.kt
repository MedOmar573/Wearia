package com.wearia.app.viewmodel

import androidx.lifecycle.LiveData
import androidx.lifecycle.MutableLiveData
import androidx.lifecycle.ViewModel
import androidx.lifecycle.ViewModelProvider
import androidx.lifecycle.viewModelScope
import com.wearia.app.WeariaApplication
import com.wearia.app.data.remote.dto.ShopperPromptRequest
import com.wearia.app.data.remote.dto.ShopperResultResponse
import com.wearia.app.repositories.ShopperRepository
import com.wearia.app.utils.Resource
import com.wearia.app.utils.ShopperSessionCache
import kotlinx.coroutines.launch

class ShopperViewModel(
    private val repository: ShopperRepository,
    private val cache: ShopperSessionCache = ShopperSessionCache(WeariaApplication.instance)
) : ViewModel() {

    private val _shopperResult = MutableLiveData<Resource<ShopperResultResponse>?>(null)
    val shopperResult: LiveData<Resource<ShopperResultResponse>?> = _shopperResult

    private val previousProductIds = mutableSetOf<Int>()
    private val previousUrls = mutableSetOf<String>()
    private var lastCriteriaSignature: String? = null
    private var activeOwnerUserId: Int = -1

    var lastRequest: ShopperPromptRequest? = null
        private set

    private fun currentUserId(): Int = try {
        WeariaApplication.instance.sessionManager.getUserId()
    } catch (_: Exception) {
        -1
    }

    /**
     * Synchronise strictement l'état AI Shopper avec le compte utilisateur connecté :
     * - Si l'utilisateur a changé (ou n'est plus connecté), réinitialise totalement l'état mémoire.
     * - Restaure uniquement les dernières propositions appartenant à ce `userId`.
     */
    fun syncWithUser(userId: Int = currentUserId()) {
        if (userId <= 0) {
            clearState()
            return
        }
        if (activeOwnerUserId == userId && _shopperResult.value != null) {
            return
        }

        // Changement de compte ou première ouverture : purger tout état précédent
        previousProductIds.clear()
        previousUrls.clear()
        lastCriteriaSignature = null
        lastRequest = null
        activeOwnerUserId = userId

        val snapshot = cache.getLastProposals(userId)
        if (snapshot != null && snapshot.ownerUserId == userId) {
            lastRequest = snapshot.request
            snapshot.request?.let { lastCriteriaSignature = buildCriteriaSignature(it) }
            snapshot.result.articles.forEach { article ->
                previousProductIds.add(article.id)
                article.lienAchat?.trim()?.takeIf { it.isNotEmpty() }?.let { previousUrls.add(it) }
            }
            _shopperResult.value = Resource.Success(snapshot.result)
        } else {
            _shopperResult.value = null
        }
    }

    fun clearState() {
        activeOwnerUserId = -1
        previousProductIds.clear()
        previousUrls.clear()
        lastCriteriaSignature = null
        lastRequest = null
        _shopperResult.value = null
    }

    private fun buildCriteriaSignature(request: ShopperPromptRequest): String {
        return listOf(
            request.typeVetement?.trim()?.lowercase().orEmpty(),
            request.styleId?.toString().orEmpty(),
            request.style?.trim()?.lowercase().orEmpty(),
            request.budget?.toString().orEmpty(),
            request.genre?.trim()?.lowercase().orEmpty(),
            request.prompt.trim().lowercase(),
            request.colors.map { it.trim().lowercase() }.sorted().joinToString(","),
            request.avoidedColors.map { it.trim().lowercase() }.sorted().joinToString(","),
            request.requestedTypes.map { it.trim().lowercase() }.sorted().joinToString(","),
            request.excludedTypes.map { it.trim().lowercase() }.sorted().joinToString(",")
        ).joinToString("|")
    }

    fun searchArticles(request: ShopperPromptRequest, loadMoreUnseen: Boolean = false) {
        val hasType = !request.typeVetement.isNullOrBlank() || request.requestedTypes.any { it.isNotBlank() }
        if (!hasType && request.prompt.isBlank()) return

        val requestOwnerId = currentUserId()
        if (requestOwnerId <= 0) {
            clearState()
            return
        }
        if (activeOwnerUserId != requestOwnerId) {
            previousProductIds.clear()
            previousUrls.clear()
            lastCriteriaSignature = null
            activeOwnerUserId = requestOwnerId
        }

        val signature = buildCriteriaSignature(request)
        val sameCriteria = signature == lastCriteriaSignature
        if (!loadMoreUnseen && !sameCriteria) {
            previousProductIds.clear()
            previousUrls.clear()
        }
        lastCriteriaSignature = signature
        lastRequest = request

        val shouldExclude = loadMoreUnseen || sameCriteria
        val mergedExcludedIds = if (shouldExclude) {
            (request.excludedProductIds + previousProductIds).distinct()
        } else {
            request.excludedProductIds.distinct()
        }
        val mergedExcludedUrls = if (shouldExclude) {
            (request.excludedUrls + previousUrls).distinct()
        } else {
            request.excludedUrls.distinct()
        }

        val outgoing = request.copy(
            excludedProductIds = mergedExcludedIds,
            excludedUrls = mergedExcludedUrls
        )
        viewModelScope.launch {
            _shopperResult.value = Resource.Loading
            val result = repository.generateOutfits(outgoing)

            // Sécurité anti-fuite : ignorer la réponse si le compte a changé pendant le scraping
            if (currentUserId() != requestOwnerId) {
                return@launch
            }

            if (result is Resource.Success) {
                val returnedArticles = result.data.articles.ifEmpty {
                    result.data.tenues.flatMap { it.articles } + result.data.articlesComplementaires
                }
                if (returnedArticles.isNotEmpty()) {
                    returnedArticles.forEach { article ->
                        previousProductIds.add(article.id)
                        article.lienAchat?.trim()?.takeIf { it.isNotEmpty() }?.let { previousUrls.add(it) }
                    }
                    cache.saveLastProposals(requestOwnerId, request, result.data)
                } else if (shouldExclude) {
                    // Toutes les propositions uniques de cette session ont déjà été vues :
                    // la prochaine recherche repartira sur un historique vierge.
                    lastCriteriaSignature = null
                }
            }
            _shopperResult.value = result
        }
    }

    fun generateOutfits(request: ShopperPromptRequest, regenerate: Boolean = false) {
        searchArticles(request, loadMoreUnseen = regenerate)
    }

    class Factory : ViewModelProvider.Factory {
        override fun <T : ViewModel> create(modelClass: Class<T>): T {
            @Suppress("UNCHECKED_CAST")
            return ShopperViewModel(ShopperRepository()) as T
        }
    }
}
