package com.wearia.app.viewmodel

import androidx.lifecycle.*
import com.wearia.app.data.remote.dto.TokenResponse
import com.wearia.app.data.remote.dto.UserResponse
import com.wearia.app.repositories.AuthRepository
import com.wearia.app.utils.Resource
import kotlinx.coroutines.launch

class AuthViewModel(private val repository: AuthRepository) : ViewModel() {

    private val _registerState = MutableLiveData<Resource<UserResponse>>()
    val registerState: LiveData<Resource<UserResponse>> = _registerState

    private val _loginState = MutableLiveData<Resource<TokenResponse>>()
    val loginState: LiveData<Resource<TokenResponse>> = _loginState

    fun register(nom: String, email: String, password: String) {
        viewModelScope.launch {
            _registerState.value = Resource.Loading
            _registerState.value = repository.register(nom, email, password)
        }
    }

    fun login(email: String, password: String) {
        viewModelScope.launch {
            _loginState.value = Resource.Loading
            _loginState.value = repository.login(email, password)
        }
    }

    fun logout() = repository.logout()

    fun isLoggedIn() = repository.isLoggedIn()

    class Factory : ViewModelProvider.Factory {
        override fun <T : ViewModel> create(modelClass: Class<T>): T {
            @Suppress("UNCHECKED_CAST")
            return AuthViewModel(AuthRepository()) as T
        }
    }
}

