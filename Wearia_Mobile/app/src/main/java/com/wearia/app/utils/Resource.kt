package com.wearia.app.utils

/**
 * Resource<T> : sealed class pour représenter les états d'un appel réseau.
 * Utilisée dans tous les Repositories et observée par les ViewModels.
 */
sealed class Resource<out T> {
    data class Success<out T>(val data: T) : Resource<T>()
    data class Error(val message: String) : Resource<Nothing>()
    object Loading : Resource<Nothing>()
}

