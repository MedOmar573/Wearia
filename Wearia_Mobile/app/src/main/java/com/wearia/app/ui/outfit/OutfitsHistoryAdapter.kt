package com.wearia.app.ui.outfit

import android.view.LayoutInflater
import android.view.ViewGroup
import androidx.recyclerview.widget.DiffUtil
import androidx.recyclerview.widget.ListAdapter
import androidx.recyclerview.widget.RecyclerView
import coil.load
import com.wearia.app.R
import com.wearia.app.data.local.entity.TenueFavoriteEntity
import com.wearia.app.databinding.ItemSavedOutfitBinding
import com.wearia.app.utils.addPressEffect
import java.text.SimpleDateFormat
import java.util.*

/**
 * OutfitsHistoryAdapter : Liste des tenues favorites et passées modernisée Fresh Fashion Tech.
 */
class OutfitsHistoryAdapter(
    private val onItemClick: (TenueFavoriteEntity) -> Unit
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

        private val dateFormat = SimpleDateFormat("d MMMM", Locale.FRENCH)

        fun bind(outfit: TenueFavoriteEntity) {
            val occ = outfit.occasion.lowercase().replaceFirstChar { it.uppercase() }
            binding.tvSavedOccasion.text = occ
            binding.tvSavedDate.text = dateFormat.format(Date(outfit.cachedAt))
            binding.tvSavedStyle.text = if (occ.contains("Travail", ignoreCase = true) || occ.contains("Work", ignoreCase = true)) "Smart Casual" else "Casual"

            binding.ivOutfitThumb.load(R.drawable.ic_hanger) {
                crossfade(true)
            }

            binding.root.addPressEffect(0.97f)
            binding.root.setOnClickListener { onItemClick(outfit) }
        }
    }

    class OutfitDiffCallback : DiffUtil.ItemCallback<TenueFavoriteEntity>() {
        override fun areItemsTheSame(old: TenueFavoriteEntity, new: TenueFavoriteEntity) = old.id == new.id
        override fun areContentsTheSame(old: TenueFavoriteEntity, new: TenueFavoriteEntity) = old == new
    }
}
