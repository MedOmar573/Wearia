import cv2
import numpy as np
from typing import Dict

# Référentiel des couleurs standard Wearia conformes à la base de données PostgreSQL
STANDARD_COLORS = {
    "Noir":        "#000000",
    "Blanc":       "#FFFFFF",
    "Gris":        "#808080",
    "Bleu":        "#0050B4",
    "Bleu Marine": "#0A1946",
    "Rouge":       "#DC143C",
    "Vert":        "#228B22",
    "Beige":       "#F5F5DC",
    "Marron":      "#8B4513",
    "Jaune":       "#FFD700",
    "Rose":        "#FFB6C1",
    "Orange":      "#FF8C00",
    "Violet":      "#6C47FF",
    "Corail":      "#FF6B6B",
}

# Palette de référence en HSV pour chaque couleur nommée
# Format : (h_min, h_max, s_min, s_max, v_min, v_max, name)
# H en [0,180] OpenCV, S/V en [0,255]
_HSV_RANGES = [
    # Rouge (deux zones : bas et haut du spectre H)
    (0,   8,   80, 255,  60, 255, "Rouge"),
    (172, 180, 80, 255,  60, 255, "Rouge"),
    # Corail / orange vif
    (8,   15,  120, 255, 140, 255, "Corail"),
    # Orange
    (10,  22,  80, 255,  80, 255, "Orange"),
    # Jaune
    (22,  35,  80, 255, 120, 255, "Jaune"),
    # Vert
    (35,  85,  60, 255,  40, 255, "Vert"),
    # Bleu franc
    (100, 125, 60, 255,  60, 255, "Bleu"),
    # Bleu Marine (bleu sombre)
    (100, 125, 60, 255,  20,  90, "Bleu Marine"),
    # Violet
    (125, 155, 50, 255,  40, 255, "Violet"),
    # Rose
    (155, 172, 50, 255, 120, 255, "Rose"),
    # Rose clair / Pink
    (155, 172, 20,  80, 170, 255, "Rose"),
]

def _rgb_to_hsv_pixel(r: float, g: float, b: float):
    """Convertit un pixel RGB [0-255] en HSV (H en [0,180], S/V en [0,255])."""
    pixel = np.array([[[b, g, r]]], dtype=np.uint8)
    hsv = cv2.cvtColor(pixel, cv2.COLOR_BGR2HSV)
    return int(hsv[0, 0, 0]), int(hsv[0, 0, 1]), int(hsv[0, 0, 2])


def classify_rgb(r: float, g: float, b: float) -> tuple[str, str]:
    """
    Classifie un pixel RGB selon les couleurs Wearia.
    Utilise l'espace HSV (robuste aux variations d'éclairage)
    + règles achromatiques (Noir / Blanc / Gris) sur luminance et saturation.
    """
    h, s, v = _rgb_to_hsv_pixel(r, g, b)

    # 1. Achromatique : faible saturation → Noir / Blanc / Gris
    if s < 40:
        if v <= 60:
            return "Noir", STANDARD_COLORS["Noir"]
        elif v >= 200:
            return "Blanc", STANDARD_COLORS["Blanc"]
        elif v >= 100:
            return "Gris", STANDARD_COLORS["Gris"]
        else:
            return "Noir", STANDARD_COLORS["Noir"]

    # 2. Sombre mais chromatique → potentiellement Bleu Marine ou Marron sombre
    if v < 70:
        if 100 <= h <= 130 and s >= 50:
            return "Bleu Marine", STANDARD_COLORS["Bleu Marine"]
        if r > b + 15 and r > g + 10:
            return "Marron", STANDARD_COLORS["Marron"]
        return "Noir", STANDARD_COLORS["Noir"]

    # 3. Beige / Marron clair : faible-moyenne saturation, tonalité chaude
    if s < 120:
        L = 0.299 * r + 0.587 * g + 0.114 * b
        if r >= b + 10 and r >= g - 25 and L >= 110:
            if 10 <= h <= 30:
                if L >= 160:
                    return "Beige", STANDARD_COLORS["Beige"]
                return "Marron", STANDARD_COLORS["Marron"]
        if s < 50:
            if L >= 200:
                return "Blanc", STANDARD_COLORS["Blanc"]
            if L >= 120:
                return "Beige", STANDARD_COLORS["Beige"]

    # 4. Marron saturé / Beige chaud
    if 8 <= h <= 25 and s >= 40 and v < 160 and v >= 60:
        if v >= 120 and s < 100:
            return "Beige", STANDARD_COLORS["Beige"]
        return "Marron", STANDARD_COLORS["Marron"]
    if 8 <= h <= 22 and s >= 60 and v < 160:
        return "Marron", STANDARD_COLORS["Marron"]

    # 5. Plage HSV pour chaque couleur chromatique
    for (h_min, h_max, s_min, s_max, v_min, v_max, name) in _HSV_RANGES:
        if h_min <= h <= h_max and s_min <= s <= s_max and v_min <= v <= v_max:
            return name, STANDARD_COLORS[name]

    # 6. Repli luminance
    L = 0.299 * r + 0.587 * g + 0.114 * b
    if L <= 70:
        return "Noir", STANDARD_COLORS["Noir"]
    if L >= 210:
        return "Blanc", STANDARD_COLORS["Blanc"]
    return "Gris", STANDARD_COLORS["Gris"]


