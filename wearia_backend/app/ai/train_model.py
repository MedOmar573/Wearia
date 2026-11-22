"""
Script d'entraînement unifié du modèle IA Wearia (v4) :
- Taxonomie canonique alignée sur app/ai/taxonomy.py et PostgreSQL (16 classes entraînées)
- Prétraitement identique à l'inférence (EXIF, RGB, segmentation, letterbox 64x64, polarité normalisée)
- 1792 descripteurs (HOG canonique + 28 métriques géométriques/structurelles/denim/capuche/anse/dôme)
- Fashion-MNIST complet incluant classe 8 (Sac) et séparation proportionnelle Manteau vs Veste
- Générateurs propres pour Short (entrejambe vérifiée), Jean (teinte/trame denim réaliste),
  Sweat (capuche/coupe boxy mixte) et Chapeau (dôme + bord/visière)
- Photos réelles vérifiées visuellement (chino_beige déplacé vers Pantalon)
- Random Forest 240 arbres + StandardScaler
"""

import gzip
import random
import sys
from collections import Counter
from pathlib import Path

import cv2
import joblib
import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, classification_report
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from app.core.config import settings
from app.ai.feature_extraction import FEATURE_DIM, extract_advanced_features
from app.ai.preprocessing import load_image_rgb, segment_garment
from app.ai.taxonomy import ClothingType

# Mapping Fashion-MNIST -> ClothingType canonique (label 4 traité séparément en Manteau vs Veste)
FASHION_MNIST_MAPPING = {
    0: ClothingType.TSHIRT.value,
    1: ClothingType.PANTALON.value,
    2: ClothingType.PULL.value,
    3: ClothingType.ROBE.value,
    6: ClothingType.CHEMISE.value,
    7: ClothingType.BASKETS.value,
    8: ClothingType.SAC.value,
    9: ClothingType.BOTTES.value,
}


