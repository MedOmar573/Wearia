package com.wearia.app.ui.dressing

import android.net.Uri
import android.os.Bundle
import android.text.Editable
import android.text.TextWatcher
import android.view.*
import android.widget.Toast
import androidx.activity.result.contract.ActivityResultContracts
import androidx.appcompat.app.AlertDialog
import androidx.core.content.ContextCompat
import androidx.fragment.app.Fragment
import androidx.fragment.app.activityViewModels
import androidx.fragment.app.viewModels
import androidx.navigation.fragment.findNavController
import androidx.recyclerview.widget.GridLayoutManager
import com.google.android.material.dialog.MaterialAlertDialogBuilder
import com.wearia.app.R
import com.wearia.app.databinding.FragmentDressingBinding
import com.wearia.app.data.remote.dto.TypeVetementResponse
import com.wearia.app.data.remote.dto.VetementResponse
import com.wearia.app.data.remote.dto.VetementUpdateRequest
import com.wearia.app.utils.Resource
import com.wearia.app.utils.SessionManager
import com.wearia.app.utils.addPressEffect
import com.wearia.app.viewmodel.ClothingViewModel
import com.wearia.app.viewmodel.ProfileViewModel
import java.io.File

/**
 * DressingFragment : Écran principal du dressing virtuel modernisé Fresh Fashion Tech.
 * Les filtres et sélecteurs de types s'adaptent directement au compte connecté :
 * - Compte Homme : Types et catégories strictement masculins/mixtes (Robe, Jupe, Bottes totalement exclus).
 * - Compte Femme : Tous les types et catégories (mixte + femme).
 */
class DressingFragment : Fragment() {

    private var _binding: FragmentDressingBinding? = null
    private val binding get() = _binding!!
    private val viewModel: ClothingViewModel by activityViewModels { ClothingViewModel.Factory() }
    private val profileViewModel: ProfileViewModel by viewModels { ProfileViewModel.Factory() }
    private lateinit var clothingAdapter: ClothingAdapter

    private var allClothes: List<VetementResponse> = emptyList()
    private var accountGenre: String = "HOMME"
    private var currentGenreFilter: String = "HOMME" // Fixé directement selon le compte
    private var currentCategoryFilter: String = "All"
    private var currentTypeFilter: String = "ALL" // Filtre précis par type (Chemise, Jean, Robe...)
    private var currentSearchQuery: String = ""

    companion object {
        val HOMME_TYPES = listOf(
            "Chemise", "T-Shirt", "Polo", "Pull", "Sweat",
            "Jean", "Pantalon", "Short",
            "Veste", "Manteau",
            "Baskets", "Chaussures de ville",
            "Ceinture", "Chapeau", "Sac", "Écharpe", "Montre"
        )
        val FEMME_TYPES = listOf(
            "Chemise", "T-Shirt", "Polo", "Pull", "Sweat",
            "Jean", "Pantalon", "Short", "Jupe",
            "Robe",
            "Veste", "Manteau",
            "Baskets", "Bottes", "Chaussures de ville",
            "Ceinture", "Chapeau", "Sac", "Écharpe", "Montre"
        )
    }

    private val galleryLauncher =
        registerForActivityResult(ActivityResultContracts.GetContent()) { uri: Uri? ->
            uri?.let { handleGalleryImage(it) }
        }

    override fun onCreateView(inflater: LayoutInflater, container: ViewGroup?, savedInstanceState: Bundle?): View {
        _binding = FragmentDressingBinding.inflate(inflater, container, false)
        return binding.root
    }

    override fun onViewCreated(view: View, savedInstanceState: Bundle?) {
        super.onViewCreated(view, savedInstanceState)

        binding.fabAddClothing.addPressEffect()
        binding.btnFilterWardrobe.addPressEffect()

        // Détection automatique du genre du compte connecté (HOMME ou FEMME)
        accountGenre = try {
            SessionManager(requireContext()).getUserGenre().uppercase()
        } catch (e: Exception) {
            "HOMME"
        }
        currentGenreFilter = accountGenre

        // Chargement des référentiels types/catégories selon le compte
        profileViewModel.loadReferentials(currentGenreFilter)

        setupSearchAndFilters()
        setupRecyclerView()
        setupFab()
        observeClothes()

        viewModel.loadClothes()

        binding.swipeRefresh.setOnRefreshListener {
            viewModel.loadClothes()
            profileViewModel.loadReferentials(currentGenreFilter)
        }
    }

