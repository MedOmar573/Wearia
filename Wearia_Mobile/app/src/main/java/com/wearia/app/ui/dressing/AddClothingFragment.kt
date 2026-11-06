package com.wearia.app.ui.dressing

import android.graphics.Color
import android.net.Uri
import android.os.Bundle
import android.view.LayoutInflater
import android.view.View
import android.view.ViewGroup
import android.widget.AdapterView
import android.widget.ArrayAdapter
import android.widget.Toast
import androidx.activity.result.contract.ActivityResultContracts
import androidx.fragment.app.Fragment
import androidx.fragment.app.activityViewModels
import androidx.fragment.app.viewModels
import androidx.lifecycle.lifecycleScope
import androidx.navigation.fragment.findNavController
import coil.load
import com.wearia.app.BuildConfig
import com.wearia.app.R
import com.wearia.app.data.remote.dto.CouleurResponse
import com.wearia.app.data.remote.dto.TypeVetementResponse
import com.wearia.app.data.remote.dto.VetementCreateRequest
import com.wearia.app.databinding.FragmentAddClothingBinding
import com.wearia.app.utils.ImageUtils
import com.wearia.app.utils.Resource
import com.wearia.app.viewmodel.ClothingViewModel
import com.wearia.app.viewmodel.ProfileViewModel
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext
import java.io.File

/**
 * AddClothingFragment : Écran d'ajout et confirmation IA (Maquette 7.jpg).
 * Supporte :
 * 1. Prise de photo directe (CameraX)
 * 2. Importation depuis la galerie
 * 3. Prédiction IA en direct (KNN + OpenCV)
 * 4. Ajustement des dropdowns Category, Color, Style, Fit
 * 5. Ajout au dressing
 */
class AddClothingFragment : Fragment() {

    private var _binding: FragmentAddClothingBinding? = null
    private val binding get() = _binding!!

    private val clothingViewModel: ClothingViewModel by activityViewModels { ClothingViewModel.Factory() }
    private val profileViewModel: ProfileViewModel by viewModels { ProfileViewModel.Factory() }

    private var imageUrl: String = ""
    private var predictedCategory: String = ""
    private var predictedColor: String = ""
    private var suggestedTypeId: Int = -1
    private var suggestedColorId: Int = -1
    private var detectedMatiere: String? = null
    private var detectedSaison: String = "TOUTE_SAISON"
    private var detectedEstThermique: Boolean = false
    private var detectedEstImpermeable: Boolean = false
    private var detectedStyleId: Int? = null

    private var availableTypes: List<TypeVetementResponse> = emptyList()
    private var availableColors: List<CouleurResponse> = emptyList()

    // Sélecteur de galerie
    private val galleryLauncher =
        registerForActivityResult(ActivityResultContracts.GetContent()) { uri: Uri? ->
            uri?.let { handleGalleryImage(it) }
        }

    override fun onCreateView(inflater: LayoutInflater, container: ViewGroup?, savedInstanceState: Bundle?): View {
        _binding = FragmentAddClothingBinding.inflate(inflater, container, false)
        return binding.root
    }

