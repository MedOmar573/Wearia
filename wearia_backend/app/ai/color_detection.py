"""
Extraction robuste de la couleur dominante d'un vêtement :
- Utilise le prétraitement unifié (orientation EXIF, RGB cohérent, segmentation du vêtement)
- Échantillonnage prioritaire du cœur du vêtement (masque érodé, sans fond ni franges)
- Suppression des reflets extrêmes et ombres de plis mineures (sans écraser les vrais vêtements noirs)
- Clustering K-Means dans l'espace perceptuel CIELAB
- Classification complète LAB + HSV sans trou de teinte, alignée sur le référentiel Wearia
"""

import logging
from typing import Any, Dict, Optional, Tuple, Union
from pathlib import Path

import cv2
import numpy as np

from app.ai.preprocessing import GarmentSegmentation, load_image_rgb, segment_garment
from app.ai.taxonomy import ClothingColor, STANDARD_COLORS, normalize_clothing_color

logger = logging.getLogger(__name__)


def _rgb_to_hsv_lab(r: float, g: float, b: float) -> Tuple[Tuple[int, int, int], Tuple[float, float, float]]:
    """Convertit un pixel RGB [0-255] vers HSV (H:0-179, S/V:0-255) et CIELAB (L/a/b:0-255)."""
    rgb_px = np.array([[[int(round(r)), int(round(g)), int(round(b))]]], dtype=np.uint8)
    hsv_px = cv2.cvtColor(rgb_px, cv2.COLOR_RGB2HSV)[0, 0]
    lab_px = cv2.cvtColor(rgb_px, cv2.COLOR_RGB2LAB)[0, 0]
    return (
        (int(hsv_px[0]), int(hsv_px[1]), int(hsv_px[2])),
        (float(lab_px[0]), float(lab_px[1]), float(lab_px[2])),
    )


def _hex_to_lab(hex_code: str) -> np.ndarray:
    hx = hex_code.lstrip("#")
    r, g, b = int(hx[0:2], 16), int(hx[2:4], 16), int(hx[4:6], 16)
    _, lab = _rgb_to_hsv_lab(r, g, b)
    return np.array(lab, dtype=np.float32)


# Prototypes LAB précalculés pour le repli perceptuel Delta-E
_PROTOTYPE_LABS: Dict[str, np.ndarray] = {
    name: _hex_to_lab(hx) for name, hx in STANDARD_COLORS.items()
}