    private fun setupRecyclerView() {
        clothingAdapter = ClothingAdapter(
            onItemClick = { clothing ->
                showClothingDetailsAndStatusDialog(clothing)
            },
            onDeleteClick = { clothing ->
                showDeleteConfirmation(clothing)
            },
            onStatusClick = { clothing ->
                toggleClothingStatus(clothing)
            }
        )
        binding.rvClothes.apply {
            adapter = clothingAdapter
            layoutManager = GridLayoutManager(requireContext(), 2)
        }
    }

    private fun toggleClothingStatus(clothing: VetementResponse) {
        val newStatus = if (clothing.statut.equals("SALE", ignoreCase = true)) "DISPONIBLE" else "SALE"
        val req = VetementUpdateRequest(statut = newStatus)
        viewModel.updateClothing(clothing.id, req)
    }

    private fun showClothingDetailsAndStatusDialog(clothing: VetementResponse) {
        val isCurrentlySale = clothing.statut.equals("SALE", ignoreCase = true)
        val statusLabel = if (isCurrentlySale) "Sale (au panier / lavage)" else "Disponible"
        val switchAction = if (isCurrentlySale) "Rendre Disponible" else "Marquer comme Sale"

        MaterialAlertDialogBuilder(requireContext())
            .setTitle(clothing.nom)
            .setMessage("• Statut : $statusLabel\n• Catégorie : ${clothing.typeVetement.nom}\n• Couleur : ${clothing.couleur.nom}\n• Matière : ${clothing.matiere ?: "Coton"}\n• Saison : ${clothing.saison}")
            .setPositiveButton(switchAction) { _, _ ->
                toggleClothingStatus(clothing)
            }
            .setNeutralButton("Supprimer") { _, _ ->
                showDeleteConfirmation(clothing)
            }
            .setNegativeButton("Fermer", null)
            .show()
    }

