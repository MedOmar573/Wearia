package com.wearia.app.ui.outfit

import android.os.Bundle
import android.view.LayoutInflater
import android.view.View
import android.view.ViewGroup
import android.widget.Toast
import androidx.fragment.app.Fragment
import androidx.lifecycle.lifecycleScope
import androidx.navigation.fragment.findNavController
import androidx.recyclerview.widget.LinearLayoutManager
import coil.load
import com.google.android.material.bottomsheet.BottomSheetDialog
import com.google.android.material.dialog.MaterialAlertDialogBuilder
import com.google.gson.Gson
import com.google.gson.reflect.TypeToken
import com.wearia.app.BuildConfig
import com.wearia.app.R
import com.wearia.app.WeariaApplication
import com.wearia.app.data.local.entity.TenueFavoriteEntity
import com.wearia.app.data.local.entity.VetementCacheEntity
import com.wearia.app.data.remote.dto.OutfitItemSimple
import com.wearia.app.databinding.DialogSelectClothingPieceBinding
import com.wearia.app.databinding.DialogSelectOccasionBinding
import com.wearia.app.databinding.FragmentOutfitDetailBinding
import com.wearia.app.databinding.ItemOutfitPieceDetailBinding
import com.wearia.app.repositories.ClothingRepository
import com.wearia.app.utils.addPressEffect
import kotlinx.coroutines.launch

/**
 * OutfitDetailFragment : Interface de détails d'une combinaison favorite.
 * - Flèche de retour vers « Tenues ».
 * - Affiche toutes les pièces composant la combinaison.
 * - Possibilité de retirer une pièce de la combinaison via son icône corbeille (comme dans dressing).
 * - Possibilité d'ajouter une pièce du dressing à cette combinaison.
 */
class OutfitDetailFragment : Fragment() {

    private var _binding: FragmentOutfitDetailBinding? = null
    private val binding get() = _binding!!
    private val gson = Gson()
    private var outfitId: Int = -1
    private var currentOutfit: TenueFavoriteEntity? = null
    private val clothingRepository = ClothingRepository()

    override fun onCreateView(inflater: LayoutInflater, container: ViewGroup?, savedInstanceState: Bundle?): View {
        _binding = FragmentOutfitDetailBinding.inflate(inflater, container, false)
        return binding.root
    }

    override fun onViewCreated(view: View, savedInstanceState: Bundle?) {
        super.onViewCreated(view, savedInstanceState)

        outfitId = arguments?.getInt("outfitId", -1) ?: -1

        // Flèche de retour vers l'interface « Tenues »
        binding.btnBack.addPressEffect()
        binding.btnBack.setOnClickListener {
            findNavController().popBackStack()
        }

        // Bouton pour ajouter une pièce à cette combinaison
        binding.btnAddPieceToOutfit.addPressEffect()
        binding.btnAddPieceToOutfit.setOnClickListener {
            showAddPieceDialog()
        }

        // Bouton pour modifier le type de combinaison (occasion)
        binding.btnEditOccasion.addPressEffect(0.85f)
        binding.btnEditOccasion.setOnClickListener {
            showEditOccasionDialog()
        }
        binding.tvSummaryOccasion.setOnClickListener {
            showEditOccasionDialog()
        }

        loadOutfitDetails()
    }

    private fun loadOutfitDetails() {
        if (outfitId == -1) {
            Toast.makeText(requireContext(), "Tenue introuvable.", Toast.LENGTH_SHORT).show()
            findNavController().popBackStack()
            return
        }

        viewLifecycleOwner.lifecycleScope.launch {
            val uid = WeariaApplication.instance.sessionManager.getUserId()
            val outfit = if (uid > 0) {
                WeariaApplication.instance.database.outfitDao().getFavoriteByIdForUser(outfitId, uid)
            } else null
            if (outfit == null) {
                Toast.makeText(requireContext(), "Tenue introuvable.", Toast.LENGTH_SHORT).show()
                findNavController().popBackStack()
                return@launch
            }

            currentOutfit = outfit
            displayOutfit(outfit)
        }
    }

