package com.wearia.app.ui.profile

import android.net.Uri
import android.os.Bundle
import android.view.LayoutInflater
import android.view.View
import android.view.ViewGroup
import android.widget.ArrayAdapter
import android.widget.LinearLayout
import android.widget.Spinner
import android.widget.TextView
import android.widget.Toast
import androidx.activity.result.contract.ActivityResultContracts
import androidx.core.content.ContextCompat
import androidx.fragment.app.Fragment
import androidx.fragment.app.viewModels
import androidx.navigation.fragment.findNavController
import coil.load
import coil.transform.CircleCropTransformation
import com.google.android.material.card.MaterialCardView
import com.wearia.app.R
import com.wearia.app.WeariaApplication
import com.wearia.app.databinding.FragmentProfileBinding
import com.wearia.app.utils.Resource
import com.wearia.app.utils.addPressEffect
import com.wearia.app.viewmodel.ProfileViewModel

/**
 * ProfileFragment : Gestion du profil, style et routines hebdomadaires.
 */
class ProfileFragment : Fragment() {

    private var _binding: FragmentProfileBinding? = null
    private val binding get() = _binding!!
    private val viewModel: ProfileViewModel by viewModels { ProfileViewModel.Factory() }

    private val galleryLauncher =
        registerForActivityResult(ActivityResultContracts.GetContent()) { uri: Uri? ->
            uri?.let { handleAvatarPicked(it) }
        }

    override fun onCreateView(inflater: LayoutInflater, container: ViewGroup?, savedInstanceState: Bundle?): View {
        _binding = FragmentProfileBinding.inflate(inflater, container, false)
        return binding.root
    }

    override fun onViewCreated(view: View, savedInstanceState: Bundle?) {
        super.onViewCreated(view, savedInstanceState)

        val session = WeariaApplication.instance.sessionManager
        binding.tvProfileName.text = session.getUserName().ifEmpty { "Ameni" }
        binding.tvProfileEmail.text = session.getUserEmail().ifEmpty { "ameni@wearia.tn" }
        binding.tvProfileVille.text = "Ville : ${session.getUserVille().ifEmpty { "Tunis" }}"

        // Photo de profil
        loadAvatar()

        val pickAvatarAction = View.OnClickListener {
            try {
                galleryLauncher.launch("image/*")
            } catch (e: Exception) {
                Toast.makeText(requireContext(), "Impossible d'ouvrir la galerie : ${e.localizedMessage}", Toast.LENGTH_SHORT).show()
            }
        }
        binding.layoutAvatarContainer.setOnClickListener(pickAvatarAction)
        binding.btnChangeAvatar.setOnClickListener(pickAvatarAction)
        binding.tvChangeAvatarPrompt.setOnClickListener(pickAvatarAction)

        // Tactile press effects
        binding.layoutAvatarContainer.addPressEffect(0.95f)
        binding.tvChangeAvatarPrompt.addPressEffect(0.97f)
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
            session.clearSession()
            Toast.makeText(requireContext(), "Déconnexion réussie.", Toast.LENGTH_SHORT).show()
            findNavController().navigate(R.id.loginFragment)
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
                    com.google.android.material.dialog.MaterialAlertDialogBuilder(requireContext())
                        .setTitle("Routine : $dayFr")
                        .setMessage("Occasion programmée : $occasionFr\nVoulez-vous supprimer cette routine ?")
                        .setPositiveButton("Supprimer") { _, _ ->
                            viewModel.deleteRoutine(routine.id)
                            Toast.makeText(requireContext(), "Routine supprimée", Toast.LENGTH_SHORT).show()
                        }
                        .setNegativeButton("Fermer", null)
                        .show()
                }
            }
            binding.layoutRoutinesList.addView(card)
        }
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

    private fun loadAvatar() {
        val session = WeariaApplication.instance.sessionManager
        val userName = session.getUserName().ifEmpty { "A" }
        binding.tvAvatarInitial.text = userName.first().uppercase()

        val avatarUriStr = session.getAvatarUri()
        if (!avatarUriStr.isNullOrEmpty()) {
            try {
                binding.ivProfileAvatar.load(Uri.parse(avatarUriStr)) {
                    crossfade(true)
                    transformations(CircleCropTransformation())
                    listener(
                        onSuccess = { _, _ -> binding.tvAvatarInitial.visibility = View.GONE },
                        onError = { _, _ -> binding.tvAvatarInitial.visibility = View.VISIBLE }
                    )
                }
            } catch (e: Exception) {
                binding.tvAvatarInitial.visibility = View.VISIBLE
            }
        } else {
            binding.tvAvatarInitial.visibility = View.VISIBLE
        }
    }

    private fun handleAvatarPicked(uri: Uri) {
        val session = WeariaApplication.instance.sessionManager
        session.saveAvatarUri(uri.toString())
        binding.ivProfileAvatar.load(uri) {
            crossfade(true)
            transformations(CircleCropTransformation())
            listener(
                onSuccess = { _, _ -> binding.tvAvatarInitial.visibility = View.GONE },
                onError = { _, _ -> binding.tvAvatarInitial.visibility = View.VISIBLE }
            )
        }
        Toast.makeText(requireContext(), "Photo de profil importée avec succès ! ✨", Toast.LENGTH_SHORT).show()
    }

    override fun onDestroyView() {
        super.onDestroyView()
        _binding = null
    }
}