def detect_dominant_color(image_path: str) -> Dict[str, str]:
    """
    Détecte la couleur dominante du vêtement avec une pipeline robuste :
    1. Suppression adaptative du fond (bordures + GrabCut léger)
    2. Conversion en HSV pour résistance aux variations d'éclairage
    3. K-Means k=4 pour capturer toutes les nuances du tissu
    4. Sélection du cluster tissu dominant (ni fond, ni ombre, ni reflet)
    5. Classification via l'espace HSV + règles achromatiques
    """
    try:
        img = cv2.imread(image_path)
        if img is None:
            return {"name": "Noir", "hex": STANDARD_COLORS["Noir"]}

        # Redimensionnement pour efficacité
        small = cv2.resize(img, (224, 224), interpolation=cv2.INTER_AREA)
        h, w = small.shape[:2]

        # ── ÉTAPE 1 : Estimation couleur de fond via les bordures ──────────────
        border_px = 14
        borders = np.concatenate([
            small[:border_px, :].reshape(-1, 3),
            small[-border_px:, :].reshape(-1, 3),
            small[:, :border_px].reshape(-1, 3),
            small[:, -border_px:].reshape(-1, 3),
        ])
        bg_med = np.median(borders, axis=0)        # couleur médiane du fond
        bg_std = np.std(borders, axis=0) + 12.0    # tolérance

        # Masque : pixels suffisamment éloignés du fond
        diff = np.linalg.norm(
            (small.astype(np.float32) - bg_med) / bg_std, axis=2
        )
        garment_mask = diff > 1.5

        # ── ÉTAPE 2 : GrabCut rapide pour affiner le masque ───────────────────
        try:
            fg_model = np.zeros((1, 65), dtype=np.float64)
            bg_model = np.zeros((1, 65), dtype=np.float64)
            rect = (border_px, border_px, w - 2 * border_px, h - 2 * border_px)
            gc_mask = np.zeros((h, w), dtype=np.uint8)
            cv2.grabCut(small, gc_mask, rect, bg_model, fg_model, 3, cv2.GC_INIT_WITH_RECT)
            gc_fg = np.where((gc_mask == cv2.GC_FGD) | (gc_mask == cv2.GC_PR_FGD), True, False)
            # Combiner avec le masque fond : prendre l'union
            combined_mask = garment_mask | gc_fg
            if np.sum(combined_mask) >= 500:
                garment_mask = combined_mask
        except Exception:
            pass  # GrabCut facultatif

        # ── ÉTAPE 3 : Extraction des pixels du vêtement ───────────────────────
        if np.sum(garment_mask) >= 500:
            garment_pixels = small[garment_mask]
        else:
            # Repli : carré central 40%–60%
            m = int(0.2 * h), int(0.8 * h), int(0.2 * w), int(0.8 * w)
            garment_pixels = small[m[0]:m[1], m[2]:m[3]].reshape(-1, 3)

        # ── ÉTAPE 4 : K-Means k=4 en BGR ──────────────────────────────────────
        k = min(4, len(garment_pixels) // 50)
        k = max(k, 2)
        criteria = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 20, 0.5)
        _, labels, centers = cv2.kmeans(
            garment_pixels.astype(np.float32), k, None,
            criteria, 10, cv2.KMEANS_PP_CENTERS
        )
        counts = np.bincount(labels.flatten())

        # ── ÉTAPE 5 : Sélection du cluster tissu ──────────────────────────────
        # Convertir chaque centroïde BGR→HSV pour comparer avec le fond
        clusters = []
        for cnt, c in zip(counts, centers):
            b_v, g_v, r_v = float(c[0]), float(c[1]), float(c[2])
            L = 0.299 * r_v + 0.587 * g_v + 0.114 * b_v
            # Distance du centroïde au fond (en BGR)
            dist_to_bg = float(np.linalg.norm(c - bg_med))
            clusters.append({
                "cnt": int(cnt), "b": b_v, "g": g_v, "r": r_v,
                "L": L, "dist_bg": dist_to_bg,
                "ratio": int(cnt) / len(garment_pixels)
            })

        # Trier par fréquence décroissante
        clusters.sort(key=lambda x: x["cnt"], reverse=True)

        # Rejeter les clusters trop similaires au fond (reflet / table)
        filtered = [c for c in clusters if c["dist_bg"] > 25.0]
        if not filtered:
            filtered = clusters  # repli si tout ressemble au fond

        # Priorité aux clusters sombres (vêtements noirs souvent sous-représentés)
        chosen = filtered[0]
        for c in filtered:
            if c["L"] <= 75 and c["ratio"] >= 0.15:
                chosen = c
                break

        r_f, g_f, b_f = chosen["r"], chosen["g"], chosen["b"]
        color_name, hex_code = classify_rgb(r_f, g_f, b_f)
        return {"name": color_name, "hex": hex_code}

    except Exception:
        return {"name": "Noir", "hex": STANDARD_COLORS["Noir"]}
