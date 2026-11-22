package com.wearia.app.ui.profile

import android.os.Bundle
import android.view.LayoutInflater
import android.view.View
import android.view.ViewGroup
import android.widget.ArrayAdapter
import android.widget.LinearLayout
import android.widget.Spinner
import android.widget.TextView
import android.widget.Toast
import androidx.core.content.ContextCompat
import androidx.fragment.app.Fragment
import androidx.fragment.app.activityViewModels
import androidx.fragment.app.viewModels
import androidx.lifecycle.lifecycleScope
import androidx.navigation.NavOptions
import androidx.navigation.fragment.findNavController
import com.google.android.material.card.MaterialCardView
import com.wearia.app.R
import com.wearia.app.WeariaApplication
import com.wearia.app.databinding.FragmentProfileBinding
import com.wearia.app.repositories.AuthRepository
import com.wearia.app.utils.Resource
import com.wearia.app.utils.addPressEffect
import com.wearia.app.viewmodel.ClothingViewModel
import com.wearia.app.viewmodel.ProfileViewModel
import kotlinx.coroutines.launch

/**
 * ProfileFragment : Gestion du profil, style et routines hebdomadaires.
 */
class ProfileFragment : Fragment() {

    private var _binding: FragmentProfileBinding? = null
    private val binding get() = _binding!!
    private val viewModel: ProfileViewModel by viewModels { ProfileViewModel.Factory() }
    private val clothingViewModel: ClothingViewModel by activityViewModels { ClothingViewModel.Factory() }

    override fun onCreateView(inflater: LayoutInflater, container: ViewGroup?, savedInstanceState: Bundle?): View {
        _binding = FragmentProfileBinding.inflate(inflater, container, false)
        return binding.root
    }

    override fun onViewCreated(view: View, savedInstanceState: Bundle?) {
        super.onViewCreated(view, savedInstanceState)

        val session = WeariaApplication.instance.sessionManager
        val initialName = session.getUserName().ifEmpty { "Utilisateur" }
        binding.tvProfileName.text = initialName
        binding.tvProfileEmail.text = session.getUserEmail().ifEmpty { "" }
        binding.tvProfileVille.text = "Ville : ${session.getUserVille().ifEmpty { "Tunis" }}"
        binding.tvAvatarInitial.text = initialName.firstOrNull()?.uppercase() ?: "W"

        // Tactile press effects
        binding.cardOpenStyleProfile.addPressEffect()
        binding.cardOpenColorPreferences.addPressEffect()
        binding.btnAddRoutine.addPressEffect()
        binding.btnLogout.addPressEffect()

        // Chargement du profil et des routines
        viewModel.loadProfile()
        viewModel.loadRoutines()

        viewModel.profileState.observe(viewLifecycleOwner) { state ->
            if (state is Resource.Success) {
                val user = state.data
                binding.tvProfileName.text = user.nom
                binding.tvProfileEmail.text = user.email
                binding.tvProfileVille.text = "Ville : ${user.ville}"
                binding.tvAvatarInitial.text = user.nom.firstOrNull()?.uppercase() ?: "W"
            }
        }

        viewModel.routines.observe(viewLifecycleOwner) { state ->
            if (state is Resource.Success) {
                displayRoutines(state.data)
            }
        }

        // Accès rapide Style Profile
        binding.cardOpenStyleProfile.setOnClickListener {
            findNavController().navigate(R.id.styleProfileFragment)
        }

        // Accès rapide Color Preferences
        binding.cardOpenColorPreferences.setOnClickListener {
            findNavController().navigate(R.id.colorPreferencesFragment)
        }

        binding.btnAddRoutine.setOnClickListener {
            showAddRoutineDialog()
        }

        binding.btnLogout.setOnClickListener {
            viewLifecycleOwner.lifecycleScope.launch {
                clothingViewModel.clearSessionState()
                AuthRepository().logoutAndClearCaches()
                Toast.makeText(requireContext(), "Déconnexion réussie.", Toast.LENGTH_SHORT).show()
                val navController = findNavController()
                // Purger les backstacks sauvegardés des onglets (ex. AI Shopper, Dressing, Accueil)
                // afin qu'aucun ViewModel ni proposition du compte précédent ne fuite vers un autre compte
                listOf(
                    R.id.shoppingFragment,
                    R.id.dressingFragment,
                    R.id.outfitsHistoryFragment,
                    R.id.homeFragment
                ).forEach { tabId ->
                    try {
                        navController.clearBackStack(tabId)
                    } catch (_: Exception) {
                        // Onglet non encore sauvegardé
                    }
                }
                val navOptions = NavOptions.Builder()
                    .setPopUpTo(R.id.nav_graph, true)
                    .setLaunchSingleTop(true)
                    .build()
                navController.navigate(R.id.loginFragment, null, navOptions)
            }
        }
    }