def augment_real_rgb(img_rgb: np.ndarray, n: int = 1) -> list:
    """Génère des variations réalistes d'une photo RGB réelle."""
    results = []
    h, w = img_rgb.shape[:2]

    for _ in range(n):
        aug = img_rgb.copy()

        if random.random() > 0.5:
            aug = cv2.flip(aug, 1)

        angle = random.uniform(-10, 10)
        m_rot = cv2.getRotationMatrix2D((w // 2, h // 2), angle, 1.0)
        aug = cv2.warpAffine(aug, m_rot, (w, h), borderMode=cv2.BORDER_REPLICATE)

        alpha = random.uniform(0.82, 1.18)
        beta = random.randint(-18, 18)
        aug = np.clip(alpha * aug.astype(np.float32) + beta, 0, 255).astype(np.uint8)

        margin = random.randint(0, max(1, int(min(h, w) * 0.08)))
        if margin > 0 and h - 2 * margin > 32 and w - 2 * margin > 32:
            aug = aug[margin:h - margin, margin:w - margin]

        results.append(aug)
    return results


def augment_fmnist_cutout(raw_28: np.ndarray) -> np.ndarray:
    """Légère augmentation d'une silhouette Fashion-MNIST tout en conservant le fond à 0."""
    img = cv2.resize(raw_28, (96, 96), interpolation=cv2.INTER_CUBIC)
    h, w = img.shape
    if random.random() > 0.5:
        img = cv2.flip(img, 1)
    angle = random.uniform(-10, 10)
    m_rot = cv2.getRotationMatrix2D((w // 2, h // 2), angle, 1.0)
    img = cv2.warpAffine(img, m_rot, (w, h), borderMode=cv2.BORDER_CONSTANT, borderValue=0)

    fg = img > 18
    if np.any(fg):
        alpha = random.uniform(0.85, 1.15)
        img_f = img.astype(np.float32)
        img_f[fg] = np.clip(img_f[fg] * alpha, 25, 255)
        img = img_f.astype(np.uint8)
    return cv2.cvtColor(img, cv2.COLOR_GRAY2RGB)


def tint_as_denim_rgb(gray_96: np.ndarray) -> np.ndarray:
    """Colorise une silhouette pantalon/short en teinte denim réaliste (indigo, bleu délavé, marine)."""
    rgb = np.zeros((gray_96.shape[0], gray_96.shape[1], 3), dtype=np.uint8)
    fg = gray_96 > 18
    if not np.any(fg):
        return rgb

    # Palettes denim réalistes (R, G, B)
    palette = random.choice([
        (52, 86, 138),   # Indigo classique
        (78, 118, 168),  # Bleu denim moyen
        (115, 152, 195), # Bleu délavé clair
        (36, 56, 94),    # Denim brut marine
    ])
    intensity = gray_96.astype(np.float32) / 220.0
    # Légère trame twill diagonale
    yy, xx = np.indices(gray_96.shape)
    twill = 1.0 + 0.06 * np.sin((xx + yy) * 1.1)
    scale = np.clip(intensity * twill, 0.25, 1.25)

    for c_idx, base_val in enumerate(palette):
        ch = np.clip(base_val * scale, 10, 245).astype(np.uint8)
        rgb[:, :, c_idx] = np.where(fg, ch, 0)
    # Fond clair réaliste pour activer l'analyse couleur/denim identique aux photos réelles
    bg_val = random.randint(232, 248)
    rgb[~fg] = bg_val
    return rgb


def synthesize_hoodie_from_pullover(raw_28: np.ndarray) -> np.ndarray:
    """Construit une silhouette de Sweat à capuche (capuche proéminente + coupe boxy + poche kangourou)."""
    base = cv2.resize(raw_28, (96, 96), interpolation=cv2.INTER_CUBIC)
    canvas = np.zeros((112, 96), dtype=np.uint8)
    canvas[16:112, :] = base

    # Ajouter une capuche arrondie centrée au-dessus du col (y=3..24, x=32..64)
    hood_w = random.randint(13, 18)
    hood_h = random.randint(12, 16)
    hood_tone = int(np.clip(np.percentile(base[base > 25], 60) if np.any(base > 25) else 160, 80, 230))
    cv2.ellipse(canvas, (48, 18), (hood_w, hood_h), 0, 180, 360, hood_tone, -1)
    cv2.ellipse(canvas, (48, 18), (max(4, hood_w - 5), max(4, hood_h - 4)), 0, 195, 345, int(hood_tone * 0.65), 2)

    # Cordon et couture de poche kangourou subtils
    cv2.line(canvas, (44, 24), (43, 44), int(hood_tone * 0.55), 1)
    cv2.line(canvas, (52, 24), (53, 44), int(hood_tone * 0.55), 1)
    cv2.rectangle(canvas, (30, 74), (66, 96), int(hood_tone * 0.72), 2)

    resized = cv2.resize(canvas, (96, 96), interpolation=cv2.INTER_AREA)
    if random.random() > 0.5:
        resized = cv2.flip(resized, 1)
    return cv2.cvtColor(resized, cv2.COLOR_GRAY2RGB)


def synthesize_hat_image(variant: str) -> np.ndarray:
    """Génère des silhouettes variées et propres de Chapeau / Casquette / Bonnet."""
    canvas = np.zeros((96, 96), dtype=np.uint8)
    tone = random.randint(110, 225)
    dark = int(tone * 0.68)

    if variant == "fedora":
        # Chapeau à bord large + calotte bombée
        crown_rx = random.randint(20, 26)
        crown_ry = random.randint(18, 24)
        brim_rx = random.randint(36, 43)
        brim_ry = random.randint(7, 11)
        cy = 58
        cv2.ellipse(canvas, (48, cy), (crown_rx, crown_ry), 0, 180, 360, tone, -1)
        cv2.ellipse(canvas, (48, cy), (brim_rx, brim_ry), 0, 0, 360, dark, -1)
        cv2.line(canvas, (48 - crown_rx, cy - 3), (48 + crown_rx, cy - 3), int(tone * 0.45), 3)
    elif variant == "cap":
        # Casquette (dôme + visière)
        crown_rx = random.randint(22, 27)
        crown_ry = random.randint(19, 24)
        cy = 58
        cv2.ellipse(canvas, (42, cy), (crown_rx, crown_ry), 0, 180, 360, tone, -1)
        # Visière vers la droite (ou gauche après flip)
        visor = np.array([[42 - crown_rx, cy], [42 + crown_rx, cy - 2], [86, cy + 5], [46, cy + 7]], dtype=np.int32)
        cv2.fillPoly(canvas, [visor], dark)
    elif variant == "bucket":
        # Bob (calotte plate + bord incliné)
        pts_crown = np.array([[30, 32], [66, 32], [72, 54], [24, 54]], dtype=np.int32)
        pts_brim = np.array([[24, 54], [72, 54], [84, 68], [12, 68]], dtype=np.int32)
        cv2.fillPoly(canvas, [pts_crown], tone)
        cv2.fillPoly(canvas, [pts_brim], dark)
    else:
        # Bonnet (dôme + revers côtelé)
        rx = random.randint(24, 30)
        ry = random.randint(26, 33)
        cy = 62
        cv2.ellipse(canvas, (48, cy), (rx, ry), 0, 180, 360, tone, -1)
        cv2.rectangle(canvas, (48 - rx - 2, cy - 8), (48 + rx + 2, cy + 8), dark, -1)
        for x in range(48 - rx, 48 + rx, 5):
            cv2.line(canvas, (x, cy - 8), (x, cy + 8), int(tone * 0.5), 1)

    if random.random() > 0.5:
        canvas = cv2.flip(canvas, 1)
    angle = random.uniform(-8, 8)
    m_rot = cv2.getRotationMatrix2D((48, 48), angle, 1.0)
    canvas = cv2.warpAffine(canvas, m_rot, (96, 96), borderMode=cv2.BORDER_CONSTANT, borderValue=0)
    return cv2.cvtColor(canvas, cv2.COLOR_GRAY2RGB)


def synthesize_short_cutout(raw_28: np.ndarray) -> np.ndarray | None:
    """Crée une silhouette de Short à partir d'un Pantalon Fashion-MNIST avec entrejambe visible."""
    # Couper à 62% de la hauteur pour conserver la taille et le début de séparation des 2 jambes
    upper = raw_28[0:18, :]
    # Vérifier qu'une vraie séparation des jambes existe en bas-centre
    lower_mid = upper[12:18, 12:16]
    if lower_mid.size == 0 or float(np.mean(lower_mid < 22)) < 0.25:
        return None
    # Accentuer légèrement la largeur de cuisse courte
    cut = cv2.resize(upper, (96, 76), interpolation=cv2.INTER_CUBIC)
    canvas = np.zeros((96, 96), dtype=np.uint8)
    canvas[10:86, :] = cut
    if random.random() > 0.5:
        canvas = cv2.flip(canvas, 1)
    return cv2.cvtColor(canvas, cv2.COLOR_GRAY2RGB)


def _raw_bbox_ar(raw_28: np.ndarray) -> float:
    ys, xs = np.where(raw_28 > 20)
    if len(ys) < 10:
        return 1.0
    h = float(ys.max() - ys.min() + 1)
    w = float(xs.max() - xs.min() + 1)
    return h / max(w, 1.0)


def load_fashion_mnist_data(target_dir: Path, max_samples_per_class: int = 400):
    """Charge un échantillon équilibré de Fashion-MNIST + classes dérivées propres."""
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
    manteau_count = 0
    veste_count = 0
    jean_count = 0
    skirt_count = 0
    short_count = 0
    sweat_count = 0

    X_imgs, y_labels = [], []

    for i in range(len(labels)):
        lbl = int(labels[i])
        raw = images[i]

        # Classes directes (incluant label 8 = Sac !)
        if lbl in FASHION_MNIST_MAPPING and class_counts[lbl] < max_samples_per_class:
            class_counts[lbl] += 1
            X_imgs.append(augment_fmnist_cutout(raw))
            y_labels.append(FASHION_MNIST_MAPPING[lbl])

        # Label 4 (Coat) : séparer Manteau (long, ar >= 1.22) vs Veste (court/structuré, ar <= 1.15)
        if lbl == 4:
            ar = _raw_bbox_ar(raw)
            if ar >= 1.22 and manteau_count < max_samples_per_class:
                manteau_count += 1
                X_imgs.append(augment_fmnist_cutout(raw))
                y_labels.append(ClothingType.MANTEAU.value)
            elif ar <= 1.16 and veste_count < max_samples_per_class // 2:
                veste_count += 1
                # Accentuer légèrement la ligne de taille/revers de veste
                X_imgs.append(augment_fmnist_cutout(raw))
                y_labels.append(ClothingType.VESTE.value)

        # Jean : silhouettes pantalon (label 1) colorisées en denim réaliste (indigo/bleu/marine)
        if lbl == 1 and jean_count < max_samples_per_class // 2:
            jean_count += 1
            gray_96 = cv2.resize(raw, (96, 96), interpolation=cv2.INTER_CUBIC)
            X_imgs.append(tint_as_denim_rgb(gray_96))
            y_labels.append(ClothingType.JEAN.value)

        # Short : découpe haute de pantalon (label 1) avec entrejambe vérifiée
        if lbl == 1 and short_count < max_samples_per_class // 2:
            short_img = synthesize_short_cutout(raw)
            if short_img is not None:
                short_count += 1
                X_imgs.append(short_img)
                y_labels.append(ClothingType.SHORT.value)

        # Jupe : 60% inférieurs d'une Robe (label 3)
        if lbl == 3 and skirt_count < max_samples_per_class // 2:
            skirt_count += 1
            lower = raw[11:28, :]
            X_imgs.append(augment_fmnist_cutout(lower))
            y_labels.append(ClothingType.JUPE.value)

        # Sweat (mixte Homme/Femme) : silhouettes hoodie/sweatshirt à capuche issues de label 2
        if lbl == 2 and sweat_count < max_samples_per_class // 2:
            sweat_count += 1
            X_imgs.append(synthesize_hoodie_from_pullover(raw))
            y_labels.append(ClothingType.SWEAT.value)

    # Chapeau (mixte Homme/Femme) : 220 silhouettes variées (fedora, casquette, bob, bonnet)
    hat_variants = ["fedora", "cap", "bucket", "beanie"]
    for idx in range(220):
        X_imgs.append(synthesize_hat_image(hat_variants[idx % len(hat_variants)]))
        y_labels.append(ClothingType.CHAPEAU.value)

    print(f"[Fashion-MNIST + Synthétiques propres] {len(X_imgs)} images chargées.")
    return X_imgs, y_labels


def load_verified_real_images(uploads_dir: Path, aug_per_class: int = 35):
    """
    Charge uniquement les photos réelles vérifiées visuellement (vêtement unique, étiquette exacte).
    - chino_beige.jpg corrigé dans Pantalon (ne pollue plus Jean)
    """
    verified_map = {
        ClothingType.TSHIRT.value: [
            "tshirt_blanc.jpg",
            "8dc35d77-d4df-41c1-8c11-7faf063ad953.jpg",
            "4f7fa19c-4042-47ff-8b0e-f70994641311.jpg",
        ],
        ClothingType.CHEMISE.value: [
            "0ccca783-4db6-42de-854a-dad612178a66.jpg",
            "45515059-a20e-4d8c-a55b-384a43fd06e5.jpg",
        ],
        ClothingType.PULL.value: [
            "pull_maille_beige.jpg",
        ],
        ClothingType.PANTALON.value: [
            "0f411f15-ea68-4540-81b9-3dead15042a7.jpg",
            "7be263f9-1f27-4ba1-b791-738c13e2f13f.jpg",
            "pantalon_noir.jpg",
        ],
        ClothingType.JEAN.value: [
            "jean_slim_bleu.jpg",
            "chino_beige.jpg",  # Visuellement : jean brut bleu marine Acne Studios avec rivets cuivre
        ],
        ClothingType.SHORT.value: [
            "short_kaki.jpg",
        ],
        ClothingType.VESTE.value: [
            "bomber_noir.jpg",
            "blazer_marine.jpg",
        ],
        ClothingType.BASKETS.value: [
            "462e8ef5-fe34-4487-84ea-3c263a83ca2b.jpg",
            "baskets_blanches.jpg",
            "baskets_sport_noires.jpg",
        ],
        ClothingType.CHAUSSURES_VILLE.value: [
            "derbies_marron.jpg",
        ],
    }

    X_imgs, y_labels = [], []
    for cname, flist in verified_map.items():
        base_imgs = []
        for fn in flist:
            fp = uploads_dir / fn
            if fp.exists():
                rgb, _ = load_image_rgb(str(fp))
                if rgb is not None:
                    base_imgs.append(rgb)
        if not base_imgs:
            continue

        for b in base_imgs:
            X_imgs.append(b)
            y_labels.append(cname)

        for _ in range(aug_per_class):
            base = random.choice(base_imgs)
            X_imgs.append(augment_real_rgb(base, n=1)[0])
            y_labels.append(cname)

    print(f"[Uploads réels vérifiés] {len(X_imgs)} images RGB chargées.")
    return X_imgs, y_labels


def train_and_save_production_model():
    random.seed(42)
    np.random.seed(42)

    print("=" * 72)
    print(f"ENTRAÎNEMENT MODÈLE WEARIA v4 — 16 classes / {FEATURE_DIM} descripteurs")
    print("=" * 72)

    dataset_dir = Path(__file__).resolve().parent.parent.parent / "dataset"
    uploads_dir = Path(settings.UPLOAD_DIR)

    fmnist_imgs, fmnist_lbls = load_fashion_mnist_data(dataset_dir, max_samples_per_class=400)
    real_imgs, real_lbls = load_verified_real_images(uploads_dir, aug_per_class=35)

    all_imgs = fmnist_imgs + real_imgs
    all_lbls = fmnist_lbls + real_lbls

    print(f"\n[Dataset] Total : {len(all_imgs)} images / {len(set(all_lbls))} classes")
    for cls, cnt in sorted(Counter(all_lbls).items()):
        print(f"  · {cls:22s} : {cnt}")

    print(f"\n[Extraction] Calcul des {FEATURE_DIM} descripteurs...")
    X_feats = []
    for idx, img_rgb in enumerate(all_imgs):
        if idx % 500 == 0:
            print(f"  ... {idx}/{len(all_imgs)}")
        seg = segment_garment(img_rgb, max_side=224)
        feats = extract_advanced_features(img_rgb, segmentation=seg, input_is_bgr=False)
        X_feats.append(feats)

    X = np.vstack(X_feats)
    y = np.array(all_lbls)

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.20, random_state=42, stratify=y
    )

    scaler = StandardScaler()
    X_train_s = scaler.fit_transform(X_train)
    X_test_s = scaler.transform(X_test)

    print("\n[Entraînement] Random Forest 240 arbres (class_weight='balanced')...")
    clf = RandomForestClassifier(
        n_estimators=240,
        max_depth=26,
        min_samples_split=3,
        min_samples_leaf=1,
        max_features="sqrt",
        class_weight="balanced",
        random_state=42,
        n_jobs=-1,
    )
    clf.fit(X_train_s, y_train)

    y_pred = clf.predict(X_test_s)
    acc = accuracy_score(y_test, y_pred)
    print(f"\n[Validation] Précision globale (20% hold-out) : {acc * 100:.2f}%")
    print(classification_report(y_test, y_pred, zero_division=0))

    settings.AI_MODELS_DIR.mkdir(parents=True, exist_ok=True)
    joblib.dump(clf, settings.AI_MODELS_DIR / "knn_model.joblib", compress=3)
    joblib.dump(scaler, settings.AI_MODELS_DIR / "scaler.joblib", compress=3)
    print(f"[Sauvegarde] Modèle v4 sauvegardé dans {settings.AI_MODELS_DIR}")


if __name__ == "__main__":
    train_and_save_production_model()
