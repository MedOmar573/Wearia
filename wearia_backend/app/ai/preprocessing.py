"""
Prétraitement d'image unifié pour la classification de vêtements et l'extraction de couleur :
- Lecture avec correction systématique d'orientation EXIF (Pillow ImageOps.exif_transpose)
- Gestion propre des PNG transparents (fond blanc) et espace colorimétrique unique RGB
- Redimensionnement conservant les proportions (aspect ratio) et letterbox carré
- Segmentation du vêtement (isolation du premier plan, suppression fond/ombres/bordures)
"""

from dataclasses import dataclass
import logging
from pathlib import Path
from typing import Any, Dict, Optional, Tuple, Union

import cv2
import numpy as np
from PIL import Image, ImageOps

logger = logging.getLogger(__name__)


@dataclass
class GarmentSegmentation:
    """Résultat de la segmentation et normalisation géométrique d'un vêtement."""
    img_rgb: np.ndarray          # Image RGB redimensionnée en conservant les proportions
    mask: np.ndarray             # Masque booléen (H, W) du vêtement isolé
    inner_mask: np.ndarray       # Masque érodé (H, W) sans les contours/franges pour la couleur
    bbox: Tuple[int, int, int, int]  # (x1, y1, x2, y2) boîte englobante du vêtement
    garment_ar: float            # Ratio hauteur/largeur RÉEL du vêtement (indépendant du cadrage photo)
    bg_lab: np.ndarray           # Couleur CIELAB médiane du fond estimé (bordures)
    bg_uniform: bool             # True si fond studio/uniforme, False si fond réel complexe
    fg_ratio: float              # Proportion de pixels appartenant au vêtement
    is_synthetic_cutout: bool = False  # True pour silhouettes type Fashion-MNIST (fond noir pur)


def load_image_rgb(
    image_path_or_array: Union[str, Path, np.ndarray],
    input_is_bgr: bool = True,
) -> Tuple[Optional[np.ndarray], Dict[str, Any]]:
    """
    Charge une image en tableau NumPy RGB (uint8) avec correction EXIF garantie.
    Si un ndarray est fourni, convertit explicitement selon input_is_bgr.
    """
    meta: Dict[str, Any] = {"exif_orientation": 1, "exif_transposed": False, "orig_shape": None}

    try:
        if isinstance(image_path_or_array, (str, Path)):
            path = Path(image_path_or_array)
            if not path.exists():
                logger.warning(f"[Preprocess] Fichier introuvable : {path}")
                return None, meta

            with Image.open(path) as pil_img:
                try:
                    exif = pil_img.getexif()
                    orient = int(exif.get(274, 1)) if exif else 1
                except Exception:
                    orient = 1

                meta["exif_orientation"] = orient
                if orient != 1:
                    pil_img = ImageOps.exif_transpose(pil_img)
                    meta["exif_transposed"] = True

                # Gestion des images avec transparence (PNG/WebP RGBA) -> composition sur fond blanc
                if pil_img.mode in ("RGBA", "LA") or (
                    pil_img.mode == "P" and "transparency" in pil_img.info
                ):
                    rgba = pil_img.convert("RGBA")
                    bg = Image.new("RGBA", rgba.size, (255, 255, 255, 255))
                    rgb_img = Image.alpha_composite(bg, rgba).convert("RGB")
                else:
                    rgb_img = pil_img.convert("RGB")

                arr = np.array(rgb_img, dtype=np.uint8)
                meta["orig_shape"] = (arr.shape[0], arr.shape[1])
                return arr, meta

        elif isinstance(image_path_or_array, np.ndarray):
            arr = image_path_or_array
            if arr.size == 0:
                return None, meta
            if arr.ndim == 2:
                arr = cv2.cvtColor(arr, cv2.COLOR_GRAY2RGB)
            elif arr.ndim == 3 and arr.shape[2] == 4:
                if input_is_bgr:
                    arr = cv2.cvtColor(arr, cv2.COLOR_BGRA2RGB)
                else:
                    arr = cv2.cvtColor(arr, cv2.COLOR_RGBA2RGB)
            elif arr.ndim == 3 and arr.shape[2] == 3 and input_is_bgr:
                arr = cv2.cvtColor(arr, cv2.COLOR_BGR2RGB)
            else:
                arr = arr.copy()

            if arr.dtype != np.uint8:
                arr = np.clip(arr, 0, 255).astype(np.uint8)
            meta["orig_shape"] = (arr.shape[0], arr.shape[1])
            return arr, meta

        return None, meta
    except Exception as e:
        logger.error(f"[Preprocess] Erreur chargement image : {e}")
        return None, meta


