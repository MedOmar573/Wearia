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

/**
 * ShoppingAdapter : Suggestions de pièces manquantes (Maquette 10.jpg).
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

        fun bind(article: ArticleCatalogueResponse, position: Int) {
            binding.tvArticleNom.text = article.nom
            binding.tvArticlePrix.text = "${"%.2f".format(article.prix)} TND"

            // Raisons personnalisées IA (Maquette 10.jpg)
            when (position % 3) {
                0 -> {
                    binding.tvArticleReason1.text = "Matches your casual and elegant styles"
                    binding.tvArticleReason2.text = "Your blue blazer and chinos"
                }
                1 -> {
                    binding.tvArticleReason1.text = "Works with 5 items in your wardrobe"
                    binding.tvArticleReason2.text = "Your navy jacket and white shirt"
                }
                else -> {
                    binding.tvArticleReason1.text = "Suitable for your preferred colors"
                    binding.tvArticleReason2.text = "Your dark trousers and tees"
                }
            }

            val fullUrl = if (article.imageUrl.startsWith("http")) article.imageUrl else "${BuildConfig.BASE_URL.trimEnd('/')}${article.imageUrl}"
            binding.ivArticlePhoto.load(fullUrl) {
                placeholder(R.drawable.ic_hanger)
                error(R.drawable.ic_hanger)
                crossfade(true)
            }

            binding.btnViewSuggestion.setOnClickListener {
                Toast.makeText(binding.root.context, "Suggestion for ${article.nom}: Available at ${article.vendeur}", Toast.LENGTH_SHORT).show()
            }
        }
    }
}
