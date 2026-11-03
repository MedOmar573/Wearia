import cv2
import numpy as np
from typing import Dict

# Référentiel des couleurs standard Wearia conformes à la base de données PostgreSQL
STANDARD_COLORS = {
    "Noir": "#000000",
    "Blanc": "#FFFFFF",
    "Gris": "#808080",
    "Bleu": "#0050B4",
    "Bleu Marine": "#0A1946",
    "Rouge": "#DC143C",
    "Vert": "#228B22",
    "Beige": "#F5F5DC",
    "Marron": "#8B4513",
    "Jaune": "#FFD700",
    "Rose": "#FFB6C1"
}

def classify_rgb(r: float, g: float, b: float) -> tuple[str, str]:
    """
    Classifie les composantes RGB d'un tissu selon la perception visuelle humaine :
    - Évite la fausse détection de 'Bleu Marine' pour les vêtements noirs capturés par caméra smartphone
    - Distingue précisément le Noir, le Bleu Marine, le Gris, le Blanc, le Beige, etc.
    """
    L = 0.299 * r + 0.587 * g + 0.114 * b
    max_diff = max(abs(r - g), abs(r - b), abs(g - b))

    # 1. Tissu sombre à très faible chromaticité -> NOIR absolu (tissu noir en intérieur)
    if L <= 80 and max_diff <= 22:
        return "Noir", STANDARD_COLORS["Noir"]

    # 2. Bleu Marine : exige une dominante bleue très marquée (B >> R et B >> G)
    if (b >= r + 24) and (b >= g + 14):
        if L <= 95:
            return "Bleu Marine", STANDARD_COLORS["Bleu Marine"]
        return "Bleu", STANDARD_COLORS["Bleu"]

    # 3. Tissu très clair à faible chromaticité -> BLANC
    if L >= 195 and max_diff <= 24:
        return "Blanc", STANDARD_COLORS["Blanc"]

    # 4. Couleurs neutres achromatiques (Gris, Noir, Blanc)
    if max_diff <= 22:
        if L <= 80:
            return "Noir", STANDARD_COLORS["Noir"]
        elif L >= 195:
            return "Blanc", STANDARD_COLORS["Blanc"]
        else:
            return "Gris", STANDARD_COLORS["Gris"]

    # 5. Bleu franc
    if b > r + 20 and b > g + 8:
        return "Bleu", STANDARD_COLORS["Bleu"]

    # 6. Vert
    if (g > r + 15) and (g > b + 15):
        return "Vert", STANDARD_COLORS["Vert"]

    # 7. Beige (couleur chaude, douce, terre claire)
    if L >= 135 and r >= 130 and g >= 120 and b >= 90 and r >= b and abs(r - g) <= 30:
        return "Beige", STANDARD_COLORS["Beige"]

    # 8. Marron (chaud, sombre, teinté)
    if (r > b + 20) and (r >= g) and L < 130:
        return "Marron", STANDARD_COLORS["Marron"]

    # 9. Jaune
    if r > 175 and g > 155 and b < 125:
        return "Jaune", STANDARD_COLORS["Jaune"]

    # 10. Rose vs Rouge
    if r > g + 25 and r > b + 25:
        if L >= 165:
            return "Rose", STANDARD_COLORS["Rose"]
        return "Rouge", STANDARD_COLORS["Rouge"]

    # Repli final basé sur la luminance
    if L <= 80:
        return "Noir", STANDARD_COLORS["Noir"]
    elif L >= 190:
        return "Blanc", STANDARD_COLORS["Blanc"]
    return "Gris", STANDARD_COLORS["Gris"]

def detect_dominant_color(image_path: str) -> Dict[str, str]:
    """
    Détecte avec précision la couleur dominante du vêtement avec OpenCV :
    1. Estime la couleur d'arrière-plan (fond de table, lit, sol, mur) depuis les bordures
    2. Isole le masque précis du vêtement
    3. Segmente le tissu et extrait les composantes RGB réelles
    4. Applique la classification textile perceptuelle
    """
    try:
        img = cv2.imread(image_path)
        if img is None:
            return {"name": "Noir", "hex": STANDARD_COLORS["Noir"]}

        # Redimensionnement rapide pour analyse haute performance
        small = cv2.resize(img, (200, 200), interpolation=cv2.INTER_AREA)

        # 1. Estimation de l'arrière-plan sur les bordures extérieures (12px)
        borders = np.concatenate([
            small[:12, :].reshape(-1, 3),
            small[-12:, :].reshape(-1, 3),
            small[:, :12].reshape(-1, 3),
            small[:, -12:].reshape(-1, 3)
        ])
        bg_med = np.median(borders, axis=0)
        bg_std = np.std(borders, axis=0) + 10.0

        # Distance euclidienne pondérée de chaque pixel par rapport à l'arrière-plan
        diff = np.linalg.norm((small.astype(np.float32) - bg_med) / bg_std, axis=2)
        garment_mask = diff > 1.8

        # Si le masque détecte au moins 400 pixels (~1% de l'image), on utilise les pixels du vêtement
        if np.sum(garment_mask) >= 400:
            garment_pixels = small[garment_mask]
        else:
            # Repli sur le cadran central (35% à 65%)
            garment_pixels = small[35:165, 35:165].reshape(-1, 3)

        # 2. K-Means clustering (k=2) pour isoler le tissu principal des ombres/reflets
        criteria = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 10, 1.0)
        _, labels, centers = cv2.kmeans(garment_pixels.astype(np.float32), 2, None, criteria, 10, cv2.KMEANS_RANDOM_CENTERS)
        counts = np.bincount(labels.flatten())

        clusters_info = []
        for cnt, c in zip(counts, centers):
            b, g, r = float(c[0]), float(c[1]), float(c[2])
            L = 0.299 * r + 0.587 * g + 0.114 * b
            clusters_info.append({"cnt": cnt, "b": b, "g": g, "r": r, "L": L})

        # Trier par fréquence
        clusters_info.sort(key=lambda x: x["cnt"], reverse=True)

        # Priorité au tissu sombre si un cluster sombre significatif existe
        chosen = clusters_info[0]
        for c in clusters_info:
            if c["L"] <= 80 and (c["cnt"] / len(garment_pixels)) >= 0.20:
                chosen = c
                break

        r, g, b = chosen["r"], chosen["g"], chosen["b"]
        color_name, hex_code = classify_rgb(r, g, b)
        return {"name": color_name, "hex": hex_code}

    except Exception as e:
        return {"name": "Noir", "hex": STANDARD_COLORS["Noir"]}

