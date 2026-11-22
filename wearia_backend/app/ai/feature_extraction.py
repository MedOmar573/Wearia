"""
Extraction de caractéristiques visuelles unifiées et invariantes au domaine :
- Utilise la segmentation du vêtement (preprocessing.py) pour supprimer le fond
- Recadre sur la boîte englobante (bbox) et place en letterbox carré 64x64 (proportions préservées)
- Normalise la polarité (fond=0, vêtement=[90..255] avec contraste intérieur CLAHE)
  afin d'aligner Fashion-MNIST et photos réelles dans le même espace HOG
- Calcule 20 descripteurs géométriques/structurels bornés sur le vêtement isolé
- Fournit une signature d'apparence multi-modale (HOG + histogramme LAB + vignette) L2-normalisée
  pour l'Active Learning sans biais d'échelle.
"""

import logging
from pathlib import Path
from typing import Dict, Optional, Tuple, Union

import cv2
import numpy as np
from skimage.feature import hog

from app.ai.preprocessing import (
    GarmentSegmentation,
    letterbox_square,
    load_image_rgb,
    segment_garment,
)

logger = logging.getLogger(__name__)

HOG_DIM = 1764
EXTRA_DIM = 28
FEATURE_DIM = HOG_DIM + EXTRA_DIM  # 1792


def _build_canonical_garment_canvas(seg: GarmentSegmentation, size: int = 64) -> np.ndarray:
    """
    Construit un canvas carré (size x size, uint8) invariant à la couleur du vêtement et du fond :
    - Fond strictement à 0
    - Vêtement normalisé dans [95..255] avec contraste intérieur (boutons, col, plis, lacets)
    """
    x1, y1, x2, y2 = seg.bbox
    crop_rgb = seg.img_rgb[y1:y2, x1:x2]
    crop_mask = seg.mask[y1:y2, x1:x2]

    crop_gray = cv2.cvtColor(crop_rgb, cv2.COLOR_RGB2GRAY)

    if seg.is_synthetic_cutout:
        norm_fg = crop_gray.copy()
        norm_fg[~crop_mask] = 0
    else:
        # Contraste local CLAHE pour faire ressortir boutons, col, poches, coutures même sur tissu noir
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(4, 4))
        enhanced = clahe.apply(crop_gray).astype(np.float32)

        fg_vals = enhanced[crop_mask]
        if len(fg_vals) >= 16:
            p5 = float(np.percentile(fg_vals, 5))
            p95 = float(np.percentile(fg_vals, 95))
            span = max(p95 - p5, 15.0)
            # Projeter la luminosité intérieure dans [100..245] pour garder une silhouette nette sur fond 0
            scaled = np.clip((enhanced - p5) / span, 0.0, 1.0) * 145.0 + 100.0
            norm_fg = np.where(crop_mask, scaled, 0.0).astype(np.uint8)
        else:
            norm_fg = (crop_mask.astype(np.uint8) * 180)

    return letterbox_square(norm_fg, size=size, pad_value=0, margin_ratio=0.08)