    private fun displayOutfit(outfit: TenueFavoriteEntity) {
        val occ = outfit.occasion.lowercase().replaceFirstChar { it.uppercase() }
        binding.tvDetailTitle.text = "Combinaison • $occ"
        binding.tvSummaryOccasion.text = "Occasion • $occ"
        binding.tvSummaryStyle.text = if (occ.contains("Travail", ignoreCase = true) || occ.contains("Work", ignoreCase = true)) "Smart Casual" else "Casual"

        if (!outfit.weather.isNullOrBlank() || outfit.temperature != null) {
            val temp = outfit.temperature?.let { "${it.toInt()}°C" } ?: ""
            val w = outfit.weather ?: ""
            binding.tvSummaryWeather.text = "Météo adaptée : $temp $w".trim()
            binding.tvSummaryWeather.visibility = View.VISIBLE
        } else {
            binding.tvSummaryWeather.visibility = View.GONE
        }

        // Liste de toutes les pièces composant cette combinaison
        val items = parseOutfitItems(outfit.itemsJson)
        binding.tvSummaryPiecesCount.text = "Combinaison complète (${items.size} pièces)"
        binding.tvPiecesSectionTitle.text = "Pièces de la combinaison (${items.size})"

        binding.layoutPiecesList.removeAllViews()
        val baseUrl = BuildConfig.BASE_URL.trimEnd('/')

        if (items.isNotEmpty()) {
            val inflater = LayoutInflater.from(requireContext())
            items.forEach { item ->
                val pieceBinding = ItemOutfitPieceDetailBinding.inflate(inflater, binding.layoutPiecesList, false)

                pieceBinding.tvPieceName.text = item.name
                pieceBinding.tvPieceCategory.text = item.category ?: "Pièce"
                pieceBinding.tvPieceColor.text = item.color ?: "Standard"

                val fullImgUrl = item.imageUrl?.let {
                    if (it.startsWith("http")) it else "$baseUrl$it"
                }

                if (!fullImgUrl.isNullOrBlank()) {
                    pieceBinding.ivPieceImage.load(fullImgUrl) {
                        crossfade(true)
                        placeholder(R.drawable.bg_clothing_item_preview)
                        error(R.drawable.ic_hanger)
                    }
                } else {
                    pieceBinding.ivPieceImage.load(R.drawable.ic_hanger) {
                        crossfade(true)
                    }
                }

                // Bouton Corbeille pour retirer cette pièce de la combinaison
                pieceBinding.btnDeletePiece.addPressEffect(0.85f)
                pieceBinding.btnDeletePiece.setOnClickListener {
                    confirmRemovePiece(item)
                }

                binding.layoutPiecesList.addView(pieceBinding.root)
            }
        }
    }

    private fun confirmRemovePiece(pieceToRemove: OutfitItemSimple) {
        MaterialAlertDialogBuilder(requireContext())
            .setTitle("Retirer la pièce")
            .setMessage("Voulez-vous retirer '${pieceToRemove.name}' de cette combinaison ?")
            .setPositiveButton("Retirer") { _, _ ->
                performRemovePiece(pieceToRemove)
            }
            .setNegativeButton("Annuler", null)
            .show()
    }

    private fun performRemovePiece(pieceToRemove: OutfitItemSimple) {
        val outfit = currentOutfit ?: return
        val currentItems = parseOutfitItems(outfit.itemsJson)
        val updatedItems = currentItems.filter { it.id != pieceToRemove.id && it.name != pieceToRemove.name }

        viewLifecycleOwner.lifecycleScope.launch {
            val uid = WeariaApplication.instance.sessionManager.getUserId()
            if (updatedItems.isEmpty()) {
                // S'il n'y a plus aucune pièce, la combinaison est supprimée
                if (uid > 0) {
                    WeariaApplication.instance.database.outfitDao().deleteFavoriteByIdForUser(outfitId, uid)
                }
                Toast.makeText(requireContext(), "Combinaison supprimée", Toast.LENGTH_SHORT).show()
                try {
                    WeariaApplication.instance.apiService.deleteOutfit(
                        WeariaApplication.instance.sessionManager.getAuthHeader(),
                        outfitId
                    )
                } catch (e: Exception) {}
                findNavController().popBackStack()
            } else {
                val updatedJson = gson.toJson(updatedItems)
                if (uid > 0) {
                    WeariaApplication.instance.database.outfitDao().updateFavoriteItemsForUser(outfitId, uid, updatedJson)
                }

                val updatedOutfit = outfit.copy(itemsJson = updatedJson)
                currentOutfit = updatedOutfit
                Toast.makeText(requireContext(), "'${pieceToRemove.name}' retiré de la combinaison", Toast.LENGTH_SHORT).show()

                displayOutfit(updatedOutfit)

                try {
                    WeariaApplication.instance.apiService.removeItemFromOutfit(
                        WeariaApplication.instance.sessionManager.getAuthHeader(),
                        outfitId,
                        pieceToRemove.id
                    )
                } catch (e: Exception) {
                    // Silencieux
                }
            }
        }
    }

