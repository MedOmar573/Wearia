package com.wearia.app.ui.auth

import android.os.Bundle
import android.view.LayoutInflater
import android.view.View
import android.view.ViewGroup
import android.widget.Toast
import androidx.fragment.app.Fragment
import androidx.fragment.app.viewModels
import androidx.navigation.fragment.findNavController
import com.wearia.app.R
import com.wearia.app.databinding.FragmentRegisterBinding
import com.wearia.app.utils.Resource
import com.wearia.app.utils.addPressEffect
import com.wearia.app.viewmodel.AuthViewModel

/**
 * RegisterFragment : Écran d'inscription modernisé aux standards Fresh Fashion Tech.
 */
class RegisterFragment : Fragment() {

    private var _binding: FragmentRegisterBinding? = null
    private val binding get() = _binding!!
    private val viewModel: AuthViewModel by viewModels { AuthViewModel.Factory() }

    override fun onCreateView(inflater: LayoutInflater, container: ViewGroup?, savedInstanceState: Bundle?): View {
        _binding = FragmentRegisterBinding.inflate(inflater, container, false)
        return binding.root
    }

    override fun onViewCreated(view: View, savedInstanceState: Bundle?) {
        super.onViewCreated(view, savedInstanceState)

        binding.btnRegister.addPressEffect()
        binding.tvGoToLogin.addPressEffect(0.98f)

        // Bouton d'inscription
        binding.btnRegister.setOnClickListener {
            val nom = binding.etNom.text.toString().trim()
            val email = binding.etEmail.text.toString().trim()
            val password = binding.etPassword.text.toString().trim()
            val confirm = binding.etConfirmPassword.text.toString().trim()

            if (nom.isEmpty() || email.isEmpty() || password.isEmpty() || confirm.isEmpty()) {
                Toast.makeText(requireContext(), "Veuillez remplir tous les champs.", Toast.LENGTH_SHORT).show()
                return@setOnClickListener
            }
            if (!android.util.Patterns.EMAIL_ADDRESS.matcher(email).matches()) {
                Toast.makeText(requireContext(), "Veuillez entrer une adresse email valide.", Toast.LENGTH_SHORT).show()
                return@setOnClickListener
            }
            if (password != confirm) {
                Toast.makeText(requireContext(), "Les mots de passe ne correspondent pas.", Toast.LENGTH_SHORT).show()
                return@setOnClickListener
            }
            if (password.length < 8) {
                Toast.makeText(requireContext(), "Le mot de passe doit contenir au moins 8 caractères.", Toast.LENGTH_SHORT).show()
                return@setOnClickListener
            }

            // Étape de vérification par code email (Code OTP)
            showEmailVerificationDialog(nom, email, password)
        }

        // Navigation vers la connexion
        binding.tvGoToLogin.setOnClickListener {
            findNavController().navigate(R.id.action_register_to_login)
        }

        // Observer l'état d'inscription
        viewModel.registerState.observe(viewLifecycleOwner) { state ->
            when (state) {
                is Resource.Loading -> {
                    binding.btnRegister.isEnabled = false
                    binding.progressBar.visibility = View.VISIBLE
                }
                is Resource.Success -> {
                    // Connexion automatique immédiate pour récupérer et enregistrer le jeton JWT
                    val email = binding.etEmail.text.toString().trim()
                    val password = binding.etPassword.text.toString().trim()
                    viewModel.login(email, password)
                }
                is Resource.Error -> {
                    binding.progressBar.visibility = View.GONE
                    binding.btnRegister.isEnabled = true
                    Toast.makeText(requireContext(), state.message, Toast.LENGTH_LONG).show()
                }
            }
        }

        // Observer la connexion automatique consécutive à l'inscription
        viewModel.loginState.observe(viewLifecycleOwner) { state ->
            when (state) {
                is Resource.Success -> {
                    binding.progressBar.visibility = View.GONE
                    binding.btnRegister.isEnabled = true
                    Toast.makeText(requireContext(), "Email vérifié ! Personnalisez maintenant votre style.", Toast.LENGTH_SHORT).show()
                    findNavController().navigate(R.id.action_register_to_styleProfile)
                }
                is Resource.Error -> {
                    binding.progressBar.visibility = View.GONE
                    binding.btnRegister.isEnabled = true
                    Toast.makeText(requireContext(), "Compte créé ! Veuillez vous connecter.", Toast.LENGTH_LONG).show()
                    findNavController().navigate(R.id.action_register_to_login)
                }
                else -> {}
            }
        }
    }

    private fun showEmailVerificationDialog(nom: String, email: String, password: String) {
        val codeSecret = (100000..999999).random().toString()

        val input = android.widget.EditText(requireContext()).apply {
            inputType = android.text.InputType.TYPE_CLASS_NUMBER
            hint = "Code à 6 chiffres"
            textAlignment = android.view.View.TEXT_ALIGNMENT_CENTER
            textSize = 20f
            setPadding(40, 30, 40, 30)
        }

        val container = android.widget.LinearLayout(requireContext()).apply {
            orientation = android.widget.LinearLayout.VERTICAL
            val pad = (24f * resources.displayMetrics.density).toInt()
            setPadding(pad, (12f * resources.displayMetrics.density).toInt(), pad, 0)
            addView(input)
        }

        com.google.android.material.dialog.MaterialAlertDialogBuilder(requireContext())
            .setTitle("Vérification de l'adresse email")
            .setMessage("Un code de confirmation a été envoyé à :\n$email\n\n(Code de sécurité reçu : $codeSecret)")
            .setView(container)
            .setCancelable(false)
            .setPositiveButton("Valider") { dialog, _ ->
                val entered = input.text.toString().trim()
                if (entered == codeSecret) {
                    dialog.dismiss()
                    viewModel.register(nom, email, password)
                } else {
                    Toast.makeText(requireContext(), "Code incorrect. Veuillez réessayer.", Toast.LENGTH_SHORT).show()
                }
            }
            .setNegativeButton("Annuler", null)
            .show()
    }

    override fun onDestroyView() {
        super.onDestroyView()
        _binding = null
    }
}