def resize_keep_aspect(img: np.ndarray, max_side: int = 256) -> np.ndarray:
    """Redimensionne une image (sans agrandissement inutile) en préservant strictement son ratio."""
    h, w = img.shape[:2]
    longest = max(h, w)
    if longest <= 0 or longest <= max_side:
        return img
    scale = max_side / float(longest)
    new_w = max(1, int(round(w * scale)))
    new_h = max(1, int(round(h * scale)))
    return cv2.resize(img, (new_w, new_h), interpolation=cv2.INTER_AREA)


def letterbox_square(
    img: np.ndarray,
    size: int = 64,
    pad_value: int = 0,
    margin_ratio: float = 0.08,
) -> np.ndarray:
    """
    Place un recadrage de vêtement dans un carré (size x size) en conservant
    exactement ses proportions, centré avec une petite marge uniforme.
    """
    h, w = img.shape[:2]
    if h == 0 or w == 0:
        if img.ndim == 3:
            return np.full((size, size, img.shape[2]), pad_value, dtype=np.uint8)
        return np.full((size, size), pad_value, dtype=np.uint8)

    inner = max(4, int(round(size * (1.0 - 2.0 * margin_ratio))))
    scale = inner / float(max(h, w))
    new_w = max(1, int(round(w * scale)))
    new_h = max(1, int(round(h * scale)))
    interp = cv2.INTER_AREA if scale < 1.0 else cv2.INTER_CUBIC
    resized = cv2.resize(img, (new_w, new_h), interpolation=interp)

    if img.ndim == 3:
        canvas = np.full((size, size, img.shape[2]), pad_value, dtype=np.uint8)
    else:
        canvas = np.full((size, size), pad_value, dtype=np.uint8)

    y_off = (size - new_h) // 2
    x_off = (size - new_w) // 2
    canvas[y_off:y_off + new_h, x_off:x_off + new_w] = resized
    return canvas


def _keep_central_components(mask: np.ndarray) -> np.ndarray:
    """
    Filtre les composants connexes du masque pour conserver le vêtement principal
    au centre de l'image et éliminer les objets parasites dans les coins/bords.
    """
    h, w = mask.shape
    mask_u8 = (mask.astype(np.uint8)) * 255
    num_labels, labels, stats, centroids = cv2.connectedComponentsWithStats(mask_u8, connectivity=8)
    if num_labels <= 1:
        return mask

    cx, cy = w / 2.0, h / 2.0
    total_area = float(h * w)
    best_label = -1
    best_score = -1.0

    # Zone centrale (30% à 70%)
    center_box = np.zeros_like(mask, dtype=bool)
    center_box[int(h * 0.25):int(h * 0.75), int(w * 0.25):int(w * 0.75)] = True

    selected = np.zeros_like(mask, dtype=bool)
    comp_infos = []
    for lbl in range(1, num_labels):
        area = int(stats[lbl, cv2.CC_STAT_AREA])
        if area < max(40, int(0.005 * total_area)):
            continue
        comp_mask = labels == lbl
        overlap_center = float(np.sum(comp_mask & center_box)) / max(float(area), 1.0)
        dist_center = np.hypot((centroids[lbl][0] - cx) / max(w, 1), (centroids[lbl][1] - cy) / max(h, 1))
        score = (area / total_area) * (0.4 + 1.5 * overlap_center) / (0.3 + dist_center)
        comp_infos.append((lbl, area, overlap_center, score, comp_mask))
        if score > best_score:
            best_score = score
            best_label = lbl

    if best_label == -1:
        return mask

    best_area = next(a for l, a, _, _, _ in comp_infos if l == best_label)
    for lbl, area, overlap_center, _, comp_mask in comp_infos:
        # Garder le composant principal + les éventuels gros sous-éléments centraux (ex: 2 baskets)
        if lbl == best_label or (area >= 0.22 * best_area and overlap_center > 0.10):
            selected |= comp_mask

    return selected if np.sum(selected) >= 50 else mask


