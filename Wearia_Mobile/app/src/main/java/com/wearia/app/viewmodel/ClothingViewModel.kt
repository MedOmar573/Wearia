package com.wearia.app.viewmodel

import androidx.lifecycle.*
import com.wearia.app.data.remote.dto.*
import com.wearia.app.repositories.ClothingRepository
import com.wearia.app.utils.Resource
import kotlinx.coroutines.launch
import java.io.File

class ClothingViewModel(private val repository: ClothingRepository) : ViewModel() {

    private val _clothesList = MutableLiveData<Resource<List<VetementResponse>>>()
    val clothesList: LiveData<Resource<List<VetementResponse>>> = _clothesList
    val clothesState: LiveData<Resource<List<VetementResponse>>> get() = _clothesList

    private val _addClothingState = MutableLiveData<Resource<VetementResponse>>()
    val addClothingState: LiveData<Resource<VetementResponse>> = _addClothingState

    private val _classifyState = MutableLiveData<Resource<ClassifyResponse>?>()
    val classifyState: LiveData<Resource<ClassifyResponse>?> = _classifyState

    private val _deleteState = MutableLiveData<Resource<Unit>>()
    val deleteState: LiveData<Resource<Unit>> = _deleteState

    // Filtres actifs
    var filterCategorieId: Int? = null
    var filterCouleurId: Int? = null
    var filterStatut: String? = null
    var searchQuery: String? = null

    /** Cache local Room pour le mode hors-ligne */
    val localClothes = repository.getLocalClothes().asLiveData()

    fun loadClothes() {
        viewModelScope.launch {
            _clothesList.value = Resource.Loading
            _clothesList.value = repository.getClothes(
                categorieId = filterCategorieId,
                couleurId = filterCouleurId,
                statut = filterStatut,
                search = searchQuery
            )
        }
    }

    fun addClothing(request: VetementCreateRequest) {
        viewModelScope.launch {
            _addClothingState.value = Resource.Loading
            _addClothingState.value = repository.addClothing(request)
        }
    }

    /**
     * Envoie la photo capturée avec CameraX ou importée de la galerie au backend pour classification KNN.
     */
    fun classifyImage(imageFile: File) {
        viewModelScope.launch {
            _classifyState.value = Resource.Loading
            _classifyState.value = repository.classifyClothing(imageFile)
        }
    }

    fun classifyClothing(imageFile: File) {
        classifyImage(imageFile)
    }

    fun resetClassifyState() {
        _classifyState.value = null
    }

    fun resetAddClothingState() {
        _addClothingState.value = null
    }

    fun deleteClothing(id: Int) {
        viewModelScope.launch {
            _deleteState.value = Resource.Loading
            _deleteState.value = repository.deleteClothing(id)
            if (_deleteState.value is Resource.Success) {
                loadClothes()
            }
        }
    }

    fun updateClothing(id: Int, request: VetementUpdateRequest) {
        viewModelScope.launch {
            repository.updateClothing(id, request)
            loadClothes()
        }
    }

    class Factory : ViewModelProvider.Factory {
        override fun <T : ViewModel> create(modelClass: Class<T>): T {
            @Suppress("UNCHECKED_CAST")
            return ClothingViewModel(ClothingRepository()) as T
        }
    }
}
