package com.wearia.app.ui.profile

import android.os.Bundle
import android.view.LayoutInflater
import android.view.View
import android.view.ViewGroup
import android.widget.Toast
import androidx.core.content.ContextCompat
import androidx.fragment.app.Fragment
import androidx.fragment.app.viewModels
import androidx.navigation.fragment.findNavController
import com.wearia.app.R
import com.wearia.app.WeariaApplication
import com.wearia.app.data.remote.dto.UserUpdateRequest
import com.wearia.app.databinding.FragmentStyleProfileBinding
import com.wearia.app.utils.Resource
import com.wearia.app.viewmodel.ProfileViewModel

/**
 * StyleProfileFragment : Écran de configuration du profil morphologique et styles (Étape 2 du parcours).
 * Permet de définir le genre, la taille, le poids, la coupe préférée et les styles vestimentaires.
 */
class StyleProfileFragment : Fragment() {

    private var _binding: FragmentStyleProfileBinding? = null
    private val binding get() = _binding!!
    private val profileViewModel: ProfileViewModel by viewModels { ProfileViewModel.Factory() }

    private var selectedGender: String = "HOMME"
    private var selectedFit: String = "Regular"

    override fun onCreateView(inflater: LayoutInflater, container: ViewGroup?, savedInstanceState: Bundle?): View {
        _binding = FragmentStyleProfileBinding.inflate(inflater, container, false)
        return binding.root
    }

    override fun onViewCreated(view: View, savedInstanceState: Bundle?) {
        super.onViewCreated(view, savedInstanceState)

        setupGenderSelection()
        setupFitChips()
        setupStyles()
        observeViewModel()

        // Charger le profil existant pour restaurer les valeurs (persistance)
        profileViewModel.loadProfile()
        profileViewModel.loadReferentials()

        binding.btnContinueProfile.setOnClickListener {
            saveProfileAndContinue()
        }
    }

    private fun setupGenderSelection() {
        val initialGenre = WeariaApplication.instance.sessionManager.getUserGenre()
        if (!initialGenre.isNullOrEmpty()) {
            selectedGender = initialGenre.uppercase()
        }
        updateGenderUI()

        binding.cardGenderMan.setOnClickListener {
            selectedGender = "HOMME"
            updateGenderUI()
        }

        binding.cardGenderWoman.setOnClickListener {
            selectedGender = "FEMME"
            updateGenderUI()
        }
    }

    private fun updateGenderUI() {
        val primaryColor = ContextCompat.getColor(requireContext(), R.color.colorPrimary)
        val textSecondaryColor = ContextCompat.getColor(requireContext(), R.color.colorTextSecondary)
        val borderColor = ContextCompat.getColor(requireContext(), R.color.colorBorder)

        if (selectedGender == "HOMME") {
            binding.cardGenderMan.strokeColor = primaryColor
            binding.cardGenderMan.strokeWidth = dpToPx(2)
            binding.tvGenderMan.setTextColor(primaryColor)

            binding.cardGenderWoman.strokeColor = borderColor
            binding.cardGenderWoman.strokeWidth = dpToPx(1)
            binding.tvGenderWoman.setTextColor(textSecondaryColor)
        } else {
            binding.cardGenderWoman.strokeColor = primaryColor
            binding.cardGenderWoman.strokeWidth = dpToPx(2)
            binding.tvGenderWoman.setTextColor(primaryColor)

            binding.cardGenderMan.strokeColor = borderColor
            binding.cardGenderMan.strokeWidth = dpToPx(1)
            binding.tvGenderMan.setTextColor(textSecondaryColor)
        }
    }

    private fun setupFitChips() {
        updateFitChips()

        binding.chipFitFitted.setOnClickListener {
            selectedFit = "Fitted"
            updateFitChips()
        }
        binding.chipFitRegular.setOnClickListener {
            selectedFit = "Regular"
            updateFitChips()
        }
        binding.chipFitOversized.setOnClickListener {
            selectedFit = "Oversized"
            updateFitChips()
        }
    }

    private fun updateFitChips() {
        val selectedBg = R.drawable.bg_badge_taupe
        val normalBg = R.drawable.bg_badge_outline

        val isFitted = selectedFit.equals("Fitted", ignoreCase = true)
        val isRegular = selectedFit.equals("Regular", ignoreCase = true)
        val isOversized = selectedFit.equals("Oversized", ignoreCase = true)

        binding.chipFitFitted.setBackgroundResource(if (isFitted) selectedBg else normalBg)
        binding.chipFitFitted.setTextColor(ContextCompat.getColor(requireContext(), if (isFitted) R.color.colorOnPrimary else R.color.colorTextPrimary))

        binding.chipFitRegular.setBackgroundResource(if (isRegular) selectedBg else normalBg)
        binding.chipFitRegular.setTextColor(ContextCompat.getColor(requireContext(), if (isRegular) R.color.colorOnPrimary else R.color.colorTextPrimary))

        binding.chipFitOversized.setBackgroundResource(if (isOversized) selectedBg else normalBg)
        binding.chipFitOversized.setTextColor(ContextCompat.getColor(requireContext(), if (isOversized) R.color.colorOnPrimary else R.color.colorTextPrimary))
    }