    private fun setupSearchAndFilters() {
        // 1. Barre de recherche texte
        binding.etSearchWardrobe.addTextChangedListener(object : TextWatcher {
            override fun beforeTextChanged(s: CharSequence?, start: Int, count: Int, after: Int) {}
            override fun onTextChanged(s: CharSequence?, start: Int, before: Int, count: Int) {
                currentSearchQuery = s?.toString()?.trim() ?: ""
                applyFilterAndSearch()
            }
            override fun afterTextChanged(s: Editable?) {}
        })

        // 2. Bouton Filtre général
        binding.btnFilterWardrobe.setOnClickListener {
            val filterOptions = arrayOf(
                "Tous les vêtements",
                "🏷️ Filtrer par type précis...",
                "📂 Filtrer par catégorie...",
                "✅ Disponibles uniquement",
                "🧺 Au lavage / Sales"
            )
            MaterialAlertDialogBuilder(requireContext())
                .setTitle("Filtres du dressing")
                .setItems(filterOptions) { _, which ->
                    when (which) {
                        0 -> {
                            currentSearchQuery = ""
                            binding.etSearchWardrobe.setText("")
                            currentCategoryFilter = "All"
                            currentTypeFilter = "ALL"
                            binding.chipCustomCategory.text = "+ Type"
                            updateChipSelection(binding.chipAll.id)
                        }
                        1 -> {
                            showTypePickerFilterDialog()
                            return@setItems
                        }
                        2 -> {
                            showCategoryPickerFilterDialog()
                            return@setItems
                        }
                        3 -> currentSearchQuery = "DISPONIBLE"
                        4 -> currentSearchQuery = "SALE"
                    }
                    applyFilterAndSearch()
                }
                .show()
        }

        // 3. Configuration de la visibilité des chips selon le compte
        if (accountGenre == "FEMME") {
            binding.chipDresses.visibility = View.VISIBLE
        } else {
            binding.chipDresses.visibility = View.GONE
        }

        // 4. Chips de Catégories Horizontales
        updateChipSelection(binding.chipAll.id)

        binding.chipAll.setOnClickListener {
            currentCategoryFilter = "All"
            currentTypeFilter = "ALL"
            binding.chipCustomCategory.text = "+ Type"
            updateChipSelection(binding.chipAll.id)
            applyFilterAndSearch()
        }
        binding.chipTops.setOnClickListener {
            currentCategoryFilter = "Haut"
            currentTypeFilter = "ALL"
            binding.chipCustomCategory.text = "+ Type"
            updateChipSelection(binding.chipTops.id)
            applyFilterAndSearch()
        }
        binding.chipBottoms.setOnClickListener {
            currentCategoryFilter = "Bas"
            currentTypeFilter = "ALL"
            binding.chipCustomCategory.text = "+ Type"
            updateChipSelection(binding.chipBottoms.id)
            applyFilterAndSearch()
        }
        binding.chipDresses.setOnClickListener {
            currentCategoryFilter = "Robe"
            currentTypeFilter = "ALL"
            binding.chipCustomCategory.text = "+ Type"
            updateChipSelection(binding.chipDresses.id)
            applyFilterAndSearch()
        }
        binding.chipJackets.setOnClickListener {
            currentCategoryFilter = "Veste"
            currentTypeFilter = "ALL"
            binding.chipCustomCategory.text = "+ Type"
            updateChipSelection(binding.chipJackets.id)
            applyFilterAndSearch()
        }
        binding.chipShoes.setOnClickListener {
            currentCategoryFilter = "Chauss"
            currentTypeFilter = "ALL"
            binding.chipCustomCategory.text = "+ Type"
            updateChipSelection(binding.chipShoes.id)
            applyFilterAndSearch()
        }
        binding.chipAccessories.setOnClickListener {
            currentCategoryFilter = "Access"
            currentTypeFilter = "ALL"
            binding.chipCustomCategory.text = "+ Type"
            updateChipSelection(binding.chipAccessories.id)
            applyFilterAndSearch()
        }
        binding.chipCustomCategory.setOnClickListener {
            if (currentTypeFilter != "ALL") {
                // Réinitialiser le filtre type actif
                currentTypeFilter = "ALL"
                binding.chipCustomCategory.text = "+ Type"
                updateChipSelection(binding.chipAll.id)
                applyFilterAndSearch()
            } else {
                showTypePickerFilterDialog()
            }
        }
        binding.chipCustomCategory.setOnLongClickListener {
            showTypePickerFilterDialog()
            true
        }
    }

    private fun showTypePickerFilterDialog() {
        val isHomme = accountGenre == "HOMME"
        val serverTypes = profileViewModel.types.value

        val typesList = if (!serverTypes.isNullOrEmpty()) {
            val list = serverTypes.map { it.nom }.toMutableList()
            if (isHomme) {
                // Règle stricte : exclure Robe, Jupe, Bottes pour homme
                list.removeAll { it.equals("Robe", true) || it.equals("Jupe", true) || it.equals("Bottes", true) }
            }
            list
        } else {
            if (isHomme) HOMME_TYPES else FEMME_TYPES
        }

        val options = mutableListOf("Tous les types").apply { addAll(typesList) }
        val dialogTitle = if (isHomme) "Types de vêtements" else "Types de vêtements"

        MaterialAlertDialogBuilder(requireContext())
            .setTitle(dialogTitle)
            .setItems(options.toTypedArray()) { _, which ->
                if (which == 0) {
                    currentTypeFilter = "ALL"
                    binding.chipCustomCategory.text = "+ Type"
                    updateChipSelection(binding.chipAll.id)
                } else {
                    currentTypeFilter = options[which]
                    binding.chipCustomCategory.text = "🏷️ $currentTypeFilter ✕"
                    updateChipSelection(binding.chipCustomCategory.id)
                }
                applyFilterAndSearch()
            }
            .setNegativeButton("Fermer", null)
            .show()
    }