    /**
     * Ouvre la boîte de dialogue pour modifier l'occasion / le type de combinaison.
     */
    private fun showEditOccasionDialog() {
        val outfit = currentOutfit ?: return
        val dialog = BottomSheetDialog(requireContext())
        val sheetBinding = DialogSelectOccasionBinding.inflate(layoutInflater)
        dialog.setContentView(sheetBinding.root)

        sheetBinding.tvOccasionDialogTitle.text = "Modifier le type de combinaison"

        val occNorm = outfit.occasion.lowercase().trim()
            .replace("é", "e").replace("è", "e").replace("ê", "e")

        val initialChipId = when {
            occNorm.contains("universit") -> R.id.chip_dialog_university
            occNorm.contains("travail") || occNorm.contains("work") -> R.id.chip_dialog_work
            occNorm.contains("quotidien") || occNorm.contains("daily") -> R.id.chip_dialog_daily
            occNorm.contains("evenement") || occNorm.contains("event") -> R.id.chip_dialog_events
            else -> R.id.chip_dialog_outings
        }
        sheetBinding.chipGroupOccasionsDialog.check(initialChipId)

        var selectedOccasion = when (initialChipId) {
            R.id.chip_dialog_university -> "Université"
            R.id.chip_dialog_work -> "Travail"
            R.id.chip_dialog_daily -> "Quotidien"
            R.id.chip_dialog_events -> "Événements"
            else -> "Sortie"
        }

        sheetBinding.chipGroupOccasionsDialog.setOnCheckedStateChangeListener { _, checkedIds ->
            val id = checkedIds.firstOrNull() ?: return@setOnCheckedStateChangeListener
            selectedOccasion = when (id) {
                R.id.chip_dialog_university -> "Université"
                R.id.chip_dialog_work -> "Travail"
                R.id.chip_dialog_daily -> "Quotidien"
                R.id.chip_dialog_events -> "Événements"
                else -> "Sortie"
            }
        }

        sheetBinding.btnConfirmOccasion.setOnClickListener {
            dialog.dismiss()
            updateCombinationOccasion(selectedOccasion)
        }

        sheetBinding.btnCancelOccasion.setOnClickListener {
            dialog.dismiss()
        }

        dialog.show()
    }

    private fun updateCombinationOccasion(newOccasion: String) {
        val outfit = currentOutfit ?: return
        viewLifecycleOwner.lifecycleScope.launch {
            // 1. Mise à jour immédiate de l'objet et de toute l'interface (entête + carte résumé)
            val updated = outfit.copy(occasion = newOccasion)
            currentOutfit = updated
            displayOutfit(updated)

            // 2. Mise à jour dans Room (scopée à l'utilisateur connecté)
            val uid = WeariaApplication.instance.sessionManager.getUserId()
            val dao = WeariaApplication.instance.database.outfitDao()
            if (uid > 0) {
                val rows = dao.updateFavoriteOccasionForUser(outfitId, uid, newOccasion)
                if (rows == 0) {
                    dao.insertFavorite(updated.copy(userId = uid))
                }
            }

            // Notifier le retour arrière
            findNavController().previousBackStackEntry?.savedStateHandle?.set("outfit_updated", true)

            Toast.makeText(requireContext(), "Type de combinaison modifié : $newOccasion", Toast.LENGTH_SHORT).show()

            // 3. Synchronisation backend
            try {
                val token = WeariaApplication.instance.sessionManager.getAuthHeader()
                WeariaApplication.instance.apiService.updateOutfit(token, outfitId, occasion = newOccasion)
            } catch (e: Exception) {
                // Silencieux
            }
        }
    }

