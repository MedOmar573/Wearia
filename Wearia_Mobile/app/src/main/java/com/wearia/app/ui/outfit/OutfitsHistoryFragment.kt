package com.wearia.app.ui.outfit

import android.os.Bundle
import android.view.LayoutInflater
import android.view.View
import android.view.ViewGroup
import android.widget.Toast
import androidx.fragment.app.Fragment
import androidx.lifecycle.lifecycleScope
import androidx.navigation.fragment.findNavController
import androidx.recyclerview.widget.GridLayoutManager
import androidx.recyclerview.widget.LinearLayoutManager
import com.google.android.material.bottomsheet.BottomSheetDialog
import com.google.android.material.dialog.MaterialAlertDialogBuilder
import com.google.gson.Gson
import com.google.gson.reflect.TypeToken
import com.wearia.app.R
import com.wearia.app.WeariaApplication
import com.wearia.app.data.local.entity.TenueFavoriteEntity
import com.wearia.app.data.remote.dto.OutfitItemSimple
import com.wearia.app.data.remote.dto.TenueCreateRequest
import com.wearia.app.databinding.DialogCreateCustomOutfitBinding
import com.wearia.app.databinding.FragmentMyOutfitsBinding
import com.wearia.app.repositories.ClothingRepository
import com.wearia.app.repositories.OutfitRepository
import com.wearia.app.utils.addPressEffect
import kotlinx.coroutines.flow.collectLatest
import kotlinx.coroutines.launch

/**
 * OutfitsHistoryFragment : Écran principal « Mes Combinaisons Favorites ».
 * - Grille à 2 colonnes avec cartes et composition de pièces côte à côte.
 * - Pas de flèche de retour (écran racine).
 * - Suppression par clic sur la corbeille ou long-clic sur la carte.
 * - Clic sur la carte -> navigation vers l'interface de détails.
 * - Bouton flottant pour créer une combinaison favorite personnalisée selon le dressing.
 */
class OutfitsHistoryFragment : Fragment() {

    private var _binding: FragmentMyOutfitsBinding? = null
    private val binding get() = _binding!!
    private lateinit var adapter: OutfitsHistoryAdapter
    private val outfitRepository = OutfitRepository()
    private val clothingRepository = ClothingRepository()
    private val gson = Gson()

    private var allFavorites: List<TenueFavoriteEntity> = emptyList()
    private var currentFilter: String = "All"

    override fun onCreateView(inflater: LayoutInflater, container: ViewGroup?, savedInstanceState: Bundle?): View {
        _binding = FragmentMyOutfitsBinding.inflate(inflater, container, false)
        return binding.root
    }

    override fun onViewCreated(view: View, savedInstanceState: Bundle?) {
        super.onViewCreated(view, savedInstanceState)

        // Configuration de l'Adapter :
        // 1. Clic carte -> Rediriger vers l'interface de détails OutfitDetailFragment
        // 2. Clic Corbeille ou Long-Clic -> Confirmation et suppression
        adapter = OutfitsHistoryAdapter(
            onItemClick = { outfit ->
                val bundle = Bundle().apply {
                    putInt("outfitId", outfit.id)
                }
                findNavController().navigate(R.id.action_outfitsHistory_to_outfitDetail, bundle)
            },
            onDeleteClick = { outfit ->
                confirmDeleteOutfit(outfit)
            }
        )

        binding.rvOutfits.apply {
            layoutManager = GridLayoutManager(requireContext(), 2)
            adapter = this@OutfitsHistoryFragment.adapter
        }

        // Bouton Flottant pour créer une combinaison favorite depuis le dressing
        binding.fabCreateOutfit.addPressEffect()
        binding.fabCreateOutfit.setOnClickListener {
            showCreateCustomOutfitDialog()
        }

        setupChips()
        loadFavorites()

        // Rafraîchir immédiatement la liste des cartes si une tenue a été modifiée dans les détails
        findNavController().currentBackStackEntry?.savedStateHandle?.getLiveData<Boolean>("outfit_updated")
            ?.observe(viewLifecycleOwner) { updated ->
                if (updated == true) {
                    viewLifecycleOwner.lifecycleScope.launch {
                        val uid = WeariaApplication.instance.sessionManager.getUserId()
                        allFavorites = if (uid > 0) {
                            WeariaApplication.instance.database.outfitDao().getFavoritesListForUser(uid)
                        } else emptyList()
                        filterAndDisplay()
                    }
                }
            }
    }

