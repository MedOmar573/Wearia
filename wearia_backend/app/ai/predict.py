import logging
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple

import joblib
import numpy as np

from app.core.config import settings
from app.ai.preprocessing import load_image_rgb, segment_garment
from app.ai.feature_extraction import (
    FEATURE_DIM,
    extract_advanced_features,
    extract_structural_metrics,
)
from app.ai.color_detection import detect_dominant_color
from app.ai.feedback_learning import ActiveLearningManager
from app.ai.taxonomy import (
    ClothingColor,
    ClothingType,
    FEMME_ONLY_TYPES,
    STANDARD_COLORS,
    TOP_TYPES,
    normalize_clothing_color,
    normalize_clothing_type,
)

logger = logging.getLogger(__name__)

# Cache mémoire des modèles
_CACHED_MODEL = None
_CACHED_SCALER = None


def reload_models():
    """Force le rechargement disque du modèle et du scaler (utile après réentraînement)."""
    global _CACHED_MODEL, _CACHED_SCALER
    _CACHED_MODEL = None
    _CACHED_SCALER = None
    return get_loaded_models()


def get_loaded_models():
    global _CACHED_MODEL, _CACHED_SCALER
    if _CACHED_MODEL is None or _CACHED_SCALER is None:
        model_path = settings.AI_MODELS_DIR / "knn_model.joblib"
        scaler_path = settings.AI_MODELS_DIR / "scaler.joblib"
        if model_path.exists() and scaler_path.exists():
            try:
                _CACHED_MODEL = joblib.load(model_path)
                _CACHED_SCALER = joblib.load(scaler_path)
                logger.info(
                    f"[AI] Modèle {type(_CACHED_MODEL).__name__} + Scaler chargés "
                    f"(features={getattr(_CACHED_SCALER, 'n_features_in_', '?')}, "
                    f"classes={len(getattr(_CACHED_MODEL, 'classes_', []))})."
                )
            except Exception as e:
                logger.error(f"[AI] Erreur chargement modèle : {e}")
    return _CACHED_MODEL, _CACHED_SCALER


def infer_clothing_attributes(category: str, color: str) -> Dict[str, Any]:
    """Déduit matière, saison, coupe et style selon la catégorie canonique détectée."""
    cat_lower = category.lower()

    matiere = "Coton"
    saison = "TOUTE_SAISON"
    est_thermique = False
    est_impermeable = False
    coupe = "REGULIERE"
    style_id = 1
    style_name = "Casual"

    if "chemise" in cat_lower:
        matiere = "100% Coton Oxford"
        coupe = "REGULIERE"
        style_id = 2
        style_name = "Classic"
    elif "pull" in cat_lower or "tricot" in cat_lower:
        matiere = "Laine / Maille tricotée"
        saison = "HIVER"
        est_thermique = True
    elif "t-shirt" in cat_lower or "tshirt" in cat_lower:
        matiere = "100% Coton peigné"
        saison = "ETE"
    elif "polo" in cat_lower:
        matiere = "Piqué de coton respirant"
        saison = "ETE"
        coupe = "AJUSTEE"
        style_id = 2
        style_name = "Classic"
    elif "sweat" in cat_lower:
        matiere = "Coton molleton"
        saison = "AUTOMNE"
        est_thermique = True
        coupe = "OVERSIZE"
        style_id = 3
        style_name = "Sporty"
    elif "robe" in cat_lower:
        matiere = "Soie / Viscose fluide"
        saison = "ETE"
        coupe = "AJUSTEE"
        style_id = 5
        style_name = "Elegant"
    elif "jupe" in cat_lower:
        matiere = "Coton / Denim / Plissé"
        saison = "ETE"
        coupe = "AJUSTEE"
    elif "jean" in cat_lower:
        matiere = "Denim stretch"
        coupe = "AJUSTEE"
    elif "pantalon" in cat_lower or "chino" in cat_lower:
        matiere = "Coton sergé / Toile"
        style_id = 2
        style_name = "Classic"
    elif "short" in cat_lower:
        matiere = "Coton léger"
        saison = "ETE"
    elif "veste" in cat_lower or "blazer" in cat_lower:
        matiere = "Laine mélangée structurée"
        saison = "AUTOMNE"
        est_thermique = True
        coupe = "AJUSTEE"
        style_id = 5
        style_name = "Elegant"
    elif "manteau" in cat_lower:
        matiere = "Laine & Cachemire"
        saison = "HIVER"
        est_thermique = True
        est_impermeable = True
        style_id = 2
        style_name = "Classic"
    elif "botte" in cat_lower:
        matiere = "Cuir véritable / Daim"
        saison = "HIVER"
        est_thermique = True
        est_impermeable = True
        coupe = "AJUSTEE"
        style_id = 2
        style_name = "Classic"
    elif "basket" in cat_lower or "sneaker" in cat_lower:
        matiere = "Cuir & Toile respirante"
        style_id = 3
        style_name = "Sporty"
    elif "chaussure" in cat_lower or "derbie" in cat_lower:
        matiere = "Cuir véritable"
        style_id = 2
        style_name = "Classic"
    elif "sac" in cat_lower:
        matiere = "Cuir / Toile structurée"
        saison = "TOUTE_SAISON"
        coupe = "REGULIERE"
        style_id = 5
        style_name = "Elegant"
    elif "chapeau" in cat_lower or "casquette" in cat_lower or "bonnet" in cat_lower:
        matiere = "Coton / Feutre"
        saison = "TOUTE_SAISON"
        coupe = "REGULIERE"
        style_id = 1
        style_name = "Casual"

    return {
        "name": f"{category} {color}",
        "matiere": matiere,
        "saison": saison,
        "est_thermique": est_thermique,
        "est_impermeable": est_impermeable,
        "coupe": coupe,
        "style_id": style_id,
        "style_name": style_name,
    }


