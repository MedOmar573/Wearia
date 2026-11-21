# 🧥 Wearia — Backend API & Module IA

Backend REST développé avec **FastAPI**, **PostgreSQL** (SQLAlchemy ORM) et **Scikit-Learn (KNN)** pour l'application mobile Wearia (Projet d'Intégration L3-DSI2, ISET de Radès).

---

## 🚀 Installation & Démarrage Rapide

### 1. Prérequis
- Python 3.10+
- PostgreSQL (ou SQLite en fallback de développement)

### 2. Création de l'environnement virtuel & Dépendances
Dans le dossier `wearia_backend` :
```bash
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```

### 3. Configuration (.env)
Un fichier `.env` est prêt à l'emploi. Vous pouvez modifier la variable `DATABASE_URL` pour cibler votre base PostgreSQL :
```env
DATABASE_URL="postgresql+psycopg://postgres:postgres@localhost:5432/wearia_db"
USE_SQLITE_FALLBACK=True
# Sources configurées pour le marché tunisien
WEARIA_SHOPPER_STORES="Exist Tunisie Homme|https://www.exist.com.tn|/235-t-shirts,/189-jeans,/196-baskets,/206-chemises;Mabrouk Femme|https://mabrouk.tn|/categorie-produit/vetements-femmes/pulls-t-shirts/,/categorie-produit/vetements-femmes/jupes-pantalons/,/categorie-produit/accessoires/chaussures/"
```

Le Shopper synchronise ces pages au démarrage d'une recherche si le catalogue n'a pas
été actualisé dans les 30 dernières minutes. Il n'ajoute une fiche que si la page produit
HTTPS confirme le nom et le prix en JSON-LD et annonce un stock disponible. Il respecte
`robots.txt`. Sans source configurée ou sans métadonnées vérifiables, aucune tenue n'est
retournée; aucune liste de démonstration n'est utilisée.

### 4. Lancer le serveur FastAPI
```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

- **Documentation Swagger interactive :** [http://localhost:8000/docs](http://localhost:8000/docs)
- **Documentation ReDoc :** [http://localhost:8000/redoc](http://localhost:8000/redoc)

---

## 🤖 Entraînement du Modèle IA (KNN)

Pour lancer le pipeline d'entraînement et d'évaluation du KNN (HOG + scikit-learn + métriques) :
```bash
python -m app.ai.train_model
```
Le modèle et le normaliseur sont enregistrés dans le dossier `models/` sous `knn_model.joblib` et `scaler.joblib`.

---

## 📱 Configuration pour l'Application Android (Membre A)

1. **Émulateur Android Studio :**
   Utilisez l'URL de base : `http://10.0.2.2:8000` (et non `localhost`).

2. **Téléphone physique :**
   Connectez le PC et le smartphone au même réseau Wi-Fi et utilisez l'adresse IP locale du PC :
   `http://192.168.x.x:8000`

3. **Trafic HTTP en clair (Android) :**
   Ajoutez dans le fichier `AndroidManifest.xml` de votre projet Android :
   ```xml
   android:usesCleartextTraffic="true"
   ```

---

## 📌 Routes Principales de l'API

| Méthode | Route | Description |
|---|---|---|
| **POST** | `/auth/register` | Inscription d'un utilisateur (BR05) |
| **POST** | `/auth/login` | Connexion et obtention du jeton JWT |
| **GET / PUT / DELETE** | `/users/me` | Profil, mensurations et préférences |
| **GET** | `/referentials/categories`, `/types`, `/colors`, `/styles` | Listes pour formulaires |
| **GET / POST** | `/clothes` | Dressing : consultation filtrée et ajout vêtement |
| **GET / PUT / DELETE** | `/clothes/{id}` | Détail, modification et suppression |
| **POST** | `/ai/classify` | Analyse d'une photo (catégorie KNN + couleur OpenCV) |
| **GET / POST / PUT / DELETE** | `/routines` | Routines hebdomadaires (ex. Lundi = Université) |
| **GET / POST / PUT / DELETE** | `/events` | Événements ponctuels |
| **POST** | `/recommendations` | Génération de tenue selon météo et règles BR01 à BR09 |
| **GET / POST / PUT / DELETE** | `/outfits` | Historique et favoris |
| **GET / POST** | `/outfits/{id}/feedback` | Avis sur une tenue (AIME / MOYEN / PAS_POUR_MOI) |
| **GET** | `/shopping/suggestions` | Suggestions d'achat (Personal Shopper IA) |
| **POST** | `/shopper/generate-outfits` | Tenues issues des fiches produit vérifiées des boutiques configurées |

