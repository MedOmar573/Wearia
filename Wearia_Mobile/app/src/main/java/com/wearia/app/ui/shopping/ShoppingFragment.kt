package com.wearia.app.ui.shopping

import android.os.Bundle
import android.view.LayoutInflater
import android.view.View
import android.view.ViewGroup
import android.view.inputmethod.EditorInfo
import android.widget.Toast
import androidx.fragment.app.Fragment
import androidx.fragment.app.viewModels
import androidx.recyclerview.widget.LinearLayoutManager
import com.wearia.app.databinding.FragmentShoppingBinding
import com.wearia.app.utils.Resource
import com.wearia.app.utils.SessionManager
import com.wearia.app.utils.addPressEffect
import com.wearia.app.viewmodel.ShopperViewModel

/**
 * ShoppingFragment : Écran AI Shopper Wearia.
 * Interface épurée : prompt style/occasion + budget libre + liste de tenues réelles.
 */
class ShoppingFragment : Fragment() {

    private var _binding: FragmentShoppingBinding? = null
    private val binding get() = _binding!!
    private val viewModel: ShopperViewModel by viewModels { ShopperViewModel.Factory() }
    private lateinit var outfitAdapter: ShopperOutfitAdapter

    override fun onCreateView(
        inflater: LayoutInflater,
        container: ViewGroup?,
        savedInstanceState: Bundle?
    ): View {
        _binding = FragmentShoppingBinding.inflate(inflater, container, false)
        return binding.root
    }

    override fun onViewCreated(view: View, savedInstanceState: Bundle?) {
        super.onViewCreated(view, savedInstanceState)

        binding.btnGenerateOutfits.addPressEffect()

        setupRecyclerView()
        setupListeners()
        observeViewModel()

        // Valeurs par défaut
        binding.etShopperPrompt.setText("Tenue streetwear noire pour l'université")
        binding.etShopperBudget.setText("250")
    }

    private fun setupRecyclerView() {
        outfitAdapter = ShopperOutfitAdapter()
        binding.rvShopperOutfits.apply {
            layoutManager = LinearLayoutManager(requireContext())
            adapter = outfitAdapter
        }
    }

    private fun setupListeners() {
        // Bouton principal
        binding.btnGenerateOutfits.setOnClickListener {
            triggerSearchFromInputs()
        }

        // Touche Entrée du clavier sur le prompt
        binding.etShopperPrompt.setOnEditorActionListener { _, actionId, _ ->
            if (actionId == EditorInfo.IME_ACTION_NEXT || actionId == EditorInfo.IME_ACTION_DONE) {
                binding.etShopperBudget.requestFocus()
                true
            } else false
        }

        // Touche Entrée du clavier sur le budget
        binding.etShopperBudget.setOnEditorActionListener { _, actionId, _ ->
            if (actionId == EditorInfo.IME_ACTION_DONE) {
                triggerSearchFromInputs()
                true
            } else false
        }

        // Chips de budget rapide
        binding.chipBudget150.setOnClickListener { setQuickBudget(150) }
        binding.chipBudget200.setOnClickListener { setQuickBudget(200) }
        binding.chipBudget250.setOnClickListener { setQuickBudget(250) }
        binding.chipBudget350.setOnClickListener { setQuickBudget(350) }
        binding.chipBudget500.setOnClickListener { setQuickBudget(500) }
    }

    private fun setQuickBudget(amount: Int) {
        binding.etShopperBudget.setText(amount.toString())
    }

    private fun triggerSearchFromInputs() {
        val prompt = binding.etShopperPrompt.text.toString().trim()
        val budgetStr = binding.etShopperBudget.text.toString().trim()

        if (prompt.isEmpty()) {
            Toast.makeText(
                requireContext(),
                "Veuillez préciser le style ou l'occasion souhaitée.",
                Toast.LENGTH_SHORT
            ).show()
            return
        }

        val budget = budgetStr.toFloatOrNull()
        executeSearch(prompt, budget)
    }

    private fun executeSearch(prompt: String, budget: Float?) {
        val genre = try {
            SessionManager(requireContext()).getUserGenre()
        } catch (e: Exception) {
            "HOMME"
        }
        viewModel.generateOutfits(prompt, budget, genre)
    }

    private fun observeViewModel() {
        viewModel.shopperResult.observe(viewLifecycleOwner) { state ->
            when (state) {
                is Resource.Loading -> {
                    binding.llLoadingAi.visibility = View.VISIBLE
                    binding.tvEmptyShopper.visibility = View.GONE
                    binding.tvOutfitsHeader.visibility = View.GONE
                    binding.tvLoadingStatus.text =
                        "Recherche d'articles réels chez Exist, Zen, Bershka, Zara..."
                }

                is Resource.Success -> {
                    binding.llLoadingAi.visibility = View.GONE
                    val result = state.data

                    outfitAdapter.submitList(result.tenues)

                    if (result.tenues.isEmpty()) {
                        binding.tvEmptyShopper.text =
                            "Aucune tenue n'a pu être composée avec ce budget. Essayez d'augmenter le budget ou d'ajuster le style."
                        binding.tvEmptyShopper.visibility = View.VISIBLE
                        binding.tvOutfitsHeader.visibility = View.GONE
                    } else {
                        binding.tvEmptyShopper.visibility = View.GONE
                        binding.tvOutfitsHeader.visibility = View.VISIBLE
                        val nb = result.nbTenuesTrouvees
                        binding.tvOutfitsHeader.text =
                            if (nb > 0) "$nb tenue${if (nb > 1) "s" else ""} composée${if (nb > 1) "s" else ""} pour vous"
                            else "Tenues composées pour vous"
                    }
                }

                is Resource.Error -> {
                    binding.llLoadingAi.visibility = View.GONE
                    binding.tvEmptyShopper.text = state.message
                    binding.tvEmptyShopper.visibility = View.VISIBLE
                    binding.tvOutfitsHeader.visibility = View.GONE
                    Toast.makeText(requireContext(), state.message, Toast.LENGTH_LONG).show()
                }
            }
        }
    }

    override fun onDestroyView() {
        super.onDestroyView()
        _binding = null
    }
}
