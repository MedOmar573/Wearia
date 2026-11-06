package com.wearia.app.data.local.entity

import androidx.room.Entity
import androidx.room.PrimaryKey

/**
 * Entité Room : cache local des vêtements favoris et de la tenue favorite.
 * Permet la consultation hors-ligne (Room - Priorité 2 du cahier des charges).
 */

@Entity(tableName = "favoris_tenues")
data class TenueFavoriteEntity(
    @PrimaryKey val id: Int,
    val occasion: String,
    val temperature: Float?,
    val weather: String?,
    val score: Int,
    val explanation: String,
    val itemsJson: String,      // JSON sérialisé de la liste des vêtements
    val cachedAt: Long = System.currentTimeMillis()
)

@Entity(tableName = "vetements_cache")
data class VetementCacheEntity(
    @PrimaryKey val id: Int,
    val nom: String,
    val photoUrl: String,
    val categorie: String,
    val couleur: String,
    val couleurHex: String,
    val statut: String,
    val estFavori: Boolean = false,
    val syncedAt: Long = System.currentTimeMillis()
)

