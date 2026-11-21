import logging
from pathlib import Path
from typing import Dict, Any, Optional
import cv2
import numpy as np
import joblib
from app.core.config import settings
from app.ai.feature_extraction import extract_advanced_features
from app.ai.color_detection import detect_dominant_color, STANDARD_COLORS
from app.ai.feedback_learning import ActiveLearningManager

logger = logging.getLogger(__name__)

# Cache mémoire des modèles
_CACHED_MODEL = None
_CACHED_SCALER = None


def get_loaded_models():
    global _CACHED_MODEL, _CACHED_SCALER
    if _CACHED_MODEL is None or _CACHED_SCALER is None:
        model_path = settings.AI_MODELS_DIR / "knn_model.joblib"
        scaler_path = settings.AI_MODELS_DIR / "scaler.joblib"
        if model_path.exists() and scaler_path.exists():
            try:
                _CACHED_MODEL = joblib.load(model_path)
                _CACHED_SCALER = joblib.load(scaler_path)
                logger.info("Modèles KNN + Scaler chargés en mémoire.")
            except Exception as e:
                logger.error(f"Erreur chargement modèle : {e}")
    return _CACHED_MODEL, _CACHED_SCALER


def infer_clothing_attributes(category: str, color: str) -> Dict[str, Any]:
    """Déduit matière, saison, coupe et style selon la catégorie détectée."""
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
        style_id = 2; style_name = "Classic"
    elif "pull" in cat_lower or "tricot" in cat_lower:
        matiere = "Laine / Maille tricotée"
        saison = "HIVER"; est_thermique = True
    elif "t-shirt" in cat_lower or "tshirt" in cat_lower:
        matiere = "100% Coton peigné"
        saison = "ETE"
    elif "polo" in cat_lower:
        matiere = "Piqué de coton respirant"
        saison = "ETE"; coupe = "AJUSTEE"
        style_id = 2; style_name = "Classic"
    elif "sweat" in cat_lower:
        matiere = "Coton molleton"
        saison = "AUTOMNE"; est_thermique = True
        coupe = "OVERSIZE"; style_id = 3; style_name = "Sporty"
    elif "robe" in cat_lower:
        matiere = "Soie / Viscose fluide"
        saison = "ETE"; coupe = "AJUSTEE"
        style_id = 5; style_name = "Elegant"
    elif "jupe" in cat_lower:
        matiere = "Coton / Denim / Plissé"
        saison = "ETE"; coupe = "AJUSTEE"
    elif "jean" in cat_lower:
        matiere = "Denim stretch"; coupe = "AJUSTEE"
    elif "pantalon" in cat_lower or "chino" in cat_lower:
        matiere = "Coton sergé / Toile"
        style_id = 2; style_name = "Classic"
    elif "short" in cat_lower:
        matiere = "Coton léger"; saison = "ETE"
    elif "veste" in cat_lower or "blazer" in cat_lower:
        matiere = "Laine mélangée structurée"
        saison = "AUTOMNE"; est_thermique = True
        coupe = "AJUSTEE"; style_id = 5; style_name = "Elegant"
    elif "manteau" in cat_lower:
        matiere = "Laine & Cachemire"
        saison = "HIVER"; est_thermique = True; est_impermeable = True
        style_id = 2; style_name = "Classic"
    elif "botte" in cat_lower:
        matiere = "Cuir véritable / Daim"
        saison = "HIVER"; est_thermique = True; est_impermeable = True
        coupe = "AJUSTEE"; style_id = 2; style_name = "Classic"
    elif "basket" in cat_lower or "sneaker" in cat_lower:
        matiere = "Cuir & Toile respirante"; style_id = 3; style_name = "Sporty"
    elif "chaussure" in cat_lower or "derbie" in cat_lower:
        matiere = "Cuir véritable"; style_id = 2; style_name = "Classic"
    elif "sac" in cat_lower:
        matiere = "Cuir de maroquinerie"

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


# ─────────────────────────────────────────────────────────────
#  RÈGLES STRUCTURELLES AMÉLIORÉES
# ─────────────────────────────────────────────────────────────

def _load_gray(image_path: str, size: int = 256):
    img = cv2.imread(image_path)
    if img is None:
        return None, None, None
    h, w = img.shape[:2]
    gray = cv2.cvtColor(cv2.resize(img, (size, size)), cv2.COLOR_BGR2GRAY)
    return img, gray, h / max(w, 1)


def _score_placket(gray: np.ndarray) -> float:
    """Score de patte de boutonnage (élevé = Chemise)."""
    h, w = gray.shape
    cx = w // 2
    strip_w = max(int(w * 0.08), 8)
    center = gray[int(h*0.25):int(h*0.85), cx-strip_w:cx+strip_w]
    left   = gray[int(h*0.25):int(h*0.85), cx-strip_w*3:cx-strip_w]
    right  = gray[int(h*0.25):int(h*0.85), cx+strip_w:cx+strip_w*3]
    s_c = np.mean(np.abs(cv2.Sobel(center, cv2.CV_64F, 1, 0, ksize=3)))
    s_s = (np.mean(np.abs(cv2.Sobel(left,  cv2.CV_64F, 1, 0, ksize=3))) +
           np.mean(np.abs(cv2.Sobel(right,  cv2.CV_64F, 1, 0, ksize=3)))) / 2.0
    return float(s_c / max(s_s, 1e-4))


