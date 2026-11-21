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
 * LoginFragment : Écran de connexion modernisé avec carte flottante et retour tactile.
 */
class LoginFragment : Fragment() {

    private var _binding: FragmentLoginBinding? = null
    private val binding get() = _binding!!
    private val viewModel: AuthViewModel by viewModels { AuthViewModel.Factory() }

    override fun onCreateView(inflater: LayoutInflater, container: ViewGroup?, savedInstanceState: Bundle?): View {
        _binding = FragmentLoginBinding.inflate(inflater, container, false)
        return binding.root
    }

    override fun onViewCreated(view: View, savedInstanceState: Bundle?) {
        super.onViewCreated(view, savedInstanceState)

        // Effets tactiles
        binding.btnLogin.addPressEffect()
        binding.tvGoToRegister.addPressEffect(0.98f)

        // Si déjà connecté, rediriger vers l'accueil
        if (viewModel.isLoggedIn()) {
            findNavController().navigate(R.id.action_login_to_home)
            return
        }

        // Bouton de connexion
        binding.btnLogin.setOnClickListener {
            val email = binding.etEmail.text.toString().trim()
            val password = binding.etPassword.text.toString().trim()

            if (email.isEmpty() || password.isEmpty()) {
                Toast.makeText(requireContext(), "Veuillez remplir tous les champs.", Toast.LENGTH_SHORT).show()
                return@setOnClickListener
            }
            viewModel.login(email, password)
        }

        // Navigation vers l'inscription
        binding.tvGoToRegister.setOnClickListener {
            findNavController().navigate(R.id.action_login_to_register)
        }

        // Observer l'état de connexion
        viewModel.loginState.observe(viewLifecycleOwner) { state ->
            when (state) {
                is Resource.Loading -> {
                    binding.btnLogin.isEnabled = false
                    binding.progressBar.visibility = View.VISIBLE
                }
                is Resource.Success -> {
                    binding.progressBar.visibility = View.GONE
                    binding.btnLogin.isEnabled = true
                    Toast.makeText(requireContext(), "Bienvenue sur Wearia !", Toast.LENGTH_SHORT).show()
                    findNavController().navigate(R.id.action_login_to_home)
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
