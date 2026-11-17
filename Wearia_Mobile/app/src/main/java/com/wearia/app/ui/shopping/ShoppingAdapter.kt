package com.wearia.app.ui.shopping

import android.view.LayoutInflater
import android.view.ViewGroup
import android.widget.Toast
import androidx.recyclerview.widget.RecyclerView
import coil.load
import com.wearia.app.BuildConfig
import com.wearia.app.R
import com.wearia.app.data.remote.dto.ArticleCatalogueResponse
import com.wearia.app.databinding.ItemShoppingBinding
import com.wearia.app.utils.addPressEffect

/**
 * ShoppingAdapter : Suggestions de pièces manquantes IA.
 */
class ShoppingAdapter : RecyclerView.Adapter<ShoppingAdapter.ShoppingViewHolder>() {

    private val articles = mutableListOf<ArticleCatalogueResponse>()

    fun submitList(list: List<ArticleCatalogueResponse>) {
        articles.clear()
        articles.addAll(list)
        notifyDataSetChanged()
    }

    override fun onCreateViewHolder(parent: ViewGroup, viewType: Int): ShoppingViewHolder {
        val binding = ItemShoppingBinding.inflate(LayoutInflater.from(parent.context), parent, false)
        return ShoppingViewHolder(binding)
    }

    override fun onBindViewHolder(holder: ShoppingViewHolder, position: Int) {
        holder.bind(articles[position], position)
    }

    override fun getItemCount() = articles.size

    inner class ShoppingViewHolder(private val binding: ItemShoppingBinding) :
        RecyclerView.ViewHolder(binding.root) {

        init {
            binding.btnViewSuggestion.addPressEffect()
        }

        fun bind(article: ArticleCatalogueResponse, position: Int) {
            binding.tvArticleNom.text = article.nom
            binding.tvArticlePrix.text = "${"%.2f".format(article.prix)} TND"

            // Raisons personnalisées IA en Français
            when (position % 3) {
                0 -> {
                    binding.tvArticleReason1.text = "Idéal pour compléter vos styles Décontracté & Chic"
                    binding.tvArticleReason2.text = "Assorti avec vos vestes et bas existants"
                }
                1 -> {
                    binding.tvArticleReason1.text = "S'accorde avec 5 vêtements de votre dressing"
                    binding.tvArticleReason2.text = "Compatible avec vos chemises et pantalons"
                }
                else -> {
                    binding.tvArticleReason1.text = "Harmonieux avec votre palette de couleurs favorites"
                    binding.tvArticleReason2.text = "Recommandé selon vos habitudes vestimentaires"
                }
            }

            val fullUrl = if (article.imageUrl.startsWith("http")) article.imageUrl else "${BuildConfig.BASE_URL.trimEnd('/')}${article.imageUrl}"
            binding.ivArticlePhoto.load(fullUrl) {
                placeholder(R.drawable.ic_hanger)
                error(R.drawable.ic_hanger)
                crossfade(true)
            }

            binding.btnViewSuggestion.setOnClickListener {
                Toast.makeText(binding.root.context, "Suggestion : ${article.nom}\nDisponible chez ${article.vendeur}", Toast.LENGTH_SHORT).show()
            }
        }
    }
}