    override fun onViewCreated(view: View, savedInstanceState: Bundle?) {
        super.onViewCreated(view, savedInstanceState)

        // Récupérer les arguments passés depuis CameraFragment s'il y en a
        arguments?.let { args ->
            imageUrl = args.getString("imageUrl", "")
            predictedCategory = args.getString("category", "")
            predictedColor = args.getString("color", "")
            suggestedTypeId = args.getInt("suggestedTypeId", -1)
            suggestedColorId = args.getInt("suggestedColorId", -1)
            detectedMatiere = args.getString("matiere")
            detectedSaison = args.getString("saison", "TOUTE_SAISON")
            detectedEstThermique = args.getBoolean("estThermique", false)
            detectedEstImpermeable = args.getBoolean("estImpermeable", false)
            detectedStyleId = args.getInt("styleId", 1)
        }

        // Actions Carte 1 (Prise de photo & Galerie - Maquette 7.jpg)
        binding.cardTakePhoto.setOnClickListener {
            try {
                findNavController().navigate(R.id.cameraFragment)
            } catch (e: Exception) {
                Toast.makeText(requireContext(), "Impossible d'ouvrir la caméra : ${e.localizedMessage}", Toast.LENGTH_SHORT).show()
            }
        }

        binding.tvChooseGallery.setOnClickListener {
            try {
                galleryLauncher.launch("image/*")
            } catch (e: Exception) {
                Toast.makeText(requireContext(), "Impossible d'ouvrir la galerie : ${e.localizedMessage}", Toast.LENGTH_SHORT).show()
            }
        }

        // Configuration des dropdowns Style et Fit
        setupStylesAndFits()

        // Charger l'image si présente
        if (imageUrl.isNotEmpty()) {
            val fullUrl = if (imageUrl.startsWith("http")) imageUrl else "${BuildConfig.BASE_URL.trimEnd('/')}$imageUrl"
            binding.ivClothingPreview.load(fullUrl) {
                placeholder(R.drawable.ic_hanger)
                error(R.drawable.ic_hanger)
            }
            val argName = arguments?.getString("name")
            val defaultTitle = "${predictedCategory.replaceFirstChar { it.uppercase() }} $predictedColor"
            binding.etName.setText(if (!argName.isNullOrEmpty()) argName else defaultTitle)

            arguments?.getString("styleName")?.let { sName ->
                val stylesList = listOf("Casual", "Classic", "Streetwear", "Elegant", "Sporty", "Minimal")
                val styleIdx = stylesList.indexOfFirst { it.equals(sName, ignoreCase = true) }
                if (styleIdx != -1) binding.spinnerStyle.setSelection(styleIdx)
            }

            arguments?.getString("coupe")?.let { cName ->
                val fitsList = listOf("Regular", "Fitted", "Oversized", "Slim", "Loose")
                val fitIdx = when (cName.uppercase()) {
                    "AJUSTEE", "SLIM" -> fitsList.indexOfFirst { it.equals("Slim", ignoreCase = true) }
                    "OVERSIZE", "OVERSIZED" -> fitsList.indexOfFirst { it.equals("Oversized", ignoreCase = true) }
                    else -> fitsList.indexOfFirst { it.equals("Regular", ignoreCase = true) }
                }
                if (fitIdx != -1) binding.spinnerFit.setSelection(fitIdx)
            }
        }

        // Charger les référentiels filtrés selon le genre de l'utilisateur (Homme vs Femme)
        val userGenre = com.wearia.app.WeariaApplication.instance.sessionManager.getUserGenre()
        profileViewModel.loadReferentials(userGenre)

        profileViewModel.types.observe(viewLifecycleOwner) { types ->
            availableTypes = types
            val typeNames = types.map { it.nom }
            val adapter = ArrayAdapter(requireContext(), android.R.layout.simple_spinner_dropdown_item, typeNames)
            binding.spinnerType.adapter = adapter

            val index = types.indexOfFirst { it.id == suggestedTypeId || it.nom.equals(predictedCategory, ignoreCase = true) }
            if (index != -1) binding.spinnerType.setSelection(index)
        }

        profileViewModel.colors.observe(viewLifecycleOwner) { colors ->
            availableColors = colors
            val colorNames = colors.map { it.nom }
            val adapter = ArrayAdapter(requireContext(), android.R.layout.simple_spinner_dropdown_item, colorNames)
            binding.spinnerColor.adapter = adapter

            val index = colors.indexOfFirst { it.id == suggestedColorId || it.nom.equals(predictedColor, ignoreCase = true) }
            if (index != -1) {
                binding.spinnerColor.setSelection(index)
                updateColorSwatch(colors[index].codeHex)
            }
        }

        binding.spinnerColor.onItemSelectedListener = object : AdapterView.OnItemSelectedListener {
            override fun onItemSelected(parent: AdapterView<*>?, view: View?, position: Int, id: Long) {
                if (position in availableColors.indices) {
                    updateColorSwatch(availableColors[position].codeHex)
                }
            }
            override fun onNothingSelected(parent: AdapterView<*>?) {}
        }

        // Observer la classification IA
        clothingViewModel.classifyState.observe(viewLifecycleOwner) { state ->
            if (state == null) return@observe
            when (state) {
                is Resource.Loading -> {
                    binding.progressBarAi.visibility = View.VISIBLE
                    binding.tvAiPredictionBanner.text = "AI analyzing clothing item..."
                }
                is Resource.Success -> {
                    binding.progressBarAi.visibility = View.GONE
                    val result = state.data
                    imageUrl = result.imageUrl
                    predictedCategory = result.category
                    predictedColor = result.color
                    suggestedTypeId = result.suggestedTypeId ?: -1
                    suggestedColorId = result.suggestedColorId ?: -1

                    binding.tvAiPredictionBanner.text = "AI detected — you can edit these details."
                    val smartTitle = result.name ?: "${predictedCategory.replaceFirstChar { it.uppercase() }} $predictedColor"
                    binding.etName.setText(smartTitle)

                    detectedMatiere = result.matiere
                    detectedSaison = result.saison ?: "TOUTE_SAISON"
                    detectedEstThermique = result.estThermique ?: false
                    detectedEstImpermeable = result.estImpermeable ?: false
                    detectedStyleId = result.styleId

                    val fullUrl = if (imageUrl.startsWith("http")) imageUrl else "${BuildConfig.BASE_URL.trimEnd('/')}$imageUrl"
                    binding.ivClothingPreview.load(fullUrl) {
                        placeholder(R.drawable.ic_hanger)
                        error(R.drawable.ic_hanger)
                    }

                    // Sélectionner dans les dropdowns Type et Couleur
                    val typeIdx = availableTypes.indexOfFirst { it.id == suggestedTypeId || it.nom.equals(predictedCategory, ignoreCase = true) }
                    if (typeIdx != -1) binding.spinnerType.setSelection(typeIdx)

                    val colorIdx = availableColors.indexOfFirst { it.id == suggestedColorId || it.nom.equals(predictedColor, ignoreCase = true) }
                    if (colorIdx != -1) {
                        binding.spinnerColor.setSelection(colorIdx)
                        updateColorSwatch(availableColors[colorIdx].codeHex)
                    }

                    // Sélectionner automatiquement le Style adapté
                    result.styleName?.let { sName ->
                        val stylesList = listOf("Casual", "Classic", "Streetwear", "Elegant", "Sporty", "Minimal")
                        val styleIdx = stylesList.indexOfFirst { it.equals(sName, ignoreCase = true) }
                        if (styleIdx != -1) binding.spinnerStyle.setSelection(styleIdx)
                    }

                    // Sélectionner automatiquement la Coupe adaptée
                    result.coupe?.let { cName ->
                        val fitsList = listOf("Regular", "Fitted", "Oversized", "Slim", "Loose")
                        val fitIdx = when (cName.uppercase()) {
                            "AJUSTEE", "SLIM" -> fitsList.indexOfFirst { it.equals("Slim", ignoreCase = true) }
                            "OVERSIZE", "OVERSIZED" -> fitsList.indexOfFirst { it.equals("Oversized", ignoreCase = true) }
                            else -> fitsList.indexOfFirst { it.equals("Regular", ignoreCase = true) }
                        }
                        if (fitIdx != -1) binding.spinnerFit.setSelection(fitIdx)
                    }
                }
                is Resource.Error -> {
                    binding.progressBarAi.visibility = View.GONE
                    binding.tvAiPredictionBanner.text = "Could not classify automatically. Please select details below."
                }
            }
        }

        // Bouton Add to wardrobe
        binding.btnSaveClothing.setOnClickListener {
            saveClothing()
        }

        clothingViewModel.addClothingState.observe(viewLifecycleOwner) { state ->
            if (state == null) return@observe
            when (state) {
                is Resource.Loading -> {
                    binding.progressBar.visibility = View.VISIBLE
                    binding.btnSaveClothing.isEnabled = false
                }
                is Resource.Success -> {
                    binding.progressBar.visibility = View.GONE
                    binding.btnSaveClothing.isEnabled = true
                    Toast.makeText(requireContext(), "Vêtement ajouté avec succès !", Toast.LENGTH_SHORT).show()
                    clothingViewModel.loadClothes()
                    clothingViewModel.resetClassifyState()
                    clothingViewModel.resetAddClothingState()

                    try {
                        if (!findNavController().popBackStack(R.id.dressingFragment, false)) {
                            findNavController().navigate(R.id.action_addClothing_to_dressing)
                        }
                    } catch (e: Exception) {
                        try {
                            findNavController().popBackStack()
                        } catch (e2: Exception) {
                            // ignore
                        }
                    }
                }
                is Resource.Error -> {
                    binding.progressBar.visibility = View.GONE
                    binding.btnSaveClothing.isEnabled = true
                    Toast.makeText(requireContext(), state.message, Toast.LENGTH_LONG).show()
                }
            }
        }
    }

