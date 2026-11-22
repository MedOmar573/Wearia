package com.wearia.app.ui.outfit

import android.os.Bundle
import android.view.LayoutInflater
import android.view.View
import android.view.ViewGroup
import android.widget.Toast
import androidx.fragment.app.Fragment
import androidx.fragment.app.viewModels
import androidx.lifecycle.lifecycleScope
import androidx.navigation.fragment.findNavController
import coil.load
import com.google.android.material.bottomsheet.BottomSheetDialog
import com.google.android.material.card.MaterialCardView
import com.google.android.material.chip.Chip
import com.google.android.material.dialog.MaterialAlertDialogBuilder
import com.wearia.app.BuildConfig
import com.wearia.app.R
import com.wearia.app.WeariaApplication
import com.wearia.app.data.local.entity.TenueFavoriteEntity
import com.wearia.app.data.remote.dto.RecommendationResponse
import com.wearia.app.databinding.DialogManualWeatherBinding
import com.wearia.app.databinding.DialogOutfitFeedbackBinding
import com.wearia.app.databinding.DialogSelectOccasionBinding
import com.wearia.app.databinding.FragmentOutfitRecommendationBinding
import com.wearia.app.utils.Resource
import com.wearia.app.utils.addPressEffect
import com.wearia.app.viewmodel.OutfitViewModel
import kotlinx.coroutines.launch

/**
 * OutfitRecommendationFragment : Écran de recommandation de tenue modernisé Fresh Fashion Tech.
 */
class OutfitRecommendationFragment : Fragment() {

    private var _binding: FragmentOutfitRecommendationBinding? = null
    private val binding get() = _binding!!
    private val viewModel: OutfitViewModel by viewModels { OutfitViewModel.Factory() }

    private var currentOutfitId: Int? = null
    private var isFavorite: Boolean = false
    private var variationIndex: Int = 0
    private var swapCounter: Int = 0
    private var currentOutfitItems: List<com.wearia.app.data.remote.dto.OutfitItemSimple> = emptyList()

    override fun onCreateView(inflater: LayoutInflater, container: ViewGroup?, savedInstanceState: Bundle?): View {
        _binding = FragmentOutfitRecommendationBinding.inflate(inflater, container, false)
        return binding.root
    }

    override fun onViewCreated(view: View, savedInstanceState: Bundle?) {
        super.onViewCreated(view, savedInstanceState)

        // Effets tactiles
        binding.btnBack.addPressEffect()
        binding.btnLikeOutfit.addPressEffect()
        binding.btnTryAnother.addPressEffect()
        binding.btnChangeItem.addPressEffect()
        binding.btnManualWeather.addPressEffect()
        binding.btnRecommendationAddClothing.addPressEffect()

        binding.btnBack.setOnClickListener {
            findNavController().popBackStack()
        }

        // Charger la première recommandation optimale
        generateRecommendation()

        // Bouton J'aime cette tenue
        binding.btnLikeOutfit.setOnClickListener {
            currentOutfitId?.let { id ->
                if (!isFavorite) {
                    showSelectOccasionDialog(id)
                } else {
                    isFavorite = false
                    viewModel.toggleFavorite(id, false)
                    binding.btnLikeOutfit.text = "J'aime cette tenue"
                    Toast.makeText(requireContext(), "Retiré des favoris", Toast.LENGTH_SHORT).show()
                }
            }
        }

        // Bouton Autre idée / Autre tenue
        binding.btnTryAnother.setOnClickListener {
            variationIndex++
            val excludeIds = currentOutfitItems.map { it.id }
            Toast.makeText(requireContext(), "Recherche d'une autre combinaison...", Toast.LENGTH_SHORT).show()
            binding.layoutRecommendationDetails.animate().alpha(0.3f).scaleX(0.96f).scaleY(0.96f).setDuration(180).withEndAction {
                viewModel.generateRecommendation(
                    variation = variationIndex,
                    excludeItemIds = if (excludeIds.isNotEmpty()) excludeIds else null
                )
            }
        }

        // Bouton Changer une pièce
        binding.btnChangeItem.setOnClickListener {
            showChangePieceDialog()
        }

        // Bouton saisie météo manuelle (démonstration)
        binding.btnManualWeather.setOnClickListener {
            showManualWeatherDialog()
        }

        binding.btnRecommendationAddClothing.setOnClickListener {
            try {
                findNavController().navigate(R.id.action_outfit_to_camera)
            } catch (e: Exception) {
                findNavController().navigateUp()
            }
        }

        observeRecommendation()
    }