def classify_rgb(r: float, g: float, b: float) -> Tuple[str, str]:
    """
    Classifie une couleur RGB [0-255] vers l'une des couleurs standard Wearia.
    Combine chroma/luminance CIELAB (robuste aux tons sombres et neutres)
    et teinte HSV (couverture complète [0, 179] sans angle mort).
    """
    (h, s, v), (l_lab, a_lab, b_lab) = _rgb_to_hsv_lab(r, g, b)
    da = a_lab - 128.0
    db = b_lab - 128.0
    chroma = float(np.hypot(da, db))

    # ── 1. Couleurs achromatiques pures (Noir / Gris / Blanc) ─────────────────
    # En CIELAB, chroma < 6.5 indique un gris/noir/blanc quasi neutre.
    if chroma < 6.5 and s < 32:
        if l_lab <= 70.0 or v <= 65:
            return ClothingColor.NOIR.value, STANDARD_COLORS[ClothingColor.NOIR.value]
        if l_lab >= 208.0 or v >= 205:
            return ClothingColor.BLANC.value, STANDARD_COLORS[ClothingColor.BLANC.value]
        return ClothingColor.GRIS.value, STANDARD_COLORS[ClothingColor.GRIS.value]

    # Très sombre : distinguer Noir vs Bleu Marine vs Vert forêt vs Marron Foncé
    if l_lab < 78.0 and v < 82:
        # Bleu Marine (tonalité froide bleue détectable même sombre)
        if (92 <= h <= 135) and (db <= -4.5 or (chroma >= 6.0 and s >= 38)):
            return ClothingColor.BLEU_MARINE.value, STANDARD_COLORS[ClothingColor.BLEU_MARINE.value]
        # Vert foncé / sapin (a_lab < 124)
        if (35 <= h <= 92) and da <= -5.0 and chroma >= 6.5:
            return ClothingColor.VERT.value, STANDARD_COLORS[ClothingColor.VERT.value]
        # Rouge bordeaux sombre
        if (h <= 6 or h >= 168) and da >= 12.0 and s >= 65:
            return ClothingColor.ROUGE.value, STANDARD_COLORS[ClothingColor.ROUGE.value]
        # Marron foncé (tonalité chaude sombre)
        if (4 <= h <= 28) and da >= 4.0 and db >= 5.0 and chroma >= 7.5 and l_lab >= 38.0:
            return ClothingColor.MARRON_FONCE.value, STANDARD_COLORS[ClothingColor.MARRON_FONCE.value]
        return ClothingColor.NOIR.value, STANDARD_COLORS[ClothingColor.NOIR.value]

    # Très clair et très peu saturé : Blanc vs Beige/Sable vs Bleu clair vs Rose pâle
    if l_lab >= 210.0 and chroma < 11.5:
        if (85 <= h <= 130) and db <= -4.5 and chroma >= 6.5:
            return ClothingColor.BLEU.value, STANDARD_COLORS[ClothingColor.BLEU.value]
        if (150 <= h <= 179 or h <= 8) and da >= 6.0:
            return ClothingColor.ROSE.value, STANDARD_COLORS[ClothingColor.ROSE.value]
        if (12 <= h <= 34) and db >= 7.0:
            return ClothingColor.BEIGE.value, STANDARD_COLORS[ClothingColor.BEIGE.value]
        return ClothingColor.BLANC.value, STANDARD_COLORS[ClothingColor.BLANC.value]

    # Neutre moyen peu chromatique (Gris vs Beige doux vs Bleu délavé)
    if chroma < 9.5 and s < 42:
        if (88 <= h <= 130) and db <= -5.5:
            if l_lab < 115.0:
                return ClothingColor.BLEU_MARINE.value, STANDARD_COLORS[ClothingColor.BLEU_MARINE.value]
            return ClothingColor.BLEU.value, STANDARD_COLORS[ClothingColor.BLEU.value]
        if (12 <= h <= 34) and db >= 6.0 and l_lab >= 135.0:
            return ClothingColor.BEIGE.value, STANDARD_COLORS[ClothingColor.BEIGE.value]
        if l_lab >= 200.0:
            return ClothingColor.BLANC.value, STANDARD_COLORS[ClothingColor.BLANC.value]
        if l_lab <= 78.0:
            return ClothingColor.NOIR.value, STANDARD_COLORS[ClothingColor.NOIR.value]
        return ClothingColor.GRIS.value, STANDARD_COLORS[ClothingColor.GRIS.value]

    # ── 2. Classification chromatique complète sur tout le cercle HSV [0..179] ─

    # A. Rouge / Rose poudré / Corail / Marron (H: 0-12 et 170-179)
    if h <= 12 or h >= 170:
        # Teinte chaude sombre/moyenne tirant vers le brun (H 5-12, luminance modérée)
        if 5 <= h <= 12 and l_lab < 130.0 and v < 155:
            if l_lab < 85.0:
                return ClothingColor.MARRON_FONCE.value, STANDARD_COLORS[ClothingColor.MARRON_FONCE.value]
            return ClothingColor.MARRON.value, STANDARD_COLORS[ClothingColor.MARRON.value]
        # Rose / Saumon clair (haute luminosité, saturation faible à moyenne)
        if l_lab >= 150.0 and s < 125:
            return ClothingColor.ROSE.value, STANDARD_COLORS[ClothingColor.ROSE.value]
        # Corail (rouge-orangé lumineux et saturé)
        if 5 <= h <= 12 and l_lab >= 135.0 and s >= 125:
            return ClothingColor.CORAIL.value, STANDARD_COLORS[ClothingColor.CORAIL.value]
        return ClothingColor.ROUGE.value, STANDARD_COLORS[ClothingColor.ROUGE.value]

    # B. Orange / Marron / Beige / Sable (H: 13-26)
    if 13 <= h <= 26:
        # Beige / Sable : clair ou modérément ombré mais faiblement saturé (sans dominante rouge-brun)
        if (l_lab >= 145.0 and s < 115) or (l_lab >= 105.0 and s < 72 and a_lab <= 134.0):
            if l_lab >= 195.0 and s < 55:
                return ClothingColor.SABLE.value, STANDARD_COLORS[ClothingColor.SABLE.value]
            return ClothingColor.BEIGE.value, STANDARD_COLORS[ClothingColor.BEIGE.value]
        # Marron / Marron Foncé : luminance basse à moyenne
        if l_lab < 140.0 or v < 165:
            if l_lab < 85.0:
                return ClothingColor.MARRON_FONCE.value, STANDARD_COLORS[ClothingColor.MARRON_FONCE.value]
            return ClothingColor.MARRON.value, STANDARD_COLORS[ClothingColor.MARRON.value]
        # Orange vif
        return ClothingColor.ORANGE.value, STANDARD_COLORS[ClothingColor.ORANGE.value]

    # C. Jaune / Jaune Clair / Beige chaud / Kaki (H: 27-37)
    if 27 <= h <= 37:
        if s < 80:
            if l_lab >= 150.0:
                return ClothingColor.BEIGE.value, STANDARD_COLORS[ClothingColor.BEIGE.value]
            return ClothingColor.VERT.value, STANDARD_COLORS[ClothingColor.VERT.value]  # kaki / olive
        if l_lab < 120.0:
            return ClothingColor.VERT.value, STANDARD_COLORS[ClothingColor.VERT.value]  # olive foncé
        if l_lab >= 205.0 and s < 155:
            return ClothingColor.JAUNE_CLAIR.value, STANDARD_COLORS[ClothingColor.JAUNE_CLAIR.value]
        return ClothingColor.JAUNE.value, STANDARD_COLORS[ClothingColor.JAUNE.value]

    # D. Vert (y compris kaki, menthe, émeraude, vert sapin) (H: 38-86)
    if 38 <= h <= 86:
        return ClothingColor.VERT.value, STANDARD_COLORS[ClothingColor.VERT.value]

    # E. Cyan / Bleu Ciel / Denim / Bleu / Bleu Marine (H: 87-130)
    if 87 <= h <= 130:
        # Bleu Marine : bleu sombre (L* < 105 ou V < 105)
        if l_lab < 102.0 or v < 105:
            return ClothingColor.BLEU_MARINE.value, STANDARD_COLORS[ClothingColor.BLEU_MARINE.value]
        return ClothingColor.BLEU.value, STANDARD_COLORS[ClothingColor.BLEU.value]

    # F. Violet / Mauve (H: 131-154)
    if 131 <= h <= 154:
        if h <= 136 and l_lab < 85.0:
            return ClothingColor.BLEU_MARINE.value, STANDARD_COLORS[ClothingColor.BLEU_MARINE.value]
        return ClothingColor.VIOLET.value, STANDARD_COLORS[ClothingColor.VIOLET.value]

    # G. Rose / Magenta (H: 155-169)
    if 155 <= h <= 169:
        if l_lab < 105.0 and s >= 100:
            return ClothingColor.VIOLET.value, STANDARD_COLORS[ClothingColor.VIOLET.value]
        return ClothingColor.ROSE.value, STANDARD_COLORS[ClothingColor.ROSE.value]

    # ── 3. Repli perceptuel CIELAB Delta-E (ne laisse aucun pixel sans classe) ─
    px_lab = np.array([l_lab, a_lab, b_lab], dtype=np.float32)
    best_name = min(
        _PROTOTYPE_LABS.keys(),
        key=lambda n: float(np.linalg.norm(px_lab - _PROTOTYPE_LABS[n])),
    )
    return best_name, STANDARD_COLORS[best_name]


