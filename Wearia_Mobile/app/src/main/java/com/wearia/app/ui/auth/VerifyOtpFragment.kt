package com.wearia.app.ui.auth

import android.content.Context
import android.os.Bundle
import android.os.CountDownTimer
import android.text.Editable
import android.text.TextWatcher
import android.view.KeyEvent
import android.view.LayoutInflater
import android.view.View
import android.view.ViewGroup
import android.view.inputmethod.InputMethodManager
import android.widget.EditText
import android.widget.Toast
import androidx.fragment.app.Fragment
import androidx.fragment.app.viewModels
import androidx.navigation.fragment.findNavController
import com.wearia.app.R
import com.wearia.app.WeariaApplication
import com.wearia.app.databinding.FragmentVerifyOtpBinding
import com.wearia.app.utils.Resource
import com.wearia.app.utils.addPressEffect
import com.wearia.app.viewmodel.AuthViewModel

/**
 * VerifyOtpFragment : Écran de validation du code OTP envoyé par email
 * Utilisé à la fois pour l'inscription (UC06) et la connexion (UC07).
 */
class VerifyOtpFragment : Fragment() {

    private var _binding: FragmentVerifyOtpBinding? = null
    private val binding get() = _binding!!
    private val viewModel: AuthViewModel by viewModels { AuthViewModel.Factory() }

    private var email: String = ""
    private var purpose: String = "LOGIN"
    private var resendTimer: CountDownTimer? = null

    private lateinit var otpInputs: List<EditText>
    private var isUpdatingBoxes = false

    override fun onCreateView(inflater: LayoutInflater, container: ViewGroup?, savedInstanceState: Bundle?): View {
        _binding = FragmentVerifyOtpBinding.inflate(inflater, container, false)
        return binding.root
    }

    override fun onViewCreated(view: View, savedInstanceState: Bundle?) {
        super.onViewCreated(view, savedInstanceState)

        binding.btnVerifyOtp.addPressEffect()
        binding.btnBack.addPressEffect()

        email = arguments?.getString("email") ?: ""
        purpose = arguments?.getString("purpose") ?: "LOGIN"

        binding.tvEmailDisplay.text = email

        if (purpose == "REGISTER") {
            binding.tvInstruction.text = "Activez votre compte avec le code envoyé à :"
        } else {
            binding.tvInstruction.text = "Autorisez votre connexion avec le code envoyé à :"
        }

        otpInputs = listOf(
            binding.etOtp1,
            binding.etOtp2,
            binding.etOtp3,
            binding.etOtp4,
            binding.etOtp5,
            binding.etOtp6
        )

        setupOtpInputListeners()

        binding.btnBack.setOnClickListener {
            findNavController().popBackStack()
        }

        binding.btnVerifyOtp.setOnClickListener {
            submitOtp()
        }

        binding.tvResendBtn.setOnClickListener {
            if (email.isNotEmpty()) {
                viewModel.resendOtp(email, purpose)
                startResendCooldown()
            }
        }

        observeViewModel()

        // Focus automatique sur la première case et ouverture clavier
        binding.etOtp1.requestFocus()
        binding.etOtp1.postDelayed({
            val imm = requireContext().getSystemService(Context.INPUT_METHOD_SERVICE) as? InputMethodManager
            imm?.showSoftInput(binding.etOtp1, InputMethodManager.SHOW_IMPLICIT)
        }, 200)
    }

    private fun fillOtpBoxes(code: String, autoSubmit: Boolean = true) {
        val digits = code.filter { it.isDigit() }
        if (digits.isEmpty()) return

        isUpdatingBoxes = true
        for (i in otpInputs.indices) {
            if (i < digits.length) {
                otpInputs[i].setText(digits[i].toString())
            } else {
                otpInputs[i].setText("")
            }
        }
        isUpdatingBoxes = false

        // Déplacer le curseur sur la dernière case remplie
        val lastIndex = minOf(digits.length - 1, otpInputs.lastIndex)
        if (lastIndex >= 0) {
            otpInputs[lastIndex].requestFocus()
            otpInputs[lastIndex].setSelection(otpInputs[lastIndex].text.length)
        }

        if (autoSubmit && digits.length >= 6) {
            submitOtp()
        }
    }