def extract_structural_metrics(seg: GarmentSegmentation) -> Dict[str, float]:
    """
    Calcule les métriques géométriques et structurelles strictement sur le vêtement isolé (bbox).
    """
    x1, y1, x2, y2 = seg.bbox
    crop_mask = seg.mask[y1:y2, x1:x2]
    crop_rgb = seg.img_rgb[y1:y2, x1:x2]
    ch, cw = crop_mask.shape[:2]

    # 1. Aspect ratio réel du vêtement (borné)
    garment_ar = float(np.clip(seg.garment_ar, 0.25, 3.0))

    # 2. Solidité et étendue (extent)
    mask_u8 = crop_mask.astype(np.uint8) * 255
    area = float(np.sum(crop_mask))
    extent = float(area / max(float(ch * cw), 1.0))

    solidity = extent
    try:
        contours, _ = cv2.findContours(mask_u8, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        if contours:
            all_pts = np.vstack(contours)
            hull = cv2.convexHull(all_pts)
            hull_area = float(cv2.contourArea(hull))
            if hull_area > 1.0:
                solidity = float(np.clip(area / hull_area, 0.0, 1.0))
    except Exception:
        pass

    # 3. Symétrie horizontale (élevée pour hauts/pantalons/robes, faible pour chaussures de profil)
    flipped = np.fliplr(crop_mask)
    inter = float(np.sum(crop_mask & flipped))
    union = float(np.sum(crop_mask | flipped))
    horiz_sym = float(inter / max(union, 1.0))

    # Asymétrie gauche/droite (utile pour profil chaussures)
    mid_x = max(1, cw // 2)
    left_area = float(np.sum(crop_mask[:, :mid_x]))
    right_area = float(np.sum(crop_mask[:, mid_x:]))
    lr_asym = float(abs(left_area - right_area) / max(area, 1.0))

    # 4. Séparation des jambes (gap central bas et milieu : Pantalon/Jean/Short vs Robe/Jupe/Haut)
    c_x1 = int(cw * 0.42)
    c_x2 = max(c_x1 + 1, int(cw * 0.58))
    low_y1 = int(ch * 0.55)
    low_y2 = max(low_y1 + 1, int(ch * 0.96))
    mid_y1 = int(ch * 0.40)
    mid_y2 = max(mid_y1 + 1, int(ch * 0.65))

    lower_center = crop_mask[low_y1:low_y2, c_x1:c_x2]
    mid_center = crop_mask[mid_y1:mid_y2, c_x1:c_x2]
    # Fraction de pixels de fond dans le couloir central entre les deux jambes
    lower_split_ratio = float(1.0 - np.mean(lower_center)) if lower_center.size > 0 else 0.0
    mid_split_ratio = float(1.0 - np.mean(mid_center)) if mid_center.size > 0 else 0.0

    # 5. Profil de largeur sur 8 tranches verticales (10% à 94%)
    width_profile = []
    for idx in range(8):
        ry1 = int(ch * (0.06 + idx * 0.11))
        ry2 = max(ry1 + 1, int(ch * (0.06 + (idx + 1) * 0.11)))
        band = crop_mask[ry1:min(ch, ry2), :]
        if band.size > 0:
            # Largeur effective (span entre premier et dernier pixel actif)
            col_any = np.any(band, axis=0)
            active_cols = np.where(col_any)[0]
            if len(active_cols) >= 2:
                span_w = (active_cols[-1] - active_cols[0] + 1) / float(max(cw, 1))
            else:
                span_w = float(np.mean(band))
        else:
            span_w = 0.0
        width_profile.append(float(np.clip(span_w, 0.0, 1.0)))

    upper_w = float(np.mean(width_profile[:3]))
    lower_w = float(np.mean(width_profile[5:]))
    upper_lower_width_ratio = float(np.clip(upper_w / max(lower_w, 0.08), 0.1, 4.0))

    # 6. Descripteurs de texture/structure internes sur la bbox normalisée (128x128)
    gray_128 = cv2.resize(
        cv2.cvtColor(crop_rgb, cv2.COLOR_RGB2GRAY),
        (128, 128),
        interpolation=cv2.INTER_AREA,
    )
    # Normalisation de contraste locale pour rendre placket/collar/texture indépendants de l'exposition
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(4, 4))
    g_eq = clahe.apply(gray_128)

    # Patte de boutonnage verticale centrale (Chemise vs T-Shirt/Pull)
    center_strip = g_eq[26:110, 56:72]
    left_strip = g_eq[26:110, 32:48]
    right_strip = g_eq[26:110, 80:96]
    s_center = float(np.mean(np.abs(cv2.Sobel(center_strip, cv2.CV_64F, 1, 0, ksize=3))))
    s_sides = (
        float(np.mean(np.abs(cv2.Sobel(left_strip, cv2.CV_64F, 1, 0, ksize=3))))
        + float(np.mean(np.abs(cv2.Sobel(right_strip, cv2.CV_64F, 1, 0, ksize=3))))
    ) / 2.0
    placket_ratio = float(np.clip(s_center / max(s_sides, 2.0), 0.0, 5.0))

    # Densité de contours au col (haut-centre de la bbox)
    collar_patch = g_eq[4:32, 34:94]
    collar_edge_density = float(np.mean(cv2.Canny(collar_patch, 50, 140)) / 255.0)

    # Texture de torse (compressée logarithmiquement -> bornée [0..9])
    torso_patch = g_eq[36:96, 36:96]
    torso_texture_log = float(np.log1p(max(0.0, float(cv2.Laplacian(torso_patch, cv2.CV_64F).var()))))

    # Ratio gradients horizontaux / verticaux
    gx = float(np.mean(np.abs(cv2.Sobel(g_eq, cv2.CV_64F, 1, 0, ksize=3))))
    gy = float(np.mean(np.abs(cv2.Sobel(g_eq, cv2.CV_64F, 0, 1, ksize=3))))
    grad_hv_ratio = float(np.clip(gx / max(gy, 1.0), 0.1, 5.0))

    # 7. Nouveaux descripteurs discriminants (Jean vs Pantalon, Short, Sweat, Veste/Manteau/Chemise, Sac, Chapeau)
    # 7a. Proportion de teinte denim/indigo sur le vêtement isolé (Jean vs Pantalon)
    fg_pixels = seg.img_rgb[seg.inner_mask]
    if len(fg_pixels) < 20:
        fg_pixels = seg.img_rgb[seg.mask]
    if len(fg_pixels) >= 16 and not seg.is_synthetic_cutout:
        fg_hsv = cv2.cvtColor(fg_pixels.reshape(-1, 1, 3), cv2.COLOR_RGB2HSV).reshape(-1, 3)
        h_ch, s_ch, v_ch = fg_hsv[:, 0], fg_hsv[:, 1], fg_hsv[:, 2]
        denim_mask = (h_ch >= 92) & (h_ch <= 135) & (s_ch >= 22) & (s_ch <= 235) & (v_ch >= 28) & (v_ch <= 238)
        denim_blue_ratio = float(np.mean(denim_mask))
    else:
        denim_blue_ratio = 0.0

    # 7b. Micro-texture tissu (différence haute fréquence sur le torse/corps)
    blurred = cv2.GaussianBlur(g_eq, (3, 3), 0)
    hf_diff = np.abs(g_eq.astype(np.float32) - blurred.astype(np.float32))
    fabric_micro_texture = float(np.clip(np.mean(hf_diff[24:104, 24:104]) / 25.0, 0.0, 3.0))

    # 7c. Ouverture supérieure centrale (anse de Sac ou décolleté/revers ouvert de Veste/Blazer)
    th_y1, th_y2 = int(ch * 0.04), max(int(ch * 0.04) + 1, int(ch * 0.32))
    th_x1, th_x2 = int(cw * 0.28), max(int(cw * 0.28) + 1, int(cw * 0.72))
    top_center_patch = crop_mask[th_y1:th_y2, th_x1:th_x2]
    top_hole_ratio = float(1.0 - np.mean(top_center_patch)) if top_center_patch.size > 0 else 0.0

    # 7d. Proéminence supérieure type capuche (Sweat à capuche : sommet étroit au-dessus d'épaules larges)
    def _band_span(y_start_frac: float, y_end_frac: float) -> float:
        by1 = int(ch * y_start_frac)
        by2 = max(by1 + 1, int(ch * y_end_frac))
        band = crop_mask[by1:min(ch, by2), :]
        if band.size == 0:
            return 0.0
        cols = np.where(np.any(band, axis=0))[0]
        return float((cols[-1] - cols[0] + 1) / max(float(cw), 1.0)) if len(cols) >= 2 else 0.0

    top_tip_w = _band_span(0.0, 0.14)
    shoulder_w = max(_band_span(0.20, 0.38), 0.10)
    hood_peak_ratio = float(np.clip(top_tip_w / shoulder_w, 0.0, 2.0))

    # 7e. Largeur de l'ourlet inférieur (Manteau/Chapeau large vs Bomber/Veste ajustée)
    bottom_hem_width = _band_span(0.84, 1.0)

    # 7f. Encoche d'entrejambe courte en bas (caractéristique Short)
    sh_y1 = int(ch * 0.68)
    sh_y2 = max(sh_y1 + 1, ch)
    sh_x1 = int(cw * 0.43)
    sh_x2 = max(sh_x1 + 1, int(cw * 0.57))
    short_notch_patch = crop_mask[sh_y1:sh_y2, sh_x1:sh_x2]
    short_leg_notch = float(1.0 - np.mean(short_notch_patch)) if short_notch_patch.size > 0 else 0.0

    # 7g. Contraste d'ouverture verticale centrale (Veste/Blazer/Manteau ouverts vs Chemise fermée)
    mid_band_mean = float(np.mean(g_eq[24:108, 56:72]))
    side_band_mean = 0.5 * (float(np.mean(g_eq[24:108, 24:46])) + float(np.mean(g_eq[24:108, 82:104])))
    center_open_contrast = float(np.clip(abs(mid_band_mean - side_band_mean) / 80.0, 0.0, 3.0))

    # 7h. Remplissage de la couronne supérieure (Chapeau/Bonnet bombé plein vs Sac à anse creux)
    crown_patch = crop_mask[int(ch * 0.06):max(int(ch * 0.06) + 1, int(ch * 0.38)), int(cw * 0.22):max(int(cw * 0.22) + 1, int(cw * 0.78))]
    upper_crown_convexity = float(np.mean(crown_patch)) if crown_patch.size > 0 else 0.0

    return {
        "garment_ar": garment_ar,
        "solidity": solidity,
        "extent": extent,
        "horiz_sym": horiz_sym,
        "lr_asym": lr_asym,
        "lower_split_ratio": lower_split_ratio,
        "mid_split_ratio": mid_split_ratio,
        "width_profile": width_profile,
        "upper_lower_width_ratio": upper_lower_width_ratio,
        "placket_ratio": placket_ratio,
        "collar_edge_density": collar_edge_density,
        "torso_texture_log": torso_texture_log,
        "grad_hv_ratio": grad_hv_ratio,
        "denim_blue_ratio": denim_blue_ratio,
        "fabric_micro_texture": fabric_micro_texture,
        "top_hole_ratio": top_hole_ratio,
        "hood_peak_ratio": hood_peak_ratio,
        "bottom_hem_width": bottom_hem_width,
        "short_leg_notch": short_leg_notch,
        "center_open_contrast": center_open_contrast,
        "upper_crown_convexity": upper_crown_convexity,
    }


def extract_advanced_features(
    image_path_or_array: Union[str, Path, np.ndarray],
    segmentation: Optional[GarmentSegmentation] = None,
    input_is_bgr: bool = True,
) -> np.ndarray:
    """
    Extrait le vecteur complet (1, 1784) de descripteurs HOG + géométrie/structure
    sur le vêtement isolé (bbox + letterbox carré 64x64).
    """
    try:
        if segmentation is None:
            img_rgb, _ = load_image_rgb(image_path_or_array, input_is_bgr=input_is_bgr)
            if img_rgb is None:
                return np.zeros((1, FEATURE_DIM), dtype=np.float32)
            segmentation = segment_garment(img_rgb, max_side=224)

        canvas_64 = _build_canonical_garment_canvas(segmentation, size=64)
        hog_feats = hog(
            canvas_64,
            orientations=9,
            pixels_per_cell=(8, 8),
            cells_per_block=(2, 2),
            block_norm="L2-Hys",
            visualize=False,
        ).astype(np.float32).flatten()

        m = extract_structural_metrics(segmentation)
        extra_list = [
            m["garment_ar"],
            m["solidity"],
            m["extent"],
            m["horiz_sym"],
            m["lr_asym"],
            m["lower_split_ratio"],
            m["mid_split_ratio"],
            *m["width_profile"],  # 8 valeurs
            m["upper_lower_width_ratio"],
            m["placket_ratio"],
            m["collar_edge_density"],
            m["torso_texture_log"],
            m["grad_hv_ratio"],
            m["denim_blue_ratio"],
            m["fabric_micro_texture"],
            m["top_hole_ratio"],
            m["hood_peak_ratio"],
            m["bottom_hem_width"],
            m["short_leg_notch"],
            m["center_open_contrast"],
            m["upper_crown_convexity"],
        ]
        extra_feats = np.array(extra_list, dtype=np.float32)

        full_vector = np.concatenate([hog_feats, extra_feats])
        return full_vector.reshape(1, -1)
    except Exception as e:
        logger.error(f"[FeatureExtraction] Erreur extraction : {e}")
        return np.zeros((1, FEATURE_DIM), dtype=np.float32)


def extract_appearance_signature(
    image_path_or_array: Union[str, Path, np.ndarray],
    segmentation: Optional[GarmentSegmentation] = None,
    input_is_bgr: bool = True,
) -> Optional[Dict[str, np.ndarray]]:
    """
    Extrait une signature d'apparence strictement L2-normalisée pour l'Active Learning :
    - hog : forme normalisée (1764,) norme = 1
    - color_hist : histogramme CIELAB 4x4x4 (64,) norme = 1
    - thumb : vignette RGB 16x16 centrée-réduite (768,) norme = 1
    Empêche toute fausse correspondance due à des caractéristiques non normalisées.
    """
    try:
        if segmentation is None:
            img_rgb, _ = load_image_rgb(image_path_or_array, input_is_bgr=input_is_bgr)
            if img_rgb is None:
                return None
            segmentation = segment_garment(img_rgb, max_side=224)

        canvas_64 = _build_canonical_garment_canvas(segmentation, size=64)
        hog_vec = hog(
            canvas_64,
            orientations=9,
            pixels_per_cell=(8, 8),
            cells_per_block=(2, 2),
            block_norm="L2-Hys",
            visualize=False,
        ).astype(np.float32).flatten()
        hog_norm = float(np.linalg.norm(hog_vec))
        if hog_norm < 1e-6:
            return None
        hog_vec = hog_vec / hog_norm

        # Histogramme CIELAB sur le masque interne du vêtement
        pixels_rgb = segmentation.img_rgb[segmentation.inner_mask]
        if len(pixels_rgb) < 20:
            pixels_rgb = segmentation.img_rgb[segmentation.mask]
        pixels_lab = cv2.cvtColor(pixels_rgb.reshape(-1, 1, 3), cv2.COLOR_RGB2LAB).reshape(-1, 3)
        hist, _ = np.histogramdd(
            pixels_lab.astype(np.float32),
            bins=(4, 4, 4),
            range=((0, 256), (0, 256), (0, 256)),
        )
        hist_vec = hist.astype(np.float32).flatten()
        hist_norm = float(np.linalg.norm(hist_vec))
        if hist_norm > 1e-6:
            hist_vec = hist_vec / hist_norm

        # Vignette RGB 16x16 de la bbox en letterbox (centrée-réduite)
        x1, y1, x2, y2 = segmentation.bbox
        crop_rgb = segmentation.img_rgb[y1:y2, x1:x2]
        thumb_16 = letterbox_square(crop_rgb, size=16, pad_value=128, margin_ratio=0.05).astype(np.float32).flatten()
        thumb_16 = thumb_16 - float(np.mean(thumb_16))
        thumb_norm = float(np.linalg.norm(thumb_16))
        if thumb_norm > 1e-6:
            thumb_16 = thumb_16 / thumb_norm

        return {
            "hog": hog_vec,
            "color_hist": hist_vec,
            "thumb": thumb_16,
        }
    except Exception as e:
        logger.error(f"[AppearanceSignature] Erreur : {e}")
        return None


def extract_hog_features(image_path_or_array, target_size=(64, 64)) -> np.ndarray:
    """Rétrocompatibilité : appelle extract_advanced_features."""
    return extract_advanced_features(image_path_or_array)
