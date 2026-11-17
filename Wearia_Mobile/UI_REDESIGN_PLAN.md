# PLAN DE REFONTE UI/UX — PROJET WEARIA
**Direction Artistique : Fresh Fashion Tech**  
*Palette : Violet #6C47FF, Turquoise #12B5A6, Dégradé 135°, Fond #F7F6FB / Dark #0E0D14*

---

## 1. Audit de l'Application Existante

### A. Écrans (Fragments & Activités)
1. **MainActivity (`activity_main.xml`)** : Conteneur Single-Activity avec `NavHostFragment` et `BottomNavigationView` (`bottom_nav_menu.xml`).
2. **Onboarding (`fragment_onboarding.xml`)** : Slider de bienvenue en ViewPager2 avec 3 slides de présentation et bouton d'action.
3. **Authentification (`fragment_login.xml`, `fragment_register.xml`)** : Connexion et inscription avec token JWT.
4. **Accueil / Dashboard (`fragment_home.xml`)** : Salutation dynamique, carte météo, carte héros tenue du jour, tuiles d'actions rapides 2x2, aperçu planning hebdomadaire.
5. **Garde-robe / Dressing (`fragment_dressing.xml`, `item_clothing.xml`)** : Barre de recherche arrondie, chips de catégories défilantes, grille 2 colonnes avec statuts et badges pastel.
6. **Capture & Ajout vêtement (`fragment_camera.xml`, `fragment_add_clothing.xml`)** : Prise de vue CameraX ou galerie, animation de scan IA, formulaire d'édition de catégorie, couleur, style, coupe, bouton d'enregistrement.
7. **Recommandation & Détail Tenue (`fragment_outfit_recommendation.xml`, `dialog_manual_weather.xml`, `dialog_outfit_feedback.xml`)** : Collage des pièces de la tenue, anneau de score de compatibilité /100, explication des règles météo/occasion, boutons aimer/autre idée, dialog feedback avec chips de raisons.
8. **Favoris & Historique (`fragment_my_outfits.xml`, `item_saved_outfit.xml`)** : Liste des tenues enregistrées hors-ligne (Room) et historique.
9. **Profil & Routines (`fragment_profile.xml`, `fragment_color_preferences.xml`, `fragment_style_profile.xml`, `item_color_palette.xml`)** : Avatar utilisateur, mensurations, sélecteur de routine hebdomadaire en puces rondes, grilles de pastilles de couleurs, styles favoris.
10. **Personal Shopper (`fragment_shopping.xml`, `item_shopping.xml`)** : Carrousel d'articles suggérés (mode démo statique préservé).

### B. Composants Réutilisables à Créer
- **Dégradé de marque 135°** (`bg_brand_gradient.xml` : #12B5A6 → #6C47FF).
- **Badges de catégories pastel** (Haut: lavande douce, Bas: bleu ciel doux, Chaussures: pêche douce, Veste: ambre douce, Robe: rose poudré, Accessoire: menthe douce).
- **Cartes arrondies 20dp & 28dp** avec élévation douce et fond de surface distinct.
- **Effet de pression tactile générique (Extension Kotlin)** : Animation de scale à 0.96 avec haptique légère (`HapticFeedbackConstants.CONTEXT_CLICK`).
- **Anneau de progression de compatibilité** : Anneau dégradé avec count-up animé.
- **Animation de balayage de scan IA** : Ligne lumineuse animée pendant la classification d'image.

---

## 2. Déroulement des Phases de Refonte

- **Phase 1 : Design System & Ressources**
  - Configuration de `colors.xml` (clair) et `values-night/colors.xml` (sombre).
  - Thèmes complets `themes.xml` (Material3 DayNight).
  - Dégradés, drawables vectoriels (icônes modernes arrondies remplaçant les emojis), sélecteurs d'état.
  - Typographie (Plus Jakarta Sans & Inter) et dimensions (espacements 4/8/16/20/28dp).

- **Phase 2 : Composants Partagés & Extensions**
  - Extension d'effet de pression tactile et haptique.
  - Anneau de score personnalisé.
  - Vues d'états vides et d'erreurs élégantes.

- **Phase 3 : Refonte des Écrans (dans l'ordre spécifié)**
  - 1. Onboarding & Auth (Login / Register).
  - 2. Accueil (HomeFragment).
  - 3. Garde-robe (DressingFragment & item_clothing.xml).
  - 4. Ajout & Reconnaissance IA (Camera & AddClothingFragment).
  - 5. Tenue & Feedback (OutfitRecommendationFragment & Dialogs).
  - 6. Favoris, Routines, Profil & Shopping.

- **Phase 4 : Polish & Transitions**
  - Transitions fluides entre fragments (shared axis / fade through).
  - Mode sombre complet et réactivité.

- **Phase 5 : Compilation & Validation**
  - Vérification de compilation (`assembleDebug`).
  - Validation de non-régression sur le dossier `data/`, les ViewModels et le backend.
