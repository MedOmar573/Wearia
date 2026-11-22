package com.wearia.app.ui.shopping

import android.content.res.ColorStateList
import android.graphics.Color
import android.os.Bundle
import android.view.Gravity
import android.view.LayoutInflater
import android.view.View
import android.view.ViewGroup
import android.view.inputmethod.EditorInfo
import android.widget.ArrayAdapter
import android.widget.FrameLayout
import android.widget.LinearLayout
import android.widget.TextView
import android.widget.Toast
import androidx.core.content.ContextCompat
import androidx.core.graphics.ColorUtils
import androidx.fragment.app.Fragment
import androidx.fragment.app.viewModels
import androidx.recyclerview.widget.LinearLayoutManager
import com.wearia.app.R
import com.wearia.app.data.remote.dto.CouleurResponse
import com.wearia.app.data.remote.dto.ShopperPromptRequest
import com.wearia.app.data.remote.dto.TypeVetementResponse
import com.wearia.app.databinding.FragmentShoppingBinding
import com.wearia.app.utils.Resource
import com.wearia.app.utils.SessionManager
import com.wearia.app.utils.addPressEffect
import com.wearia.app.viewmodel.ProfileViewModel
import com.wearia.app.viewmodel.ShopperViewModel

/**
 * ShoppingFragment : Écran AI Shopper en mode sélection d'articles individuels.
 * - Genre issu du compte connecté (HOMME ou FEMME, + compatibilité MIXTE)
 * - Type de vêtement chargé dynamiquement depuis la BDD selon le genre
 * - Couleurs préférées et non préférées associées au compte représentées en cercles ronds
 * - Budget maximum strict respecté sur chaque article proposé
 * - Résultats : liste d'articles individuels du type demandé (sans combinaison multi-pièces)
 */
class ShoppingFragment : Fragment() {

    private var _binding: FragmentShoppingBinding? = null
    private val binding get() = _binding!!
    private val viewModel: ShopperViewModel by viewModels { ShopperViewModel.Factory() }
    private val profileViewModel: ProfileViewModel by viewModels { ProfileViewModel.Factory() }
    private lateinit var articleAdapter: ShopperArticleAdapter

    private var availableTypes: List<TypeVetementResponse> = emptyList()
    private var referentialColors: List<CouleurResponse> = emptyList()
    private var accountPreferredColors: List<CouleurResponse> = emptyList()
    private var accountAvoidedColors: List<CouleurResponse> = emptyList()
    private var loadedFromProfileApi: Boolean = false
    private var accountGenre: String = "HOMME"
    private var activeUserId: Int = -1

    companion object {
        private val EXCLUDED_TYPES = setOf("ceinture", "écharpe", "echarpe", "montre")
    }

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
        binding.btnRegenerateOutfits.addPressEffect()

        setupRecyclerView()
        setupListeners()
        observeReferentials()
        observeViewModel()

        binding.etShopperBudget.setText("150")
        syncForCurrentAccount(forceReloadProfile = true)

