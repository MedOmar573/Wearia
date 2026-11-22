package com.wearia.app.ui.shopping

import android.content.Context
import android.content.Intent
import android.graphics.Color
import android.net.Uri
import android.view.LayoutInflater
import android.view.View
import android.view.ViewGroup
import android.widget.Toast
import androidx.recyclerview.widget.DiffUtil
import androidx.recyclerview.widget.ListAdapter
import androidx.recyclerview.widget.RecyclerView
import coil.load
import com.wearia.app.R
import com.wearia.app.WeariaApplication
import com.wearia.app.data.remote.dto.ShopperArticleResponse
import com.wearia.app.databinding.ItemShopperArticleBinding
import com.wearia.app.utils.addPressEffect
import java.util.Locale

/**
 * ShopperArticleAdapter : affiche la liste de propositions individuelles
 * retournées par l'AI Shopper pour le type de vêtement demandé.
 */
class ShopperArticleAdapter :
    ListAdapter<ShopperArticleResponse, ShopperArticleAdapter.ArticleViewHolder>(DiffCallback) {

    override fun onCreateViewHolder(parent: ViewGroup, viewType: Int): ArticleViewHolder {
        val binding = ItemShopperArticleBinding.inflate(
            LayoutInflater.from(parent.context), parent, false
        )
        return ArticleViewHolder(binding)
    }

    override fun onBindViewHolder(holder: ArticleViewHolder, position: Int) {
        holder.bind(getItem(position))
    }

    class ArticleViewHolder(
        private val binding: ItemShopperArticleBinding
    ) : RecyclerView.ViewHolder(binding.root) {

        fun bind(article: ShopperArticleResponse) {
            val context = itemView.context

            // Badge type exact demandé
            binding.tvShopperArticleBadge.text = article.typeVetementNom.uppercase(Locale.FRANCE)

            // Style + score de correspondance
            val stylePrefix = article.styleNom?.takeIf { it.isNotBlank() }?.let { "$it · " } ?: ""
            binding.tvShopperArticleStyleScore.text = "${stylePrefix}★ ${article.scoreCompatibilite}%"

            // Nom produit
            binding.tvShopperArticleName.text = article.nom

            // Boutique + couleur + tailles + fraîcheur
            val sizeLabel = article.taillesDisponibles
                .takeIf { it.isNotBlank() && !it.equals("Non vérifiées", true) }
                ?.let { " · Tailles $it" } ?: ""
            val checkedAt = article.verifieLe?.take(10)?.let { " · Vérifié le $it" } ?: ""
            binding.tvShopperArticleStore.text = "${article.vendeur} · ${article.couleurNom}$sizeLabel$checkedAt"

            // Prix + statut budget
            binding.tvShopperArticlePrice.text =
                "${String.format(Locale.FRANCE, "%.2f", article.prix)} ${article.devise}"
            if (article.respecteBudget) {
                binding.tvShopperArticleBudgetBadge.visibility = View.VISIBLE
                binding.tvShopperArticleBudgetBadge.text = "· Dans le budget"
                binding.tvShopperArticleBudgetBadge.setTextColor(Color.parseColor("#22C55E"))
            } else {
                binding.tvShopperArticleBudgetBadge.visibility = View.VISIBLE
                binding.tvShopperArticleBudgetBadge.text = "· Hors budget"
                binding.tvShopperArticleBudgetBadge.setTextColor(Color.parseColor("#EF4444"))
            }

            // Image produit
            binding.ivShopperArticleImage.load(article.imageUrl) {
                placeholder(R.drawable.ic_hanger)
                error(R.drawable.ic_hanger)
                crossfade(true)
            }

            // Validation stricte du lien produit
            val validProductUrl = ShopperOutfitAdapter.validatedProductUrl(article.lienAchat)
            val openUrl: () -> Unit = {
                if (validProductUrl == null) {
                    Toast.makeText(context, "Lien produit vérifié indisponible", Toast.LENGTH_SHORT).show()
                } else {
                    try {
                        val intent = Intent(Intent.ACTION_VIEW, Uri.parse(validProductUrl)).apply {
                            addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
                        }
                        context.startActivity(intent)
                    } catch (_: Exception) {
                        Toast.makeText(context, "Impossible d'ouvrir ${article.vendeur}", Toast.LENGTH_SHORT).show()
                    }
                }
            }

            val hasDirectLink = validProductUrl != null
            binding.btnBuyArticle.text = if (hasDirectLink) "Voir ↗" else "Indisponible"
            binding.btnBuyArticle.isEnabled = hasDirectLink

            // Favoris AI Shopper strictement isolés par compte utilisateur
            val userId = WeariaApplication.instance.sessionManager.getUserId()
            val favKey = "product_ids_user_$userId"
            val favorites = context.getSharedPreferences("shopper_favorites", Context.MODE_PRIVATE)
            fun refreshFavorite() {
                val saved = favorites.getStringSet(favKey, emptySet()).orEmpty().contains(article.id.toString())
                binding.tvShopperArticleFavorite.text = if (saved) "♥ Favori" else "♡ Favori"
            }
            refreshFavorite()
            binding.tvShopperArticleFavorite.setOnClickListener {
                val savedIds = favorites.getStringSet(favKey, emptySet()).orEmpty().toMutableSet()
                if (!savedIds.add(article.id.toString())) savedIds.remove(article.id.toString())
                favorites.edit().putStringSet(favKey, savedIds).apply()
                refreshFavorite()
            }

            binding.btnBuyArticle.addPressEffect()
            binding.btnBuyArticle.setOnClickListener { openUrl() }
            binding.root.setOnClickListener { openUrl() }
        }
    }

    companion object DiffCallback : DiffUtil.ItemCallback<ShopperArticleResponse>() {
        override fun areItemsTheSame(
            oldItem: ShopperArticleResponse,
            newItem: ShopperArticleResponse
        ) = oldItem.id == newItem.id

        override fun areContentsTheSame(
            oldItem: ShopperArticleResponse,
            newItem: ShopperArticleResponse
        ) = oldItem == newItem
    }
}
