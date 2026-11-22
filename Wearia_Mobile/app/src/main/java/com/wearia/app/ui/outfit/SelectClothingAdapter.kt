package com.wearia.app.ui.outfit

import android.view.LayoutInflater
import android.view.View
import android.view.ViewGroup
import androidx.recyclerview.widget.RecyclerView
import coil.load
import com.wearia.app.BuildConfig
import com.wearia.app.R
import com.wearia.app.data.local.entity.VetementCacheEntity
import com.wearia.app.databinding.ItemSelectClothingBinding
import com.wearia.app.utils.addPressEffect

/**
 * SelectClothingAdapter : Adaptateur polyvalent pour la sélection de vêtements
 * - Mode mono-sélection : pour ajouter une pièce à une tenue existante
 * - Mode multi-sélection : pour créer une combinaison favorite personnalisée
 */
class SelectClothingAdapter(
    private val isMultiSelect: Boolean = false,
    private val onItemSelected: (VetementCacheEntity, Boolean) -> Unit
) : RecyclerView.Adapter<SelectClothingAdapter.ViewHolder>() {

    private val items = mutableListOf<VetementCacheEntity>()
    private val selectedIds = mutableSetOf<Int>()

    fun submitList(newItems: List<VetementCacheEntity>) {
        items.clear()
        items.addAll(newItems)
        notifyDataSetChanged()
    }

    fun getSelectedItems(): List<VetementCacheEntity> {
        return items.filter { selectedIds.contains(it.id) }
    }

    override fun onCreateViewHolder(parent: ViewGroup, viewType: Int): ViewHolder {
        val binding = ItemSelectClothingBinding.inflate(LayoutInflater.from(parent.context), parent, false)
        return ViewHolder(binding)
    }

    override fun getItemCount(): Int = items.size

    override fun onBindViewHolder(holder: ViewHolder, position: Int) {
        holder.bind(items[position])
    }

    inner class ViewHolder(private val binding: ItemSelectClothingBinding) : RecyclerView.ViewHolder(binding.root) {
        private val baseUrl = BuildConfig.BASE_URL.trimEnd('/')

        fun bind(clothing: VetementCacheEntity) {
            binding.tvClothingName.text = clothing.nom
            binding.tvClothingCategory.text = clothing.categorie
            binding.tvClothingColor.text = clothing.couleur

            val fullUrl = if (clothing.photoUrl.startsWith("http")) clothing.photoUrl else "$baseUrl${clothing.photoUrl}"
            binding.ivClothingImg.load(fullUrl) {
                crossfade(true)
                placeholder(R.drawable.bg_clothing_item_preview)
                error(R.drawable.ic_hanger)
            }

            if (isMultiSelect) {
                binding.cbSelect.visibility = View.VISIBLE
                binding.ivAddArrow.visibility = View.GONE
                val isSelected = selectedIds.contains(clothing.id)
                binding.cbSelect.isChecked = isSelected
                binding.root.strokeColor = if (isSelected) {
                    binding.root.context.getColor(R.color.colorPrimary)
                } else {
                    binding.root.context.getColor(R.color.colorBorder)
                }
                binding.root.strokeWidth = if (isSelected) 2 else 1
            } else {
                binding.cbSelect.visibility = View.GONE
                binding.ivAddArrow.visibility = View.VISIBLE
                binding.root.strokeWidth = 1
                binding.root.strokeColor = binding.root.context.getColor(R.color.colorBorder)
            }

            binding.root.addPressEffect(0.98f)
            binding.root.setOnClickListener {
                if (isMultiSelect) {
                    val wasSelected = selectedIds.contains(clothing.id)
                    if (wasSelected) {
                        selectedIds.remove(clothing.id)
                    } else {
                        selectedIds.add(clothing.id)
                    }
                    val pos = adapterPosition
                    if (pos != RecyclerView.NO_POSITION) {
                        notifyItemChanged(pos)
                    }
                    onItemSelected(clothing, !wasSelected)
                } else {
                    onItemSelected(clothing, true)
                }
            }
        }
    }
}