        profileViewModel.profileState.observe(viewLifecycleOwner) { state ->
            if (state is Resource.Success) {
                val user = state.data
                // Ignorer si le profil reçu ne correspond pas au compte actif
                val currentUid = SessionManager(requireContext()).getUserId()
                if (currentUid > 0 && user.id != currentUid) {
                    return@observe
                }
                loadedFromProfileApi = true
                accountPreferredColors = user.preferencesCouleur
                    .filter { it.typePreference.equals("AIME", ignoreCase = true) }
                    .map { it.couleur }
                    .distinctBy { it.id }
                accountAvoidedColors = user.preferencesCouleur
                    .filter { it.typePreference.equals("EVITE", ignoreCase = true) }
                    .map { it.couleur }
                    .distinctBy { it.id }

                // Synchroniser le cache local de session avec les préférences réelles du compte
                val session = SessionManager(requireContext())
                session.savePreferredColors(accountPreferredColors.map { it.nom }.toSet())
                session.saveAvoidedColors(accountAvoidedColors.map { it.nom }.toSet())

                renderAccountColorCircles()

                val updatedGenre = user.genre?.uppercase()
                if (!updatedGenre.isNullOrBlank() && updatedGenre != accountGenre) {
                    refreshAccountGenreAndReferentials()
                }
            }
        }
    }

    override fun onResume() {
        super.onResume()
        syncForCurrentAccount(forceReloadProfile = false)
    }

    private fun syncForCurrentAccount(forceReloadProfile: Boolean) {
        val currentUid = try {
            SessionManager(requireContext()).getUserId()
        } catch (_: Exception) {
            -1
        }
        val accountChanged = currentUid != activeUserId
        if (accountChanged) {
            activeUserId = currentUid
            loadedFromProfileApi = false
            accountPreferredColors = emptyList()
            accountAvoidedColors = emptyList()
            renderAccountColorCircles()
        }

        viewModel.syncWithUser(currentUid)

        if (accountChanged || forceReloadProfile) {
            refreshAccountGenreAndReferentials()
            profileViewModel.loadProfile()
        }
    }

    private fun refreshAccountGenreAndReferentials() {
        accountGenre = try {
            SessionManager(requireContext()).getUserGenre().uppercase()
        } catch (_: Exception) {
            "HOMME"
        }
        if (accountGenre !in setOf("HOMME", "FEMME")) {
            accountGenre = "HOMME"
        }

        val genreLabel = if (accountGenre == "FEMME") "Femme" else "Homme"
        binding.tvShopperAccountGenre.text = "Profil actif : $genreLabel · Articles $genreLabel & Mixte"
        profileViewModel.loadReferentials(accountGenre)
    }

    private fun setupRecyclerView() {
        articleAdapter = ShopperArticleAdapter()
        binding.rvShopperOutfits.apply {
            layoutManager = LinearLayoutManager(requireContext())
            adapter = articleAdapter
        }
    }

    private fun setupListeners() {
        binding.btnGenerateOutfits.setOnClickListener {
            triggerSearchFromInputs()
        }
        binding.btnRegenerateOutfits.setOnClickListener {
            viewModel.lastRequest?.let { viewModel.searchArticles(it, loadMoreUnseen = true) }
        }

        binding.etShopperBudget.setOnEditorActionListener { _, actionId, _ ->
            if (actionId == EditorInfo.IME_ACTION_DONE) {
                triggerSearchFromInputs()
                true
            } else false
        }

        binding.chipBudget80.setOnClickListener { setQuickBudget(80) }
        binding.chipBudget120.setOnClickListener { setQuickBudget(120) }
        binding.chipBudget150.setOnClickListener { setQuickBudget(150) }
        binding.chipBudget200.setOnClickListener { setQuickBudget(200) }
        binding.chipBudget300.setOnClickListener { setQuickBudget(300) }
    }

    private fun setQuickBudget(amount: Int) {
        binding.etShopperBudget.setText(amount.toString())
        binding.etShopperBudget.error = null
    }

    private fun observeReferentials() {
        // 1. Types de vêtements dynamiques (filtrés selon le genre du compte)
        profileViewModel.typesState.observe(viewLifecycleOwner) { state ->
            when (state) {
                is Resource.Loading -> {
                    binding.spinnerShopperType.isEnabled = false
                    binding.tvShopperTypeStatus.text = "Chargement des types de vêtements..."
                    binding.tvShopperTypeStatus.visibility = View.VISIBLE
                    setSpinnerPlaceholder(binding.spinnerShopperType, "Chargement...")
                }
                is Resource.Success -> {
                    val cleaned = state.data.filterNot {
                        it.nom.trim().lowercase() in EXCLUDED_TYPES
                    }
                    val filtered = if (accountGenre == "HOMME") {
                        cleaned.filterNot {
                            it.nom.equals("Robe", true) ||
                                it.nom.equals("Jupe", true) ||
                                it.nom.equals("Bottes", true)
                        }
                    } else {
                        cleaned
                    }
                    availableTypes = filtered
                    if (filtered.isEmpty()) {
                        binding.spinnerShopperType.isEnabled = false
                        binding.tvShopperTypeStatus.text = "Aucun type de vêtement disponible en base."
                        binding.tvShopperTypeStatus.visibility = View.VISIBLE
                        setSpinnerPlaceholder(binding.spinnerShopperType, "Aucun type disponible")
                    } else {
                        binding.spinnerShopperType.isEnabled = true
                        binding.tvShopperTypeStatus.visibility = View.GONE
                        val names = filtered.map { it.nom }
                        val adapter = ArrayAdapter(
                            requireContext(),
                            android.R.layout.simple_spinner_dropdown_item,
                            names
                        )
                        binding.spinnerShopperType.adapter = adapter
                    }
                }
                is Resource.Error -> {
                    availableTypes = emptyList()
                    binding.spinnerShopperType.isEnabled = false
                    binding.tvShopperTypeStatus.text =
                        "Impossible de charger les types (${state.message}). Vérifiez la connexion serveur."
                    binding.tvShopperTypeStatus.visibility = View.VISIBLE
                    setSpinnerPlaceholder(binding.spinnerShopperType, "Indisponible")
                }
            }
        }

        // 2. Fallback référentiel couleurs avant réception de /users/me
        profileViewModel.colors.observe(viewLifecycleOwner) { colors ->
            referentialColors = colors.orEmpty()
            if (!loadedFromProfileApi) {
                populateAccountColorsFromSessionCache()
            }
        }
    }

    private fun populateAccountColorsFromSessionCache() {
        val session = SessionManager(requireContext())
        val likedNames = session.getPreferredColors().map { it.trim().lowercase() }.toSet()
        val avoidedNames = session.getAvoidedColors().map { it.trim().lowercase() }.toSet()

        accountPreferredColors = referentialColors.filter {
            it.nom.trim().lowercase() in likedNames
        }
        accountAvoidedColors = referentialColors.filter {
            it.nom.trim().lowercase() in avoidedNames
        }
        renderAccountColorCircles()
    }

    private fun renderAccountColorCircles() {
        renderColorCircleRow(
            colors = accountPreferredColors,
            container = binding.llPreferredColorCircles,
            scrollView = binding.hsvPreferredColors,
            emptyView = binding.tvPreferredColorsEmpty,
            isAvoided = false
        )
        renderColorCircleRow(
            colors = accountAvoidedColors,
            container = binding.llAvoidedColorCircles,
            scrollView = binding.hsvAvoidedColors,
            emptyView = binding.tvAvoidedColorsEmpty,
            isAvoided = true
        )
    }

    private fun renderColorCircleRow(
        colors: List<CouleurResponse>,
        container: LinearLayout,
        scrollView: View,
        emptyView: TextView,
        isAvoided: Boolean
    ) {
        container.removeAllViews()
        if (colors.isEmpty()) {
            scrollView.visibility = View.GONE
            emptyView.visibility = View.VISIBLE
            return
        }

        scrollView.visibility = View.VISIBLE
        emptyView.visibility = View.GONE

        val density = resources.displayMetrics.density
        val circleSizePx = (36 * density).toInt()
        val marginEndPx = (10 * density).toInt()

        colors.forEach { couleur ->
            val parsedColor = try {
                Color.parseColor(couleur.codeHex)
            } catch (_: Exception) {
                Color.GRAY
            }

            val circleContainer = FrameLayout(requireContext()).apply {
                layoutParams = LinearLayout.LayoutParams(circleSizePx, circleSizePx).apply {
                    marginEnd = marginEndPx
                }
                contentDescription = couleur.nom
                isClickable = true
                isFocusable = true
                setOnClickListener {
                    Toast.makeText(requireContext(), couleur.nom, Toast.LENGTH_SHORT).show()
                }
            }

            val circleView = View(requireContext()).apply {
                layoutParams = FrameLayout.LayoutParams(
                    FrameLayout.LayoutParams.MATCH_PARENT,
                    FrameLayout.LayoutParams.MATCH_PARENT
                )
                background = ContextCompat.getDrawable(requireContext(), R.drawable.circle_shape)
                backgroundTintList = ColorStateList.valueOf(parsedColor)
            }
            circleContainer.addView(circleView)

            val luminance = ColorUtils.calculateLuminance(parsedColor)
            val symbolColor = if (luminance > 0.6) Color.parseColor("#1F1E1D") else Color.WHITE
            val symbolView = TextView(requireContext()).apply {
                layoutParams = FrameLayout.LayoutParams(
                    FrameLayout.LayoutParams.MATCH_PARENT,
                    FrameLayout.LayoutParams.MATCH_PARENT
                )
                gravity = Gravity.CENTER
                text = if (isAvoided) "✕" else "✓"
                textSize = 13f
                setTextColor(symbolColor)
            }
            circleContainer.addView(symbolView)
            container.addView(circleContainer)
        }
    }

    private fun setSpinnerPlaceholder(spinner: android.widget.Spinner, text: String) {
        spinner.adapter = ArrayAdapter(
            requireContext(),
            android.R.layout.simple_spinner_dropdown_item,
            listOf(text)
        )
    }

    private fun triggerSearchFromInputs() {
        val typePos = binding.spinnerShopperType.selectedItemPosition
        if (availableTypes.isEmpty() || typePos !in availableTypes.indices) {
            Toast.makeText(
                requireContext(),
                "Veuillez attendre le chargement des types de vêtements.",
                Toast.LENGTH_SHORT
            ).show()
            profileViewModel.loadReferentials(accountGenre)
            return
        }
        val selectedType = availableTypes[typePos]

        val budgetStr = binding.etShopperBudget.text.toString().trim()
        val budget = budgetStr.toFloatOrNull()
        if (budgetStr.isNotEmpty() && (budget == null || budget <= 0f)) {
            binding.etShopperBudget.error = "Entrez un budget valide (> 0)"
            return
        }

        val session = SessionManager(requireContext())
        val colors = accountPreferredColors.map { it.nom }
            .ifEmpty { session.getPreferredColors().toList() }
        val avoided = accountAvoidedColors.map { it.nom }
            .ifEmpty { session.getAvoidedColors().toList() }

        val request = ShopperPromptRequest(
            prompt = "",
            typeVetement = selectedType.nom,
            styleId = null,
            style = null,
            budget = budget,
            genre = accountGenre,
            colors = colors,
            avoidedColors = avoided,
            requestedTypes = listOf(selectedType.nom),
            maxResults = 12
        )
        viewModel.searchArticles(request, loadMoreUnseen = false)
    }

    private fun observeViewModel() {
        viewModel.shopperResult.observe(viewLifecycleOwner) { state ->
            when (state) {
                null -> {
                    binding.llLoadingAi.visibility = View.GONE
                    articleAdapter.submitList(emptyList())
                    binding.tvOutfitsHeader.visibility = View.GONE
                    binding.btnRegenerateOutfits.visibility = View.GONE
                    binding.tvEmptyShopper.text =
                        "Choisissez un type de vêtement et votre budget puis cliquez sur « Rechercher des propositions »."
                    binding.tvEmptyShopper.visibility = View.VISIBLE
                }

                is Resource.Loading -> {
                    binding.llLoadingAi.visibility = View.VISIBLE
                    binding.tvEmptyShopper.visibility = View.GONE
                    binding.tvOutfitsHeader.visibility = View.GONE
                    binding.btnRegenerateOutfits.visibility = View.GONE
                    binding.tvLoadingStatus.text =
                        "Scraping en direct des boutiques selon vos critères..."
                }

                is Resource.Success -> {
                    binding.llLoadingAi.visibility = View.GONE
                    val result = state.data
                    val articles = result.articles

                    articleAdapter.submitList(articles)
                    binding.btnRegenerateOutfits.visibility =
                        if (articles.isNotEmpty()) View.VISIBLE else View.GONE

                    if (articles.isEmpty()) {
                        val typeLabel = result.typeDemande ?: viewModel.lastRequest?.typeVetement ?: "cet article"
                        val budgetText = result.budgetMax?.let { " dans un budget de ${it.toInt()} TND" } ?: ""
                        binding.tvEmptyShopper.text =
                            "Aucune proposition de $typeLabel trouvée$budgetText pour votre profil. Essayez d'élargir le budget ou de modifier vos préférences couleurs dans votre profil."
                        binding.tvEmptyShopper.visibility = View.VISIBLE
                        binding.tvOutfitsHeader.visibility = View.GONE
                    } else {
                        binding.tvEmptyShopper.visibility = View.GONE
                        binding.tvOutfitsHeader.visibility = View.VISIBLE
                        val nb = articles.size
                        val typeLabel = result.typeDemande ?: viewModel.lastRequest?.typeVetement ?: "articles"
                        binding.tvOutfitsHeader.text =
                            "$nb proposition${if (nb > 1) "s" else ""} · $typeLabel"
                    }
                }

                is Resource.Error -> {
                    binding.llLoadingAi.visibility = View.GONE
                    articleAdapter.submitList(emptyList())
                    binding.tvEmptyShopper.text = state.message
                    binding.tvEmptyShopper.visibility = View.VISIBLE
                    binding.tvOutfitsHeader.visibility = View.GONE
                    binding.btnRegenerateOutfits.visibility = View.GONE
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
