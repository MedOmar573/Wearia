package com.wearia.app.viewmodel

import androidx.lifecycle.*
import com.wearia.app.data.remote.dto.*
import com.wearia.app.repositories.ProfileRepository
import com.wearia.app.utils.Resource
import kotlinx.coroutines.launch

class ProfileViewModel(private val repository: ProfileRepository) : ViewModel() {

    private val _profileState = MutableLiveData<Resource<UserResponse>>()
    val profileState: LiveData<Resource<UserResponse>> = _profileState

    private val _updateState = MutableLiveData<Resource<UserResponse>>()
    val updateState: LiveData<Resource<UserResponse>> = _updateState

    private val _colorPreferencesState = MutableLiveData<Resource<List<PreferenceCouleurResponse>>>()
    val colorPreferencesState: LiveData<Resource<List<PreferenceCouleurResponse>>> = _colorPreferencesState

    private val _stylePreferencesState = MutableLiveData<Resource<List<PreferenceStyleResponse>>>()
    val stylePreferencesState: LiveData<Resource<List<PreferenceStyleResponse>>> = _stylePreferencesState

    private val _colors = MutableLiveData<List<CouleurResponse>>()
    val colors: LiveData<List<CouleurResponse>> = _colors

    private val _types = MutableLiveData<List<TypeVetementResponse>>()
    val types: LiveData<List<TypeVetementResponse>> = _types

    private val _styles = MutableLiveData<List<StyleVestimentaireResponse>>()
    val styles: LiveData<List<StyleVestimentaireResponse>> = _styles

    private val _categories = MutableLiveData<List<CategorieResponse>>()
    val categories: LiveData<List<CategorieResponse>> = _categories

    private val _routines = MutableLiveData<Resource<List<RoutineHebdomadaireResponse>>>()
    val routines: LiveData<Resource<List<RoutineHebdomadaireResponse>>> = _routines

    private val _suggestions = MutableLiveData<Resource<List<ArticleCatalogueResponse>>>()
    val suggestions: LiveData<Resource<List<ArticleCatalogueResponse>>> = _suggestions

    fun loadProfile() {
        viewModelScope.launch {
            _profileState.value = Resource.Loading
            _profileState.value = repository.getProfile()
        }
    }

    fun updateProfile(request: UserUpdateRequest) {
        viewModelScope.launch {
            _updateState.value = Resource.Loading
            _updateState.value = repository.updateProfile(request)
        }
    }

    fun saveColorPreferences(likedColorIds: List<Int>, avoidedColorIds: List<Int> = emptyList()) {
        viewModelScope.launch {
            _colorPreferencesState.value = Resource.Loading
            _colorPreferencesState.value = repository.updateColorPreferences(likedColorIds, avoidedColorIds)
        }
    }

    fun saveStylePreferences(styleIds: List<Int>) {
        viewModelScope.launch {
            _stylePreferencesState.value = Resource.Loading
            _stylePreferencesState.value = repository.updateStylePreferences(styleIds)
        }
    }

    fun loadReferentials(genre: String? = null) {
        viewModelScope.launch {
            when (val res = repository.getColors()) {
                is Resource.Success -> _colors.value = res.data
                else -> {}
            }
            when (val res = repository.getStyles()) {
                is Resource.Success -> _styles.value = res.data
                else -> {}
            }
            when (val res = repository.getCategories()) {
                is Resource.Success -> _categories.value = res.data
                else -> {}
            }
            when (val res = repository.getTypes(genre)) {
                is Resource.Success -> _types.value = res.data
                else -> {}
            }
        }
    }

    fun loadRoutines() {
        viewModelScope.launch {
            _routines.value = Resource.Loading
            _routines.value = repository.getRoutines()
        }
    }

    fun createRoutine(jour: String, occasion: String) {
        viewModelScope.launch {
            repository.createRoutine(jour, occasion)
            loadRoutines()
        }
    }

    fun deleteRoutine(id: Int) {
        viewModelScope.launch {
            repository.deleteRoutine(id)
            loadRoutines()
        }
    }

    fun loadShoppingSuggestions(besoin: String? = null) {
        viewModelScope.launch {
            _suggestions.value = Resource.Loading
            _suggestions.value = repository.getShoppingSuggestions(besoin)
        }
    }

    class Factory : ViewModelProvider.Factory {
        override fun <T : ViewModel> create(modelClass: Class<T>): T {
            @Suppress("UNCHECKED_CAST")
            return ProfileViewModel(ProfileRepository()) as T
        }
    }
}

