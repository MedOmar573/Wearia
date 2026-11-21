package com.wearia.app.viewmodel

import androidx.lifecycle.LiveData
import androidx.lifecycle.MutableLiveData
import androidx.lifecycle.ViewModel
import androidx.lifecycle.ViewModelProvider
import androidx.lifecycle.viewModelScope
import com.wearia.app.data.remote.dto.ShopperResultResponse
import com.wearia.app.repositories.ShopperRepository
import com.wearia.app.utils.Resource
import kotlinx.coroutines.launch

class ShopperViewModel(private val repository: ShopperRepository) : ViewModel() {

    private val _shopperResult = MutableLiveData<Resource<ShopperResultResponse>>()
    val shopperResult: LiveData<Resource<ShopperResultResponse>> = _shopperResult

    fun generateOutfits(prompt: String, budget: Float? = null, genre: String? = null) {
        if (prompt.isBlank()) return
        viewModelScope.launch {
            _shopperResult.value = Resource.Loading
            _shopperResult.value = repository.generateOutfits(prompt, budget, genre)
        }
    }

    class Factory : ViewModelProvider.Factory {
        override fun <T : ViewModel> create(modelClass: Class<T>): T {
            @Suppress("UNCHECKED_CAST")
            return ShopperViewModel(ShopperRepository()) as T
        }
    }
}
