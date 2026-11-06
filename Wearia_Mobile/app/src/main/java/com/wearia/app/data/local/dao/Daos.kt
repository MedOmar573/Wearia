package com.wearia.app.data.local.dao

import androidx.room.*
import com.wearia.app.data.local.entity.TenueFavoriteEntity
import com.wearia.app.data.local.entity.VetementCacheEntity
import kotlinx.coroutines.flow.Flow

@Dao
interface OutfitDao {
    @Query("SELECT * FROM favoris_tenues ORDER BY cachedAt DESC")
    fun getAllFavorites(): Flow<List<TenueFavoriteEntity>>

    @Insert(onConflict = OnConflictStrategy.REPLACE)
    suspend fun insertFavorite(tenue: TenueFavoriteEntity): Long

    @Delete
    suspend fun deleteFavorite(tenue: TenueFavoriteEntity): Int

    @Query("DELETE FROM favoris_tenues WHERE id = :id")
    suspend fun deleteFavoriteById(id: Int): Int

    @Query("SELECT COUNT(*) FROM favoris_tenues")
    suspend fun countFavorites(): Int
}

@Dao
interface ClothingDao {
    @Query("SELECT * FROM vetements_cache ORDER BY syncedAt DESC")
    fun getAllClothes(): Flow<List<VetementCacheEntity>>

    @Insert(onConflict = OnConflictStrategy.REPLACE)
    suspend fun insertAll(clothes: List<VetementCacheEntity>): List<Long>

    @Insert(onConflict = OnConflictStrategy.REPLACE)
    suspend fun insert(clothing: VetementCacheEntity): Long

    @Query("DELETE FROM vetements_cache")
    suspend fun clearAll(): Int

    @Query("SELECT * FROM vetements_cache WHERE id = :id")
    suspend fun getById(id: Int): VetementCacheEntity?
}
