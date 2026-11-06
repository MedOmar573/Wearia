"""
Script d'entraînement professionnel du modèle IA Wearia
Utilise le benchmark réel Fashion-MNIST (Zalando) combiné aux photos haute résolution de vêtements.
Permet une vraie généralisation capable de distinguer les vraies coupes et textures :
- Pull (Pullover : maille, pas de boutons verticaux, col rond/roulé)
- Chemise (Shirt : col rabattu rigide, patte de boutonnage centrale)
- T-Shirt (T-shirt/top : col rond fin, jersey plat)
- Pantalon (Trouser : jambes longues, denim ou chino)
- Veste (Coat / Jacket : revers, fermeture, matière épaisse)
- Baskets (Sneakers : semelle basse plate)
- Chaussures de ville (Boots / Richelieu / Derbies)
"""

import os
import sys
import gzip
import random
from pathlib import Path
import numpy as np
import cv2
import joblib
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import classification_report, accuracy_score

# Ajouter le chemin racine du backend
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from app.core.config import settings
from app.ai.feature_extraction import extract_advanced_features

# Mapping des labels officiels Fashion-MNIST vers les types de vêtements Wearia
FASHION_MNIST_MAPPING = {
    0: "T-Shirt",
    1: "Pantalon",
    2: "Pull",
    4: "Veste",
    6: "Chemise",
    7: "Baskets",
    9: "Chaussures de ville"
}

def load_fashion_mnist_data(target_dir: Path, max_samples_per_class: int = 300):
    """Charge un échantillon équilibré d'images réelles Fashion-MNIST."""
    lbl_p = target_dir / "train-labels-idx1-ubyte.gz"
    img_p = target_dir / "train-images-idx3-ubyte.gz"

    if not lbl_p.exists() or not img_p.exists():
        print(f"Dataset Fashion-MNIST introuvable dans {target_dir}")
        return [], []

    with gzip.open(lbl_p, "rb") as lb:
        labels = np.frombuffer(lb.read(), dtype=np.uint8, offset=8)
    with gzip.open(img_p, "rb") as im:
        images = np.frombuffer(im.read(), dtype=np.uint8, offset=16).reshape(len(labels), 28, 28)

    class_counts = {k: 0 for k in FASHION_MNIST_MAPPING.keys()}
    X_imgs = []
    y_labels = []

    for i in range(len(labels)):
        lbl = int(labels[i])
        if lbl in FASHION_MNIST_MAPPING and class_counts[lbl] < max_samples_per_class:
            class_counts[lbl] += 1
            # Redimensionner l'image 28x28 en 128x128 pour l'extraction HOG
            img_128 = cv2.resize(images[i], (128, 128), interpolation=cv2.INTER_CUBIC)
            X_imgs.append(img_128)
            y_labels.append(FASHION_MNIST_MAPPING[lbl])

    print(f"Fashion-MNIST : {len(X_imgs)} images chargées ({max_samples_per_class} par classe).")
    return X_imgs, y_labels

