package com.wearia.app.ui.home

import android.os.Bundle
import android.view.LayoutInflater
import android.view.View
import android.view.ViewGroup
import androidx.fragment.app.Fragment
import androidx.fragment.app.viewModels
import androidx.navigation.fragment.findNavController
import coil.load
import com.wearia.app.BuildConfig
import com.wearia.app.R
import com.wearia.app.WeariaApplication
import com.wearia.app.databinding.FragmentHomeBinding
import com.wearia.app.utils.Resource
import com.wearia.app.utils.addPressEffect
import com.wearia.app.viewmodel.OutfitViewModel

/**
 * HomeFragment : Écran d'accueil modernisé Fresh Fashion Tech avec carte météo, tenue du jour et actions 2x2.
 */
class HomeFragment : Fragment() {

    private var _binding: FragmentHomeBinding? = null
    private val binding get() = _binding!!
    private val outfitViewModel: OutfitViewModel by viewModels { OutfitViewModel.Factory() }

    override fun onCreateView(inflater: LayoutInflater, container: ViewGroup?, savedInstanceState: Bundle?): View {
        _binding = FragmentHomeBinding.inflate(inflater, container, false)
        return binding.root
    }

    override fun onViewCreated(view: View, savedInstanceState: Bundle?) {
        super.onViewCreated(view, savedInstanceState)

        // Effets tactiles sur tous les éléments cliquables
        binding.cardActionAdd.addPressEffect()
        binding.cardActionDressing.addPressEffect()
        binding.cardActionFavorites.addPressEffect()
        binding.cardActionShopping.addPressEffect()
        binding.btnViewOutfit.addPressEffect()
        binding.btnEmptyAddClothing.addPressEffect()
        binding.cardTodayOutfit.addPressEffect(0.98f)

        // Salutation dynamique personnalisée
        val userName = WeariaApplication.instance.sessionManager.getUserName() ?: ""
        val ville = WeariaApplication.instance.sessionManager.getUserVille() ?: ""
        binding.tvGreeting.text = if (userName.isNotEmpty()) "Bonjour, $userName" else "Bonjour"
        binding.tvCityWeatherQuick.text = if (ville.isNotEmpty()) ville else "Tunis"

        // Observer la tenue du jour
        outfitViewModel.recommendationState.observe(viewLifecycleOwner) { state ->
            if (state == null) return@observe
            when (state) {
                is Resource.Loading -> {
                    binding.pbOutfitLoading.visibility = View.VISIBLE
                    binding.layoutOutfitContent.visibility = View.GONE
                    binding.layoutOutfitEmpty.visibility = View.GONE
                }
                is Resource.Success -> {
                    val rec = state.data
                    if (rec.items.isNotEmpty()) {
                        val baseUrl = BuildConfig.BASE_URL.trimEnd('/')
                        var topLoaded = false
                        var bottomLoaded = false
                        var shoesLoaded = false
                        var jacketLoaded = false

                        rec.items.forEach { item ->
                            val cat = item.category?.lowercase() ?: ""
                            val fullUrl = item.imageUrl?.let { if (it.startsWith("http")) it else "$baseUrl$it" }

                            when {
                                (cat.contains("haut") || cat.contains("chemise") || cat.contains("top") || cat.contains("t-shirt") || cat.contains("polo") || cat.contains("pull") || cat.contains("sweat")) && !topLoaded -> {
                                    fullUrl?.let {
                                        binding.ivOutfitTop.load(it) { crossfade(true) }
                                        topLoaded = true
                                    }
                                }
                                (cat.contains("bas") || cat.contains("pantalon") || cat.contains("jean") || cat.contains("short")) && !bottomLoaded -> {
                                    fullUrl?.let {
                                        binding.ivOutfitBottom.load(it) { crossfade(true) }
                                        bottomLoaded = true
                                    }
                                }
                                (cat.contains("chaussure") || cat.contains("sneaker") || cat.contains("shoe") || cat.contains("basket")) && !shoesLoaded -> {
                                    fullUrl?.let {
                                        binding.ivOutfitShoes.load(it) { crossfade(true) }
                                        shoesLoaded = true
                                    }
                                }
                                (cat.contains("veste") || cat.contains("manteau") || cat.contains("jacket") || cat.contains("blazer") || cat.contains("bomber")) && !jacketLoaded -> {
                                    fullUrl?.let {
                                        binding.ivOutfitJacket.load(it) { crossfade(true) }
                                        jacketLoaded = true
                                    }
                                }
                            }
                        }

                        // Tags descriptifs
                        binding.tagStyle.text = "${rec.score}% match"
                        binding.tagOccasion.text = rec.occasion.lowercase().replaceFirstChar { it.uppercase() }
                        binding.tagWeather.text = "${rec.temperature?.toInt() ?: 20}°C adapté"

                        binding.ivOutfitTop.visibility = if (topLoaded) View.VISIBLE else View.INVISIBLE
                        binding.ivOutfitBottom.visibility = if (bottomLoaded) View.VISIBLE else View.INVISIBLE
                        binding.ivOutfitShoes.visibility = if (shoesLoaded) View.VISIBLE else View.INVISIBLE
                        binding.ivOutfitJacket.visibility = if (jacketLoaded) View.VISIBLE else View.GONE

                        binding.pbOutfitLoading.visibility = View.GONE
                        binding.layoutOutfitContent.visibility = View.VISIBLE
                        binding.layoutOutfitEmpty.visibility = View.GONE
                    } else {
                        binding.pbOutfitLoading.visibility = View.GONE
                        binding.layoutOutfitContent.visibility = View.GONE
                        binding.layoutOutfitEmpty.visibility = View.VISIBLE
                    }
                }
                is Resource.Error -> {
                    binding.pbOutfitLoading.visibility = View.GONE
                    binding.layoutOutfitContent.visibility = View.GONE
                    binding.layoutOutfitEmpty.visibility = View.VISIBLE
                    if (state.message.isNotEmpty()) {
                        binding.tvEmptyOutfitDesc.text = state.message
                    } else {
                        binding.tvEmptyOutfitDesc.text = "Votre garde-robe ne contient aucun vêtement.\nAjoutez des pièces pour que l'IA compose votre tenue !"
                    }
                }
            }
        }

        // Charger la tenue du jour
        outfitViewModel.generateRecommendation()

        // Bouton "Voir la tenue complète"
        binding.btnViewOutfit.setOnClickListener {
            findNavController().navigate(R.id.action_home_to_outfit)
        }

        binding.btnEmptyAddClothing.setOnClickListener {
            findNavController().navigate(R.id.action_home_to_camera)
        }

        binding.cardTodayOutfit.setOnClickListener {
            if (binding.layoutOutfitContent.visibility == View.VISIBLE) {
                findNavController().navigate(R.id.action_home_to_outfit)
            } else if (binding.layoutOutfitEmpty.visibility == View.VISIBLE) {
                findNavController().navigate(R.id.action_home_to_camera)
            }
        }

        // Actions rapides
        binding.cardActionAdd.setOnClickListener {
            findNavController().navigate(R.id.action_home_to_outfit)
        }

        binding.cardActionDressing.setOnClickListener {
            findNavController().navigate(R.id.action_home_to_dressing)
        }

        binding.cardActionFavorites.setOnClickListener {
            findNavController().navigate(R.id.action_home_to_outfitsHistory)
        }

        binding.cardActionShopping.setOnClickListener {
            findNavController().navigate(R.id.action_home_to_shopping)
        }
    }

    override fun onDestroyView() {
        super.onDestroyView()
        _binding = null
    }
}
