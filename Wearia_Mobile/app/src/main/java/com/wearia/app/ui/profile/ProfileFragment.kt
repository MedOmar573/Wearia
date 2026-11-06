package com.wearia.app.ui.profile

import android.os.Bundle
import android.view.LayoutInflater
import android.view.View
import android.view.ViewGroup
import android.widget.ArrayAdapter
import android.widget.Spinner
import android.widget.TextView
import android.widget.Toast
import androidx.fragment.app.Fragment
import androidx.fragment.app.viewModels
import androidx.navigation.fragment.findNavController
import com.wearia.app.R
import com.wearia.app.WeariaApplication
import com.wearia.app.databinding.FragmentProfileBinding
import com.wearia.app.utils.Resource
import com.wearia.app.viewmodel.ProfileViewModel

/**
 * ProfileFragment : Gestion du profil, style et routines (Maquettes 4.jpg & 5.jpg).
 */
class ProfileFragment : Fragment() {

    private var _binding: FragmentProfileBinding? = null
    private val binding get() = _binding!!
    private val viewModel: ProfileViewModel by viewModels { ProfileViewModel.Factory() }

    override fun onCreateView(inflater: LayoutInflater, container: ViewGroup?, savedInstanceState: Bundle?): View {
        _binding = FragmentProfileBinding.inflate(inflater, container, false)
        return binding.root
    }

    override fun onViewCreated(view: View, savedInstanceState: Bundle?) {
        super.onViewCreated(view, savedInstanceState)

        val session = WeariaApplication.instance.sessionManager
        binding.tvProfileName.text = session.getUserName().ifEmpty { "Ameni" }
        binding.tvProfileEmail.text = session.getUserEmail().ifEmpty { "ameni@wearia.tn" }
        binding.tvProfileVille.text = "City : ${session.getUserVille().ifEmpty { "Tunis" }}"

        // Chargement du profil et des routines
        viewModel.loadProfile()
        viewModel.loadRoutines()

        viewModel.profileState.observe(viewLifecycleOwner) { state ->
            if (state is Resource.Success) {
                val user = state.data
                binding.tvProfileName.text = user.nom
                binding.tvProfileEmail.text = user.email
                binding.tvProfileVille.text = "City : ${user.ville}"
            }
        }

        viewModel.routines.observe(viewLifecycleOwner) { state ->
            if (state is Resource.Success) {
                displayRoutines(state.data)
            }
        }

        // Accès rapide Style Profile (Maquette 4.jpg)
        binding.cardOpenStyleProfile.setOnClickListener {
            findNavController().navigate(R.id.styleProfileFragment)
        }

        // Accès rapide Color Preferences (Maquette 5.jpg)
        binding.cardOpenColorPreferences.setOnClickListener {
            findNavController().navigate(R.id.colorPreferencesFragment)
        }

        binding.btnAddRoutine.setOnClickListener {
            showAddRoutineDialog()
        }

        binding.btnLogout.setOnClickListener {
            session.clearSession()
            Toast.makeText(requireContext(), "Signed out.", Toast.LENGTH_SHORT).show()
            findNavController().navigate(R.id.loginFragment)
        }
    }

    private fun displayRoutines(routines: List<com.wearia.app.data.remote.dto.RoutineHebdomadaireResponse>) {
        binding.layoutRoutinesList.removeAllViews()
        if (routines.isEmpty()) {
            val emptyTv = TextView(requireContext()).apply {
                text = "No routines yet. (e.g. MONDAY -> UNIVERSITY)"
                setTextColor(resources.getColor(R.color.colorTextSecondary, null))
                setPadding(0, 8, 0, 8)
            }
            binding.layoutRoutinesList.addView(emptyTv)
            return
        }

        routines.forEach { routine ->
            val itemTv = TextView(requireContext()).apply {
                text = "📅 ${routine.jourSemaine} : ${routine.occasion}"
                textSize = 14f
                setTextColor(resources.getColor(R.color.colorTextPrimary, null))
                setPadding(0, 6, 0, 6)
            }
            binding.layoutRoutinesList.addView(itemTv)
        }
    }

    private fun showAddRoutineDialog() {
        val days = listOf("MONDAY", "TUESDAY", "WEDNESDAY", "THURSDAY", "FRIDAY", "SATURDAY", "SUNDAY")
        val occasions = listOf("UNIVERSITY", "WORK", "OUTINGS", "EVENTS", "SPORT", "CASUAL")

        val layout = android.widget.LinearLayout(requireContext()).apply {
            orientation = android.widget.LinearLayout.VERTICAL
            setPadding(50, 40, 50, 10)
        }

        val daySpinner = Spinner(requireContext()).apply {
            adapter = ArrayAdapter(requireContext(), android.R.layout.simple_spinner_dropdown_item, days)
        }
        val occasionSpinner = Spinner(requireContext()).apply {
            adapter = ArrayAdapter(requireContext(), android.R.layout.simple_spinner_dropdown_item, occasions)
        }

        layout.addView(TextView(requireContext()).apply { text = "Day of the week :" })
        layout.addView(daySpinner)
        layout.addView(TextView(requireContext()).apply { text = "\nCorresponding Occasion :" })
        layout.addView(occasionSpinner)

        android.app.AlertDialog.Builder(requireContext())
            .setTitle("Add Weekly Routine (BR09)")
            .setView(layout)
            .setPositiveButton("Save") { _, _ ->
                val selectedDay = days[daySpinner.selectedItemPosition]
                val selectedOccasion = occasions[occasionSpinner.selectedItemPosition]
                viewModel.createRoutine(selectedDay, selectedOccasion)
                Toast.makeText(requireContext(), "Routine saved!", Toast.LENGTH_SHORT).show()
            }
            .setNegativeButton("Cancel", null)
            .show()
    }

    override fun onDestroyView() {
        super.onDestroyView()
        _binding = null
    }
}