def load_real_upload_images(uploads_dir: Path, aug_count_per_class: int = 40):
    """Enrichit avec les photos réelles HD du dossier uploads/."""
    source_map = {
        "Pull": ["pull_maille_beige.jpg", "4f7fa19c-4042-47ff-8b0e-f70994641311.jpg"],
        "Chemise": ["chemise_oxford_blanche.jpg"],
        "T-Shirt": ["tshirt_noir.jpg", "tshirt_blanc.jpg"],
        "Pantalon": ["chino_beige.jpg", "pantalon_noir.jpg", "jean_slim_bleu.jpg", "short_kaki.jpg"],
        "Veste": ["bomber_noir.jpg", "blazer_marine.jpg", "veste_jean.jpg", "manteau_gris.jpg"],
        "Baskets": ["baskets_blanches.jpg", "baskets_sport_noires.jpg"],
        "Chaussures de ville": ["derbies_marron.jpg"]
    }

    X_imgs = []
    y_labels = []

    for cname, flist in source_map.items():
        base_imgs = []
        for fn in flist:
            fp = uploads_dir / fn
            if fp.exists():
                im = cv2.imread(str(fp))
                if im is not None:
                    base_imgs.append(im)

        if not base_imgs:
            continue

        for _ in range(aug_count_per_class):
            base = random.choice(base_imgs)
            # Variations légères
            h, w = base.shape[:2]
            if random.random() > 0.5:
                base = cv2.flip(base, 1)
            angle = random.uniform(-10, 10)
            M = cv2.getRotationMatrix2D((w // 2, h // 2), angle, 1.0)
            aug = cv2.warpAffine(base, M, (w, h), borderMode=cv2.BORDER_REFLECT)
            alpha = random.uniform(0.9, 1.1)
            beta = random.randint(-15, 15)
            aug = np.clip(alpha * aug.astype(np.float32) + beta, 0, 255).astype(np.uint8)
            X_imgs.append(aug)
            y_labels.append(cname)

    print(f"Photos réelles uploads/ augmentées : {len(X_imgs)} images créées.")
    return X_imgs, y_labels

def train_and_save_production_model():
    print("=" * 65)
    print("ENTRAINEMENT DU MODELE DE PRODUCTION WEARIA (GENERALISATION IA)")
    print("=" * 65)

    dataset_dir = Path(__file__).resolve().parent.parent.parent / "dataset"
    uploads_dir = Path(settings.UPLOAD_DIR)

    # 1. Charger Fashion-MNIST (300 échantillons par classe)
    fmnist_imgs, fmnist_lbls = load_fashion_mnist_data(dataset_dir, max_samples_per_class=350)

    # 2. Charger les photos réelles augmentées (40 par classe)
    real_imgs, real_lbls = load_real_upload_images(uploads_dir, aug_count_per_class=40)

    all_imgs = fmnist_imgs + real_imgs
    all_lbls = fmnist_lbls + real_lbls

    print(f"Total combiné : {len(all_imgs)} images réelles à traiter.")

    # 3. Extraction des 1776 caractéristiques HOG + Texture + Géométrie
    print("Extraction des 1776 descripteurs visuels pour chaque image...")
    X_feats = []
    for img in all_imgs:
        feats = extract_advanced_features(img)
        X_feats.append(feats)

    X = np.vstack(X_feats)
    y = np.array(all_lbls)

    # 4. Train/Test Split (80% train / 20% test)
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )

    # 5. Normalisation
    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train)
    X_test_scaled = scaler.transform(X_test)

    # 6. Entraînement du modèle Random Forest (120 arbres de décision)
    print("Entraînement de l'ensemble Random Forest (120 arbres, n_jobs=-1)...")
    clf = RandomForestClassifier(n_estimators=120, max_depth=20, min_samples_split=3, random_state=42, n_jobs=-1)
    clf.fit(X_train_scaled, y_train)

    # 7. Évaluation rigoureuse
    y_pred = clf.predict(X_test_scaled)
    acc = accuracy_score(y_test, y_pred)
    print(f"\n[SUCCES] Precision globale sur le jeu de test : {acc * 100:.2f}%")
    print("\nRapport de classification par categorie réelle :")
    print(classification_report(y_test, y_pred, zero_division=0))

    # 8. Sauvegarde des artefacts de production
    settings.AI_MODELS_DIR.mkdir(parents=True, exist_ok=True)
    model_path = settings.AI_MODELS_DIR / "knn_model.joblib"
    scaler_path = settings.AI_MODELS_DIR / "scaler.joblib"

    joblib.dump(clf, model_path)
    joblib.dump(scaler, scaler_path)

    print(f"\n[OK] Modèle de production enregistré : {model_path}")
    print(f"[OK] Scaler de production enregistré : {scaler_path}")
    print("=" * 65)

if __name__ == "__main__":
    train_and_save_production_model()