    private fun showChangePieceDialog() {
        if (currentOutfitItems.isEmpty()) {
            Toast.makeText(requireContext(), "Aucune pièce dans la tenue actuelle.", Toast.LENGTH_SHORT).show()
            return
        }

        val itemLabels = currentOutfitItems.map { item ->
            val icon = when {
                item.category?.contains("haut", true) == true || item.name.contains("pull", true) || item.name.contains("chemise", true) || item.name.contains("t-shirt", true) -> "👕"
                item.category?.contains("bas", true) == true || item.name.contains("pantalon", true) || item.name.contains("jean", true) -> "👖"
                item.category?.contains("robe", true) == true -> "👗"
                item.category?.contains("chauss", true) == true || item.name.contains("basket", true) -> "👟"
                item.category?.contains("veste", true) == true || item.name.contains("manteau", true) -> "🧥"
                else -> "✨"
            }
            "$icon ${item.category ?: "Pièce"} — ${item.name}"
        }.toTypedArray()

        MaterialAlertDialogBuilder(requireContext())
            .setTitle("Quelle pièce souhaitez-vous changer ?")
            .setItems(itemLabels) { _, which ->
                if (which in currentOutfitItems.indices) {
                    val targetItem = currentOutfitItems[which]
                    val catName = targetItem.category?.lowercase() ?: "haut"
                    swapCounter++
                    Toast.makeText(requireContext(), "Remplacement de '${targetItem.name}'...", Toast.LENGTH_SHORT).show()
                    binding.layoutRecommendationDetails.animate().alpha(0.4f).scaleX(0.97f).scaleY(0.97f).setDuration(180).withEndAction {
                        viewModel.generateRecommendation(
                            swapCategory = catName,
                            currentItemIds = currentOutfitItems.map { it.id },
                            variation = swapCounter
                        )
                    }
                }
            }
            .setNegativeButton("Annuler", null)
            .show()
    }

    private fun generateRecommendation(manualTemp: Float? = null, manualPrecip: Boolean? = null) {
        viewModel.generateRecommendation(
            manualTemp = manualTemp,
            manualPrecip = manualPrecip,
            variation = variationIndex
        )
    }

    private fun observeRecommendation() {
        viewModel.favoriteState.observe(viewLifecycleOwner) { state ->
            if (state is Resource.Error) {
                Toast.makeText(requireContext(), state.message, Toast.LENGTH_SHORT).show()
                if (state.message.contains("existe déjà", ignoreCase = true)) {
                    isFavorite = true
                    binding.btnLikeOutfit.text = "Tenue sauvegardée !"
                } else {
                    isFavorite = false
                    binding.btnLikeOutfit.text = "J'aime cette tenue"
                }
            }
        }

        viewModel.recommendationState.observe(viewLifecycleOwner) { state ->
            if (state == null) return@observe
            when (state) {
                is Resource.Loading -> {
                    binding.progressBar.visibility = View.VISIBLE
                    binding.layoutRecommendationEmpty.visibility = View.GONE
                    binding.layoutRecommendationDetails.visibility = View.GONE
                }
                is Resource.Success -> {
                    binding.progressBar.visibility = View.GONE
                    if (state.data.items.isNotEmpty()) {
                        binding.layoutRecommendationEmpty.visibility = View.GONE
                        binding.layoutRecommendationDetails.visibility = View.VISIBLE
                        displayRecommendation(state.data)
                    } else {
                        binding.layoutRecommendationEmpty.visibility = View.VISIBLE
                        binding.layoutRecommendationDetails.visibility = View.GONE
                    }
                }
                is Resource.Error -> {
                    binding.progressBar.visibility = View.GONE
                    binding.layoutRecommendationEmpty.visibility = View.VISIBLE
                    binding.layoutRecommendationDetails.visibility = View.GONE
                    if (state.message.isNotEmpty()) {
                        binding.tvEmptyRecommendationDesc.text = state.message
                    }
                }
            }
        }
    }

