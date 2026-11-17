# 👗 Wearia — Assistant Vestimentaire Intelligent

Projet d'Intégration — L3 DSI (Garde-robe virtuelle, Recommandation IA de tenues selon météo/occasion/style, Feedback & Routines).

---

## 🏗️ Architecture du Projet

Le projet se compose de trois parties principales :
1. **Base de données** : PostgreSQL (`wearia_db`)
2. **Backend API** : Python 3.10+ / FastAPI (dans le dossier `wearia_backend/`)
3. **Application Mobile** : Android natif Kotlin + XML (dans le dossier `Wearia_Mobile/`)

---

## 🚀 Guide de Démarrage Rapide

### Étape 1 : Base de données (PostgreSQL)
1. Assurez-vous que le service **PostgreSQL** est démarré.
2. Créez la base de données :
   ```sql
   CREATE DATABASE wearia_db;
   ```
3. Vérifiez vos identifiants dans le fichier `wearia_backend/.env` :
   ```env
   DATABASE_URL="postgresql+psycopg2://postgres:admin@localhost:5432/wearia_db"
   ```

---

### Étape 2 : Backend FastAPI (avec VS Code ou Terminal)
1. Ouvrez un terminal dans le dossier `wearia_backend/` :
   ```bash
   cd wearia_backend
   ```
2. Installez les dépendances :
   ```bash
   pip install -r requirements.txt
   ```
3. Démarrez le serveur :
   ```bash
   python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
   ```
4. La documentation Swagger interactive est accessible sur :  
   👉 **http://localhost:8000/docs**

---

### Étape 3 : Application Mobile (avec Android Studio)
1. Ouvrez le dossier `Wearia_Mobile/` directement dans **Android Studio**.
2. Laissez Gradle synchroniser les dépendances automatiquement.
3. Branchez votre téléphone Android en USB (ou lancez un émulateur).
4. **Si vous utilisez un téléphone physique en USB**, redirigez le port vers votre PC :
   ```bash
   adb reverse tcp:8000 tcp:8000
   ```
5. Cliquez sur le bouton **Run ▶** (vert) dans Android Studio pour lancer l'application !
