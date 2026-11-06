package com.wearia.app.ui.dressing

import android.graphics.Color
import android.view.LayoutInflater
import android.view.ViewGroup
import androidx.core.content.ContextCompat
import androidx.recyclerview.widget.DiffUtil
import androidx.recyclerview.widget.ListAdapter
import androidx.recyclerview.widget.RecyclerView
import coil.load
import com.wearia.app.BuildConfig
import com.wearia.app.R
import com.wearia.app.data.remote.dto.VetementResponse
import com.wearia.app.databinding.ItemClothingBinding

/**
 * ClothingAdapter : RecyclerView Adapter pour la liste des vêtements du dressing (Maquette 6.jpg).
 */
class ClothingAdapter(
    private val onItemClick: (VetementResponse) -> Unit,
    private val onDeleteClick: (VetementResponse) -> Unit,
    private val onStatusClick: ((VetementResponse) -> Unit)? = null
) : ListAdapter<VetementResponse, ClothingAdapter.ClothingViewHolder>(ClothingDiffCallback()) {

    override fun onCreateViewHolder(parent: ViewGroup, viewType: Int): ClothingViewHolder {
        val binding = ItemClothingBinding.inflate(LayoutInflater.from(parent.context), parent, false)
        return ClothingViewHolder(binding)
    }

    override fun onBindViewHolder(holder: ClothingViewHolder, position: Int) {
        holder.bind(getItem(position))
    }

    inner class ClothingViewHolder(private val binding: ItemClothingBinding) :
        RecyclerView.ViewHolder(binding.root) {

        fun bind(clothing: VetementResponse) {
            binding.tvClothingName.text = clothing.nom ?: "Vêtement"
            val colorName = clothing.couleur?.nom ?: ""
            val coupeName = clothing.coupe ?: "Casual"
            binding.tvClothingType.text = if (colorName.isNotEmpty()) "$colorName · $coupeName" else coupeName
            binding.tvClothingCategoryBadge.text = clothing.typeVetement?.nom ?: "Vêtement"

            // Statut vêtement (Disponible / Sale)
            val isDirty = clothing.statut.equals("SALE", ignoreCase = true)
            if (isDirty) {
                binding.tvClothingStatus.text = "Sale"
                binding.tvClothingStatus.setTextColor(ContextCompat.getColor(binding.root.context, R.color.chipPinkText))
                binding.tvClothingStatus.setBackgroundResource(R.drawable.bg_badge_dirty)
            } else {
                binding.tvClothingStatus.text = "Disponible"
                binding.tvClothingStatus.setTextColor(ContextCompat.getColor(binding.root.context, R.color.chipGreenText))
                binding.tvClothingStatus.setBackgroundResource(R.drawable.bg_badge_available)
            }

            binding.tvClothingStatus.setOnClickListener {
                onStatusClick?.invoke(clothing) ?: onItemClick(clothing)
            }

            // Pastille de couleur
            val hex = clothing.couleur?.codeHex
            try {
                if (!hex.isNullOrEmpty()) {
                    binding.viewColorBadge.setBackgroundColor(Color.parseColor(hex))
                } else {
                    binding.viewColorBadge.setBackgroundColor(Color.GRAY)
                }
            } catch (e: Exception) {
                binding.viewColorBadge.setBackgroundColor(Color.GRAY)
            }

            // Image via Coil
            val photo = clothing.photoUrl ?: ""
            val fullUrl = when {
                photo.startsWith("http") -> photo
                photo.isNotEmpty() -> "${BuildConfig.BASE_URL.trimEnd('/')}/${photo.trimStart('/')}"
                else -> null
            }
            binding.ivClothingPhoto.load(fullUrl) {
                placeholder(R.drawable.ic_hanger)
                error(R.drawable.ic_hanger)
                crossfade(true)
            }

            binding.root.setOnClickListener { onItemClick(clothing) }
            binding.btnDelete.setOnClickListener { onDeleteClick(clothing) }
        }
    }

    class ClothingDiffCallback : DiffUtil.ItemCallback<VetementResponse>() {
        override fun areItemsTheSame(old: VetementResponse, new: VetementResponse) = old.id == new.id
        override fun areContentsTheSame(old: VetementResponse, new: VetementResponse) = old == new
    }
}