    private fun displayRecommendation(data: RecommendationResponse) {
        currentOutfitId = data.outfitId
        currentOutfitItems = data.items
        isFavorite = false
        binding.btnLikeOutfit.text = "J'aime cette tenue"
        binding.layoutRecommendationDetails.animate().alpha(1f).scaleX(1f).scaleY(1f).setDuration(250).start()

        // Titre et occasion
        val occasionName = data.occasion.lowercase().replaceFirstChar { it.uppercaseChar() }
        binding.tvOutfitTitle.text = "Style Harmonieux • $occasionName"
        binding.tvOccasion.text = "Occasion — $occasionName"

        // Météo
        val temp = data.temperature?.let { "${it.toInt()}°C" } ?: "19°C"
        val meteo = when (data.weather?.lowercase()) {
            "sunny" -> "Ensoleillé"
            "rain", "rainy" -> "Pluvieux"
            "cloudy" -> "Nuageux"
            else -> data.weather ?: "Agréable"
        }
        binding.tvWeather.text = "$temp — $meteo"

        // Couleurs
        val colorsList = data.items.mapNotNull { it.color }.distinct().take(3)
        val colorsText = if (colorsList.isNotEmpty()) colorsList.joinToString(" / ") else "Blanc / Bleu Marine / Noir"
        binding.tvColorsInfo.text = "Palette — $colorsText"

        // Répartition des pièces dans le collage
        val baseUrl = BuildConfig.BASE_URL.trimEnd('/')
        var topLoaded = false
        var bottomLoaded = false
        var shoesLoaded = false
        var jacketLoaded = false

        binding.ivPieceTop.setImageDrawable(null)
        binding.ivPieceJacket.setImageDrawable(null)
        binding.ivPieceBottom.setImageDrawable(null)
        binding.ivPieceShoes.setImageDrawable(null)

        data.items.forEach { item ->
            val cat = item.category?.lowercase() ?: ""
            val fullImgUrl = item.imageUrl?.let { if (it.startsWith("http")) it else "$baseUrl$it" }

            when {
                (cat.contains("haut") || cat.contains("chemise") || cat.contains("top") || cat.contains("t-shirt") || cat.contains("polo") || cat.contains("pull") || cat.contains("sweat")) && !topLoaded -> {
                    fullImgUrl?.let {
                        binding.ivPieceTop.load(it) { crossfade(true) }
                        topLoaded = true
                    }
                }
                (cat.contains("bas") || cat.contains("pantalon") || cat.contains("jean") || cat.contains("short")) && !bottomLoaded -> {
                    fullImgUrl?.let {
                        binding.ivPieceBottom.load(it) { crossfade(true) }
                        bottomLoaded = true
                    }
                }
                (cat.contains("chaussure") || cat.contains("sneaker") || cat.contains("shoe") || cat.contains("basket") || cat.contains("derbie")) && !shoesLoaded -> {
                    fullImgUrl?.let {
                        binding.ivPieceShoes.load(it) { crossfade(true) }
                        shoesLoaded = true
                    }
                }
                (cat.contains("veste") || cat.contains("manteau") || cat.contains("jacket") || cat.contains("blazer") || cat.contains("bomber")) && !jacketLoaded -> {
                    fullImgUrl?.let {
                        binding.ivPieceJacket.load(it) { crossfade(true) }
                        jacketLoaded = true
                    }
                }
                else -> {
                    if (!topLoaded) {
                        fullImgUrl?.let {
                            binding.ivPieceTop.load(it) { crossfade(true) }
                            topLoaded = true
                        }
                    }
                }
            }
        }
    }

    private fun showManualWeatherDialog() {
        val dialogBinding = DialogManualWeatherBinding.inflate(layoutInflater)
        MaterialAlertDialogBuilder(requireContext())
            .setTitle("Simulation Météo")
            .setView(dialogBinding.root)
            .setPositiveButton("Simuler") { _, _ ->
                val temp = dialogBinding.etManualTemp.text.toString().toFloatOrNull() ?: 12f
                val precip = dialogBinding.cbManualPrecip.isChecked
                generateRecommendation(manualTemp = temp, manualPrecip = precip)
            }
            .setNegativeButton("Annuler", null)
            .show()
    }

    private fun showSelectOccasionDialog(outfitId: Int) {
        val currentIds = currentOutfitItems.map { it.id }.toSet()
        viewLifecycleOwner.lifecycleScope.launch {
            val uid = WeariaApplication.instance.sessionManager.getUserId()
            if (currentIds.isNotEmpty() && uid > 0) {
                val allFavs = WeariaApplication.instance.database.outfitDao().getFavoritesListForUser(uid)
                val alreadyExists = allFavs.any { fav ->
                    val itemIds = parseOutfitItemIds(fav.itemsJson)
                    itemIds.isNotEmpty() && itemIds == currentIds
                }
                if (alreadyExists) {
                    Toast.makeText(requireContext(), "Cette combinaison existe déjà dans vos favoris", Toast.LENGTH_SHORT).show()
                    return@launch
                }
            }

            val dialog = BottomSheetDialog(requireContext())
            val sheetBinding = DialogSelectOccasionBinding.inflate(layoutInflater)
            dialog.setContentView(sheetBinding.root)

            sheetBinding.tvOccasionDialogTitle.text = "Type de combinaison à ajouter"

            sheetBinding.btnConfirmOccasion.setOnClickListener {
                val selectedOccasion = when (sheetBinding.chipGroupOccasionsDialog.checkedChipId) {
                    R.id.chip_dialog_university -> "Université"
                    R.id.chip_dialog_work -> "Travail"
                    R.id.chip_dialog_daily -> "Quotidien"
                    R.id.chip_dialog_events -> "Événements"
                    else -> "Sortie"
                }
                dialog.dismiss()
                saveOutfitWithOccasion(outfitId, selectedOccasion)
            }

            sheetBinding.btnCancelOccasion.setOnClickListener {
                dialog.dismiss()
            }

            dialog.show()
        }
    }