def _extract_bbox(mask: np.ndarray) -> Tuple[int, int, int, int]:
    h, w = mask.shape
    ys, xs = np.where(mask)
    if len(ys) == 0 or len(xs) == 0:
        return (int(w * 0.1), int(h * 0.1), int(w * 0.9), int(h * 0.9))
    x1, x2 = int(xs.min()), int(xs.max()) + 1
    y1, y2 = int(ys.min()), int(ys.max()) + 1
    return (x1, y1, max(x1 + 1, x2), max(y1 + 1, y2))


def segment_garment(img_rgb: np.ndarray, max_side: int = 224) -> GarmentSegmentation:
    """
    Isole le vêtement de son arrière-plan de manière robuste :
    - Cas 1 : Silhouette synthétique fond noir pur (Fashion-MNIST) -> seuillage direct ultra-rapide
    - Cas 2 : Fond studio/uniforme -> distance CIELAB + floodfill depuis les bords (avec repli GrabCut si ton-sur-ton)
    - Cas 3 : Photo réelle complexe (lit, sol, extérieur) -> GrabCut initialisé par masque bord/centre + filtre central
    """
    small_rgb = resize_keep_aspect(img_rgb, max_side=max_side)
    h, w = small_rgb.shape[:2]
    total_px = float(h * w)

    # Conversion en CIELAB et niveaux de gris
    lab = cv2.cvtColor(small_rgb, cv2.COLOR_RGB2LAB).astype(np.float32)
    gray = cv2.cvtColor(small_rgb, cv2.COLOR_RGB2GRAY)

    # Estimation du fond sur un anneau périphérique (5% des bords)
    b = max(4, int(round(min(h, w) * 0.05)))
    border_lab = np.concatenate([
        lab[:b, :].reshape(-1, 3),
        lab[-b:, :].reshape(-1, 3),
        lab[:, :b].reshape(-1, 3),
        lab[:, -b:].reshape(-1, 3),
    ], axis=0)
    border_gray = np.concatenate([
        gray[:b, :].ravel(),
        gray[-b:, :].ravel(),
        gray[:, :b].ravel(),
        gray[:, -b:].ravel(),
    ])

    bg_lab = np.median(border_lab, axis=0)
    bg_lab_std = float(np.mean(np.std(border_lab, axis=0)))
    bg_gray_med = float(np.median(border_gray))
    bg_gray_std = float(np.std(border_gray))

    # ── CAS 1 : Silhouette synthétique sur fond noir pur (Fashion-MNIST) ─────
    # Même si le vêtement touche le bord haut/bas, >40% de la bordure reste noir pur (<= 8)
    if bg_gray_med <= 5.0 and float(np.mean(border_gray <= 8)) >= 0.40 and np.mean(gray > 20) > 0.08:
        mask = gray > 20
        bbox = _extract_bbox(mask)
        garment_ar = (bbox[3] - bbox[1]) / float(max(bbox[2] - bbox[0], 1))
        return GarmentSegmentation(
            img_rgb=small_rgb,
            mask=mask,
            inner_mask=mask,
            bbox=bbox,
            garment_ar=float(garment_ar),
            bg_lab=bg_lab,
            bg_uniform=True,
            fg_ratio=float(np.mean(mask)),
            is_synthetic_cutout=True,
        )

    bg_uniform = bg_lab_std < 11.5
    mask = None

    # ── CAS 2 : Fond studio / uniforme (blanc, gris clair, uni) ──────────────
    if bg_uniform:
        delta_e = np.linalg.norm(lab - bg_lab.reshape(1, 1, 3), axis=2)
        thresh = max(11.0, min(28.0, 2.8 * bg_lab_std + 7.0))
        bg_candidate = (delta_e <= thresh).astype(np.uint8)

        # Floodfill du fond uniquement à partir des pixels connectés aux bordures
        # (préserve ainsi les zones intérieures blanches/logos/boutons du vêtement !)
        ff_mask = np.zeros((h + 2, w + 2), dtype=np.uint8)
        visited_bg = np.zeros((h, w), dtype=np.uint8)
        work = bg_candidate.copy()
        for x in range(0, w, max(1, w // 16)):
            if work[0, x] == 1:
                cv2.floodFill(work, ff_mask, (x, 0), 2)
            if work[h - 1, x] == 1:
                cv2.floodFill(work, ff_mask, (x, h - 1), 2)
        for y in range(0, h, max(1, h // 16)):
            if work[y, 0] == 1:
                cv2.floodFill(work, ff_mask, (0, y), 2)
            if work[y, w - 1] == 1:
                cv2.floodFill(work, ff_mask, (w - 1, y), 2)
        visited_bg = (work == 2)
        studio_mask = ~visited_bg

        # Nettoyage morphologique léger
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
        studio_mask_u8 = cv2.morphologyEx(studio_mask.astype(np.uint8) * 255, cv2.MORPH_OPEN, kernel)
        studio_mask_u8 = cv2.morphologyEx(studio_mask_u8, cv2.MORPH_CLOSE, kernel)
        studio_mask = studio_mask_u8 > 0

        fg_frac = float(np.mean(studio_mask))
        # Si le vêtement a une taille réaliste (8% à 92% de l'image), valider le masque studio
        if 0.08 <= fg_frac <= 0.92:
            mask = _keep_central_components(studio_mask)

    # ── CAS 3 : Fond complexe OU vêtement ton-sur-ton (GrabCut structuré) ────
    if mask is None:
        try:
            small_bgr = cv2.cvtColor(small_rgb, cv2.COLOR_RGB2BGR)
            gc_mask = np.full((h, w), cv2.GC_PR_BGD, dtype=np.uint8)

            # Bordure externe = fond probable/sûr
            b_outer = max(2, int(round(min(h, w) * 0.03)))
            gc_mask[:b_outer, :] = cv2.GC_BGD
            gc_mask[-b_outer:, :] = cv2.GC_BGD
            gc_mask[:, :b_outer] = cv2.GC_BGD
            gc_mask[:, -b_outer:] = cv2.GC_BGD

            # Intérieur principal = premier plan probable
            x1_r, x2_r = int(w * 0.12), int(w * 0.88)
            y1_r, y2_r = int(h * 0.10), int(h * 0.90)
            gc_mask[y1_r:y2_r, x1_r:x2_r] = cv2.GC_PR_FGD

            fg_model = np.zeros((1, 65), dtype=np.float64)
            bg_model = np.zeros((1, 65), dtype=np.float64)
            cv2.setRNGSeed(42)
            cv2.grabCut(small_bgr, gc_mask, None, bg_model, fg_model, 3, cv2.GC_INIT_WITH_MASK)

            gc_fg = (gc_mask == cv2.GC_FGD) | (gc_mask == cv2.GC_PR_FGD)
            kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
            gc_fg = cv2.morphologyEx(gc_fg.astype(np.uint8) * 255, cv2.MORPH_OPEN, kernel) > 0
            gc_fg = _keep_central_components(gc_fg)

            fg_frac = float(np.mean(gc_fg))
            if 0.06 <= fg_frac <= 0.94:
                mask = gc_fg
        except Exception as e:
            logger.debug(f"[Preprocess] GrabCut ignoré : {e}")

    # Repli ultime : ellipse centrale si aucune segmentation valide
    if mask is None or np.sum(mask) < max(80, int(0.04 * total_px)):
        mask = np.zeros((h, w), dtype=bool)
        mask[int(h * 0.15):int(h * 0.85), int(w * 0.15):int(w * 0.85)] = True

    # Masque interne érodé pour la détection de couleur (élimine les pixels de contour/ombre portée)
    erode_r = max(3, int(round(min(h, w) * 0.03)))
    erode_k = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (erode_r, erode_r))
    eroded = cv2.erode(mask.astype(np.uint8) * 255, erode_k, iterations=1) > 0
    inner_mask = eroded if np.sum(eroded) >= max(100, int(0.25 * np.sum(mask))) else mask

    bbox = _extract_bbox(mask)
    garment_ar = (bbox[3] - bbox[1]) / float(max(bbox[2] - bbox[0], 1))

    return GarmentSegmentation(
        img_rgb=small_rgb,
        mask=mask,
        inner_mask=inner_mask,
        bbox=bbox,
        garment_ar=float(garment_ar),
        bg_lab=bg_lab,
        bg_uniform=bg_uniform,
        fg_ratio=float(np.mean(mask)),
        is_synthetic_cutout=False,
    )