def _select_garment_color_pixels(seg: GarmentSegmentation) -> Tuple[np.ndarray, np.ndarray]:
    """
    Extrait les pixels représentatifs du tissu (en RGB et LAB) depuis le masque interne du vêtement,
    en privilégiant le cœur du vêtement et en excluant les reflets extrêmes / ombres de plis parasites.
    """
    rgb = seg.img_rgb
    h, w = rgb.shape[:2]
    x1, y1, x2, y2 = seg.bbox
    bw, bh = max(1, x2 - x1), max(1, y2 - y1)

    # Sous-zone centrale du vêtement (10% à 90% de sa bbox) pour éviter étiquettes de col et bords
    core_mask = np.zeros((h, w), dtype=bool)
    cy1, cy2 = y1 + int(bh * 0.10), y2 - int(bh * 0.10)
    cx1, cx2 = x1 + int(bw * 0.10), x2 - int(bw * 0.10)
    if cy2 > cy1 and cx2 > cx1:
        core_mask[cy1:cy2, cx1:cx2] = True

    sample_mask = seg.inner_mask & core_mask
    if np.sum(sample_mask) < 120:
        sample_mask = seg.inner_mask
    if np.sum(sample_mask) < 80:
        sample_mask = seg.mask

    pixels_rgb = rgb[sample_mask]
    pixels_lab = cv2.cvtColor(pixels_rgb.reshape(-1, 1, 3), cv2.COLOR_RGB2LAB).reshape(-1, 3).astype(np.float32)

    # Filtrage intelligent des ombres de plis (UNIQUEMENT si le vêtement n'est pas lui-même sombre)
    l_vals = pixels_lab[:, 0]
    if len(pixels_lab) >= 200 and float(np.mean(l_vals > 85.0)) > 0.55:
        keep = l_vals >= np.percentile(l_vals, 8)
        if np.sum(keep) >= 120:
            pixels_rgb = pixels_rgb[keep]
            pixels_lab = pixels_lab[keep]

    # Filtrage des reflets spéculaires purs (UNIQUEMENT si le vêtement n'est pas majoritairement blanc)
    l_vals = pixels_lab[:, 0]
    chroma_vals = np.hypot(pixels_lab[:, 1] - 128.0, pixels_lab[:, 2] - 128.0)
    is_glare = (l_vals > 246.0) & (chroma_vals < 5.0)
    if len(pixels_lab) >= 200 and float(np.mean(is_glare)) < 0.35:
        keep = ~is_glare
        if np.sum(keep) >= 120:
            pixels_rgb = pixels_rgb[keep]
            pixels_lab = pixels_lab[keep]

    return pixels_rgb, pixels_lab