    private fun saveOutfitWithOccasion(outfitId: Int, selectedOccasion: String) {
        isFavorite = true
        binding.btnLikeOutfit.text = "Tenue sauvegardée !"
        viewModel.toggleFavorite(outfitId, true)

        viewLifecycleOwner.lifecycleScope.launch {
            val uid = WeariaApplication.instance.sessionManager.getUserId()
            if (uid > 0) {
                WeariaApplication.instance.database.outfitDao().updateFavoriteOccasionForUser(outfitId, uid, selectedOccasion)
            }
            try {
                val token = WeariaApplication.instance.sessionManager.getAuthHeader()
                WeariaApplication.instance.apiService.updateOutfit(token, outfitId, estFavorite = true, occasion = selectedOccasion)
            } catch (e: Exception) {
                // Silencieux
            }
            Toast.makeText(requireContext(), "Combinaison ajoutée aux favoris ($selectedOccasion) !", Toast.LENGTH_SHORT).show()
            showFeedbackBottomSheet(outfitId)
        }
    }

    private fun showFeedbackBottomSheet(outfitId: Int) {
        val bottomSheet = BottomSheetDialog(requireContext())
        val feedbackBinding = DialogOutfitFeedbackBinding.inflate(layoutInflater)
        bottomSheet.setContentView(feedbackBinding.root)

        var selectedReaction = "LOVE"
        fun updateReactionUI(selectedCard: MaterialCardView) {
            val unselectedBg = resources.getColor(R.color.colorSurfaceCard, null)
            val selectedBg = resources.getColor(R.color.badge_haut_bg, null)
            val primaryColor = resources.getColor(R.color.colorPrimary, null)
            val borderColor = resources.getColor(R.color.colorBorder, null)

            listOf(
                feedbackBinding.cardReactionLove,
                feedbackBinding.cardReactionOkay,
                feedbackBinding.cardReactionNotForMe
            ).forEach { card ->
                card.setCardBackgroundColor(unselectedBg)
                card.strokeColor = borderColor
                card.strokeWidth = 1
            }

            selectedCard.setCardBackgroundColor(selectedBg)
            selectedCard.strokeColor = primaryColor
            selectedCard.strokeWidth = 2
        }

        updateReactionUI(feedbackBinding.cardReactionLove)

        feedbackBinding.cardReactionLove.setOnClickListener {
            selectedReaction = "LOVE"
            updateReactionUI(feedbackBinding.cardReactionLove)
        }
        feedbackBinding.cardReactionOkay.setOnClickListener {
            selectedReaction = "OKAY"
            updateReactionUI(feedbackBinding.cardReactionOkay)
        }
        feedbackBinding.cardReactionNotForMe.setOnClickListener {
            selectedReaction = "NOT_FOR_ME"
            updateReactionUI(feedbackBinding.cardReactionNotForMe)
        }

        feedbackBinding.btnSaveFeedback.setOnClickListener {
            val selectedReasons = mutableListOf<String>()
            val group = feedbackBinding.chipGroupFeedbackReasons
            for (i in 0 until group.childCount) {
                val chip = group.getChildAt(i) as? Chip
                if (chip?.isChecked == true) {
                    selectedReasons.add(chip.text.toString())
                }
            }

            val appreciation = when (selectedReaction) {
                "LOVE" -> "AIME"
                "OKAY" -> "MOYEN"
                else -> "PAS_POUR_MOI"
            }
            val commentaire = if (selectedReasons.isNotEmpty()) selectedReasons.joinToString(", ") else null
            viewModel.submitFeedback(outfitId, appreciation, commentaire)
            Toast.makeText(requireContext(), "Merci pour votre retour !", Toast.LENGTH_SHORT).show()
            bottomSheet.dismiss()
        }

        bottomSheet.show()
    }

    private fun parseOutfitItemIds(json: String?): Set<Int> {
        if (json.isNullOrBlank()) return emptySet()
        return try {
            val type = object : com.google.gson.reflect.TypeToken<List<com.wearia.app.data.remote.dto.OutfitItemSimple>>() {}.type
            val items: List<com.wearia.app.data.remote.dto.OutfitItemSimple> = com.google.gson.Gson().fromJson(json, type)
            items.map { it.id }.toSet()
        } catch (e: Exception) {
            emptySet()
        }
    }

    override fun onDestroyView() {
        super.onDestroyView()
        _binding = null
    }
}
