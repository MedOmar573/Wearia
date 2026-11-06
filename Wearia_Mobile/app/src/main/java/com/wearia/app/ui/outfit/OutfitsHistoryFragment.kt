package com.wearia.app.ui.outfit

import android.os.Bundle
import android.view.LayoutInflater
import android.view.View
import android.view.ViewGroup
import androidx.fragment.app.Fragment
import androidx.lifecycle.lifecycleScope
import androidx.navigation.fragment.findNavController
import androidx.recyclerview.widget.GridLayoutManager
import com.wearia.app.R
import com.wearia.app.WeariaApplication
import com.wearia.app.data.local.entity.TenueFavoriteEntity
import com.wearia.app.databinding.FragmentMyOutfitsBinding
import kotlinx.coroutines.flow.collectLatest
import kotlinx.coroutines.launch

/**
 * OutfitsHistoryFragment : Écran "My Outfits" avec Favoris et Historique (Maquette 11.jpg).
 */
class OutfitsHistoryFragment : Fragment() {

    private var _binding: FragmentMyOutfitsBinding? = null
    private val binding get() = _binding!!
    private lateinit var adapter: OutfitsHistoryAdapter

    private var allFavorites: List<TenueFavoriteEntity> = emptyList()
    private var currentFilter: String = "All"
    private var isFavoritesTab: Boolean = true

    override fun onCreateView(inflater: LayoutInflater, container: ViewGroup?, savedInstanceState: Bundle?): View {
        _binding = FragmentMyOutfitsBinding.inflate(inflater, container, false)
        return binding.root
    }

    override fun onViewCreated(view: View, savedInstanceState: Bundle?) {
        super.onViewCreated(view, savedInstanceState)

        adapter = OutfitsHistoryAdapter { outfit ->
            // Ouvrir l'écran de détail / recommandation de cette tenue
            findNavController().navigate(R.id.outfitRecommendationFragment)
        }

        binding.rvOutfits.apply {
            layoutManager = GridLayoutManager(requireContext(), 2)
            adapter = this@OutfitsHistoryFragment.adapter
        }

        setupTabs()
        setupChips()
        loadFavoritesFromRoom()
    }

    private fun setupTabs() {
        binding.tabFavorites.setOnClickListener {
            isFavoritesTab = true
            binding.tvTabFavorites.setTextColor(resources.getColor(R.color.colorTextPrimary, null))
            binding.indicatorFavorites.setBackgroundColor(resources.getColor(R.color.colorPrimary, null))
            binding.tvTabHistory.setTextColor(resources.getColor(R.color.colorTextSecondary, null))
            binding.indicatorHistory.setBackgroundColor(resources.getColor(android.R.color.transparent, null))
            filterAndDisplay()
        }

        binding.tabHistory.setOnClickListener {
            isFavoritesTab = false
            binding.tvTabHistory.setTextColor(resources.getColor(R.color.colorTextPrimary, null))
            binding.indicatorHistory.setBackgroundColor(resources.getColor(R.color.colorPrimary, null))
            binding.tvTabFavorites.setTextColor(resources.getColor(R.color.colorTextSecondary, null))
            binding.indicatorFavorites.setBackgroundColor(resources.getColor(android.R.color.transparent, null))
            filterAndDisplay()
        }
    }

    private fun setupChips() {
        binding.chipOccasionAll.setOnClickListener {
            currentFilter = "All"
            filterAndDisplay()
        }
        binding.chipOccasionUniversity.setOnClickListener {
            currentFilter = "University"
            filterAndDisplay()
        }
        binding.chipOccasionWork.setOnClickListener {
            currentFilter = "Work"
            filterAndDisplay()
        }
        binding.chipOccasionOutings.setOnClickListener {
            currentFilter = "Outings"
            filterAndDisplay()
        }
        binding.chipOccasionEvents.setOnClickListener {
            currentFilter = "Events"
            filterAndDisplay()
        }
    }

    private fun loadFavoritesFromRoom() {
        viewLifecycleOwner.lifecycleScope.launch {
            WeariaApplication.instance.database.outfitDao().getAllFavorites().collectLatest { list ->
                allFavorites = list
                filterAndDisplay()
            }
        }
    }

    private fun filterAndDisplay() {
        var filtered = allFavorites

        if (currentFilter != "All") {
            filtered = filtered.filter { it.occasion.contains(currentFilter, ignoreCase = true) }
        }

        adapter.submitList(filtered)
        binding.tvEmpty.visibility = if (filtered.isEmpty()) View.VISIBLE else View.GONE
    }

    override fun onDestroyView() {
        super.onDestroyView()
        _binding = null
    }
}

