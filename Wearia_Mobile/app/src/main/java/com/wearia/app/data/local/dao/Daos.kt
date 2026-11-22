package com.wearia.app.data.local.dao

import androidx.room.*
import com.wearia.app.data.local.entity.TenueFavoriteEntity
import com.wearia.app.data.local.entity.VetementCacheEntity
import kotlinx.coroutines.flow.Flow

@Dao
interface OutfitDao {
    @Query("SELECT * FROM favoris_tenues WHERE userId = :userId ORDER BY cachedAt DESC")
    fun getFavoritesForUser(userId: Int): Flow<List<TenueFavoriteEntity>>

    @Query("SELECT * FROM favoris_tenues WHERE userId = :userId ORDER BY cachedAt DESC")
    suspend fun getFavoritesListForUser(userId: Int): List<TenueFavoriteEntity>

    @Query("SELECT * FROM favoris_tenues WHERE id = :id AND userId = :userId")
    suspend fun getFavoriteByIdForUser(id: Int, userId: Int): TenueFavoriteEntity?

    @Insert(onConflict = OnConflictStrategy.REPLACE)
    suspend fun insertFavorite(tenue: TenueFavoriteEntity): Long

    @Insert(onConflict = OnConflictStrategy.REPLACE)
    suspend fun insertAllFavorites(tenues: List<TenueFavoriteEntity>): List<Long>

    @Delete
    suspend fun deleteFavorite(tenue: TenueFavoriteEntity): Int

    @Query("DELETE FROM favoris_tenues WHERE id = :id AND userId = :userId")
    suspend fun deleteFavoriteByIdForUser(id: Int, userId: Int): Int

    @Query("UPDATE favoris_tenues SET itemsJson = :itemsJson WHERE id = :id AND userId = :userId")
    suspend fun updateFavoriteItemsForUser(id: Int, userId: Int, itemsJson: String): Int

    @Query("UPDATE favoris_tenues SET occasion = :occasion WHERE id = :id AND userId = :userId")
    suspend fun updateFavoriteOccasionForUser(id: Int, userId: Int, occasion: String): Int

    @Query("DELETE FROM favoris_tenues WHERE userId = :userId")
    suspend fun clearFavoritesForUser(userId: Int): Int

    @Query("DELETE FROM favoris_tenues")
    suspend fun clearAllFavorites(): Int

    @Query("SELECT COUNT(*) FROM favoris_tenues WHERE userId = :userId")
    suspend fun countFavoritesForUser(userId: Int): Int
}

@Dao
interface ClothingDao {
    @Query("SELECT * FROM vetements_cache WHERE userId = :userId ORDER BY syncedAt DESC")
    fun getClothesForUser(userId: Int): Flow<List<VetementCacheEntity>>

    @Query("SELECT * FROM vetements_cache WHERE userId = :userId ORDER BY syncedAt DESC")
    suspend fun getClothesListForUser(userId: Int): List<VetementCacheEntity>

    @Insert(onConflict = OnConflictStrategy.REPLACE)
    suspend fun insertAll(clothes: List<VetementCacheEntity>): List<Long>

    @Insert(onConflict = OnConflictStrategy.REPLACE)
    suspend fun insert(clothing: VetementCacheEntity): Long

    @Query("DELETE FROM vetements_cache WHERE userId = :userId")
    suspend fun clearClothesForUser(userId: Int): Int

    @Query("DELETE FROM vetements_cache")
    suspend fun clearAll(): Int

    @Query("SELECT * FROM vetements_cache WHERE id = :id AND userId = :userId")
    suspend fun getByIdForUser(id: Int, userId: Int): VetementCacheEntity?
}