    private fun showCategoryPickerFilterDialog() {
        if (accountGenre == "HOMME") {
            // Pour Homme : Pas de robe, pas de jupe, pas de bottes
            val categories = arrayOf(
                "Toutes les catégories",
                "Hauts (T-shirts, Chemises, Pulls, Polos, Sweats)",
                "Bas (Pantalons, Jeans, Shorts)",
                "Vestes & Manteaux",
                "Chaussures (Baskets, Chaussures de ville)",
                "Accessoires (Sacs, Ceintures, Montres, Chapeaux)"
            )

            MaterialAlertDialogBuilder(requireContext())
                .setTitle("Catégories de vêtements")
                .setItems(categories) { _, which ->
                    currentTypeFilter = "ALL"
                    binding.chipCustomCategory.text = "+ Type"
                    when (which) {
                        0 -> {
                            currentCategoryFilter = "All"
                            updateChipSelection(binding.chipAll.id)
                        }
                        1 -> {
                            currentCategoryFilter = "Haut"
                            updateChipSelection(binding.chipTops.id)
                        }
                        2 -> {
                            currentCategoryFilter = "Bas"
                            updateChipSelection(binding.chipBottoms.id)
                        }
                        3 -> {
                            currentCategoryFilter = "Veste"
                            updateChipSelection(binding.chipJackets.id)
                        }
                        4 -> {
                            currentCategoryFilter = "Chauss"
                            updateChipSelection(binding.chipShoes.id)
                        }
                        5 -> {
                            currentCategoryFilter = "Access"
                            updateChipSelection(binding.chipAccessories.id)
                        }
                    }
                    applyFilterAndSearch()
                }
                .setNegativeButton("Fermer", null)
                .show()
        } else {
            // Pour Femme : inclut Robes, Jupes, Bottes
            val categories = arrayOf(
                "Toutes les catégories",
                "Hauts (T-shirts, Chemises, Pulls, Polos)",
                "Bas (Pantalons, Jeans, Shorts, Jupes)",
                "Robes & Combinaisons",
                "Vestes & Manteaux",
                "Chaussures (Baskets, Bottes, Chaussures)",
                "Accessoires (Sacs, Bijoux, Ceintures)"
            )

            MaterialAlertDialogBuilder(requireContext())
                .setTitle("Catégories de vêtements")
                .setItems(categories) { _, which ->
                    currentTypeFilter = "ALL"
                    binding.chipCustomCategory.text = "+ Type"
                    when (which) {
                        0 -> {
                            currentCategoryFilter = "All"
                            updateChipSelection(binding.chipAll.id)
                        }
                        1 -> {
                            currentCategoryFilter = "Haut"
                            updateChipSelection(binding.chipTops.id)
                        }
                        2 -> {
                            currentCategoryFilter = "Bas"
                            updateChipSelection(binding.chipBottoms.id)
                        }
                        3 -> {
                            currentCategoryFilter = "Robe"
                            updateChipSelection(binding.chipDresses.id)
                        }
                        4 -> {
                            currentCategoryFilter = "Veste"
                            updateChipSelection(binding.chipJackets.id)
                        }
                        5 -> {
                            currentCategoryFilter = "Chauss"
                            updateChipSelection(binding.chipShoes.id)
                        }
                        6 -> {
                            currentCategoryFilter = "Access"
                            updateChipSelection(binding.chipAccessories.id)
                        }
                    }
                    applyFilterAndSearch()
                }
                .setNegativeButton("Fermer", null)
                .show()
        }
    }

