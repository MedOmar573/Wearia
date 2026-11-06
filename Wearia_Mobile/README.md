# 📱 Wearia — Application Android Native

Application mobile Android native développée en **Kotlin** avec architecture **MVVM** stricte pour le projet Wearia (Projet d'Intégration L3-DSI2, ISET de Radès).

---

## 🏗️ Architecture Mobile

- **Modèle (Data) :**
  - **Remote (Retrofit 2 + Gson) :** `ApiService.kt`, communication REST asynchrone avec coroutines (`suspend fun`), injection du JWT Bearer token dans chaque requête protégée.
  - **Local (Room Database) :** `WeariaDatabase.kt`, `OutfitDao.kt`, `ClothingDao.kt`, persistance locale et consultation des favoris hors-ligne (**NF04**).
- **Repositories :**
  - `AuthRepository` : Inscription (BR05), connexion, session JWT.
  - `ClothingRepository` : CRUD dressing, upload multipart photo et appel IA (`/ai/classify`).
  - `OutfitRepository` : Recommandations (BR01 à BR09), favoris, feedback (AIME / MOYEN / PAS_POUR_MOI).
  - `ProfileRepository` : Profil utilisateur, mensurations, routines hebdomadaires et catalogue.
- **ViewModels :**
  - `AuthViewModel`, `ClothingViewModel`, `OutfitViewModel`, `ProfileViewModel`.
  - Encapsulent la logique d'état (`LiveData` / `StateFlow`), isolation complète de la vue.
- **Vue (UI) :**
  - **Single-Activity Architecture :** `MainActivity.kt` hébergeant le `NavHostFragment` et la `BottomNavigationView`.
  - `LoginFragment` & `RegisterFragment` (Sprint 1)
  - `HomeFragment` : Tableau de bord d'accueil et raccourcis
  - `CameraFragment` : Capture photo avec **CameraX** (Sprint 2)
  - `AddClothingFragment` : Vérification et correction manuelle des tags IA (**US02**)
  - `DressingFragment` : Liste en grille 2 colonnes, filtres par statut et recherche
  - `OutfitRecommendationFragment` : Recommandation, score /100, météo et saisie de secours
  - `ProfileFragment` : Profil et gestion des routines (Lundi = Université, etc. - BR09)
  - `ShoppingFragment` : Démonstration du Personal Shopper IA

---

## ⚙️ Configuration & Lancement dans Android Studio

### 1. Ouvrir le projet
1. Lancez **Android Studio**.
2. Cliquez sur **Open** et sélectionnez le dossier `Wearia_Mobile` :
   `C:\Users\DELL\Desktop\L3DSI\projet\Wearia\Wearia_Mobile`
3. Attendez la synchronisation Gradle initiale.

---

### ⚠️ Pièges de Démonstration à Respecter (Mentionnés dans l'Architecture)

1. **Émulateur Android Studio :**
   Le fichier `app/build.gradle.kts` est préconfiguré avec :
   ```kotlin
   buildConfigField("String", "BASE_URL", "\"http://10.0.2.2:8000/\"")
   ```
   > **Rappel :** N'utilisez **jamais** `localhost` depuis l'émulateur Android, car `localhost` pointe vers le téléphone lui-même. `10.0.2.2` est l'adresse IP de votre PC hôte vue par l'émulateur.

2. **Smartphone physique (Wi-Fi) :**
   Si vous testez sur un vrai téléphone connecté au même réseau Wi-Fi :
   - Récupérez l'IP locale de votre PC (`ipconfig` sous Windows, ex: `192.168.1.45`).
   - Modifiez dans `app/build.gradle.kts` :
     ```kotlin
     buildConfigField("String", "BASE_URL", "\"http://192.168.1.45:8000/\"")
     ```
   - Assurez-vous de lancer Uvicorn avec `--host 0.0.0.0` :
     ```bash
     uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
     ```

3. **Trafic HTTP en clair autorisé :**
   Le fichier `AndroidManifest.xml` intègre déjà `android:usesCleartextTraffic="true"` pour autoriser les requêtes HTTP de test en local.

4. **Secours Météo :**
   Sur l'écran de recommandation, une icône permet de saisir manuellement la température (ex: `12°C`) et la pluie pour tester immédiatement la règle **BR02** (veste obligatoire en cas de froid ou de pluie) même sans connexion Internet.