    override fun onResume() {
        super.onResume()
        viewLifecycleOwner.lifecycleScope.launch {
            val uid = WeariaApplication.instance.sessionManager.getUserId()
            allFavorites = if (uid > 0) {
                WeariaApplication.instance.database.outfitDao().getFavoritesListForUser(uid)
            } else emptyList()
            filterAndDisplay()
        }
    }

    private fun setupChips() {
        binding.chipGroupOccasions.setOnCheckedStateChangeListener { _, checkedIds ->
            val checkedId = checkedIds.firstOrNull() ?: R.id.chip_occasion_all
            currentFilter = when (checkedId) {
                R.id.chip_occasion_university -> "Université"
                R.id.chip_occasion_work -> "Travail"
                R.id.chip_occasion_outings -> "Sorties"
                R.id.chip_occasion_events -> "Événements"
                R.id.chip_occasion_daily -> "Quotidien"
                else -> "Toutes"
            }
            filterAndDisplay()
        }
    }

    private fun loadFavorites() {
        val uid = WeariaApplication.instance.sessionManager.getUserId()
        if (uid <= 0) {
            allFavorites = emptyList()
            filterAndDisplay()
            return
        }

        // 1. Observer uniquement les favoris Room du compte connecté (isolation stricte par userId)
        viewLifecycleOwner.lifecycleScope.launch {
            WeariaApplication.instance.database.outfitDao().getFavoritesForUser(uid).collectLatest { list ->
                allFavorites = list
                filterAndDisplay()
            }
        }

        // 2. Synchroniser depuis le serveur (remplace atomiquement les favoris de ce compte)
        viewLifecycleOwner.lifecycleScope.launch {
            try {
                outfitRepository.getOutfits(favorisOnly = true)
            } catch (e: Exception) {
                // Mode hors-ligne : données Room isolées de cet utilisateur déjà affichées
            }
        }
    }

    private fun confirmDeleteOutfit(outfit: TenueFavoriteEntity) {
        MaterialAlertDialogBuilder(requireContext())
            .setTitle("Supprimer la combinaison")
            .setMessage("Voulez-vous retirer cette combinaison de vos favoris ?")
            .setPositiveButton("Supprimer") { _, _ ->
                unfavoriteOutfit(outfit)
            }
            .setNegativeButton("Annuler", null)
            .show()
    }

    private fun unfavoriteOutfit(outfit: TenueFavoriteEntity) {
        viewLifecycleOwner.lifecycleScope.launch {
            val uid = WeariaApplication.instance.sessionManager.getUserId()
            // Suppression immédiate du cache Room pour ce compte
            if (uid > 0) {
                WeariaApplication.instance.database.outfitDao().deleteFavoriteByIdForUser(outfit.id, uid)
            }
            Toast.makeText(requireContext(), "Combinaison retirée des favoris", Toast.LENGTH_SHORT).show()

            // Synchronisation backend
            try {
                outfitRepository.toggleFavorite(outfit.id, false)
            } catch (e: Exception) {
                // Silencieux
            }
        }
    }

