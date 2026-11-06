package com.wearia.app.ui.home

import android.os.Bundle
import android.view.LayoutInflater
import android.view.View
import android.view.ViewGroup
import android.widget.Toast
import androidx.fragment.app.Fragment
import androidx.fragment.app.viewModels
import androidx.navigation.fragment.findNavController
import coil.load
import com.wearia.app.BuildConfig
import com.wearia.app.R
import com.wearia.app.WeariaApplication
import com.wearia.app.databinding.FragmentHomeBinding
import com.wearia.app.utils.Resource
import com.wearia.app.viewmodel.OutfitViewModel

/**
 * HomeFragment : Tableau de bord d'accueil luxueux (Maquette 12.jpg).
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

        val session = WeariaApplication.instance.sessionManager
        val userName = session.getUserName()
        binding.tvGreeting.text = if (userName.isNotEmpty()) "Good morning, $userName 👋" else "Good morning, Mohamed 👋"

        val ville = session.getUserVille()
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
                    val baseUrl = BuildConfig.BASE_URL.trimEnd('/')
                    var topLoaded = false
                    var bottomLoaded = false
                    var shoesLoaded = false
                    var jacketLoaded = false

                    rec.items.forEach { item ->
                        val cat = item.category?.lowercase() ?: ""
                        val fullImgUrl = item.imageUrl?.let { if (it.startsWith("http")) it else "$baseUrl$it" }
                        when {
                            (cat.contains("haut") || cat.contains("chemise") || cat.contains("top") || cat.contains("t-shirt") || cat.contains("polo") || cat.contains("pull") || cat.contains("sweat") || cat.contains("robe")) && !topLoaded -> {
                                fullImgUrl?.let {
                                    binding.ivOutfitTop.load(it) { crossfade(true) }
                                    topLoaded = true
                                }
                            }
                            (cat.contains("bas") || cat.contains("pantalon") || cat.contains("jean") || cat.contains("short") || cat.contains("jupe")) && !bottomLoaded -> {
                                fullImgUrl?.let {
                                    binding.ivOutfitBottom.load(it) { crossfade(true) }
                                    bottomLoaded = true
                                }
                            }
                            (cat.contains("chaussure") || cat.contains("sneaker") || cat.contains("shoe") || cat.contains("basket") || cat.contains("derbie") || cat.contains("botte")) && !shoesLoaded -> {
                                fullImgUrl?.let {
                                    binding.ivOutfitShoes.load(it) { crossfade(true) }
                                    shoesLoaded = true
                                }
                            }
                            (cat.contains("veste") || cat.contains("manteau") || cat.contains("jacket") || cat.contains("blazer") || cat.contains("bomber")) && !jacketLoaded -> {
                                fullImgUrl?.let {
                                    binding.ivOutfitJacket.load(it) { crossfade(true) }
                                    jacketLoaded = true
                                }
                            }
                        }
                    }

                    val hasAnyPiece = topLoaded || bottomLoaded || shoesLoaded || jacketLoaded
                    if (rec.items.isNotEmpty() && hasAnyPiece) {
                        binding.tagStyle.text = "${rec.score}%"
                        binding.tagOccasion.text = rec.occasion.lowercase().replaceFirstChar { it.uppercase() }
                        binding.tagWeather.text = "${rec.temperature?.toInt() ?: 20}°C"

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

                    if (state.message.contains("sale", ignoreCase = true) || state.message.contains("disponible", ignoreCase = true)) {
                        binding.tvEmptyOutfitDesc.text = state.message
                    } else {
                        binding.tvEmptyOutfitDesc.text = "Votre garde-robe ne contient aucun vêtement.\nAjoutez des pièces pour que l'IA compose votre tenue !"
                    }
                }
            }
        }

        // Charger la recommandation du jour
        outfitViewModel.generateRecommendation()

        // Bouton View outfit & carte hero
        binding.btnViewOutfit.setOnClickListener {
            safeNavigate(R.id.action_home_to_outfit)
        }
        binding.btnEmptyAddClothing.setOnClickListener {
            safeNavigate(R.id.action_home_to_camera)
        }
        binding.cardTodayOutfit.setOnClickListener {
            if (binding.layoutOutfitContent.visibility == View.VISIBLE) {
                safeNavigate(R.id.action_home_to_outfit)
            } else if (binding.layoutOutfitEmpty.visibility == View.VISIBLE) {
                safeNavigate(R.id.action_home_to_camera)
            }
        }

        // 2x2 Grid Actions
        binding.cardActionAdd.setOnClickListener {
            safeNavigate(R.id.action_home_to_outfit)
        }

        binding.cardActionDressing.setOnClickListener {
            safeNavigate(R.id.action_home_to_dressing)
        }

        binding.cardActionFavorites.setOnClickListener {
            safeNavigate(R.id.outfitsHistoryFragment)
        }

        binding.cardActionShopping.setOnClickListener {
            safeNavigate(R.id.action_home_to_shopping)
        }
    }

    private fun safeNavigate(resId: Int) {
        try {
            findNavController().navigate(resId)
        } catch (e: Exception) {
            Toast.makeText(requireContext(), "Navigation : ${e.localizedMessage}", Toast.LENGTH_SHORT).show()
        }
    }

    override fun onDestroyView() {
        super.onDestroyView()
        _binding = null
    }
}