    private fun displayRoutines(routines: List<com.wearia.app.data.remote.dto.RoutineHebdomadaireResponse>) {
        binding.layoutRoutinesList.removeAllViews()
        if (routines.isEmpty()) {
            val emptyTv = TextView(requireContext()).apply {
                text = "Aucune routine enregistrée pour le moment.\nExemple : LUNDI → UNIVERSITÉ"
                setTextColor(ContextCompat.getColor(requireContext(), R.color.colorTextSecondary))
                textSize = 13f
                setPadding(8, 12, 8, 12)
            }
            binding.layoutRoutinesList.addView(emptyTv)
            return
        }

        val dayNamesFr = mapOf(
            "LUNDI" to "Lundi",
            "MARDI" to "Mardi",
            "MERCREDI" to "Mercredi",
            "JEUDI" to "Jeudi",
            "VENDREDI" to "Vendredi",
            "SAMEDI" to "Samedi",
            "DIMANCHE" to "Dimanche",
            "MONDAY" to "Lundi",
            "TUESDAY" to "Mardi",
            "WEDNESDAY" to "Mercredi",
            "THURSDAY" to "Jeudi",
            "FRIDAY" to "Vendredi",
            "SATURDAY" to "Samedi",
            "SUNDAY" to "Dimanche"
        )

        val occasionNamesFr = mapOf(
            "UNIVERSITE" to "Université",
            "TRAVAIL" to "Travail",
            "SORTIE" to "Sortie",
            "EVENEMENT" to "Événement",
            "SPORT" to "Sport",
            "QUOTIDIEN" to "Quotidien",
            "UNIVERSITY" to "Université",
            "WORK" to "Travail",
            "OUTINGS" to "Sortie",
            "EVENTS" to "Événement",
            "CASUAL" to "Quotidien"
        )

        routines.forEach { routine ->
            val dayFr = dayNamesFr[routine.jourSemaine.uppercase()] ?: routine.jourSemaine
            val occasionFr = occasionNamesFr[routine.occasion.uppercase()] ?: routine.occasion

            val card = MaterialCardView(requireContext()).apply {
                radius = 16f * resources.displayMetrics.density
                cardElevation = 1f * resources.displayMetrics.density
                setCardBackgroundColor(ContextCompat.getColor(requireContext(), R.color.colorSurfaceCard))
                strokeWidth = (1f * resources.displayMetrics.density).toInt()
                setStrokeColor(ContextCompat.getColor(requireContext(), R.color.colorBorder))
                val marginParams = LinearLayout.LayoutParams(
                    LinearLayout.LayoutParams.MATCH_PARENT,
                    LinearLayout.LayoutParams.WRAP_CONTENT
                ).apply {
                    bottomMargin = (8f * resources.displayMetrics.density).toInt()
                }
                layoutParams = marginParams

                val innerLayout = LinearLayout(requireContext()).apply {
                    orientation = LinearLayout.HORIZONTAL
                    setPadding(
                        (14f * resources.displayMetrics.density).toInt(),
                        (10f * resources.displayMetrics.density).toInt(),
                        (14f * resources.displayMetrics.density).toInt(),
                        (10f * resources.displayMetrics.density).toInt()
                    )
                    gravity = android.view.Gravity.CENTER_VERTICAL
                }

                val dayView = TextView(requireContext()).apply {
                    text = dayFr
                    textSize = 14f
                    setTypeface(typeface, android.graphics.Typeface.BOLD)
                    setTextColor(ContextCompat.getColor(requireContext(), R.color.colorTextPrimary))
                    layoutParams = LinearLayout.LayoutParams(0, LinearLayout.LayoutParams.WRAP_CONTENT, 1f)
                }

                val occasionBadge = TextView(requireContext()).apply {
                    text = occasionFr
                    textSize = 12f
                    setTypeface(typeface, android.graphics.Typeface.BOLD)
                    setTextColor(ContextCompat.getColor(requireContext(), R.color.colorPrimary))
                    setBackgroundResource(R.drawable.bg_badge_haut)
                    setPadding(
                        (12f * resources.displayMetrics.density).toInt(),
                        (4f * resources.displayMetrics.density).toInt(),
                        (12f * resources.displayMetrics.density).toInt(),
                        (4f * resources.displayMetrics.density).toInt()
                    )
                }

                innerLayout.addView(dayView)
                innerLayout.addView(occasionBadge)
                addView(innerLayout)

                setOnClickListener {
                    showEditRoutineDialog(routine)
                }
            }
            binding.layoutRoutinesList.addView(card)
        }
    }

