package com.wearia.app.ui.outfit

import android.os.Bundle
import android.view.LayoutInflater
import android.view.View
import android.view.ViewGroup
import android.widget.Toast
import androidx.fragment.app.Fragment
import androidx.fragment.app.viewModels
import androidx.navigation.fragment.findNavController
import coil.load
import com.google.android.material.bottomsheet.BottomSheetDialog
import com.google.android.material.card.MaterialCardView
import com.google.android.material.chip.Chip
import com.wearia.app.BuildConfig
import com.wearia.app.R
import com.wearia.app.data.remote.dto.RecommendationResponse
import com.wearia.app.databinding.FragmentOutfitRecommendationBinding
import com.wearia.app.utils.Resource
import com.wearia.app.viewmodel.OutfitViewModel

/**
 * OutfitRecommendationFragment : Écran principal de recommandation de tenue (Maquette 8.jpg & 9.jpg).
 */
class OutfitRecommendationFragment : Fragment() {

    private var _binding: FragmentOutfitRecommendationBinding? = null
    private val binding get() = _binding!!
    private val viewModel: OutfitViewModel by viewModels { OutfitViewModel.Factory() }

    private var currentOutfitId: Int? = null
    private var isFavorite: Boolean = false

    override fun onCreateView(inflater: LayoutInflater, container: ViewGroup?, savedInstanceState: Bundle?): View {
        _binding = FragmentOutfitRecommendationBinding.inflate(inflater, container, false)
        return binding.root
    }

    override fun onViewCreated(view: View, savedInstanceState: Bundle?) {
        super.onViewCreated(view, savedInstanceState)

        // Charger la recommandation
        generateRecommendation()

        // Bouton Like this outfit (8.jpg) -> Sauvegarde en favori et ouvre le feedback (9.jpg)
        binding.btnLikeOutfit.setOnClickListener {
            currentOutfitId?.let { id ->
                isFavorite = !isFavorite
                viewModel.toggleFavorite(id, isFavorite)
                binding.btnLikeOutfit.text = if (isFavorite) "🖤  Liked" else "🤍  Like this outfit"
                showFeedbackBottomSheet(id)
            }
        }

        // Bouton Try another (8.jpg)
        binding.btnTryAnother.setOnClickListener {
            generateRecommendation()
        }

        // Bouton Change one item (8.jpg)
        binding.btnChangeItem.setOnClickListener {
            generateRecommendation()
            Toast.makeText(requireContext(), "Alternative piece loaded", Toast.LENGTH_SHORT).show()
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

    private fun generateRecommendation(manualTemp: Float? = null, manualPrecip: Boolean? = null) {
        viewModel.generateRecommendation(manualTemp = manualTemp, manualPrecip = manualPrecip)
    }

    private fun observeRecommendation() {
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
        isFavorite = false
        binding.btnLikeOutfit.text = "🤍  Like this outfit"

        // Titre et occasion (8.jpg)
        val occasionName = data.occasion.lowercase().replaceFirstChar { it.uppercaseChar() }
        binding.tvOutfitTitle.text = "Casual • $occasionName"
        binding.tvOccasion.text = "Occasion — $occasionName"

        // Météo
        val temp = data.temperature?.let { "${it.toInt()}°C" } ?: "19°C"
        val meteo = data.weather ?: "Sunny"
        binding.tvWeather.text = "$temp — $meteo"

        // Couleurs
        val colorsList = data.items.mapNotNull { it.color }.distinct().take(3)
        val colorsText = if (colorsList.isNotEmpty()) colorsList.joinToString(" / ") else "White / Navy / Black"
        binding.tvColorsInfo.text = "Colors — $colorsText"

        // Répartition des pièces dans le collage (8.jpg)
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
                    } else if (!jacketLoaded) {
                        fullImgUrl?.let {
                            binding.ivPieceJacket.load(it) { crossfade(true) }
                            jacketLoaded = true
                        }
                    }
                }
            }
        }

        binding.ivPieceTop.visibility = if (topLoaded) View.VISIBLE else View.INVISIBLE
        binding.ivPieceBottom.visibility = if (bottomLoaded) View.VISIBLE else View.INVISIBLE
        binding.ivPieceShoes.visibility = if (shoesLoaded) View.VISIBLE else View.INVISIBLE
        binding.ivPieceJacket.visibility = if (jacketLoaded) View.VISIBLE else View.GONE
    }

    /**
     * Ouvre la modale de feedback "How was this outfit?" (Maquette 9.jpg)
     */
    private fun showFeedbackBottomSheet(outfitId: Int) {
        val bottomSheet = BottomSheetDialog(requireContext())
        val view = layoutInflater.inflate(R.layout.dialog_outfit_feedback, null)
        bottomSheet.setContentView(view)

        var selectedReaction = "AIME"
        val cardLove = view.findViewById<MaterialCardView>(R.id.card_reaction_love)
        val cardOkay = view.findViewById<MaterialCardView>(R.id.card_reaction_okay)
        val cardNotForMe = view.findViewById<MaterialCardView>(R.id.card_reaction_not_for_me)
        val btnSaveFeedback = view.findViewById<View>(R.id.btn_save_feedback)

        cardLove?.setOnClickListener {
            selectedReaction = "AIME"
            cardLove.strokeWidth = 4
            cardOkay?.strokeWidth = 1
            cardNotForMe?.strokeWidth = 1
        }
        cardOkay?.setOnClickListener {
            selectedReaction = "MOYEN"
            cardLove?.strokeWidth = 1
            cardOkay.strokeWidth = 4
            cardNotForMe?.strokeWidth = 1
        }
        cardNotForMe?.setOnClickListener {
            selectedReaction = "PAS_POUR_MOI"
            cardLove?.strokeWidth = 1
            cardOkay?.strokeWidth = 1
            cardNotForMe.strokeWidth = 4
        }

        btnSaveFeedback?.setOnClickListener {
            viewModel.submitFeedback(outfitId, selectedReaction)
            Toast.makeText(requireContext(), "Feedback saved! StyleAI will adapt.", Toast.LENGTH_SHORT).show()
            bottomSheet.dismiss()
        }

        bottomSheet.show()
    }

    private fun showManualWeatherDialog() {
        val dialogView = LayoutInflater.from(requireContext()).inflate(R.layout.dialog_manual_weather, null)
        val etTemp = dialogView.findViewById<android.widget.EditText>(R.id.et_manual_temp)
        val cbPrecip = dialogView.findViewById<android.widget.CheckBox>(R.id.cb_manual_precip)

        val dialog = android.app.AlertDialog.Builder(requireContext())
            .setTitle("Manual Weather Input")
            .setMessage("Set temperature and precipitation for test.")
            .setView(dialogView)
            .setPositiveButton("Generate") { d, _ ->
                val temp = etTemp.text.toString().toFloatOrNull() ?: 19f
                val precip = cbPrecip.isChecked
                generateRecommendation(manualTemp = temp, manualPrecip = precip)
                d.dismiss()
            }
            .setNegativeButton("Cancel", null)
            .create()
        dialog.show()
    }

    override fun onDestroyView() {
        super.onDestroyView()
        _binding = null
    }
}
