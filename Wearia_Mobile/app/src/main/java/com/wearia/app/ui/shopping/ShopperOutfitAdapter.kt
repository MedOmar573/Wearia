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
                    cat.contains("veste") || cat.contains("jacket") || cat.contains("manteau") -> "VESTE"
                    cat.contains("haut") || cat.contains("t-shirt") || cat.contains("chemise") -> "HAUT"
                    cat.contains("bas") || cat.contains("pant") || cat.contains("jean") -> "BAS"
                    cat.contains("chauss") || cat.contains("basket") || cat.contains("sneaker") -> "CHAUSSURES"
                    cat.contains("robe") -> "ROBE"
                    cat.contains("accessoire") -> "ACCESSOIRE"
                    else -> cat.uppercase().take(10)
                }
                a.tvShopperArticleBadge.text = badgeText

                // Nom + boutique + tailles + prix
                a.tvShopperArticleName.text = article.nom
                val checkedAt = article.verifieLe?.take(16)?.replace('T', ' ')
                val checkedLabel = checkedAt?.let { " · Offre lue le $it UTC" } ?: " · Date de lecture inconnue"
                val sizeLabel = article.taillesDisponibles.takeIf { it.isNotBlank() && !it.equals("Non vérifiées", true) }
                    ?.let { " · Tailles $it" } ?: ""
                a.tvShopperArticleStore.text = "${article.vendeur} · ${article.couleurNom}$sizeLabel$checkedLabel"
                a.tvShopperArticlePrice.text = "${String.format(java.util.Locale.FRANCE, "%.2f", article.prix)} ${article.devise}"

                // Image produit
                a.ivShopperArticleImage.load(article.imageUrl) {
                    placeholder(R.drawable.ic_hanger)
                    error(R.drawable.ic_hanger)
                    crossfade(true)
                }

                // Lien boutique validé strictement
                val validProductUrl = validatedProductUrl(article.lienAchat)
                val openUrl: () -> Unit = {
                    if (validProductUrl == null) {
                        Toast.makeText(context, "Lien produit vérifié indisponible", Toast.LENGTH_SHORT).show()
                    } else {
                        try {
                            val intent = Intent(Intent.ACTION_VIEW, Uri.parse(validProductUrl)).apply {
                                addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
                            }
                            context.startActivity(intent)
                        } catch (e: Exception) {
                            Toast.makeText(context, "Impossible d'ouvrir ${article.vendeur}", Toast.LENGTH_SHORT).show()
                        }
                    }
                }

                val hasDirectLink = validProductUrl != null
                a.btnBuyArticle.text = if (hasDirectLink) "Fiche produit ↗" else "Lien indisponible"
                a.btnBuyArticle.isEnabled = hasDirectLink
                val userId = com.wearia.app.WeariaApplication.instance.sessionManager.getUserId()
                val favKey = "product_ids_user_$userId"
                val favorites = context.getSharedPreferences("shopper_favorites", android.content.Context.MODE_PRIVATE)
                fun refreshFavorite() {
                    val saved = favorites.getStringSet(favKey, emptySet()).orEmpty().contains(article.id.toString())
                    a.tvShopperArticleFavorite.text = if (saved) "♥ Favori" else "♡ Favori"
                }
                refreshFavorite()
                a.tvShopperArticleFavorite.setOnClickListener {
                    val savedIds = favorites.getStringSet(favKey, emptySet()).orEmpty().toMutableSet()
                    if (!savedIds.add(article.id.toString())) savedIds.remove(article.id.toString())
                    favorites.edit().putStringSet(favKey, savedIds).apply()
                    refreshFavorite()
                }
                a.btnBuyArticle.addPressEffect()
                a.btnBuyArticle.setOnClickListener { openUrl() }
                a.root.setOnClickListener { openUrl() }

                binding.llOutfitArticles.addView(a.root)
            }
        }
    }

    companion object DiffCallback : DiffUtil.ItemCallback<ShopperOutfitResponse>() {
        private val BLOCKED_HOSTS = setOf(
            "localhost",
            "127.0.0.1",
            "0.0.0.0",
            "example.com",
            "www.example.com",
            "example.org",
            "example.net",
            "test.com",
            "placeholder.com"
        )
        private val CATEGORY_PATH_REGEX = Regex(
            pattern = "(-[cl]\\d+\\.html$|/categorie-produit/|/collections/all/?$|/search/?$)",
            option = RegexOption.IGNORE_CASE
        )

        fun validatedProductUrl(rawUrl: String?): String? {
            val trimmed = rawUrl?.trim().orEmpty()
            if (trimmed.isEmpty() || !trimmed.startsWith("https://", ignoreCase = true)) return null
            val uri = try {
                Uri.parse(trimmed)
            } catch (_: Exception) {
                return null
            }
            val host = uri.host?.lowercase()?.trim().orEmpty()
            if (host.isEmpty() || !host.contains('.') || host in BLOCKED_HOSTS) return null
            val path = uri.path?.trim().orEmpty()
            if (path.isEmpty() || path == "/") return null
            if (CATEGORY_PATH_REGEX.containsMatchIn(path)) return null
            return trimmed
        }

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