def _refine_prediction_structurally(
    raw_category: str,
    confidence: float,
    prob_map: Dict[str, float],
    metrics: Dict[str, float],
    color_name: str,
    user_genre: Optional[str] = None,
) -> Tuple[str, float, str]:
    """
    Raffinement structurel conservateur basé uniquement sur la géométrie réelle
    du vêtement segmenté (bbox) et la cohérence couleur/type.
    Ne remplace jamais une prédiction ML solide par des seuils arbitraires sur l'image brute.
    """
    final_cat = raw_category
    final_conf = confidence
    rule_applied = "none"

    g_ar = metrics["garment_ar"]
    lower_split = metrics["lower_split_ratio"]
    horiz_sym = metrics["horiz_sym"]
    solidity = metrics["solidity"]
    ul_ratio = metrics["upper_lower_width_ratio"]
    placket = metrics["placket_ratio"]
    collar = metrics["collar_edge_density"]
    denim_blue = metrics.get("denim_blue_ratio", 0.0)
    top_hole = metrics.get("top_hole_ratio", 0.0)
    hood_peak = metrics.get("hood_peak_ratio", 0.0)
    short_notch = metrics.get("short_leg_notch", 0.0)
    open_contrast = metrics.get("center_open_contrast", 0.0)
    crown_conv = metrics.get("upper_crown_convexity", 0.0)

    is_homme = bool(user_genre and user_genre.upper() == "HOMME")

    # 1. Cohérence Pantalon vs Jean selon la couleur et la signature denim/indigo
    non_jean_colors = {
        ClothingColor.ROUGE.value,
        ClothingColor.VERT.value,
        ClothingColor.ROSE.value,
        ClothingColor.CORAIL.value,
        ClothingColor.JAUNE.value,
        ClothingColor.JAUNE_CLAIR.value,
        ClothingColor.ORANGE.value,
        ClothingColor.VIOLET.value,
        ClothingColor.BEIGE.value,
        ClothingColor.SABLE.value,
        ClothingColor.MARRON.value,
        ClothingColor.MARRON_FONCE.value,
    }
    if final_cat == ClothingType.JEAN.value and color_name in non_jean_colors:
        final_cat = ClothingType.PANTALON.value
        rule_applied = f"jean_non_denim_color({color_name})->Pantalon"

    # 1b. Pantalon bleu/marine avec forte teinte denim -> Jean (distinction nette Jean vs Pantalon)
    elif (
        final_cat == ClothingType.PANTALON.value
        and color_name in (ClothingColor.BLEU.value, ClothingColor.BLEU_MARINE.value)
        and (denim_blue >= 0.40 or prob_map.get(ClothingType.JEAN.value, 0.0) >= 0.16)
    ):
        final_cat = ClothingType.JEAN.value
        final_conf = max(final_conf, prob_map.get(ClothingType.JEAN.value, 0.65))
        rule_applied = f"pantalon_denim(color={color_name},denim={denim_blue:.2f})->Jean"

    # 2. Distinction Short vs Pantalon / Jean / Hauts
    if (
        final_cat in (ClothingType.PANTALON.value, ClothingType.JEAN.value)
        and g_ar <= 1.12
        and (lower_split >= 0.10 or short_notch >= 0.12)
    ):
        final_cat = ClothingType.SHORT.value
        final_conf = max(final_conf, prob_map.get(ClothingType.SHORT.value, 0.68))
        rule_applied = f"short_compact_legs(ar={g_ar:.2f},split={lower_split:.2f},notch={short_notch:.2f})->Short"
    elif (
        final_cat in (ClothingType.TSHIRT.value, ClothingType.PULL.value, ClothingType.JUPE.value)
        and 0.58 <= g_ar <= 1.15
        and lower_split >= 0.18
        and short_notch >= 0.22
        and ul_ratio <= 1.25
        and prob_map.get(ClothingType.SHORT.value, 0.0) >= 0.10
    ):
        final_cat = ClothingType.SHORT.value
        final_conf = max(final_conf, prob_map.get(ClothingType.SHORT.value, 0.64))
        rule_applied = f"short_split_recovery(ar={g_ar:.2f},split={lower_split:.2f})->Short"

    # 3. Séparation nette des jambes sur une silhouette très allongée mal classée en Robe/Manteau
    elif final_cat in (ClothingType.ROBE.value, ClothingType.MANTEAU.value) and g_ar >= 1.45 and lower_split >= 0.25:
        if prob_map.get(ClothingType.PANTALON.value, 0.0) + prob_map.get(ClothingType.JEAN.value, 0.0) >= 0.12:
            if color_name in (ClothingColor.BLEU.value, ClothingColor.BLEU_MARINE.value) and denim_blue >= 0.40:
                final_cat = ClothingType.JEAN.value
                rule_applied = f"leg_split_denim(ar={g_ar:.2f},split={lower_split:.2f})->Jean"
            else:
                final_cat = ClothingType.PANTALON.value
                rule_applied = f"leg_split(ar={g_ar:.2f},split={lower_split:.2f})->Pantalon"
            final_conf = max(final_conf, 0.72)

    # 4. Robe sur silhouette trop courte -> choisir le meilleur Haut issu du modèle ML
    elif final_cat == ClothingType.ROBE.value and g_ar < 1.15:
        top_candidates = [(c, p) for c, p in prob_map.items() if c in TOP_TYPES]
        if top_candidates:
            best_top, best_p = max(top_candidates, key=lambda x: x[1])
            final_cat = best_top
            final_conf = max(0.55, best_p)
            rule_applied = f"short_robe(ar={g_ar:.2f})->{best_top}"

    # 5. Distinction nette Chemise / Veste / Manteau
    elif final_cat == ClothingType.MANTEAU.value and g_ar <= 1.16:
        p_chemise = prob_map.get(ClothingType.CHEMISE.value, 0.0)
        p_veste = prob_map.get(ClothingType.VESTE.value, 0.0)
        if placket >= 1.85 and collar >= 0.05 and p_chemise >= 0.12 and p_chemise >= p_veste:
            final_cat = ClothingType.CHEMISE.value
            final_conf = max(confidence, p_chemise, 0.56)
            rule_applied = f"short_coat_shirt(ar={g_ar:.2f},plk={placket:.2f})->Chemise"
        elif p_veste >= 0.14 or open_contrast >= 0.22:
            final_cat = ClothingType.VESTE.value
            final_conf = max(confidence, p_veste, 0.56)
            rule_applied = f"short_coat_jacket(ar={g_ar:.2f},open={open_contrast:.2f})->Veste"
    elif (
        final_cat in (ClothingType.VESTE.value, ClothingType.CHEMISE.value)
        and g_ar >= 1.42
        and lower_split < 0.10
        and prob_map.get(ClothingType.MANTEAU.value, 0.0) >= 0.14
        and confidence < 0.65
    ):
        final_cat = ClothingType.MANTEAU.value
        final_conf = max(confidence, prob_map.get(ClothingType.MANTEAU.value, 0.58))
        rule_applied = f"long_outerwear(ar={g_ar:.2f})->Manteau"
    elif (
        final_cat in (ClothingType.MANTEAU.value, ClothingType.VESTE.value, ClothingType.PULL.value)
        and confidence < 0.55
        and placket >= 2.25
        and collar >= 0.05
        and prob_map.get(ClothingType.CHEMISE.value, 0.0) >= 0.15
    ):
        final_cat = ClothingType.CHEMISE.value
        final_conf = max(confidence, prob_map.get(ClothingType.CHEMISE.value, 0.54))
        rule_applied = f"shirt_placket(plk={placket:.2f},col={collar:.2f})->Chemise"

    # 6. Distinction Sweat (capuche proéminente au sommet + épaules larges) vs Pull/Manteau
    elif (
        final_cat in (ClothingType.PULL.value, ClothingType.TSHIRT.value, ClothingType.MANTEAU.value)
        and confidence < 0.55
        and 0.22 <= hood_peak <= 0.58
        and 0.90 <= g_ar <= 1.38
        and prob_map.get(ClothingType.SWEAT.value, 0.0) >= 0.14
    ):
        final_cat = ClothingType.SWEAT.value
        final_conf = max(confidence, prob_map.get(ClothingType.SWEAT.value, 0.55))
        rule_applied = f"hoodie_crown(hood={hood_peak:.2f},ar={g_ar:.2f})->Sweat"

    # 7. Distinction Chapeau vs Chaussures/Sac (dôme symétrique à base large)
    elif (
        final_cat in (ClothingType.BASKETS.value, ClothingType.CHAUSSURES_VILLE.value, ClothingType.SAC.value)
        and g_ar <= 0.85
        and horiz_sym >= 0.80
        and solidity >= 0.78
        and ul_ratio <= 0.88
        and crown_conv >= 0.55
        and top_hole < 0.20
        and prob_map.get(ClothingType.CHAPEAU.value, 0.0) >= 0.12
    ):
        final_cat = ClothingType.CHAPEAU.value
        final_conf = max(confidence, prob_map.get(ClothingType.CHAPEAU.value, 0.58))
        rule_applied = f"hat_dome(ar={g_ar:.2f},sym={horiz_sym:.2f},ul={ul_ratio:.2f})->Chapeau"

    # 8. Chaussure basse horizontale classée Bottes -> Baskets
    elif final_cat == ClothingType.BOTTES.value and g_ar < 0.78:
        final_cat = ClothingType.BASKETS.value
        rule_applied = f"low_cut_shoe(ar={g_ar:.2f})->Baskets"

    # 9. Profil de basket clairement horizontal et asymétrique mal classé avec faible confiance
    elif (
        final_cat not in (
            ClothingType.BASKETS.value,
            ClothingType.CHAUSSURES_VILLE.value,
            ClothingType.BOTTES.value,
            ClothingType.CHAPEAU.value,
            ClothingType.SAC.value,
        )
        and g_ar <= 0.55
        and horiz_sym < 0.78
        and confidence < 0.55
    ):
        final_cat = ClothingType.BASKETS.value
        final_conf = max(confidence, 0.70)
        rule_applied = f"horizontal_shoe_profile(ar={g_ar:.2f},sym={horiz_sym:.2f})->Baskets"

    # 10. Respect strict du genre HOMME
    if is_homme and final_cat in FEMME_ONLY_TYPES:
        final_cat = normalize_clothing_type(final_cat, user_genre="HOMME")
        rule_applied = f"genre_homme_filter->{final_cat}"

    return final_cat, final_conf, rule_applied