    /**
     * Ouvre la boîte de dialogue pour composer et enregistrer une nouvelle combinaison favorite
     * à partir des vêtements du dressing.
     */
    private fun showCreateCustomOutfitDialog() {
        viewLifecycleOwner.lifecycleScope.launch {
            val uid = WeariaApplication.instance.sessionManager.getUserId()
            var clothes = if (uid > 0) {
                WeariaApplication.instance.database.clothingDao().getClothesListForUser(uid)
            } else emptyList()
            if (clothes.isEmpty()) {
                val res = clothingRepository.getClothes()
                if (res is com.wearia.app.utils.Resource.Success && uid > 0) {
                    clothes = WeariaApplication.instance.database.clothingDao().getClothesListForUser(uid)
                }
            }

            val dialog = BottomSheetDialog(requireContext())
            val sheetBinding = DialogCreateCustomOutfitBinding.inflate(layoutInflater)
            dialog.setContentView(sheetBinding.root)

            if (clothes.isEmpty()) {
                sheetBinding.tvEmptyDressing.visibility = View.VISIBLE
                sheetBinding.rvDressingClothes.visibility = View.GONE
                sheetBinding.btnSaveCustomOutfit.isEnabled = false
            } else {
                sheetBinding.tvEmptyDressing.visibility = View.GONE
                sheetBinding.rvDressingClothes.visibility = View.VISIBLE

                lateinit var selectAdapter: SelectClothingAdapter
                selectAdapter = SelectClothingAdapter(isMultiSelect = true) { _, _ ->
                    val count = selectAdapter.getSelectedItems().size
                    sheetBinding.btnSaveCustomOutfit.isEnabled = count >= 1
                    sheetBinding.btnSaveCustomOutfit.text = if (count > 0) {
                        "Enregistrer la combinaison ($count pièce${if (count > 1) "s" else ""})"
                    } else {
                        "Enregistrer la combinaison (0 pièce)"
                    }
                }

                sheetBinding.rvDressingClothes.layoutManager = LinearLayoutManager(requireContext())
                sheetBinding.rvDressingClothes.adapter = selectAdapter
                selectAdapter.submitList(clothes)

                sheetBinding.btnSaveCustomOutfit.setOnClickListener {
                    val selectedClothes = selectAdapter.getSelectedItems()
                    if (selectedClothes.isEmpty()) return@setOnClickListener

                    // Récupérer l'occasion sélectionnée
                    val selectedOccasion = when (sheetBinding.chipGroupCustomOccasion.checkedChipId) {
                        R.id.chip_custom_university -> "Université"
                        R.id.chip_custom_work -> "Travail"
                        R.id.chip_custom_outings -> "Sortie"
                        R.id.chip_custom_events -> "Événements"
                        else -> "Quotidien"
                    }

                    val selectedIds = selectedClothes.map { it.id }.toSet()

                    // Vérifier si la combinaison existe déjà dans les favoris
                    val isDuplicate = allFavorites.any { fav ->
                        val favItems = parseOutfitItems(fav.itemsJson)
                        val favIds = favItems.map { it.id }.toSet()
                        favIds.isNotEmpty() && favIds == selectedIds
                    }

                    if (isDuplicate) {
                        Toast.makeText(requireContext(), "Cette combinaison existe déjà dans vos favoris", Toast.LENGTH_SHORT).show()
                        return@setOnClickListener
                    }

                    dialog.dismiss()
                    saveCustomOutfit(selectedOccasion, selectedClothes)
                }
            }

            sheetBinding.btnCancelCustom.setOnClickListener {
                dialog.dismiss()
            }

            dialog.show()
        }
    }

    private fun saveCustomOutfit(occasion: String, clothes: List<com.wearia.app.data.local.entity.VetementCacheEntity>) {
        viewLifecycleOwner.lifecycleScope.launch {
            val uid = WeariaApplication.instance.sessionManager.getUserId()
            if (uid <= 0) return@launch

            val piecesSimple = clothes.map {
                OutfitItemSimple(
                    id = it.id,
                    name = it.nom,
                    category = it.categorie,
                    color = it.couleur,
                    imageUrl = it.photoUrl
                )
            }
            val itemsJson = gson.toJson(piecesSimple)
            val generatedLocalId = (System.currentTimeMillis() % Int.MAX_VALUE).toInt()

            // 1. Sauvegarde locale immédiate (Room, strictement scopée au userId)
            val localEntity = TenueFavoriteEntity(
                id = generatedLocalId,
                userId = uid,
                occasion = occasion,
                temperature = null,
                weather = null,
                score = 100,
                explanation = "Combinaison personnalisée créée depuis mon dressing.",
                itemsJson = itemsJson,
                cachedAt = System.currentTimeMillis()
            )
            WeariaApplication.instance.database.outfitDao().insertFavorite(localEntity)
            Toast.makeText(requireContext(), "Combinaison ajoutée à vos favoris !", Toast.LENGTH_SHORT).show()

            // 2. Synchronisation backend
            try {
                val token = WeariaApplication.instance.sessionManager.getAuthHeader()
                val request = TenueCreateRequest(
                    occasion = occasion,
                    vetement_ids = clothes.map { it.id },
                    estFavorite = true
                )
                val response = WeariaApplication.instance.apiService.createOutfit(token, request)
                if (response.isSuccessful && response.body() != null) {
                    val serverId = response.body()!!.id
                    if (serverId != generatedLocalId) {
                        WeariaApplication.instance.database.outfitDao().deleteFavoriteByIdForUser(generatedLocalId, uid)
                        WeariaApplication.instance.database.outfitDao().insertFavorite(localEntity.copy(id = serverId))
                    }
                }
            } catch (e: Exception) {
                // Silencieux
            }
        }
    }

