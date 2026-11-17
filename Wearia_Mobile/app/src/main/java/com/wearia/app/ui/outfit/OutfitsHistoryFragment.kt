package com.wearia.app.ui.outfit

import android.os.Bundle
import android.view.LayoutInflater
import android.view.View
import android.view.ViewGroup
import androidx.core.content.ContextCompat
import androidx.fragment.app.Fragment
import androidx.lifecycle.lifecycleScope
import androidx.navigation.fragment.findNavController
import androidx.recyclerview.widget.GridLayoutManager
import com.wearia.app.R
import com.wearia.app.WeariaApplication
import com.wearia.app.data.local.entity.TenueFavoriteEntity
import com.wearia.app.databinding.FragmentMyOutfitsBinding
import com.wearia.app.utils.addPressEffect
import kotlinx.coroutines.flow.collectLatest
import kotlinx.coroutines.launch

/**
 * OutfitsHistoryFragment : Écran "Mes Tenues" modernisé avec Favoris et Historique.
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

        binding.tabFavorites.addPressEffect(0.98f)
        binding.tabHistory.addPressEffect(0.98f)

        adapter = OutfitsHistoryAdapter { outfit ->
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
            binding.tvTabFavorites.setTextColor(ContextCompat.getColor(requireContext(), R.color.colorPrimary))
            binding.indicatorFavorites.setBackgroundResource(R.drawable.bg_brand_gradient)
            binding.tvTabHistory.setTextColor(ContextCompat.getColor(requireContext(), R.color.colorTextSecondary))
            binding.indicatorHistory.setBackgroundColor(ContextCompat.getColor(requireContext(), android.R.color.transparent))
            filterAndDisplay()
        }

        binding.tabHistory.setOnClickListener {
            isFavoritesTab = false
            binding.tvTabHistory.setTextColor(ContextCompat.getColor(requireContext(), R.color.colorPrimary))
            binding.indicatorHistory.setBackgroundResource(R.drawable.bg_brand_gradient)
            binding.tvTabFavorites.setTextColor(ContextCompat.getColor(requireContext(), R.color.colorTextSecondary))
            binding.indicatorFavorites.setBackgroundColor(ContextCompat.getColor(requireContext(), android.R.color.transparent))
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