    private fun setupStylesAndFits() {
        val styles = listOf("Casual", "Classic", "Streetwear", "Elegant", "Sporty", "Minimal")
        val styleAdapter = ArrayAdapter(requireContext(), android.R.layout.simple_spinner_dropdown_item, styles)
        binding.spinnerStyle.adapter = styleAdapter

        val fits = listOf("Regular", "Fitted", "Oversized", "Slim", "Loose")
        val fitAdapter = ArrayAdapter(requireContext(), android.R.layout.simple_spinner_dropdown_item, fits)
        binding.spinnerFit.adapter = fitAdapter

        val statuses = listOf("Disponible", "Sale")
        val statusAdapter = ArrayAdapter(requireContext(), android.R.layout.simple_spinner_dropdown_item, statuses)
        binding.spinnerStatus.adapter = statusAdapter
    }

    private fun updateColorSwatch(hexColor: String) {
        try {
            binding.viewSelectedColorSwatch.setBackgroundColor(Color.parseColor(hexColor))
        } catch (e: Exception) {
            binding.viewSelectedColorSwatch.setBackgroundColor(Color.LTGRAY)
        }
    }

    private fun handleGalleryImage(uri: Uri) {
        val ctx = context ?: return
        lifecycleScope.launch(Dispatchers.IO) {
            try {
                val inputStream = ctx.contentResolver.openInputStream(uri) ?: run {
                    withContext(Dispatchers.Main) {
                        Toast.makeText(ctx, "Impossible de lire l'image sélectionnée.", Toast.LENGTH_SHORT).show()
                    }
                    return@launch
                }
                val rawTempFile = File(ctx.cacheDir, "picked_cloth_${System.currentTimeMillis()}.jpg")
                rawTempFile.outputStream().use { output ->
                    inputStream.copyTo(output)
                }
                val optimizedFile = ImageUtils.compressAndPrepareFile(ctx, rawTempFile)
                withContext(Dispatchers.Main) {
                    Toast.makeText(ctx, "Image importée, analyse IA en cours...", Toast.LENGTH_SHORT).show()
                    clothingViewModel.classifyImage(optimizedFile)
                }
            } catch (e: Exception) {
                withContext(Dispatchers.Main) {
                    Toast.makeText(ctx, "Erreur lors de l'import : ${e.localizedMessage}", Toast.LENGTH_LONG).show()
                }
            }
        }
    }