def detect_dominant_color(
    image_path: Union[str, Path, np.ndarray],
    segmentation: Optional[GarmentSegmentation] = None,
) -> Dict[str, Any]:
    """
    Détecte la couleur dominante du vêtement avec diagnostic complet :
    1. Chargement RGB + EXIF et segmentation du vêtement (réutilise `segmentation` si fourni)
    2. Échantillonnage interne érodé (évite le fond, les contours et les étiquettes)
    3. K-Means en espace perceptuel CIELAB (k=3..4)
    4. Sélection du cluster tissu dominant (sans biais destructif vers le noir)
    5. Classification LAB+HSV sans angle mort -> nom canonique + code hex Wearia
    """
    try:
        if segmentation is None:
            img_rgb, _ = load_image_rgb(image_path)
            if img_rgb is None:
                return {"name": ClothingColor.NOIR.value, "hex": STANDARD_COLORS[ClothingColor.NOIR.value]}
            segmentation = segment_garment(img_rgb, max_side=224)

        pixels_rgb, pixels_lab = _select_garment_color_pixels(segmentation)
        n_px = len(pixels_lab)
        if n_px == 0:
            return {"name": ClothingColor.NOIR.value, "hex": STANDARD_COLORS[ClothingColor.NOIR.value]}

        # Sous-échantillonnage déterministe si très grand nombre de pixels (accélère K-Means)
        if n_px > 4000:
            step = n_px // 4000
            pixels_lab_km = pixels_lab[::step]
            pixels_rgb_km = pixels_rgb[::step]
        else:
            pixels_lab_km = pixels_lab
            pixels_rgb_km = pixels_rgb

        # K-Means en CIELAB
        k = min(4, max(2, len(pixels_lab_km) // 150))
        if len(pixels_lab_km) < 20:
            mean_rgb = np.mean(pixels_rgb_km, axis=0)
            r_f, g_f, b_f = float(mean_rgb[0]), float(mean_rgb[1]), float(mean_rgb[2])
            cname, chex = classify_rgb(r_f, g_f, b_f)
            return {
                "name": cname,
                "hex": chex,
                "raw_rgb": (round(r_f, 1), round(g_f, 1), round(b_f, 1)),
                "cluster_ratio": 1.0,
            }

        criteria = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 20, 0.5)
        cv2.setRNGSeed(42)
        _, labels, centers_lab = cv2.kmeans(
            pixels_lab_km.astype(np.float32),
            k,
            None,
            criteria,
            5,
            cv2.KMEANS_PP_CENTERS,
        )
        labels_flat = labels.flatten()
        counts = np.bincount(labels_flat, minlength=k)
        total_km = float(len(labels_flat))

        clusters = []
        for idx in range(k):
            cnt = int(counts[idx])
            if cnt == 0:
                continue
            lab_c = centers_lab[idx]
            # Médiane RGB des pixels du cluster (plus robuste aux outliers que la moyenne)
            med_rgb = np.median(pixels_rgb_km[labels_flat == idx], axis=0)
            r_v, g_v, b_v = float(med_rgb[0]), float(med_rgb[1]), float(med_rgb[2])
            chroma = float(np.hypot(lab_c[1] - 128.0, lab_c[2] - 128.0))
            dist_bg = float(np.linalg.norm(lab_c - segmentation.bg_lab))
            clusters.append({
                "cnt": cnt,
                "ratio": cnt / total_km,
                "r": r_v,
                "g": g_v,
                "b": b_v,
                "lab": (round(float(lab_c[0]), 1), round(float(lab_c[1]), 1), round(float(lab_c[2]), 1)),
                "l_lab": float(lab_c[0]),
                "chroma": chroma,
                "dist_bg": dist_bg,
            })

        clusters.sort(key=lambda c: c["cnt"], reverse=True)

        # Filtrer un résidu de fond UNIQUEMENT s'il existe un vrai cluster tissu significatif (>=22%)
        chosen = clusters[0]
        if segmentation.bg_uniform and chosen["dist_bg"] < 10.0:
            non_bg = [c for c in clusters if c["dist_bg"] >= 12.0 and c["ratio"] >= 0.22]
            if non_bg:
                chosen = non_bg[0]

        # Si le top cluster est un résidu achromatique minoritaire (<48%) et qu'un cluster chromatique
        # fort représente >= 28% du tissu, privilégier le tissu chromatique (ex: jean porté / motif léger)
        if chosen["chroma"] < 7.0 and chosen["ratio"] < 0.48:
            chrom_candidates = [
                c for c in clusters
                if c["chroma"] >= 14.0 and c["ratio"] >= 0.28 and (not segmentation.bg_uniform or c["dist_bg"] >= 12.0)
            ]
            if chrom_candidates:
                chosen = chrom_candidates[0]

        r_f, g_f, b_f = chosen["r"], chosen["g"], chosen["b"]
        hsv_tuple, lab_tuple = _rgb_to_hsv_lab(r_f, g_f, b_f)
        color_name, hex_code = classify_rgb(r_f, g_f, b_f)
        color_name = normalize_clothing_color(color_name)
        hex_code = STANDARD_COLORS.get(color_name, hex_code)

        return {
            "name": color_name,
            "hex": hex_code,
            "raw_rgb": (round(r_f, 1), round(g_f, 1), round(b_f, 1)),
            "raw_hsv": hsv_tuple,
            "raw_lab": (round(lab_tuple[0], 1), round(lab_tuple[1], 1), round(lab_tuple[2], 1)),
            "cluster_ratio": round(chosen["ratio"], 3),
            "bg_uniform": segmentation.bg_uniform,
        }
    except Exception as e:
        logger.error(f"[ColorDetection] Erreur extraction couleur : {e}")
        return {"name": ClothingColor.NOIR.value, "hex": STANDARD_COLORS[ClothingColor.NOIR.value]}