def _score_collar(gray: np.ndarray) -> float:
    """Score de col (élevé = Chemise ou Veste avec col pointu)."""
    h, w = gray.shape
    collar = gray[int(h*0.05):int(h*0.25), int(w*0.25):int(w*0.75)]
    return float(np.mean(cv2.Canny(collar, 40, 120)))


def _score_knit_texture(gray: np.ndarray) -> float:
    """Score de maille tricotée (élevé = Pull)."""
    h, w = gray.shape
    torso = gray[int(h*0.3):int(h*0.75), int(w*0.25):int(w*0.75)]
    return float(cv2.Laplacian(torso, cv2.CV_64F).var())


def _score_hem_line(gray: np.ndarray) -> float:
    """Score de ligne d'ourlet basse (élevé = Robe ou Jupe longue)."""
    h, w = gray.shape
    lower = gray[int(h*0.65):, :]
    return float(np.mean(np.abs(cv2.Sobel(lower, cv2.CV_64F, 0, 1, ksize=3))))


def _has_denim_texture(image_path: str) -> bool:
    """
    Teste si la texture tissu ressemble à du denim (trame croisée diagonale).
    Utilise la variance de gradient orienté dans la zone du bassin/cuisse.
    """
    try:
        img = cv2.imread(image_path)
        if img is None:
            return False
        small = cv2.resize(img, (128, 128))
        gray = cv2.cvtColor(small, cv2.COLOR_BGR2GRAY)
        patch = gray[30:95, 20:108]  # zone cuisse/bassin
        # Sobel diagonal (45°) → signature du sergé denim
        sx = cv2.Sobel(patch, cv2.CV_64F, 1, 0, ksize=3)
        sy = cv2.Sobel(patch, cv2.CV_64F, 0, 1, ksize=3)
        diag = sx + sy
        return float(np.std(diag)) > 8.0
    except Exception:
        return False


def _arbitrage_hauts(
    pred: str,
    placket: float,
    collar: float,
    knit: float,
    color_name: str,
) -> str:
    """
    Arbitrage précis entre T-Shirt, Chemise, Pull, Polo, Sweat.
    """
    # Chemise : patte de boutonnage visible + col structuré
    if placket > 1.20 and collar > 22:
        return "Chemise"
    # Pull en maille : texture fortement irrégulière
    if knit > 180:
        return "Pull"
    # Polo : texture intermédiaire + col visible
    if 60 < knit <= 180 and collar > 15:
        return "Polo"
    # Sweat : texture lisse mais masse fibreuse (faible variance, épaisseur)
    if knit <= 60 and pred in ("Pull", "Sweat"):
        return "Sweat"
    # T-Shirt par défaut
    return "T-Shirt"


def _arbitrage_bas(
    pred: str,
    color_name: str,
    image_path: str,
    aspect_ratio: float,
) -> str:
    """
    Arbitrage Jean / Pantalon / Short / Jupe selon couleur et texture.
    """
    # Jupe : silhouette large en bas (peu ou pas de jambe divisée)
    if pred == "Jupe":
        return "Jupe"
    # Jean : couleur bleue + texture denim
    if color_name in ("Bleu", "Bleu Marine") and _has_denim_texture(image_path):
        return "Jean"
    # Short : aspect ratio bas (image large et courte)
    if aspect_ratio < 0.75:
        return "Short"
    # Pantalon sinon
    return "Pantalon"


def _arbitrage_chaussures(
    pred: str,
    aspect_ratio: float,
    color_name: str,
    knit: float,
) -> str:
    """
    Arbitrage Baskets / Chaussures de ville / Bottes / Sandales.
    """
    # Bottes : tige haute → aspect_ratio élevé (image verticale)
    if aspect_ratio >= 0.90:
        return "Bottes"
    # Baskets : couleurs sportives, formes horizontales
    if color_name in ("Blanc", "Noir", "Gris", "Rouge") and aspect_ratio < 0.65:
        return "Baskets"
    # Chaussures de ville sinon
    return "Chaussures de ville"


# ─────────────────────────────────────────────────────────────
#  PIPELINE PRINCIPALE DE PRÉDICTION
# ─────────────────────────────────────────────────────────────

