package com.wearia.app

import android.os.Bundle
import android.view.View
import androidx.appcompat.app.AppCompatActivity
import androidx.navigation.NavController
import androidx.navigation.fragment.NavHostFragment
import androidx.navigation.ui.setupWithNavController
import com.wearia.app.databinding.ActivityMainBinding

/**
 * MainActivity : point d'entrée unique de l'application.
 * Héberge le NavHostFragment (Navigation Component) et la BottomNavigationView.
 * Sans ActionBar native (style luxueux NoActionBar avec écrans plein format).
 */
class MainActivity : AppCompatActivity() {

    private lateinit var binding: ActivityMainBinding
    private lateinit var navController: NavController

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        binding = ActivityMainBinding.inflate(layoutInflater)
        setContentView(binding.root)

        val navHostFragment = supportFragmentManager
            .findFragmentById(R.id.nav_host_fragment) as NavHostFragment
        navController = navHostFragment.navController

        val session = WeariaApplication.instance.sessionManager

        // Navigation dynamique :
        // 1. Déjà connecté -> Accueil
        // 2. Nouvel utilisateur (jamais vu l'onboarding) -> Onboarding
        // 3. Déconnecté (onboarding déjà vu) -> Connexion
        val navGraph = navController.navInflater.inflate(R.navigation.nav_graph)
        val startDest = when {
            session.isLoggedIn() -> R.id.homeFragment
            !session.isOnboardingCompleted() -> R.id.onboardingFragment
            else -> R.id.loginFragment
        }
        navGraph.setStartDestination(startDest)
        navController.graph = navGraph

        // Configurer la bottom navigation
        val bottomNav = binding.bottomNav
        bottomNav.setupWithNavController(navController)

        // Écrans où la barre de navigation inférieure doit être masquée (Auth, Camera, Onboarding, etc.)
        val hideBottomNavDestinations = setOf(
            R.id.onboardingFragment,
            R.id.styleProfileFragment,
            R.id.colorPreferencesFragment,
            R.id.loginFragment,
            R.id.registerFragment,
            R.id.cameraFragment
        )

        navController.addOnDestinationChangedListener { _, destination, _ ->
            bottomNav.visibility = if (destination.id in hideBottomNavDestinations) {
                View.GONE
            } else {
                View.VISIBLE
            }
        }
    }
}
