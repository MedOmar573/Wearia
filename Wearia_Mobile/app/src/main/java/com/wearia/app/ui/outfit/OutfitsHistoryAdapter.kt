package com.wearia.app.ui.outfit

import android.view.LayoutInflater
import android.view.View
import android.view.ViewGroup
import androidx.recyclerview.widget.DiffUtil
import androidx.recyclerview.widget.ListAdapter
import androidx.recyclerview.widget.RecyclerView
import coil.load
import com.google.gson.Gson
import com.google.gson.reflect.TypeToken
import com.wearia.app.BuildConfig
import com.wearia.app.R
import com.wearia.app.data.local.entity.TenueFavoriteEntity
import com.wearia.app.data.remote.dto.OutfitItemSimple
import com.wearia.app.databinding.ItemSavedOutfitBinding
import com.wearia.app.utils.addPressEffect

/**
 * OutfitsHistoryAdapter : Grille à 2 colonnes des combinaisons favorites.
 * Chaque carte affiche la composition des pièces côte à côte,
 * un bouton corbeille identique au dressing, et permet le clic pour ouvrir les détails
 * ou le long-clic pour supprimer.
 */
class OutfitsHistoryAdapter(
    private val onItemClick: (TenueFavoriteEntity) -> Unit,
    private val onDeleteClick: (TenueFavoriteEntity) -> Unit
) : ListAdapter<TenueFavoriteEntity, OutfitsHistoryAdapter.OutfitViewHolder>(OutfitDiffCallback()) {

    override fun onCreateViewHolder(parent: ViewGroup, viewType: Int): OutfitViewHolder {
        val binding = ItemSavedOutfitBinding.inflate(LayoutInflater.from(parent.context), parent, false)
        return OutfitViewHolder(binding)
    }

    override fun onBindViewHolder(holder: OutfitViewHolder, position: Int) {
        holder.bind(getItem(position))
    }

    inner class OutfitViewHolder(private val binding: ItemSavedOutfitBinding) :
        RecyclerView.ViewHolder(binding.root) {

        private val gson = Gson()
        private val baseUrl = BuildConfig.BASE_URL.trimEnd('/')

        fun bind(outfit: TenueFavoriteEntity) {
            val occ = outfit.occasion.lowercase().replaceFirstChar { it.uppercase() }
            binding.tvSavedOccasion.text = occ
            binding.tvSavedStyle.text = if (occ.contains("Travail", ignoreCase = true) || occ.contains("Work", ignoreCase = true)) "Smart Casual" else "Casual"

            val items = parseOutfitItems(outfit.itemsJson)
            binding.tvSavedPiecesCount.text = "${items.size} pièces"

            // Composition des photos des vêtements
            bindPiecesComposition(items)

            // Bouton Corbeille / Supprimer avec style dressing
            binding.btnDeleteOutfit.addPressEffect(0.85f)
            binding.btnDeleteOutfit.setOnClickListener {
                onDeleteClick(outfit)
            }

            // Long clic sur la carte pour supprimer
            binding.root.setOnLongClickListener {
                onDeleteClick(outfit)
                true
            }

            // Clic sur la carte -> redirection vers l'interface de détails
            binding.root.addPressEffect(0.98f)
            binding.root.setOnClickListener {
                onItemClick(outfit)
            }
            binding.ivPiece1.setOnClickListener { onItemClick(outfit) }
            binding.ivPiece2.setOnClickListener { onItemClick(outfit) }
            binding.ivPiece3.setOnClickListener { onItemClick(outfit) }
        }

        private fun bindPiecesComposition(items: List<OutfitItemSimple>) {
            val count = items.size
            if (count == 0) {
                binding.ivPiece1.visibility = View.VISIBLE
                binding.ivPiece2.visibility = View.GONE
                binding.ivPiece3.visibility = View.GONE
                binding.ivPiece1.load(R.drawable.ic_hanger)
                return
            }

            // Pièce 1 (ex: Haut)
            binding.ivPiece1.visibility = View.VISIBLE
            loadPieceImage(items.getOrNull(0)?.imageUrl, binding.ivPiece1)

            // Pièce 2 (ex: Bas / Pantalon)
            if (count >= 2) {
                binding.ivPiece2.visibility = View.VISIBLE
                loadPieceImage(items.getOrNull(1)?.imageUrl, binding.ivPiece2)
            } else {
                binding.ivPiece2.visibility = View.GONE
            }

            // Pièce 3 (ex: Chaussures / Accessoires)
            if (count >= 3) {
                binding.ivPiece3.visibility = View.VISIBLE
                loadPieceImage(items.getOrNull(2)?.imageUrl, binding.ivPiece3)
            } else {
                binding.ivPiece3.visibility = View.GONE
            }
        }

        private fun loadPieceImage(imageUrl: String?, imageView: android.widget.ImageView) {
            val fullUrl = imageUrl?.let {
                if (it.startsWith("http")) it else "$baseUrl$it"
            }
            if (!fullUrl.isNullOrBlank()) {
                imageView.load(fullUrl) {
                    crossfade(true)
                    placeholder(R.drawable.bg_clothing_item_preview)
                    error(R.drawable.ic_hanger)
                }
            } else {
                imageView.load(R.drawable.ic_hanger) {
                    crossfade(true)
                }
            }
        }

        private fun parseOutfitItems(json: String?): List<OutfitItemSimple> {
            if (json.isNullOrBlank()) return emptyList()
            return try {
                val type = object : TypeToken<List<OutfitItemSimple>>() {}.type
                val parsed: List<OutfitItemSimple>? = gson.fromJson(json, type)
                if (parsed != null && parsed.isNotEmpty() && parsed.firstOrNull()?.name != null) {
                    parsed
                } else {
                    emptyList()
                }
            } catch (e: Exception) {
                try {
                    val typeStr = object : TypeToken<List<String>>() {}.type
                    val names: List<String>? = gson.fromJson(json, typeStr)
                    names?.mapIndexed { index, name ->
                        OutfitItemSimple(id = index, name = name, category = null, color = null, imageUrl = null)
                    } ?: emptyList()
                } catch (e2: Exception) {
                    emptyList()
                }
            }
        }
    }

    class OutfitDiffCallback : DiffUtil.ItemCallback<TenueFavoriteEntity>() {
        override fun areItemsTheSame(old: TenueFavoriteEntity, new: TenueFavoriteEntity) = old.id == new.id
        override fun areContentsTheSame(old: TenueFavoriteEntity, new: TenueFavoriteEntity) = old == new
    }
}
