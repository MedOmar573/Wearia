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
import com.wearia.app.WeariaApplication
import com.wearia.app.databinding.FragmentLoginBinding
import com.wearia.app.utils.Resource
import com.wearia.app.utils.addPressEffect
import com.wearia.app.viewmodel.AuthViewModel

/**
 * LoginFragment : Écran de connexion avec vérification de sécurité par OTP (UC07).
 */
class LoginFragment : Fragment() {

    private var _binding: FragmentLoginBinding? = null
    private val binding get() = _binding!!
    private val viewModel: AuthViewModel by viewModels { AuthViewModel.Factory() }

    private var pendingEmail = ""

    override fun onCreateView(inflater: LayoutInflater, container: ViewGroup?, savedInstanceState: Bundle?): View {
        _binding = FragmentLoginBinding.inflate(inflater, container, false)
        return binding.root
    }

    override fun onViewCreated(view: View, savedInstanceState: Bundle?) {
        super.onViewCreated(view, savedInstanceState)

        // Effets tactiles
        binding.btnLogin.addPressEffect()
        binding.tvGoToRegister.addPressEffect(0.98f)

        // Si déjà connecté, rediriger selon l'état du profil
        if (viewModel.isLoggedIn()) {
            val session = WeariaApplication.instance.sessionManager
            if (session.isProfileCompleted()) {
                findNavController().navigate(R.id.action_login_to_home)
            } else {
                findNavController().navigate(R.id.action_login_to_styleProfile)
            }
            return
        }

        // Bouton de connexion
        binding.btnLogin.setOnClickListener {
            val email = binding.etEmail.text.toString().trim()
            val password = binding.etPassword.text.toString().trim()

            if (email.isEmpty()) {
                binding.etEmail.error = "Veuillez renseigner votre adresse email."
                binding.etEmail.requestFocus()
                return@setOnClickListener
            }

            val emailPattern = "^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\\.[A-Za-z]{2,}$".toRegex()
            if (!email.matches(emailPattern)) {
                binding.etEmail.error = "Format d'email invalide (ex: utilisateur@example.com)."
                binding.etEmail.requestFocus()
                return@setOnClickListener
            }

            if (password.isEmpty()) {
                binding.etPassword.error = "Veuillez saisir votre mot de passe."
                binding.etPassword.requestFocus()
                return@setOnClickListener
            }

            if (password.length < 8) {
                binding.etPassword.error = "Le mot de passe doit comporter au moins 8 caractères."
                binding.etPassword.requestFocus()
                return@setOnClickListener
            }

            pendingEmail = email
            viewModel.login(email, password)
        }

        // Navigation vers l'inscription
        binding.tvGoToRegister.setOnClickListener {
            findNavController().navigate(R.id.action_login_to_register)
        }

        // Observer l'état de la première étape de connexion (attente code OTP)
        viewModel.authStepState.observe(viewLifecycleOwner) { state ->
            if (state == null) return@observe
            when (state) {
                is Resource.Loading -> {
                    binding.btnLogin.isEnabled = false
                    binding.progressBar.visibility = View.VISIBLE
                }
                is Resource.Success -> {
                    binding.progressBar.visibility = View.GONE
                    binding.btnLogin.isEnabled = true
                    viewModel.resetAuthStepState()

                    Toast.makeText(requireContext(), "Code envoyé à votre adresse email !", Toast.LENGTH_SHORT).show()

                    val bundle = Bundle().apply {
                        putString("email", pendingEmail)
                        putString("purpose", "LOGIN")
                    }
                    findNavController().navigate(R.id.action_login_to_verifyOtp, bundle)
                }
                is Resource.Error -> {
                    binding.progressBar.visibility = View.GONE
                    binding.btnLogin.isEnabled = true
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
