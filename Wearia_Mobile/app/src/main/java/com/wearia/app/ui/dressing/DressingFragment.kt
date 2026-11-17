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
import androidx.navigation.fragment.findNavController
import androidx.recyclerview.widget.GridLayoutManager
import com.google.android.material.dialog.MaterialAlertDialogBuilder
import com.wearia.app.R
import com.wearia.app.databinding.FragmentDressingBinding
import com.wearia.app.data.remote.dto.VetementResponse
import com.wearia.app.data.remote.dto.VetementUpdateRequest
import com.wearia.app.utils.Resource
import com.wearia.app.utils.addPressEffect
import com.wearia.app.viewmodel.ClothingViewModel
import java.io.File

/**
 * DressingFragment : Écran principal du dressing virtuel modernisé Fresh Fashion Tech.
 */
class DressingFragment : Fragment() {

    private var _binding: FragmentDressingBinding? = null
    private val binding get() = _binding!!
    private val viewModel: ClothingViewModel by activityViewModels { ClothingViewModel.Factory() }
    private lateinit var clothingAdapter: ClothingAdapter

    private var allClothes: List<VetementResponse> = emptyList()
    private var currentCategoryFilter: String = "All"
    private var currentSearchQuery: String = ""

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

        binding.btnFilterWardrobe.setOnClickListener {
            val filterOptions = arrayOf(
                "Tous les vêtements",
                "Disponibles uniquement",
                "Au lavage / Sales",
                "Choisir une catégorie précise..."
            )
            MaterialAlertDialogBuilder(requireContext())
                .setTitle("Filtres du dressing")
                .setItems(filterOptions) { _, which ->
                    when (which) {
                        0 -> {
                            currentSearchQuery = ""
                            binding.etSearchWardrobe.setText("")
                            currentCategoryFilter = "All"
                            updateChipSelection(binding.chipAll.id)
                        }
                        1 -> currentSearchQuery = "DISPONIBLE"
                        2 -> currentSearchQuery = "SALE"
                        3 -> {
                            showCategoryPickerFilterDialog()
                            return@setItems
                        }
                    }
                    applyFilterAndSearch()
                }
                .show()
        }

        setupRecyclerView()
        setupSearchAndFilters()
        setupFab()
        observeClothes()

        viewModel.loadClothes()

        binding.swipeRefresh.setOnRefreshListener {
            viewModel.loadClothes()
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
        // Barre de recherche
        binding.etSearchWardrobe.addTextChangedListener(object : TextWatcher {
            override fun beforeTextChanged(s: CharSequence?, start: Int, count: Int, after: Int) {}
            override fun onTextChanged(s: CharSequence?, start: Int, before: Int, count: Int) {
                currentSearchQuery = s?.toString()?.trim() ?: ""
                applyFilterAndSearch()
            }
            override fun afterTextChanged(s: Editable?) {}
        })

        // Chips catégories avec mise en valeur visuelle
        updateChipSelection(binding.chipAll.id)

        binding.chipAll.setOnClickListener {
            currentCategoryFilter = "All"
            updateChipSelection(binding.chipAll.id)
            applyFilterAndSearch()
        }
        binding.chipTops.setOnClickListener {
            currentCategoryFilter = "Haut"
            updateChipSelection(binding.chipTops.id)
            applyFilterAndSearch()
        }
        binding.chipBottoms.setOnClickListener {
            currentCategoryFilter = "Bas"
            updateChipSelection(binding.chipBottoms.id)
            applyFilterAndSearch()
        }
        binding.chipDresses.setOnClickListener {
            currentCategoryFilter = "Robe"
            updateChipSelection(binding.chipDresses.id)
            applyFilterAndSearch()
        }
        binding.chipJackets.setOnClickListener {
            currentCategoryFilter = "Veste"
            updateChipSelection(binding.chipJackets.id)
            applyFilterAndSearch()
        }
        binding.chipShoes.setOnClickListener {
            currentCategoryFilter = "Chauss"
            updateChipSelection(binding.chipShoes.id)
            applyFilterAndSearch()
        }
        binding.chipAccessories.setOnClickListener {
            currentCategoryFilter = "Access"
            updateChipSelection(binding.chipAccessories.id)
            applyFilterAndSearch()
        }
        binding.chipCustomCategory.setOnClickListener {
            showCategoryPickerFilterDialog()
        }
    }

    private fun showCategoryPickerFilterDialog() {
        val categories = arrayOf(
            "Toutes les catégories",
            "Hauts (T-shirts, Chemises, Pulls)",
            "Bas (Pantalons, Jeans, Shorts)",
            "Robes & Combinaisons",
            "Vestes & Manteaux",
            "Chaussures & Baskets",
            "Accessoires"
        )

        MaterialAlertDialogBuilder(requireContext())
            .setTitle("Filtrer par catégorie")
            .setItems(categories) { _, which ->
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

    private fun updateChipSelection(selectedChipId: Int) {
        val primaryColor = ContextCompat.getColor(requireContext(), R.color.colorPrimary)
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
                    "Bas" -> item.typeVetement.categorieId == 2 ||
                            item.typeVetement.nom.contains("jean", true) ||
                            item.typeVetement.nom.contains("pantalon", true) ||
                            item.typeVetement.nom.contains("short", true) ||
                            item.typeVetement.nom.contains("jupe", true) ||
                            item.nom.contains("bas", true)
                    "Robe" -> item.typeVetement.categorieId == 3 ||
                            item.typeVetement.nom.contains("robe", true) ||
                            item.typeVetement.nom.contains("combinaison", true) ||
                            item.nom.contains("robe", true)
                    "Veste" -> item.typeVetement.categorieId == 4 ||
                            item.typeVetement.nom.contains("veste", true) ||
                            item.typeVetement.nom.contains("manteau", true) ||
                            item.nom.contains("veste", true) ||
                            item.nom.contains("blazer", true)
                    "Chauss" -> item.typeVetement.categorieId == 5 ||
                            item.typeVetement.nom.contains("basket", true) ||
                            item.typeVetement.nom.contains("botte", true) ||
                            item.typeVetement.nom.contains("chauss", true) ||
                            item.nom.contains("basket", true) ||
                            item.nom.contains("chauss", true)
                    "Access" -> item.typeVetement.categorieId == 6 ||
                            item.typeVetement.nom.contains("access", true) ||
                            item.nom.contains("access", true) ||
                            item.typeVetement.nom.contains("sac", true) ||
                            item.typeVetement.nom.contains("ceinture", true)
                    else -> item.typeVetement.nom.contains(currentCategoryFilter, ignoreCase = true) ||
                            item.nom.contains(currentCategoryFilter, ignoreCase = true)
                }
            }
        }

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