    private fun showEditRoutineDialog(routine: com.wearia.app.data.remote.dto.RoutineHebdomadaireResponse) {
        val days = listOf("LUNDI", "MARDI", "MERCREDI", "JEUDI", "VENDREDI", "SAMEDI", "DIMANCHE")
        val daysFr = listOf("Lundi", "Mardi", "Mercredi", "Jeudi", "Vendredi", "Samedi", "Dimanche")

        val occasions = listOf("UNIVERSITE", "TRAVAIL", "SORTIE", "EVENEMENT", "SPORT", "QUOTIDIEN")
        val occasionsFr = listOf("Université", "Travail", "Sortie", "Événement", "Sport", "Quotidien")

        val layout = LinearLayout(requireContext()).apply {
            orientation = LinearLayout.VERTICAL
            val pad = (20f * resources.displayMetrics.density).toInt()
            setPadding(pad, pad, pad, (8f * resources.displayMetrics.density).toInt())
        }

        val daySpinner = Spinner(requireContext()).apply {
            adapter = ArrayAdapter(requireContext(), android.R.layout.simple_spinner_dropdown_item, daysFr)
            val currentDayIdx = days.indexOfFirst { it.equals(routine.jourSemaine, ignoreCase = true) }
            if (currentDayIdx >= 0) setSelection(currentDayIdx)
        }
        val occasionSpinner = Spinner(requireContext()).apply {
            adapter = ArrayAdapter(requireContext(), android.R.layout.simple_spinner_dropdown_item, occasionsFr)
            val currentOccIdx = occasions.indexOfFirst { it.equals(routine.occasion, ignoreCase = true) }
            if (currentOccIdx >= 0) setSelection(currentOccIdx)
        }

        val labelDay = TextView(requireContext()).apply {
            text = "Jour de la semaine :"
            textSize = 14f
            setTypeface(typeface, android.graphics.Typeface.BOLD)
            setTextColor(ContextCompat.getColor(requireContext(), R.color.colorTextPrimary))
        }

        val labelOccasion = TextView(requireContext()).apply {
            text = "Occasion habituelle :"
            textSize = 14f
            setTypeface(typeface, android.graphics.Typeface.BOLD)
            setTextColor(ContextCompat.getColor(requireContext(), R.color.colorTextPrimary))
            val params = LinearLayout.LayoutParams(
                LinearLayout.LayoutParams.MATCH_PARENT,
                LinearLayout.LayoutParams.WRAP_CONTENT
            ).apply {
                topMargin = (16f * resources.displayMetrics.density).toInt()
            }
            layoutParams = params
        }

        layout.addView(labelDay)
        layout.addView(daySpinner)
        layout.addView(labelOccasion)
        layout.addView(occasionSpinner)

        com.google.android.material.dialog.MaterialAlertDialogBuilder(requireContext())
            .setTitle("Modifier la routine")
            .setView(layout)
            .setPositiveButton("Modifier") { _, _ ->
                val selectedDay = days[daySpinner.selectedItemPosition]
                val selectedOccasion = occasions[occasionSpinner.selectedItemPosition]
                viewModel.updateRoutine(routine.id, selectedDay, selectedOccasion)
                Toast.makeText(requireContext(), "Routine modifiée avec succès !", Toast.LENGTH_SHORT).show()
            }
            .setNegativeButton("Supprimer") { _, _ ->
                viewModel.deleteRoutine(routine.id)
                Toast.makeText(requireContext(), "Routine supprimée", Toast.LENGTH_SHORT).show()
            }
            .setNeutralButton("Annuler", null)
            .show()
    }