    /**
     * Ouvre une boîte de dialogue pour ajouter une pièce du dressing à cette combinaison.
     */
    private fun showAddPieceDialog() {
        val outfit = currentOutfit ?: return
        val currentItems = parseOutfitItems(outfit.itemsJson)
        val currentIds = currentItems.map { it.id }.toSet()
        val currentNames = currentItems.map { it.name.lowercase().trim() }.toSet()

        viewLifecycleOwner.lifecycleScope.launch {
            val uid = WeariaApplication.instance.sessionManager.getUserId()
            // Récupérer les vêtements du dressing depuis le cache Room de cet utilisateur
            var dressingClothes = if (uid > 0) {
                WeariaApplication.instance.database.clothingDao().getClothesListForUser(uid)
            } else emptyList()
            if (dressingClothes.isEmpty()) {
                val res = clothingRepository.getClothes()
                if (res is com.wearia.app.utils.Resource.Success && uid > 0) {
                    dressingClothes = WeariaApplication.instance.database.clothingDao().getClothesListForUser(uid)
                }
            }

            // Filtrer pour ne proposer que les vêtements NON présents dans la tenue
            val available = dressingClothes.filter { clothing ->
                !currentIds.contains(clothing.id) && !currentNames.contains(clothing.nom.lowercase().trim())
            }

            val dialog = BottomSheetDialog(requireContext())
            val sheetBinding = DialogSelectClothingPieceBinding.inflate(layoutInflater)
            dialog.setContentView(sheetBinding.root)

            if (available.isEmpty()) {
                sheetBinding.tvNoAvailableClothes.visibility = View.VISIBLE
                sheetBinding.rvAvailableClothes.visibility = View.GONE
            } else {
                sheetBinding.tvNoAvailableClothes.visibility = View.GONE
                sheetBinding.rvAvailableClothes.visibility = View.VISIBLE

                val adapter = SelectClothingAdapter(isMultiSelect = false) { selectedClothing, _ ->
                    dialog.dismiss()
                    addClothingToOutfit(selectedClothing)
                }
                sheetBinding.rvAvailableClothes.layoutManager = LinearLayoutManager(requireContext())
                sheetBinding.rvAvailableClothes.adapter = adapter
                adapter.submitList(available)
            }

            sheetBinding.btnCancelSelect.setOnClickListener {
                dialog.dismiss()
            }

            dialog.show()
        }
    }

    private fun addClothingToOutfit(clothing: VetementCacheEntity) {
        val outfit = currentOutfit ?: return
        val currentItems = parseOutfitItems(outfit.itemsJson)

        val newPiece = OutfitItemSimple(
            id = clothing.id,
            name = clothing.nom,
            category = clothing.categorie,
            color = clothing.couleur,
            imageUrl = clothing.photoUrl
        )

        val updatedItems = currentItems + newPiece
        val updatedJson = gson.toJson(updatedItems)

        viewLifecycleOwner.lifecycleScope.launch {
            val uid = WeariaApplication.instance.sessionManager.getUserId()
            // 1. Sauvegarde locale Room (scopée au compte)
            if (uid > 0) {
                WeariaApplication.instance.database.outfitDao().updateFavoriteItemsForUser(outfitId, uid, updatedJson)
            }

            // 2. Mise à jour mémoire et UI
            val updatedOutfit = outfit.copy(itemsJson = updatedJson)
            currentOutfit = updatedOutfit
            displayOutfit(updatedOutfit)

            Toast.makeText(requireContext(), "'${clothing.nom}' ajouté à la combinaison", Toast.LENGTH_SHORT).show()

            // 3. Synchronisation backend
            try {
                WeariaApplication.instance.apiService.addItemToOutfit(
                    WeariaApplication.instance.sessionManager.getAuthHeader(),
                    outfitId,
                    clothing.id
                )
            } catch (e: Exception) {
                // Silencieux
            }
        }
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
