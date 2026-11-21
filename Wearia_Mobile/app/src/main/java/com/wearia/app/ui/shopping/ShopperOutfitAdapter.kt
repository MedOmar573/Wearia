package com.wearia.app.ui.shopping

import android.content.Intent
import android.net.Uri
import android.view.LayoutInflater
import android.view.ViewGroup
import android.widget.Toast
import androidx.recyclerview.widget.DiffUtil
import androidx.recyclerview.widget.ListAdapter
import androidx.recyclerview.widget.RecyclerView
import coil.load
import com.wearia.app.R
import com.wearia.app.data.remote.dto.ShopperOutfitResponse
import com.wearia.app.databinding.ItemShopperArticleBinding
import com.wearia.app.databinding.ItemShopperOutfitBinding
import com.wearia.app.utils.addPressEffect

class ShopperOutfitAdapter :
    ListAdapter<ShopperOutfitResponse, ShopperOutfitAdapter.OutfitViewHolder>(DiffCallback) {

    override fun onCreateViewHolder(parent: ViewGroup, viewType: Int): OutfitViewHolder {
        val binding = ItemShopperOutfitBinding.inflate(
            LayoutInflater.from(parent.context), parent, false
        )
        return OutfitViewHolder(binding)
    }

    override fun onBindViewHolder(holder: OutfitViewHolder, position: Int) {
        holder.bind(getItem(position))
    }

    class OutfitViewHolder(
        private val binding: ItemShopperOutfitBinding
    ) : RecyclerView.ViewHolder(binding.root) {

        fun bind(outfit: ShopperOutfitResponse) {
            val context = itemView.context

            // Titre : Option N · Style
            val style = outfit.styleConcordance?.let { " · $it" } ?: ""
            binding.tvOutfitTitle.text = "Option ${outfit.id}$style"

            // Score match
            binding.tvOutfitScore.text = "★ ${outfit.scoreCompatibilite}%"

            // Prix total
            binding.tvOutfitTotalPrice.text = "${outfit.prixTotal} TND"

            // Statut budget
            if (outfit.respecteBudget) {
                val eco = outfit.budgetMax?.let { bMax ->
                    if (bMax >= outfit.prixTotal) " (−${String.format("%.0f", bMax - outfit.prixTotal)} TND)" else ""
                } ?: ""
                binding.tvOutfitBudgetStatus.text = " · Dans le budget$eco"
                binding.tvOutfitBudgetStatus.setTextColor(
                    android.graphics.Color.parseColor("#22C55E")
                )
            } else {
                binding.tvOutfitBudgetStatus.text = " · Dépasse le budget"
                binding.tvOutfitBudgetStatus.setTextColor(
                    android.graphics.Color.parseColor("#EF4444")
                )
            }

            // Explication sobre
            binding.tvOutfitExplanation.text =
                outfit.explication?.takeIf { it.isNotBlank() }
                    ?: "Combinaison harmonieuse de pièces réelles."

            // Articles de la tenue
            binding.llOutfitArticles.removeAllViews()
            val inflater = LayoutInflater.from(context)

            for (article in outfit.articles) {
                val a = ItemShopperArticleBinding.inflate(inflater, binding.llOutfitArticles, false)

                // Badge catégorie
                val cat = article.categorieNom.lowercase()
                val badgeText = when {
                    cat.contains("haut") || cat.contains("t-shirt") || cat.contains("chemise") -> "HAUT"
                    cat.contains("bas") || cat.contains("pant") || cat.contains("jean") -> "BAS"
                    cat.contains("chauss") || cat.contains("basket") || cat.contains("sneaker") -> "CHAUSSURES"
                    cat.contains("veste") || cat.contains("jacket") -> "VESTE"
                    cat.contains("robe") -> "ROBE"
                    else -> cat.uppercase().take(10)
                }
                a.tvShopperArticleBadge.text = badgeText

                // Nom + boutique + tailles + prix
                a.tvShopperArticleName.text = article.nom
                a.tvShopperArticleStore.text = "${article.vendeur} · ${article.taillesDisponibles}"
                a.tvShopperArticlePrice.text = "${article.prix} ${article.devise}"

                // Image produit
                a.ivShopperArticleImage.load(article.imageUrl) {
                    placeholder(R.drawable.ic_hanger)
                    error(R.drawable.ic_hanger)
                    crossfade(true)
                }

                // Lien boutique
                val openUrl: () -> Unit = {
                    val rawUrl = article.lienAchat?.trim()
                    val targetUrl = if (!rawUrl.isNullOrBlank() &&
                        (rawUrl.startsWith("http://") || rawUrl.startsWith("https://"))
                    ) {
                        rawUrl
                    } else {
                        when (article.vendeur.lowercase()) {
                            "exist" -> "https://www.exist.com.tn"
                            "zen tunisie", "zen" -> "https://zen.com.tn"
                            "pull&bear tn", "pull&bear" -> "https://www.pullandbear.com/tn"
                            "bershka tn", "bershka" -> "https://www.bershka.com/tn"
                            "zara tn", "zara" -> "https://www.zara.com/tn"
                            else -> "https://www.exist.com.tn"
                        }
                    }
                    try {
                        val intent = Intent(Intent.ACTION_VIEW, Uri.parse(targetUrl)).apply {
                            addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
                        }
                        context.startActivity(intent)
                    } catch (e: Exception) {
                        Toast.makeText(
                            context,
                            "Impossible d'ouvrir ${article.vendeur}",
                            Toast.LENGTH_SHORT
                        ).show()
                    }
                }

                a.btnBuyArticle.text = "Voir ↗"
                a.btnBuyArticle.addPressEffect()
                a.btnBuyArticle.setOnClickListener { openUrl() }
                a.root.setOnClickListener { openUrl() }

                binding.llOutfitArticles.addView(a.root)
            }
        }
    }

    companion object DiffCallback : DiffUtil.ItemCallback<ShopperOutfitResponse>() {
        override fun areItemsTheSame(
            oldItem: ShopperOutfitResponse,
            newItem: ShopperOutfitResponse
        ) = oldItem.id == newItem.id

        override fun areContentsTheSame(
            oldItem: ShopperOutfitResponse,
            newItem: ShopperOutfitResponse
        ) = oldItem == newItem
    }
}