    private fun showAddRoutineDialog() {
        val days = listOf("LUNDI", "MARDI", "MERCREDI", "JEUDI", "VENDREDI", "SAMEDI", "DIMANCHE")
        val daysFr = listOf("Lundi", "Mardi", "Mercredi", "Jeudi", "Vendredi", "Samedi", "Dimanche")

        val occasions = listOf("UNIVERSITE", "TRAVAIL", "SORTIE", "EVENEMENT", "SPORT", "QUOTIDIEN")
        val occasionsFr = listOf("Université", "Travail", "Sortie", "Événement", "Sport", "Quotidien")

        val layout = LinearLayout(requireContext()).apply {
            orientation = LinearLayout.VERTICAL
            val pad = (20f * resources.displayMetrics.density).toInt()
            setPadding(pad, pad, pad, (8f * resources.displayMetrics.density).toInt())
        }

        val daySpinner = Spinner(requireContext()).apply {
            adapter = ArrayAdapter(requireContext(), android.R.layout.simple_spinner_dropdown_item, daysFr)
        }
        val occasionSpinner = Spinner(requireContext()).apply {
            adapter = ArrayAdapter(requireContext(), android.R.layout.simple_spinner_dropdown_item, occasionsFr)
        }

        val labelDay = TextView(requireContext()).apply {
            text = "Jour de la semaine :"
            textSize = 14f
            setTypeface(typeface, android.graphics.Typeface.BOLD)
            setTextColor(ContextCompat.getColor(requireContext(), R.color.colorTextPrimary))
        }

        val labelOccasion = TextView(requireContext()).apply {
            text = "Occasion habituelle :"
            textSize = 14f
            setTypeface(typeface, android.graphics.Typeface.BOLD)
            setTextColor(ContextCompat.getColor(requireContext(), R.color.colorTextPrimary))
            val params = LinearLayout.LayoutParams(
                LinearLayout.LayoutParams.MATCH_PARENT,
                LinearLayout.LayoutParams.WRAP_CONTENT
            ).apply {
                topMargin = (16f * resources.displayMetrics.density).toInt()
            }
            layoutParams = params
        }

        layout.addView(labelDay)
        layout.addView(daySpinner)
        layout.addView(labelOccasion)
        layout.addView(occasionSpinner)

        com.google.android.material.dialog.MaterialAlertDialogBuilder(requireContext())
            .setTitle("Ajouter une routine hebdomadaire")
            .setView(layout)
            .setPositiveButton("Enregistrer") { _, _ ->
                val selectedDay = days[daySpinner.selectedItemPosition]
                val selectedOccasion = occasions[occasionSpinner.selectedItemPosition]
                viewModel.createRoutine(selectedDay, selectedOccasion)
                Toast.makeText(requireContext(), "Routine enregistrée !", Toast.LENGTH_SHORT).show()
            }
            .setNegativeButton("Annuler", null)
            .show()
    }

    override fun onDestroyView() {
        super.onDestroyView()
        _binding = null
    }
}
