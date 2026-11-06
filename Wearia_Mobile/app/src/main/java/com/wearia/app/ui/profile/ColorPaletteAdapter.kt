package com.wearia.app.ui.profile

import android.content.res.ColorStateList
import android.graphics.Color
import android.view.LayoutInflater
import android.view.View
import android.view.ViewGroup
import androidx.core.graphics.ColorUtils
import androidx.recyclerview.widget.RecyclerView
import com.wearia.app.data.remote.dto.CouleurResponse
import com.wearia.app.databinding.ItemColorPaletteBinding

class ColorPaletteAdapter(
    private val isAvoidMode: Boolean = false,
    private val onSelectionChanged: (Set<Int>) -> Unit = {}
) : RecyclerView.Adapter<ColorPaletteAdapter.ColorViewHolder>() {

    private val colors = mutableListOf<CouleurResponse>()
    private val selectedIds = mutableSetOf<Int>()

    fun setColors(newColors: List<CouleurResponse>) {
        colors.clear()
        colors.addAll(newColors)
        notifyDataSetChanged()
    }

    fun setSelectedIds(ids: Collection<Int>) {
        selectedIds.clear()
        selectedIds.addAll(ids)
        notifyDataSetChanged()
    }

    fun getSelectedIds(): Set<Int> = selectedIds

    override fun onCreateViewHolder(parent: ViewGroup, viewType: Int): ColorViewHolder {
        val binding = ItemColorPaletteBinding.inflate(LayoutInflater.from(parent.context), parent, false)
        return ColorViewHolder(binding)
    }

    override fun onBindViewHolder(holder: ColorViewHolder, position: Int) {
        holder.bind(colors[position])
    }

    override fun getItemCount(): Int = colors.size

    inner class ColorViewHolder(private val binding: ItemColorPaletteBinding) : RecyclerView.ViewHolder(binding.root) {
        fun bind(couleur: CouleurResponse) {
            val parsedColor = try {
                Color.parseColor(couleur.codeHex)
            } catch (e: Exception) {
                Color.GRAY
            }

            binding.viewColorCircle.backgroundTintList = ColorStateList.valueOf(parsedColor)

            val isSelected = selectedIds.contains(couleur.id)
            binding.tvCheck.visibility = if (isSelected) View.VISIBLE else View.GONE

            if (isAvoidMode) {
                binding.tvCheck.text = "✕"
            } else {
                binding.tvCheck.text = "✓"
            }

            // Calcul de la luminance pour un contraste lisible (texte noir sur fond clair, blanc sur fond sombre)
            val luminance = ColorUtils.calculateLuminance(parsedColor)
            val contrastColor = if (luminance > 0.6) Color.parseColor("#1F1E1D") else Color.WHITE
            binding.tvCheck.setTextColor(contrastColor)

            binding.cellColor.setOnClickListener {
                if (selectedIds.contains(couleur.id)) {
                    selectedIds.remove(couleur.id)
                } else {
                    selectedIds.add(couleur.id)
                }
                notifyItemChanged(adapterPosition)
                onSelectionChanged(selectedIds)
            }
        }
    }
}

