package com.wearia.app.data.local

import android.content.Context
import androidx.room.Database
import androidx.room.Room
import androidx.room.RoomDatabase
import com.wearia.app.data.local.dao.ClothingDao
import com.wearia.app.data.local.dao.OutfitDao
import com.wearia.app.data.local.entity.TenueFavoriteEntity
import com.wearia.app.data.local.entity.VetementCacheEntity

/**
 * Base de données Room : cache local pour les favoris hors-ligne.
 * Satisfait l'objectif NF04 (disponibilité) en permettant la consultation des favoris sans réseau.
 */
@Database(
    entities = [TenueFavoriteEntity::class, VetementCacheEntity::class],
    version = 1,
    exportSchema = false
)
abstract class WeariaDatabase : RoomDatabase() {

    abstract fun outfitDao(): OutfitDao
    abstract fun clothingDao(): ClothingDao

    companion object {
        @Volatile
        private var INSTANCE: WeariaDatabase? = null

        fun getInstance(context: Context): WeariaDatabase {
            return INSTANCE ?: synchronized(this) {
                Room.databaseBuilder(
                    context.applicationContext,
                    WeariaDatabase::class.java,
                    "wearia_local.db"
                )
                    .fallbackToDestructiveMigration()
                    .build()
                    .also { INSTANCE = it }
            }
        }
    }
}

