package com.wearia.app.ui.auth

import android.os.Bundle
import android.view.LayoutInflater
import android.view.View
import android.view.ViewGroup
import androidx.fragment.app.Fragment
import androidx.navigation.fragment.findNavController
import com.wearia.app.R
import com.wearia.app.WeariaApplication
import com.wearia.app.databinding.FragmentOnboardingBinding
import com.wearia.app.utils.addPressEffect

/**
 * OnboardingFragment : Écrans d'accueil et tutoriel modernisés aux couleurs Fresh Fashion Tech.
 */
class OnboardingFragment : Fragment() {

    private var _binding: FragmentOnboardingBinding? = null
    private val binding get() = _binding!!
    private var currentStep = 1

    override fun onCreateView(inflater: LayoutInflater, container: ViewGroup?, savedInstanceState: Bundle?): View {
        _binding = FragmentOnboardingBinding.inflate(inflater, container, false)
        return binding.root
    }

    override fun onViewCreated(view: View, savedInstanceState: Bundle?) {
        super.onViewCreated(view, savedInstanceState)
        updateStepUI()

        binding.btnOnboardingNext.addPressEffect()
        binding.btnOnboardingNext.setOnClickListener {
            if (currentStep < 3) {
                currentStep++
                updateStepUI()
            } else {
                WeariaApplication.instance.sessionManager.setOnboardingCompleted(true)
                findNavController().navigate(R.id.action_onboarding_to_register)
            }
        }
    }

    private fun updateStepUI() {
        when (currentStep) {
            1 -> {
                binding.ivOnboardingGraphic.setImageResource(R.drawable.onboarding_graphic_1)
                binding.tvOnboardingTitle.text = "Révélez votre style"
                binding.tvOnboardingSubtitle.text = "Numérisez vos vêtements et découvrez chaque jour de nouvelles combinaisons harmonieuses."
                binding.btnOnboardingNext.text = "Continuer"
                binding.tvFooterSubtext.visibility = View.INVISIBLE
                setDotActive(1)
            }
            2 -> {
                binding.ivOnboardingGraphic.setImageResource(R.drawable.onboarding_graphic_2)
                binding.tvOnboardingTitle.text = "Des tenues créées pour vous"
                binding.tvOnboardingSubtitle.text = "Couleurs, météo, coupe et occasion : l'IA fusionne vos préférences pour un look impeccable."
                binding.btnOnboardingNext.text = "Continuer"
                binding.tvFooterSubtext.visibility = View.INVISIBLE
                setDotActive(2)
            }
            3 -> {
                binding.ivOnboardingGraphic.setImageResource(R.drawable.onboarding_graphic_3)
                binding.tvOnboardingTitle.text = "Votre styliste intelligent"
                binding.tvOnboardingSubtitle.text = "Recevez des suggestions instantanées et optimisez votre garde-robe au quotidien."
                binding.btnOnboardingNext.text = "Commencer"
                binding.tvFooterSubtext.visibility = View.VISIBLE
                setDotActive(3)
            }
        }
    }

    private fun setDotActive(active: Int) {
        val activeBg = R.drawable.bg_circle_fab
        val inactiveBg = R.drawable.bg_circle_button

        binding.dot1.setBackgroundResource(if (active == 1) activeBg else inactiveBg)
        binding.dot1.setTextColor(resources.getColor(if (active == 1) R.color.colorOnPrimary else R.color.colorTextSecondary, null))

        binding.dot2.setBackgroundResource(if (active == 2) activeBg else inactiveBg)
        binding.dot2.setTextColor(resources.getColor(if (active == 2) R.color.colorOnPrimary else R.color.colorTextSecondary, null))

        binding.dot3.setBackgroundResource(if (active == 3) activeBg else inactiveBg)
        binding.dot3.setTextColor(resources.getColor(if (active == 3) R.color.colorOnPrimary else R.color.colorTextSecondary, null))
    }

    override fun onDestroyView() {
        super.onDestroyView()
        _binding = null
    }
}