    private fun setupStyles() {
        // Sélection par défaut Casual & Classic
        binding.chipStyleCasual.isChecked = true
        binding.chipStyleClassic.isChecked = true
    }

    private fun getSelectedStyleIds(): List<Int> {
        val ids = mutableListOf<Int>()
        if (binding.chipStyleCasual.isChecked) ids.add(1)     // Décontracté / Casual
        if (binding.chipStyleClassic.isChecked) ids.add(2)    // Classique
        if (binding.chipStyleSporty.isChecked) ids.add(3)     // Sportswear
        if (binding.chipStyleStreetwear.isChecked) ids.add(4) // Streetwear
        if (binding.chipStyleElegant.isChecked) ids.add(5)    // Chic / Elegant
        if (binding.chipStyleMinimal.isChecked) ids.add(6)    // Bohème / Minimal
        return ids
    }

    private fun observeViewModel() {
        // Pré-remplir les données si l'utilisateur en possède déjà
        profileViewModel.profileState.observe(viewLifecycleOwner) { state ->
            if (state is Resource.Success) {
                val user = state.data
                user.genre?.let {
                    selectedGender = it.uppercase()
                    updateGenderUI()
                }
                user.hauteurCm?.let {
                    binding.etHeight.setText(it.toString())
                }
                user.poidsKg?.let {
                    binding.etWeight.setText(it.toInt().toString())
                }
                user.coupePreferee?.let {
                    selectedFit = when (it.uppercase()) {
                        "AJUSTEE", "FITTED", "SLIM" -> "Fitted"
                        "OVERSIZE", "OVERSIZED" -> "Oversized"
                        else -> "Regular"
                    }
                    updateFitChips()
                }
                if (user.preferencesStyle.isNotEmpty()) {
                    val savedStyleIds = user.preferencesStyle.map { it.style.id }
                    binding.chipStyleCasual.isChecked = savedStyleIds.contains(1)
                    binding.chipStyleClassic.isChecked = savedStyleIds.contains(2)
                    binding.chipStyleSporty.isChecked = savedStyleIds.contains(3)
                    binding.chipStyleStreetwear.isChecked = savedStyleIds.contains(4)
                    binding.chipStyleElegant.isChecked = savedStyleIds.contains(5)
                    binding.chipStyleMinimal.isChecked = savedStyleIds.contains(6)
                }
            }
        }

        // Observer la mise à jour du profil
        profileViewModel.updateState.observe(viewLifecycleOwner) { state ->
            if (state == null) return@observe
            when (state) {
                is Resource.Loading -> {
                    binding.btnContinueProfile.text = ""
                    binding.btnContinueProfile.isEnabled = false
                    binding.progressBarProfile.visibility = View.VISIBLE
                }
                is Resource.Success -> {
                    binding.progressBarProfile.visibility = View.GONE
                    binding.btnContinueProfile.text = "Continue"
                    binding.btnContinueProfile.isEnabled = true
                    Toast.makeText(requireContext(), "Profil mis à jour !", Toast.LENGTH_SHORT).show()
                    findNavController().navigate(R.id.action_styleProfile_to_colorPreferences)
                }
                is Resource.Error -> {
                    binding.progressBarProfile.visibility = View.GONE
                    binding.btnContinueProfile.text = "Continue"
                    binding.btnContinueProfile.isEnabled = true
                    Toast.makeText(requireContext(), state.message, Toast.LENGTH_LONG).show()
                }
            }
        }
    }

    private fun saveProfileAndContinue() {
        val heightStr = binding.etHeight.text.toString().trim()
        val weightStr = binding.etWeight.text.toString().trim()

        val height = heightStr.toIntOrNull()
        if (height == null || height < 100 || height > 250) {
            binding.etHeight.error = "Veuillez entrer une taille valide (100 - 250 cm)"
            binding.etHeight.requestFocus()
            return
        }

        val weight = weightStr.toFloatOrNull()
        if (weight == null || weight < 30 || weight > 250) {
            binding.etWeight.error = "Veuillez entrer un poids valide (30 - 250 kg)"
            binding.etWeight.requestFocus()
            return
        }

        // Sauvegarder localement dans la session
        val session = WeariaApplication.instance.sessionManager
        session.saveUserGenre(selectedGender)
        session.saveUserMorphology(height, weight)

        // Sauvegarder les styles
        val selectedStyles = getSelectedStyleIds()
        profileViewModel.saveStylePreferences(selectedStyles)

        // Sauvegarder le profil (genre, taille, poids, coupe)
        val coupeEnum = when (selectedFit.uppercase()) {
            "FITTED", "SLIM", "AJUSTEE" -> "AJUSTEE"
            "OVERSIZED", "OVERSIZE" -> "OVERSIZE"
            else -> "REGULIERE"
        }

        val updateRequest = UserUpdateRequest(
            genre = selectedGender,
            hauteurCm = height,
            poidsKg = weight,
            coupePreferee = coupeEnum
        )
        profileViewModel.updateProfile(updateRequest)
    }

    private fun dpToPx(dp: Int): Int {
        val density = resources.displayMetrics.density
        return (dp * density).toInt()
    }

    override fun onDestroyView() {
        super.onDestroyView()
        _binding = null
    }
}