def predict_clothing_category(
    image_path: str,
    user_genre: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Pipeline unifiée et diagnostiquée de prédiction IA Wearia :
    1. Prétraitement unique : lecture RGB avec EXIF + segmentation vêtement (bbox, masque interne, garment_ar)
    2. Extraction couleur dominante CIELAB + HSV sur le cœur du vêtement (indépendante du type)
    3. Active Learning v2 strict (correspondance conjointe HOG + histogramme LAB + vignette)
    4. Modèle ML (RandomForest + StandardScaler) sur 1784 descripteurs canoniques (filtré par genre)
    5. Raffinement structurel conservateur sur la géométrie réelle du vêtement
    6. Normalisation canonique + logs complets de diagnostic
    """
    filename = Path(image_path).name

    # ── 1. Chargement RGB + EXIF & Segmentation unique ───────────────────────
    img_rgb, img_meta = load_image_rgb(image_path)
    if img_rgb is None:
        fallback_cat = ClothingType.TSHIRT.value
        fallback_col = ClothingColor.NOIR.value
        attrs = infer_clothing_attributes(fallback_cat, fallback_col)
        logger.warning(f"[AI-DIAG] file={filename} | Impossible de lire l'image -> repli {fallback_cat}/{fallback_col}")
        return {
            "category": fallback_cat,
            "color": fallback_col,
            "color_hex": STANDARD_COLORS[fallback_col],
            "confidence": 0.50,
            "learned_type_id": None,
            "learned_color_id": None,
            **attrs,
        }

    seg = segment_garment(img_rgb, max_side=224)
    metrics = extract_structural_metrics(seg)

    # ── 2. Extraction couleur dominante (indépendante du type) ───────────────
    color_info = detect_dominant_color(image_path, segmentation=seg)
    color_name = normalize_clothing_color(color_info["name"])
    color_hex = STANDARD_COLORS.get(color_name, color_info["hex"])

    # ── 3. Active Learning v2 (correspondance stricte multi-modale) ──────────
    learned_match = ActiveLearningManager.find_matching_memory(
        image_path, segmentation=seg
    )
    if learned_match is not None:
        matched_sample, sim = learned_match
        final_category = normalize_clothing_type(matched_sample["category"], user_genre=user_genre)
        confidence = min(0.98, max(0.90, sim))
        learned_type_id = matched_sample.get("type_id")
        learned_color_id = matched_sample.get("color_id")
        if matched_sample.get("color"):
            color_name = normalize_clothing_color(matched_sample["color"])
            color_hex = STANDARD_COLORS.get(color_name, color_hex)

        attrs = infer_clothing_attributes(final_category, color_name)
        logger.info(
            f"[AI-DIAG] file={filename} | source=ACTIVE_LEARNING(sim={sim:.3f}) | "
            f"type='{final_category}' | color='{color_name}' | conf={confidence:.2f}"
        )
        return {
            "category": final_category,
            "color": color_name,
            "color_hex": color_hex,
            "confidence": round(confidence, 2),
            "learned_type_id": learned_type_id,
            "learned_color_id": learned_color_id,
            **attrs,
        }

    # ── 4. Inférence ML (RandomForest + StandardScaler) ──────────────────────
    raw_category = ClothingType.TSHIRT.value
    raw_confidence = 0.50
    prob_map: Dict[str, float] = {}
    top3_str = "[]"

    model, scaler = get_loaded_models()
    if model is not None and scaler is not None:
        try:
            features = extract_advanced_features(img_rgb, segmentation=seg, input_is_bgr=False)
            expected_dim = getattr(scaler, "n_features_in_", FEATURE_DIM)
            if features.shape[1] != expected_dim:
                logger.error(
                    f"[AI-DIAG] Incompatibilité dimension features ({features.shape[1]} != {expected_dim}). "
                    "Relancez train_model.py."
                )
            else:
                scaled = scaler.transform(features)
                if hasattr(model, "predict_proba"):
                    probas = model.predict_proba(scaled)[0]
                    classes = [normalize_clothing_type(str(c)) for c in model.classes_]

                    # Agréger probabilités par classe canonique
                    for cls_name, p in zip(classes, probas):
                        prob_map[cls_name] = prob_map.get(cls_name, 0.0) + float(p)

                    # Filtrer les classes FEMME-only si compte HOMME
                    candidate_probs = {
                        k: v for k, v in prob_map.items()
                        if not (user_genre and user_genre.upper() == "HOMME" and k in FEMME_ONLY_TYPES)
                    }
                    if not candidate_probs:
                        candidate_probs = prob_map

                    ranked: List[Tuple[str, float]] = sorted(
                        candidate_probs.items(), key=lambda x: x[1], reverse=True
                    )
                    raw_category, raw_confidence = ranked[0]
                    top3_str = ", ".join(f"{c}:{p:.2f}" for c, p in ranked[:3])
                else:
                    pred_class = str(model.predict(scaled)[0])
                    raw_category = normalize_clothing_type(pred_class, user_genre=user_genre)
                    raw_confidence = 0.78
                    prob_map = {raw_category: raw_confidence}
                    top3_str = f"{raw_category}:{raw_confidence:.2f}"
        except Exception as e:
            logger.error(f"[AI-DIAG] Erreur inférence ML : {e}")
    else:
        logger.warning("[AI-DIAG] Modèle ML non disponible.")

    # ── 5. Raffinement structurel conservateur ───────────────────────────────
    refined_category, final_confidence, rule_applied = _refine_prediction_structurally(
        raw_category=raw_category,
        confidence=raw_confidence,
        prob_map=prob_map,
        metrics=metrics,
        color_name=color_name,
        user_genre=user_genre,
    )
    final_category = normalize_clothing_type(refined_category, user_genre=user_genre)

    # ── 6. Attributs + Logs de diagnostic clairs ─────────────────────────────
    attrs = infer_clothing_attributes(final_category, color_name)

    logger.info(
        f"[AI-DIAG] file={filename} genre={user_genre} | orig={img_meta.get('orig_shape')} exif={img_meta.get('exif_orientation')} "
        f"| seg(ar={seg.garment_ar:.2f}, fg={seg.fg_ratio:.2f}, split={metrics['lower_split_ratio']:.2f}, "
        f"notch={metrics.get('short_leg_notch', 0.0):.2f}, denim={metrics.get('denim_blue_ratio', 0.0):.2f}, "
        f"plk={metrics['placket_ratio']:.2f}, hood={metrics.get('hood_peak_ratio', 0.0):.2f}, hole={metrics.get('top_hole_ratio', 0.0):.2f}) "
        f"| color(rgb={color_info.get('raw_rgb')}, lab={color_info.get('raw_lab')}) -> '{color_name}' "
        f"| ml_raw='{raw_category}'({raw_confidence:.2f}) top3=[{top3_str}] | rule={rule_applied} "
        f"| FINAL='{final_category}' / '{color_name}' (conf={final_confidence:.2f})"
    )

    return {
        "category": final_category,
        "color": color_name,
        "color_hex": color_hex,
        "confidence": round(final_confidence, 2),
        "learned_type_id": None,
        "learned_color_id": None,
        "raw_category": raw_category,
        "raw_confidence": round(raw_confidence, 2),
        "rule_applied": rule_applied,
        **attrs,
    }