    private fun updateChipSelection(selectedChipId: Int) {
        val onPrimaryColor = ContextCompat.getColor(requireContext(), R.color.colorOnPrimary)
        val textPrimaryColor = ContextCompat.getColor(requireContext(), R.color.colorTextPrimary)

        listOf(
            binding.chipAll,
            binding.chipTops,
            binding.chipBottoms,
            binding.chipDresses,
            binding.chipJackets,
            binding.chipShoes,
            binding.chipAccessories,
            binding.chipCustomCategory
        ).forEach { chip ->
            val isSelected = chip.id == selectedChipId
            chip.isChecked = isSelected
            if (isSelected) {
                chip.setChipBackgroundColorResource(R.color.colorPrimary)
                chip.setTextColor(onPrimaryColor)
            } else {
                chip.setChipBackgroundColorResource(R.color.colorSurfaceCard)
                chip.setTextColor(textPrimaryColor)
            }
        }
    }

    private fun applyFilterAndSearch() {
        var filtered = allClothes

        // 1. Filtrage selon le Genre du compte connecté
        if (accountGenre == "HOMME") {
            filtered = filtered.filter { item ->
                val genreCible = (item.typeVetement.genreCible ?: "MIXTE").uppercase()
                val typeNom = item.typeVetement.nom.lowercase()
                val catId = item.typeVetement.categorieId

                // Règle Homme :
                // - Ne doit pas être réservé aux femmes
                // - Ne doit pas être de catégorie Robe (3)
                // - Les types spécifiques femme (jupe, robe, botte) sont strictement exclus
                genreCible != "FEMME" &&
                catId != 3 &&
                !typeNom.contains("robe") &&
                !typeNom.contains("jupe") &&
                !typeNom.contains("botte")
            }
        } else if (accountGenre == "FEMME") {
            filtered = filtered.filter { item ->
                val genreCible = (item.typeVetement.genreCible ?: "MIXTE").uppercase()
                // Règle Femme : Vêtements mixtes + femme (catégorie homme + catégorie femme)
                genreCible != "HOMME"
            }
        }

        // 2. Filtrage par Type précis de vêtement (Chemise, Jean, Polo, Robe...)
        if (currentTypeFilter != "ALL") {
            filtered = filtered.filter { item ->
                item.typeVetement.nom.equals(currentTypeFilter, ignoreCase = true) ||
                item.nom.contains(currentTypeFilter, ignoreCase = true)
            }
        }

        // 3. Filtrage selon la Catégorie sélectionnée
        if (currentCategoryFilter != "All") {
            filtered = filtered.filter { item ->
                when (currentCategoryFilter) {
                    "Haut" -> item.typeVetement.categorieId == 1 ||
                            item.typeVetement.nom.contains("t-shirt", true) ||
                            item.typeVetement.nom.contains("chemise", true) ||
                            item.typeVetement.nom.contains("pull", true) ||
                            item.typeVetement.nom.contains("polo", true) ||
                            item.typeVetement.nom.contains("sweat", true) ||
                            item.nom.contains("haut", true)
                    "Bas" -> {
                        val isBas = item.typeVetement.categorieId == 2 ||
                                item.typeVetement.nom.contains("jean", true) ||
                                item.typeVetement.nom.contains("pantalon", true) ||
                                item.typeVetement.nom.contains("short", true) ||
                                item.nom.contains("bas", true)
                        if (accountGenre == "HOMME") {
                            // Pour un homme : pas de jupes
                            isBas && !item.typeVetement.nom.contains("jupe", true)
                        } else {
                            isBas || item.typeVetement.nom.contains("jupe", true)
                        }
                    }
                    "Robe" -> {
                        // Pour un homme : jamais de robe
                        if (accountGenre == "HOMME") {
                            false
                        } else {
                            item.typeVetement.categorieId == 3 ||
                            item.typeVetement.nom.contains("robe", true) ||
                            item.typeVetement.nom.contains("combinaison", true) ||
                            item.nom.contains("robe", true)
                        }
                    }
                    "Veste" -> item.typeVetement.categorieId == 4 ||
                            item.typeVetement.nom.contains("veste", true) ||
                            item.typeVetement.nom.contains("manteau", true) ||
                            item.nom.contains("veste", true) ||
                            item.nom.contains("blazer", true)
                    "Chauss" -> {
                        val isChauss = item.typeVetement.categorieId == 5 ||
                                item.typeVetement.nom.contains("basket", true) ||
                                item.typeVetement.nom.contains("chauss", true) ||
                                item.nom.contains("basket", true) ||
                                item.nom.contains("chauss", true)
                        if (accountGenre == "HOMME") {
                            // Pour un homme : pas de bottes féminines
                            isChauss && !item.typeVetement.nom.contains("botte", true)
                        } else {
                            isChauss || item.typeVetement.nom.contains("botte", true)
                        }
                    }
                    "Access" -> item.typeVetement.categorieId == 6 ||
                            item.typeVetement.nom.contains("access", true) ||
                            item.nom.contains("access", true) ||
                            item.typeVetement.nom.contains("sac", true) ||
                            item.typeVetement.nom.contains("ceinture", true) ||
                            item.typeVetement.nom.contains("montre", true)
                    else -> item.typeVetement.nom.contains(currentCategoryFilter, ignoreCase = true) ||
                            item.nom.contains(currentCategoryFilter, ignoreCase = true)
                }
            }
        }

        // 4. Filtrage par texte de recherche
        if (currentSearchQuery.isNotEmpty()) {
            filtered = filtered.filter { item ->
                item.nom.contains(currentSearchQuery, ignoreCase = true) ||
                item.typeVetement.nom.contains(currentSearchQuery, ignoreCase = true) ||
                item.couleur.nom.contains(currentSearchQuery, ignoreCase = true) ||
                item.statut.contains(currentSearchQuery, ignoreCase = true)
            }
        }

        clothingAdapter.submitList(filtered)
        binding.tvEmpty.visibility = if (filtered.isEmpty()) View.VISIBLE else View.GONE
    }

