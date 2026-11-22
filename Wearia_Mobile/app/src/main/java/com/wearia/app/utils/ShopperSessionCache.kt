package com.wearia.app.utils

import android.content.Context
import android.content.SharedPreferences
import com.google.gson.Gson
import com.wearia.app.data.remote.dto.ShopperPromptRequest
import com.wearia.app.data.remote.dto.ShopperResultResponse

/**
 * ShopperSessionCache : conserve les dernières propositions AI Shopper
 * de manière strictement isolée par compte utilisateur (`userId`).
 *
 * - Les dernières propositions restent visibles pour le compte connecté.
 * - Aucun autre compte ne peut voir les propositions d'un autre utilisateur.
 */
class ShopperSessionCache(context: Context) {

    private val prefs: SharedPreferences =
        context.getSharedPreferences("wearia_shopper_cache", Context.MODE_PRIVATE)
    private val gson = Gson()

    data class CachedShopperSnapshot(
        val ownerUserId: Int,
        val request: ShopperPromptRequest?,
        val result: ShopperResultResponse,
        val savedAtMs: Long = System.currentTimeMillis()
    )

    private fun keyForUser(userId: Int): String = "shopper_last_snapshot_user_$userId"

    fun saveLastProposals(
        userId: Int,
        request: ShopperPromptRequest?,
        result: ShopperResultResponse
    ) {
        if (userId <= 0) return
        try {
            val snapshot = CachedShopperSnapshot(
                ownerUserId = userId,
                request = request,
                result = result
            )
            prefs.edit().putString(keyForUser(userId), gson.toJson(snapshot)).apply()
        } catch (_: Exception) {
            // Best-effort
        }
    }

    fun getLastProposals(userId: Int): CachedShopperSnapshot? {
        if (userId <= 0) return null
        val raw = prefs.getString(keyForUser(userId), null) ?: return null
        return try {
            val parsed = gson.fromJson(raw, CachedShopperSnapshot::class.java)
            if (parsed != null && parsed.ownerUserId == userId) {
                parsed
            } else {
                null
            }
        } catch (_: Exception) {
            null
        }
    }

    fun clearForUser(userId: Int) {
        if (userId <= 0) return
        prefs.edit().remove(keyForUser(userId)).apply()
    }
}
