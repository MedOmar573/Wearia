package com.wearia.app.ui.profile

import android.os.Bundle
import android.view.LayoutInflater
import android.view.View
import android.view.ViewGroup
import android.widget.Toast
import androidx.fragment.app.Fragment
import androidx.fragment.app.viewModels
import androidx.navigation.fragment.findNavController
import androidx.recyclerview.widget.GridLayoutManager
import com.wearia.app.R
import com.wearia.app.WeariaApplication
import com.wearia.app.data.remote.dto.CouleurResponse
import com.wearia.app.databinding.FragmentColorPreferencesBinding
import com.wearia.app.utils.Resource
import com.wearia.app.viewmodel.ProfileViewModel

/**
 * ColorPreferencesFragment : Écran de sélection des couleurs favorites et à éviter (Étape 3 & 4 du parcours).
 * Permet de sélectionner les teintes appréciées, d'enregistrer en BDD et de débloquer l'accès aux recommandations.
 */
class ColorPreferencesFragment : Fragment() {

    private var _binding: FragmentColorPreferencesBinding? = null
    private val binding get() = _binding!!
    private val profileViewModel: ProfileViewModel by viewModels { ProfileViewModel.Factory() }

    private lateinit var preferredAdapter: ColorPaletteAdapter
    private lateinit var avoidAdapter: ColorPaletteAdapter

    override fun onCreateView(inflater: LayoutInflater, container: ViewGroup?, savedInstanceState: Bundle?): View {
        _binding = FragmentColorPreferencesBinding.inflate(inflater, container, false)
        return binding.root
    }

    override fun onViewCreated(view: View, savedInstanceState: Bundle?) {
        super.onViewCreated(view, savedInstanceState)

        setupRecyclerViews()
        observeViewModel()

        profileViewModel.loadReferentials()
        profileViewModel.loadProfile()

        binding.btnContinueColors.setOnClickListener {
            savePreferencesAndProceed()
        }
    }

    private fun setupRecyclerViews() {
        preferredAdapter = ColorPaletteAdapter(isAvoidMode = false) { likedIds ->
            // Si une couleur est ajoutée aux aimées, la retirer des évitées
            val currentAvoided = avoidAdapter.getSelectedIds().toMutableSet()
            if (currentAvoided.removeAll(likedIds)) {
                avoidAdapter.setSelectedIds(currentAvoided)
            }
        }

        avoidAdapter = ColorPaletteAdapter(isAvoidMode = true) { avoidedIds ->
            // Si une couleur est ajoutée aux évitées, la retirer des aimées
            val currentLiked = preferredAdapter.getSelectedIds().toMutableSet()
            if (currentLiked.removeAll(avoidedIds)) {
                preferredAdapter.setSelectedIds(currentLiked)
            }
        }

        binding.rvPreferredColors.layoutManager = GridLayoutManager(requireContext(), 4)
        binding.rvPreferredColors.adapter = preferredAdapter

        binding.rvAvoidColors.layoutManager = GridLayoutManager(requireContext(), 4)
        binding.rvAvoidColors.adapter = avoidAdapter
    }

    private fun observeViewModel() {
        // Charger la palette de couleurs
        profileViewModel.colors.observe(viewLifecycleOwner) { colors ->
            if (colors.isNotEmpty()) {
                preferredAdapter.setColors(colors)
                avoidAdapter.setColors(colors)
            }
        }

        // Pré-cocher les préférences sauvegardées (persistance sur rechargement)
        profileViewModel.profileState.observe(viewLifecycleOwner) { state ->
            if (state is Resource.Success) {
                val user = state.data
                val savedLiked = user.preferencesCouleur
                    .filter { it.typePreference.equals("AIME", ignoreCase = true) }
                    .map { it.couleur.id }

                val savedAvoided = user.preferencesCouleur
                    .filter { it.typePreference.equals("EVITE", ignoreCase = true) }
                    .map { it.couleur.id }

                if (savedLiked.isNotEmpty()) {
                    preferredAdapter.setSelectedIds(savedLiked)
                } else {
                    // Par défaut selon maquette 5.jpg : Noir, Bleu Marine, Beige, Sable, Vert, Marron
                    preferredAdapter.setSelectedIds(setOf(1, 4, 6, 7, 9, 11))
                }

                if (savedAvoided.isNotEmpty()) {
                    avoidAdapter.setSelectedIds(savedAvoided)
                }
            }
        }

        // Observer la sauvegarde des préférences
        profileViewModel.colorPreferencesState.observe(viewLifecycleOwner) { state ->
            if (state == null) return@observe
            when (state) {
                is Resource.Loading -> {
                    binding.btnContinueColors.text = ""
                    binding.btnContinueColors.isEnabled = false
                    binding.progressBarColors.visibility = View.VISIBLE
                }
                is Resource.Success -> {
                    binding.progressBarColors.visibility = View.GONE
                    binding.btnContinueColors.text = "Continue"
                    binding.btnContinueColors.isEnabled = true

                    val session = WeariaApplication.instance.sessionManager
                    session.setProfileCompleted(true)

                    Toast.makeText(requireContext(), "Préférences de couleurs enregistrées !", Toast.LENGTH_SHORT).show()

                    // Étape 5 : Accès à l'application et aux fonctionnalités de recommandation
                    findNavController().navigate(R.id.action_colorPreferences_to_home)
                }
                is Resource.Error -> {
                    binding.progressBarColors.visibility = View.GONE
                    binding.btnContinueColors.text = "Continue"
                    binding.btnContinueColors.isEnabled = true
                    Toast.makeText(requireContext(), state.message, Toast.LENGTH_LONG).show()
                }
            }
        }
    }

    private fun savePreferencesAndProceed() {
        val likedIds = preferredAdapter.getSelectedIds().toList()
        val avoidedIds = avoidAdapter.getSelectedIds().toList()

        if (likedIds.isEmpty()) {
            Toast.makeText(requireContext(), "Veuillez sélectionner au moins une couleur préférée.", Toast.LENGTH_SHORT).show()
            return
        }

        profileViewModel.saveColorPreferences(likedIds, avoidedIds)
    }

    override fun onDestroyView() {
        super.onDestroyView()
        _binding = null
    }
}
