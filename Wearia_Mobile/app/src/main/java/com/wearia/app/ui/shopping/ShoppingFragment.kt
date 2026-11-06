package com.wearia.app.ui.shopping

import android.os.Bundle
import android.view.LayoutInflater
import android.view.View
import android.view.ViewGroup
import android.widget.Toast
import androidx.fragment.app.Fragment
import androidx.fragment.app.viewModels
import androidx.recyclerview.widget.LinearLayoutManager
import com.wearia.app.databinding.FragmentShoppingBinding
import com.wearia.app.utils.Resource
import com.wearia.app.viewmodel.ProfileViewModel

/**
 * ShoppingFragment : Écran Personal Shopper IA (Sprint 3 / Démonstration).
 */
class ShoppingFragment : Fragment() {

    private var _binding: FragmentShoppingBinding? = null
    private val binding get() = _binding!!
    private val viewModel: ProfileViewModel by viewModels { ProfileViewModel.Factory() }
    private lateinit var adapter: ShoppingAdapter

    override fun onCreateView(inflater: LayoutInflater, container: ViewGroup?, savedInstanceState: Bundle?): View {
        _binding = FragmentShoppingBinding.inflate(inflater, container, false)
        return binding.root
    }

    override fun onViewCreated(view: View, savedInstanceState: Bundle?) {
        super.onViewCreated(view, savedInstanceState)

        adapter = ShoppingAdapter()
        binding.rvShopping.apply {
            layoutManager = LinearLayoutManager(requireContext())
            adapter = this@ShoppingFragment.adapter
        }

        viewModel.loadShoppingSuggestions()

        viewModel.suggestions.observe(viewLifecycleOwner) { state ->
            when (state) {
                is Resource.Loading -> binding.progressBar.visibility = View.VISIBLE
                is Resource.Success -> {
                    binding.progressBar.visibility = View.GONE
                    adapter.submitList(state.data)
                }
                is Resource.Error -> {
                    binding.progressBar.visibility = View.GONE
                    Toast.makeText(requireContext(), state.message, Toast.LENGTH_SHORT).show()
                }
            }
        }

        binding.btnSearchShopping.setOnClickListener {
            val need = binding.etShoppingNeed.text.toString().trim()
            viewModel.loadShoppingSuggestions(if (need.isNotEmpty()) need else null)
        }
    }

    override fun onDestroyView() {
        super.onDestroyView()
        _binding = null
    }
}

