package com.wearia.app.viewmodel

import androidx.lifecycle.*
import com.wearia.app.data.remote.dto.AuthStepResponse
import com.wearia.app.data.remote.dto.TokenResponse
import com.wearia.app.repositories.AuthRepository
import com.wearia.app.utils.Resource
import kotlinx.coroutines.launch

class AuthViewModel(private val repository: AuthRepository) : ViewModel() {

    // Étape 1 : Demande d'inscription ou connexion -> Attente de l'OTP
    private val _authStepState = MutableLiveData<Resource<AuthStepResponse>?>()
    val authStepState: LiveData<Resource<AuthStepResponse>?> = _authStepState

    // Étape 2 : Vérification du code OTP -> Émission du jeton JWT
    private val _verifyOtpState = MutableLiveData<Resource<TokenResponse>?>()
    val verifyOtpState: LiveData<Resource<TokenResponse>?> = _verifyOtpState

    // Renvoi du code OTP
    private val _resendOtpState = MutableLiveData<Resource<String>?>()
    val resendOtpState: LiveData<Resource<String>?> = _resendOtpState

    fun register(
        nom: String, 
        email: String, 
        password: String,
        hauteurCm: Int? = null,
        poidsKg: Float? = null,
        genre: String? = null
    ) {
        viewModelScope.launch {
            _authStepState.value = Resource.Loading
            _authStepState.value = repository.register(nom, email, password, hauteurCm, poidsKg, genre)
        }
    }

    fun login(email: String, password: String) {
        viewModelScope.launch {
            _authStepState.value = Resource.Loading
            _authStepState.value = repository.login(email, password)
        }
    }

    fun verifyOtp(email: String, code: String, purpose: String) {
        viewModelScope.launch {
            _verifyOtpState.value = Resource.Loading
            _verifyOtpState.value = repository.verifyOtp(email, code, purpose)
        }
    }

    fun resendOtp(email: String, purpose: String) {
        viewModelScope.launch {
            _resendOtpState.value = Resource.Loading
            _resendOtpState.value = repository.resendOtp(email, purpose)
        }
    }

    fun resetAuthStepState() {
        _authStepState.value = null
    }

    fun resetVerifyOtpState() {
        _verifyOtpState.value = null
    }

    fun resetResendOtpState() {
        _resendOtpState.value = null
    }

    fun logout() {
        viewModelScope.launch {
            repository.logoutAndClearCaches()
        }
    }

    fun isLoggedIn() = repository.isLoggedIn()

    class Factory : ViewModelProvider.Factory {
        override fun <T : ViewModel> create(modelClass: Class<T>): T {
            @Suppress("UNCHECKED_CAST")
            return AuthViewModel(AuthRepository()) as T
        }
    }
}
