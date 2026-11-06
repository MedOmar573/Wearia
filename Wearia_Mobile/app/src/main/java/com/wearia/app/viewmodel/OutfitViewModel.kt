package com.wearia.app.viewmodel

import androidx.lifecycle.*
import com.wearia.app.data.remote.dto.*
import com.wearia.app.repositories.OutfitRepository
import com.wearia.app.utils.Resource
import kotlinx.coroutines.launch

class OutfitViewModel(private val repository: OutfitRepository) : ViewModel() {

    private val _recommendationState = MutableLiveData<Resource<RecommendationResponse>>()
    val recommendationState: LiveData<Resource<RecommendationResponse>> = _recommendationState

    private val _outfitsList = MutableLiveData<Resource<List<TenueResponse>>>()
    val outfitsList: LiveData<Resource<List<TenueResponse>>> = _outfitsList

    private val _feedbackState = MutableLiveData<Resource<FeedbackResponse>>()
    val feedbackState: LiveData<Resource<FeedbackResponse>> = _feedbackState

    private val _favoriteState = MutableLiveData<Resource<TenueResponse>>()
    val favoriteState: LiveData<Resource<TenueResponse>> = _favoriteState

    /** Tenues favorites du cache Room (hors-ligne) */
    val localFavorites = repository.getLocalFavorites().asLiveData()

    /**
     * Déclenche la génération d'une recommandation via le moteur BR01-BR09.
     * Si manualTemp/manualPrecip sont fournis, ignore OpenWeatherMap (PIÈGE DE DÉMO).
     */
    fun generateRecommendation(
        occasion: String? = null,
        manualTemp: Float? = null,
        manualPrecip: Boolean? = null
    ) {
        viewModelScope.launch {
            _recommendationState.value = Resource.Loading
            _recommendationState.value = repository.getRecommendation(
                occasion = occasion,
                manualTemp = manualTemp,
                manualPrecip = manualPrecip
            )
        }
    }

    fun loadOutfits(favorisOnly: Boolean = false) {
        viewModelScope.launch {
            _outfitsList.value = Resource.Loading
            _outfitsList.value = repository.getOutfits(favorisOnly)
        }
    }

    fun toggleFavorite(outfitId: Int, isFavorite: Boolean) {
        viewModelScope.launch {
            _favoriteState.value = repository.toggleFavorite(outfitId, isFavorite)
        }
    }

    fun submitFeedback(outfitId: Int, appreciation: String, motifRejet: String? = null) {
        viewModelScope.launch {
            _feedbackState.value = Resource.Loading
            _feedbackState.value = repository.submitFeedback(outfitId, appreciation, motifRejet)
        }
    }

    class Factory : ViewModelProvider.Factory {
        override fun <T : ViewModel> create(modelClass: Class<T>): T {
            @Suppress("UNCHECKED_CAST")
            return OutfitViewModel(OutfitRepository()) as T
        }
    }
}

