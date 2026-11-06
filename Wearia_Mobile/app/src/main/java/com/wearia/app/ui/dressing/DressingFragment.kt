package com.wearia.app.ui.dressing

import android.net.Uri
import android.os.Bundle
import android.text.Editable
import android.text.TextWatcher
import android.view.*
import android.widget.Toast
import androidx.activity.result.contract.ActivityResultContracts
import androidx.appcompat.app.AlertDialog
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
import com.wearia.app.viewmodel.ClothingViewModel
import java.io.File

/**
 * DressingFragment : Écran principal du dressing virtuel (Maquette 6.jpg).
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

        // Chips catégories
        binding.chipAll.setOnClickListener {
            currentCategoryFilter = "All"
            applyFilterAndSearch()
        }
        binding.chipTops.setOnClickListener {
            currentCategoryFilter = "Tops"
            applyFilterAndSearch()
        }
        binding.chipBottoms.setOnClickListener {
            currentCategoryFilter = "Bottoms"
            applyFilterAndSearch()
        }
        binding.chipJackets.setOnClickListener {
            currentCategoryFilter = "Jackets"
            applyFilterAndSearch()
        }
        binding.chipShoes.setOnClickListener {
            currentCategoryFilter = "Shoes"
            applyFilterAndSearch()
        }
        binding.chipAccessories.setOnClickListener {
            currentCategoryFilter = "Accessories"
            applyFilterAndSearch()
        }
    }

    private fun applyFilterAndSearch() {
        var filtered = allClothes

        if (currentCategoryFilter != "All") {
            filtered = filtered.filter { item ->
                item.typeVetement.nom.contains(currentCategoryFilter, ignoreCase = true) ||
                item.nom.contains(currentCategoryFilter, ignoreCase = true)
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
        // FAB noir '+' : Ouvre directement la page d'ajout (7.jpg)
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

    private fun handleGalleryImage(uri: Uri) {
        try {
            val inputStream = requireContext().contentResolver.openInputStream(uri) ?: return
            val tempFile = File(requireContext().cacheDir, "gallery_import_${System.currentTimeMillis()}.jpg")
            tempFile.outputStream().use { output ->
                inputStream.copyTo(output)
            }
            viewModel.classifyImage(tempFile)

            viewModel.classifyState.observe(viewLifecycleOwner) { state ->
                if (state is Resource.Success && findNavController().currentDestination?.id == R.id.dressingFragment) {
                    val result = state.data
                    val bundle = Bundle().apply {
                        putString("imageUrl", result.imageUrl)
                        putString("category", result.category)
                        putString("color", result.color)
                        putInt("suggestedTypeId", result.suggestedTypeId ?: -1)
                        putInt("suggestedColorId", result.suggestedColorId ?: -1)
                    }
                    viewModel.resetClassifyState()
                    findNavController().navigate(R.id.action_dressing_to_addClothing, bundle)
                }
            }
        } catch (e: Exception) {
            Toast.makeText(requireContext(), "Erreur import : ${e.localizedMessage}", Toast.LENGTH_SHORT).show()
        }
    }

    private fun observeClothes() {
        viewModel.clothesList.observe(viewLifecycleOwner) { state ->
            binding.swipeRefresh.isRefreshing = false
            when (state) {
                is Resource.Loading -> {
                    binding.progressBar.visibility = View.VISIBLE
                    binding.tvEmpty.visibility = View.GONE
                }
                is Resource.Success -> {
                    binding.progressBar.visibility = View.GONE
                    allClothes = state.data
                    applyFilterAndSearch()
                }
                is Resource.Error -> {
                    binding.progressBar.visibility = View.GONE
                    Toast.makeText(requireContext(), state.message, Toast.LENGTH_SHORT).show()
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
            .setTitle("Supprimer le vêtement")
            .setMessage("Voulez-vous vraiment retirer '${clothing.nom}' de votre dressing ?")
            .setPositiveButton("Supprimer") { _, _ -> viewModel.deleteClothing(clothing.id) }
            .setNegativeButton("Annuler", null)
            .show()
    }

    override fun onDestroyView() {
        super.onDestroyView()
        _binding = null
    }
}