    private fun saveClothing() {
        val name = binding.etName.text.toString().trim()
        val selectedTypeIndex = binding.spinnerType.selectedItemPosition
        val selectedColorIndex = binding.spinnerColor.selectedItemPosition

        if (selectedTypeIndex !in availableTypes.indices || selectedColorIndex !in availableColors.indices) {
            Toast.makeText(requireContext(), "Veuillez sélectionner un type et une couleur.", Toast.LENGTH_SHORT).show()
            return
        }

        val typeId = availableTypes[selectedTypeIndex].id
        val colorId = availableColors[selectedColorIndex].id
        val styleName = binding.spinnerStyle.selectedItem?.toString() ?: "Casual"
        val fitName = binding.spinnerFit.selectedItem?.toString() ?: "Regular"

        val dbCoupe = when (fitName.uppercase()) {
            "SLIM", "FITTED" -> "AJUSTEE"
            "OVERSIZED", "LOOSE" -> "OVERSIZE"
            else -> "REGULIERE"
        }

        val dbStyleId = when (styleName.lowercase()) {
            "casual" -> 1
            "classic" -> 2
            "sporty" -> 3
            "streetwear" -> 4
            "elegant" -> 5
            else -> detectedStyleId ?: 1
        }

        val statusChoice = binding.spinnerStatus.selectedItem?.toString() ?: "Disponible"
        val dbStatut = if (statusChoice.equals("Sale", ignoreCase = true)) "SALE" else "DISPONIBLE"

        val finalName = if (name.isNotEmpty()) name else "${availableTypes[selectedTypeIndex].nom} ${availableColors[selectedColorIndex].nom}"
        val finalPhotoUrl = if (imageUrl.isNotEmpty()) imageUrl else "/uploads/chemise_oxford_blanche.jpg"

        val request = VetementCreateRequest(
            nom = finalName,
            photoUrl = finalPhotoUrl,
            matiere = detectedMatiere ?: "Coton",
            coupe = dbCoupe,
            saison = detectedSaison,
            estThermique = detectedEstThermique,
            estImpermeable = detectedEstImpermeable,
            statut = dbStatut,
            typeVetementId = typeId,
            couleurId = colorId,
            styleId = dbStyleId
        )

        clothingViewModel.addClothing(request)
    }

    override fun onDestroyView() {
        super.onDestroyView()
        _binding = null
    }
}