    private fun filterAndDisplay() {
        val deduplicated = deduplicateFavorites(allFavorites)

        var filtered = deduplicated
        if (currentFilter != "Toutes" && currentFilter != "All") {
            filtered = filtered.filter { outfit -> matchesOccasionFilter(outfit.occasion, currentFilter) }
        }

        adapter.submitList(filtered.toList())
        binding.tvEmpty.visibility = if (filtered.isEmpty()) View.VISIBLE else View.GONE
    }

    private fun matchesOccasionFilter(outfitOccasion: String, filter: String): Boolean {
        if (filter == "Toutes" || filter == "All") return true
        val occ = outfitOccasion.lowercase().trim()
            .replace("é", "e")
            .replace("è", "e")
            .replace("ê", "e")
            .replace("ë", "e")

        return when (filter) {
            "Université" -> occ.contains("universit") || occ.contains("etude") || occ.contains("cours") || occ.contains("fac")
            "Travail" -> occ.contains("travail") || occ.contains("work") || occ.contains("bureau") || occ.contains("pro")
            "Sorties" -> occ.contains("sortie") || occ.contains("outing") || occ.contains("soiree") || occ.contains("fete")
            "Événements" -> occ.contains("evenement") || occ.contains("event") || occ.contains("gala") || occ.contains("mariage")
            "Quotidien" -> occ.contains("quotidien") || occ.contains("daily") || occ.contains("casual") || occ.contains("tous les jours")
            else -> occ.contains(filter.lowercase())
        }
    }

    private fun deduplicateFavorites(list: List<TenueFavoriteEntity>): List<TenueFavoriteEntity> {
        val seenCombos = mutableSetOf<Set<Int>>()
        val uniqueList = mutableListOf<TenueFavoriteEntity>()

        for (outfit in list) {
            val items = parseOutfitItems(outfit.itemsJson)
            val ids = items.map { it.id }.toSet()
            if (ids.isEmpty()) {
                uniqueList.add(outfit)
            } else if (!seenCombos.contains(ids)) {
                seenCombos.add(ids)
                uniqueList.add(outfit)
            }
        }
        return uniqueList
    }

    private fun parseOutfitItems(json: String?): List<OutfitItemSimple> {
        if (json.isNullOrBlank()) return emptyList()
        return try {
            val type = object : TypeToken<List<OutfitItemSimple>>() {}.type
            val parsed: List<OutfitItemSimple>? = gson.fromJson(json, type)
            if (parsed != null && parsed.isNotEmpty() && parsed.firstOrNull()?.name != null) {
                parsed
            } else {
                emptyList()
            }
        } catch (e: Exception) {
            try {
                val typeStr = object : TypeToken<List<String>>() {}.type
                val names: List<String>? = gson.fromJson(json, typeStr)
                names?.mapIndexed { index, name ->
                    OutfitItemSimple(id = index, name = name, category = null, color = null, imageUrl = null)
                } ?: emptyList()
            } catch (e2: Exception) {
                emptyList()
            }
        }
    }

    override fun onDestroyView() {
        super.onDestroyView()
        _binding = null
    }
}