def predict_clothing_category(image_path: str) -> Dict[str, Any]:
    """
    Pipeline améliorée de prédiction IA Wearia :
    1. Détection couleur robuste (HSV + K-Means k=4 + GrabCut)
    2. Active Learning : mémoire des corrections utilisateur
    3. Modèle ML (KNN/RF + scaler) sur descripteurs HOG 1776-dim
    4. Post-arbitrage structurel multi-critères amélioré
       (patte boutonnage, col, maille, texture denim, ratio)
    5. Remplissage complet des attributs vestimentaires
    """
    # ── 1. Couleur dominante ──────────────────────────────────────────────────
    color_info = detect_dominant_color(image_path)
    color_name = color_info["name"]

    final_category = "T-Shirt"
    confidence = 0.75
    learned_type_id = None
    learned_color_id = None

    # ── 2. Active Learning (corrections mémorisées) ───────────────────────────
    learned_match = ActiveLearningManager.find_matching_memory(image_path)
    if learned_match is not None:
        matched_sample, sim = learned_match
        final_category = matched_sample["category"]
        confidence = min(0.98, max(0.90, sim))
        learned_type_id = matched_sample.get("type_id")
        learned_color_id = matched_sample.get("color_id")
        if matched_sample.get("color"):
            color_info["name"] = matched_sample["color"]
            color_name = color_info["name"]
        logger.info(f"[ActiveLearning] Prédiction mémorisée : {final_category} (sim={sim:.2f})")
        attrs = infer_clothing_attributes(final_category, color_name)
        return {
            "category": final_category,
            "color": color_name,
            "color_hex": color_info["hex"],
            "confidence": round(confidence, 2),
            "learned_type_id": learned_type_id,
            "learned_color_id": learned_color_id,
            **attrs,
        }

    # ── 3. Modèle ML ─────────────────────────────────────────────────────────
    model, scaler = get_loaded_models()
    if model is not None and scaler is not None:
        try:
            features = extract_advanced_features(image_path)
            scaled = scaler.transform(features)
            pred_class = model.predict(scaled)[0]
            final_category = str(pred_class)
            if hasattr(model, "predict_proba"):
                probas = model.predict_proba(scaled)[0]
                confidence = float(np.max(probas))
                # Si confiance faible (<60%), ne pas utiliser la prédiction aveuglément
                if confidence < 0.60:
                    logger.warning(
                        f"[ML] Confiance faible ({confidence:.0%}) pour {final_category}. "
                        "Post-arbitrage renforcé."
                    )
            else:
                confidence = 0.82
        except Exception as e:
            logger.error(f"[ML] Erreur inférence : {e}")
    else:
        logger.warning("[ML] Modèle non disponible. Utilisation post-arbitrage seul.")

    # ── 4. Post-arbitrage structurel multi-critères ───────────────────────────
    img, gray, aspect_ratio = _load_gray(image_path)

    if gray is not None:
        placket = _score_placket(gray)
        collar  = _score_collar(gray)
        knit    = _score_knit_texture(gray)
        hem     = _score_hem_line(gray)

        logger.debug(
            f"[Arbitrage] cat={final_category} AR={aspect_ratio:.2f} "
            f"placket={placket:.2f} collar={collar:.1f} knit={knit:.1f} hem={hem:.1f}"
        )

        # A. HAUTS (Chemise / Pull / Polo / Sweat / T-Shirt)
        if final_category in ("Pull", "Chemise", "T-Shirt", "Polo", "Sweat"):
            # Vérifier si silhouette très longue → Robe
            if aspect_ratio >= 1.40 and hem > 10:
                final_category = "Robe"
                confidence = max(confidence, 0.80)
            else:
                final_category = _arbitrage_hauts(
                    final_category, placket, collar, knit, color_name
                )

        # B. BAS (Jean / Pantalon / Short / Jupe)
        elif final_category in ("Pantalon", "Jean", "Short", "Jupe"):
            final_category = _arbitrage_bas(
                final_category, color_name, image_path, aspect_ratio
            )

        # C. CHAUSSURES (Baskets / Chaussures de ville / Bottes)
        elif final_category in ("Baskets", "Chaussures de ville", "Bottes"):
            final_category = _arbitrage_chaussures(
                final_category, aspect_ratio, color_name, knit
            )

        # D. Robe : re-vérifier (image verticale + ligne d'ourlet basse)
        elif final_category == "Robe":
            if aspect_ratio < 1.10 or hem < 5:
                # Probablement un Haut mal classifié
                final_category = _arbitrage_hauts(
                    "T-Shirt", placket, collar, knit, color_name
                )
                confidence = max(0.70, confidence - 0.10)

        # E. Veste / Blazer / Manteau : ratio intermédiaire + col visible
        elif final_category in ("Veste", "Blazer", "Manteau"):
            if aspect_ratio >= 1.30 and hem > 12:
                final_category = "Manteau"
            elif collar > 18 and placket > 1.0:
                final_category = "Veste"

        # F. Image très horizontale non classifiée comme Chaussures → forcer Baskets
        if aspect_ratio <= 0.55 and final_category not in (
            "Baskets", "Chaussures de ville", "Bottes", "Short"
        ):
            final_category = "Baskets"
            confidence = max(confidence, 0.78)

    # ── 5. Attributs vestimentaires complets ─────────────────────────────────
    attrs = infer_clothing_attributes(final_category, color_name)

    logger.info(
        f"[Prédiction] {final_category} | {color_name} | confiance={confidence:.0%}"
    )

    return {
        "category": final_category,
        "color": color_name,
        "color_hex": color_info["hex"],
        "confidence": round(confidence, 2),
        "learned_type_id": learned_type_id,
        "learned_color_id": learned_color_id,
        **attrs,
    }