    private fun setupOtpInputListeners() {
        for (i in otpInputs.indices) {
            val current = otpInputs[i]
            val next = otpInputs.getOrNull(i + 1)
            val prev = otpInputs.getOrNull(i - 1)

            current.addTextChangedListener(object : TextWatcher {
                override fun beforeTextChanged(s: CharSequence?, start: Int, count: Int, after: Int) {}
                override fun onTextChanged(s: CharSequence?, start: Int, before: Int, count: Int) {
                    if (isUpdatingBoxes) return
                    val raw = s?.toString() ?: ""
                    val digits = raw.filter { it.isDigit() }

                    // Si l'utilisateur colle un texte contenant plusieurs chiffres (ex: 6 chiffres de Gmail)
                    if (digits.length >= 2) {
                        fillOtpBoxes(digits)
                        return
                    }

                    if (digits.isNotEmpty()) {
                        if (raw != digits) {
                            isUpdatingBoxes = true
                            current.setText(digits.take(1))
                            current.setSelection(1)
                            isUpdatingBoxes = false
                        }
                        next?.requestFocus()
                    }
                }
                override fun afterTextChanged(s: Editable?) {}
            })

            current.setOnKeyListener { _, keyCode, event ->
                if (event.action == KeyEvent.ACTION_DOWN && keyCode == KeyEvent.KEYCODE_DEL) {
                    if (current.text.isEmpty() && prev != null) {
                        prev.requestFocus()
                        prev.setText("")
                        return@setOnKeyListener true
                    }
                }
                false
            }
        }
    }

    private fun getEnteredOtp(): String {
        return otpInputs.joinToString("") { it.text.toString().trim() }
    }

    private fun submitOtp() {
        val code = getEnteredOtp()
        if (code.length < 6) {
            Toast.makeText(requireContext(), "Veuillez saisir les 6 chiffres du code.", Toast.LENGTH_SHORT).show()
            return
        }

        // Fermer le clavier
        val imm = requireContext().getSystemService(Context.INPUT_METHOD_SERVICE) as? InputMethodManager
        imm?.hideSoftInputFromWindow(binding.root.windowToken, 0)

        viewModel.verifyOtp(email, code, purpose)
    }

    private fun observeViewModel() {
        viewModel.verifyOtpState.observe(viewLifecycleOwner) { state ->
            if (state == null) return@observe
            when (state) {
                is Resource.Loading -> {
                    binding.progressBar.visibility = View.VISIBLE
                    binding.btnVerifyOtp.isEnabled = false
                }
                is Resource.Success -> {
                    binding.progressBar.visibility = View.GONE
                    binding.btnVerifyOtp.isEnabled = true
                    viewModel.resetVerifyOtpState()

                    val session = WeariaApplication.instance.sessionManager

                    if (purpose == "REGISTER") {
                        if (session.isProfileCompleted()) {
                            Toast.makeText(requireContext(), "Compte créé et vérifié avec succès !", Toast.LENGTH_SHORT).show()
                            findNavController().navigate(R.id.action_verifyOtp_to_home)
                        } else {
                            Toast.makeText(requireContext(), "Compte vérifié ! Configurons votre style.", Toast.LENGTH_SHORT).show()
                            findNavController().navigate(R.id.action_verifyOtp_to_styleProfile)
                        }
                    } else {
                        Toast.makeText(requireContext(), "Connexion réussie !", Toast.LENGTH_SHORT).show()
                        if (session.isProfileCompleted()) {
                            findNavController().navigate(R.id.action_verifyOtp_to_home)
                        } else {
                            findNavController().navigate(R.id.action_verifyOtp_to_home)
                        }
                    }
                }
                is Resource.Error -> {
                    binding.progressBar.visibility = View.GONE
                    binding.btnVerifyOtp.isEnabled = true
                    Toast.makeText(requireContext(), state.message, Toast.LENGTH_LONG).show()
                }
            }
        }

        viewModel.resendOtpState.observe(viewLifecycleOwner) { state ->
            if (state == null) return@observe
            when (state) {
                is Resource.Loading -> {
                    binding.tvResendBtn.isEnabled = false
                }
                is Resource.Success -> {
                    viewModel.resetResendOtpState()
                    Toast.makeText(requireContext(), state.data, Toast.LENGTH_SHORT).show()
                }
                is Resource.Error -> {
                    binding.tvResendBtn.isEnabled = true
                    viewModel.resetResendOtpState()
                    Toast.makeText(requireContext(), state.message, Toast.LENGTH_SHORT).show()
                }
            }
        }
    }

    private fun startResendCooldown() {
        binding.tvResendBtn.isEnabled = false
        binding.tvResendBtn.alpha = 0.5f
        binding.tvTimer.visibility = View.VISIBLE

        resendTimer?.cancel()
        resendTimer = object : CountDownTimer(30000, 1000) {
            override fun onTick(millisUntilFinished: Long) {
                if (_binding != null) {
                    binding.tvTimer.text = "Renvoyer dans ${millisUntilFinished / 1000}s"
                }
            }

            override fun onFinish() {
                if (_binding != null) {
                    binding.tvResendBtn.isEnabled = true
                    binding.tvResendBtn.alpha = 1.0f
                    binding.tvTimer.visibility = View.GONE
                }
            }
        }.start()
    }

    override fun onDestroyView() {
        super.onDestroyView()
        resendTimer?.cancel()
        resendTimer = null
        _binding = null
    }
}