    private fun setupFab() {
        binding.fabAddClothing.setOnClickListener {
            try {
                findNavController().navigate(R.id.action_dressing_to_addClothing)
            } catch (e: Exception) {
                try {
                    findNavController().navigate(R.id.addClothingFragment)
                } catch (e2: Exception) {
                    // ignore
                }
            }
        }
    }

    private fun observeClothes() {
        viewModel.clothesList.observe(viewLifecycleOwner) { state ->
            when (state) {
                is Resource.Loading -> {
                    binding.progressBar.visibility = View.VISIBLE
                    binding.tvEmpty.visibility = View.GONE
                }
                is Resource.Success -> {
                    binding.progressBar.visibility = View.GONE
                    binding.swipeRefresh.isRefreshing = false
                    allClothes = state.data
                    binding.tvOfflineWarning.visibility = View.GONE
                    applyFilterAndSearch()
                }
                is Resource.Error -> {
                    binding.progressBar.visibility = View.GONE
                    binding.swipeRefresh.isRefreshing = false
                    allClothes = emptyList()
                    binding.tvOfflineWarning.visibility = View.GONE
                    applyFilterAndSearch()
                    if (allClothes.isEmpty()) {
                        binding.tvEmpty.text = "Impossible de charger les vêtements.\nVérifiez votre connexion."
                        binding.tvEmpty.visibility = View.VISIBLE
                    }
                }
            }
        }

        viewModel.deleteState.observe(viewLifecycleOwner) { state ->
            if (state is Resource.Success) {
                Toast.makeText(requireContext(), "Vêtement retiré du dressing", Toast.LENGTH_SHORT).show()
                viewModel.loadClothes()
            }
        }
    }

    private fun showDeleteConfirmation(clothing: VetementResponse) {
        MaterialAlertDialogBuilder(requireContext())
            .setTitle("Supprimer ce vêtement ?")
            .setMessage("Voulez-vous vraiment retirer \"${clothing.nom}\" de votre dressing ? Cette action est irréversible.")
            .setPositiveButton("Supprimer") { _, _ ->
                viewModel.deleteClothing(clothing.id)
                Toast.makeText(requireContext(), "Vêtement supprimé", Toast.LENGTH_SHORT).show()
            }
            .setNegativeButton("Annuler", null)
            .show()
    }

    private fun handleGalleryImage(uri: Uri) {
        // Optionnel : import direct depuis galerie
    }

    override fun onDestroyView() {
        super.onDestroyView()
        _binding = null
    }
}
