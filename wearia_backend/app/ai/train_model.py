"""
Script d'entraînement amélioré du modèle IA Wearia
- Fashion-MNIST 400 échantillons/classe
- Augmentation agressive (flip, rotation, luminosité, zoom crop)
- Random Forest 200 arbres
- Rapport complet par catégorie
"""

import os
import sys
import gzip
import random
from pathlib import Path
import numpy as np
import cv2
import joblib
from sklearn.model_selection import train_test_split, StratifiedKFold
from sklearn.preprocessing import StandardScaler
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier, VotingClassifier
from sklearn.metrics import classification_report, accuracy_score
from sklearn.neighbors import KNeighborsClassifier

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from app.core.config import settings
from app.ai.feature_extraction import extract_advanced_features

# Mapping Fashion-MNIST → catégories Wearia
FASHION_MNIST_MAPPING = {
    0: "T-Shirt",
    1: "Pantalon",
    2: "Pull",
    3: "Robe",
    4: "Manteau",
    6: "Chemise",
    7: "Baskets",
    8: "Sac",
    9: "Bottes",
}


def augment_image(img: np.ndarray, n: int = 6) -> list:
    """Génère n variations augmentées d'une image pour robustesse."""
    results = [img]
    h, w = img.shape[:2]

    for _ in range(n):
        aug = img.copy()

        # Flip horizontal (50%)
        if random.random() > 0.5:
            aug = cv2.flip(aug, 1)

        # Rotation légère ±15°
        angle = random.uniform(-15, 15)
        M_rot = cv2.getRotationMatrix2D((w // 2, h // 2), angle, 1.0)
        aug = cv2.warpAffine(aug, M_rot, (w, h), borderMode=cv2.BORDER_REFLECT)

        # Luminosité + contraste
        alpha = random.uniform(0.80, 1.20)
        beta = random.randint(-25, 25)
        aug = np.clip(alpha * aug.astype(np.float32) + beta, 0, 255).astype(np.uint8)

        # Zoom crop aléatoire (5–15%)
        margin = random.randint(0, int(min(h, w) * 0.12))
        if margin > 0:
            aug = aug[margin:h-margin, margin:w-margin]
            aug = cv2.resize(aug, (w, h), interpolation=cv2.INTER_AREA)

        results.append(aug)

    return results


def load_fashion_mnist_data(target_dir: Path, max_samples_per_class: int = 400):
    """Charge un échantillon équilibré de Fashion-MNIST avec augmentation."""
    lbl_p = target_dir / "train-labels-idx1-ubyte.gz"
    img_p = target_dir / "train-images-idx3-ubyte.gz"

    if not lbl_p.exists() or not img_p.exists():
        print(f"[ERREUR] Fashion-MNIST introuvable dans {target_dir}")
        return [], []

    with gzip.open(lbl_p, "rb") as lb:
        labels = np.frombuffer(lb.read(), dtype=np.uint8, offset=8)
    with gzip.open(img_p, "rb") as im:
        images = np.frombuffer(im.read(), dtype=np.uint8, offset=16).reshape(len(labels), 28, 28)

    class_counts = {k: 0 for k in FASHION_MNIST_MAPPING}
    skirt_count = 0
    short_count = 0
    jean_count  = 0

    X_imgs, y_labels = [], []

    for i in range(len(labels)):
        lbl = int(labels[i])
        raw = images[i]  # 28×28 grayscale

        # Upscale vers 128×128 couleur simulée (gray→BGR)
        img_128 = cv2.resize(raw, (128, 128), interpolation=cv2.INTER_CUBIC)
        img_bgr = cv2.cvtColor(img_128, cv2.COLOR_GRAY2BGR)

        # Classes directes
        if lbl in FASHION_MNIST_MAPPING and class_counts[lbl] < max_samples_per_class:
            class_counts[lbl] += 1
            X_imgs.append(img_bgr)
            y_labels.append(FASHION_MNIST_MAPPING[lbl])

        # Jupe : 60% inférieurs d'une Robe (label 3)
        if lbl == 3 and skirt_count < max_samples_per_class:
            skirt_count += 1
            lower = raw[11:28, :]
            sk = cv2.resize(lower, (128, 128), interpolation=cv2.INTER_CUBIC)
            X_imgs.append(cv2.cvtColor(sk, cv2.COLOR_GRAY2BGR))
            y_labels.append("Jupe")

        # Short : 55% supérieurs d'un Pantalon (label 1)
        if lbl == 1 and short_count < max_samples_per_class:
            short_count += 1
            upper = raw[0:15, :]
            sh = cv2.resize(upper, (128, 128), interpolation=cv2.INTER_CUBIC)
            X_imgs.append(cv2.cvtColor(sh, cv2.COLOR_GRAY2BGR))
            y_labels.append("Short")

        # Jean : Pantalon (label 1) → teinte bleue simulée
        if lbl == 1 and jean_count < max_samples_per_class:
            jean_count += 1
            jean_img = cv2.cvtColor(
                cv2.resize(raw, (128, 128), interpolation=cv2.INTER_CUBIC),
                cv2.COLOR_GRAY2BGR
            )
            # Teinter en bleu denim
            jean_img[:, :, 0] = np.clip(jean_img[:, :, 0].astype(int) + 40, 0, 255)  # +blue
            jean_img[:, :, 2] = np.clip(jean_img[:, :, 2].astype(int) - 20, 0, 255)  # -red
            X_imgs.append(jean_img)
            y_labels.append("Jean")

    print(f"[Fashion-MNIST] {len(X_imgs)} images chargées.")
    return X_imgs, y_labels


def load_real_upload_images(uploads_dir: Path, aug_per_class: int = 60):
    """Charge et augmente les photos HD réelles."""
    source_map = {
        "T-Shirt":           ["tshirt_noir.jpg", "tshirt_blanc.jpg"],
        "Chemise":           ["chemise_oxford_blanche.jpg"],
        "Polo":              ["polo_marine.jpg"],
        "Pull":              ["pull_maille_beige.jpg", "4f7fa19c-4042-47ff-8b0e-f70994641311.jpg"],
        "Sweat":             ["sweat_capuche_gris.jpg"],
        "Pantalon":          ["chino_beige.jpg", "pantalon_noir.jpg"],
        "Jean":              ["jean_slim_bleu.jpg"],
        "Short":             ["short_kaki.jpg"],
        "Veste":             ["bomber_noir.jpg", "blazer_marine.jpg", "veste_jean.jpg"],
        "Manteau":           ["manteau_gris.jpg"],
        "Baskets":           ["baskets_blanches.jpg", "baskets_sport_noires.jpg"],
        "Chaussures de ville": ["derbies_marron.jpg"],
    }

    X_imgs, y_labels = [], []

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

        for _ in range(aug_per_class):
            base = random.choice(base_imgs)
            variants = augment_image(base, n=1)
            X_imgs.append(variants[-1])
            y_labels.append(cname)

    print(f"[Uploads réels] {len(X_imgs)} images augmentées chargées.")
    return X_imgs, y_labels


def train_and_save_production_model():
    print("=" * 70)
    print("ENTRAÎNEMENT MODÈLE WEARIA v2 — Random Forest 200 arbres")
    print("=" * 70)

    dataset_dir = Path(__file__).resolve().parent.parent.parent / "dataset"
    uploads_dir = Path(settings.UPLOAD_DIR)

    # 1. Données Fashion-MNIST (400/classe)
    fmnist_imgs, fmnist_lbls = load_fashion_mnist_data(dataset_dir, max_samples_per_class=400)

    # 2. Photos réelles augmentées (60/classe)
    real_imgs, real_lbls = load_real_upload_images(uploads_dir, aug_per_class=60)

    all_imgs  = fmnist_imgs + real_imgs
    all_lbls  = fmnist_lbls + real_lbls

    print(f"\n[Dataset] Total : {len(all_imgs)} images / {len(set(all_lbls))} classes")
    from collections import Counter
    for cls, cnt in sorted(Counter(all_lbls).items()):
        print(f"  · {cls:25s} : {cnt}")

    # 3. Extraction des 1776 descripteurs HOG+Texture+Géométrie
    print("\n[Extraction] Calcul des descripteurs visuels (1776 dim)...")
    X_feats = []
    for idx, img in enumerate(all_imgs):
        if idx % 200 == 0:
            print(f"  ... {idx}/{len(all_imgs)}")
        feats = extract_advanced_features(img)
        X_feats.append(feats)

    X = np.vstack(X_feats)
    y = np.array(all_lbls)

    # 4. Split 80/20 stratifié
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.20, random_state=42, stratify=y
    )

    # 5. Normalisation
    scaler = StandardScaler()
    X_train_s = scaler.fit_transform(X_train)
    X_test_s  = scaler.transform(X_test)

    # 6. Random Forest 200 arbres
    print("\n[Entraînement] Random Forest 200 arbres (n_jobs=-1)...")
    clf = RandomForestClassifier(
        n_estimators=200,
        max_depth=25,
        min_samples_split=2,
        min_samples_leaf=1,
        max_features="sqrt",
        class_weight="balanced",   # équilibre même si classes inégales
        random_state=42,
        n_jobs=-1,
    )
    clf.fit(X_train_s, y_train)

    # 7. Évaluation
    y_pred = clf.predict(X_test_s)
    acc = accuracy_score(y_test, y_pred)
    print(f"\n[RÉSULTAT] Précision globale : {acc * 100:.2f}%")
    print("\nRapport détaillé par catégorie :")
    print(classification_report(y_test, y_pred, zero_division=0))

    # 8. Sauvegarde
    settings.AI_MODELS_DIR.mkdir(parents=True, exist_ok=True)
    model_path  = settings.AI_MODELS_DIR / "knn_model.joblib"
    scaler_path = settings.AI_MODELS_DIR / "scaler.joblib"

    joblib.dump(clf, model_path)
    joblib.dump(scaler, scaler_path)

    print(f"\n[OK] Modèle sauvegardé : {model_path}")
    print(f"[OK] Scaler sauvegardé  : {scaler_path}")
    print("=" * 70)


if __name__ == "__main__":
    train_and_save_production_model()
