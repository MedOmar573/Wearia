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
 * RegisterFragment : Écran d'inscription (Étape 1 du parcours utilisateur avec vérification OTP).
 */
class RegisterFragment : Fragment() {

    private var _binding: FragmentRegisterBinding? = null
    private val binding get() = _binding!!
    private val viewModel: AuthViewModel by viewModels { AuthViewModel.Factory() }

    private var pendingEmail = ""

    override fun onCreateView(inflater: LayoutInflater, container: ViewGroup?, savedInstanceState: Bundle?): View {
        _binding = FragmentRegisterBinding.inflate(inflater, container, false)
        return binding.root
    }

    override fun onViewCreated(view: View, savedInstanceState: Bundle?) {
        super.onViewCreated(view, savedInstanceState)

        binding.btnRegister.addPressEffect()
        binding.tvGoToLogin.addPressEffect(0.98f)

        binding.btnRegister.setOnClickListener {
            val nom = binding.etNom.text.toString().trim()
            val email = binding.etEmail.text.toString().trim()
            val password = binding.etPassword.text.toString().trim()
            val confirmPassword = binding.etConfirmPassword.text.toString().trim()

            // 1. Validation des champs obligatoires
            if (nom.isEmpty()) {
                binding.etNom.error = "Veuillez renseigner votre nom complet."
                binding.etNom.requestFocus()
                return@setOnClickListener
            }

            if (email.isEmpty()) {
                binding.etEmail.error = "Veuillez renseigner votre adresse email."
                binding.etEmail.requestFocus()
                return@setOnClickListener
            }

            // 2. Validation stricte du format email
            val emailPattern = "^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\\.[A-Za-z]{2,}$".toRegex()
            if (!email.matches(emailPattern)) {
                binding.etEmail.error = "Format d'email invalide (ex: utilisateur@example.com)."
                binding.etEmail.requestFocus()
                return@setOnClickListener
            }

            // 3. Validation de la force du mot de passe (min 8 caractères, au moins 1 lettre et 1 chiffre)
            if (password.length < 8) {
                binding.etPassword.error = "Le mot de passe doit comporter au moins 8 caractères."
                binding.etPassword.requestFocus()
                return@setOnClickListener
            }

            val hasLetter = password.any { it.isLetter() }
            val hasDigit = password.any { it.isDigit() }
            if (!hasLetter || !hasDigit) {
                binding.etPassword.error = "Le mot de passe doit contenir au moins une lettre et un chiffre."
                binding.etPassword.requestFocus()
                return@setOnClickListener
            }

            if (password != confirmPassword) {
                binding.etConfirmPassword.error = "Les mots de passe ne correspondent pas."
                binding.etConfirmPassword.requestFocus()
                return@setOnClickListener
            }

            pendingEmail = email
            viewModel.register(nom, email, password)
        }

        binding.tvGoToLogin.setOnClickListener {
            findNavController().navigate(R.id.action_register_to_login)
        }

        viewModel.authStepState.observe(viewLifecycleOwner) { state ->
            if (state == null) return@observe
            when (state) {
                is Resource.Loading -> {
                    binding.btnRegister.isEnabled = false
                    binding.progressBar.visibility = View.VISIBLE
                }
                is Resource.Success -> {
                    binding.progressBar.visibility = View.GONE
                    binding.btnRegister.isEnabled = true
                    viewModel.resetAuthStepState()

                    Toast.makeText(requireContext(), "Code envoyé à votre adresse email !", Toast.LENGTH_SHORT).show()

                    val bundle = Bundle().apply {
                        putString("email", pendingEmail)
                        putString("purpose", "REGISTER")
                    }
                    findNavController().navigate(R.id.action_register_to_verifyOtp, bundle)
                }
                is Resource.Error -> {
                    binding.progressBar.visibility = View.GONE
                    binding.btnRegister.isEnabled = true
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
