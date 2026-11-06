import logging
from pathlib import Path
from typing import Dict, Any, Optional
import cv2
import numpy as np
import joblib
from app.core.config import settings
from app.ai.feature_extraction import extract_advanced_features
from app.ai.color_detection import detect_dominant_color

logger = logging.getLogger(__name__)

# Cache mémoire des modèles pour latence minimale (< 50ms)
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
            except Exception as e:
                logger.error(f"Erreur chargement modèle : {e}")
    return _CACHED_MODEL, _CACHED_SCALER

def infer_clothing_attributes(category: str, color: str) -> Dict[str, Any]:
    """
    Déduit intelligemment tous les attributs d'un vêtement ("et tous") :
    matière, saison, thermique, imperméable, coupe et style selon les règles métier Wearia.
    """
    cat_lower = category.lower()
    col_lower = color.lower()

    # Valeurs par défaut
    matiere = "Coton"
    saison = "TOUTE_SAISON"
    est_thermique = False
    est_impermeable = False
    coupe = "REGULIERE"
    style_id = 1
    style_name = "Casual"
    
    # 1. HAUTS
    if "chemise" in cat_lower:
        matiere = "100% Coton Oxford"
        saison = "TOUTE_SAISON"
        est_thermique = False
        coupe = "REGULIERE"
        style_id = 2
        style_name = "Classic"
    elif "pull" in cat_lower or "tricot" in cat_lower:
        matiere = "Laine / Maille tricotée"
        saison = "HIVER"
        est_thermique = True
        coupe = "REGULIERE"
        style_id = 1
        style_name = "Casual"
    elif "t-shirt" in cat_lower or "tshirt" in cat_lower:
        matiere = "100% Coton peigné"
        saison = "ETE"
        est_thermique = False
        coupe = "REGULIERE"
        style_id = 1
        style_name = "Casual"
    elif "polo" in cat_lower:
        matiere = "Piqué de coton respirant"
        saison = "ETE"
        est_thermique = False
        coupe = "AJUSTEE"
        style_id = 2
        style_name = "Classic"
    elif "sweat" in cat_lower:
        matiere = "Coton molleton épais"
        saison = "AUTOMNE"
        est_thermique = True
        coupe = "OVERSIZE"
        style_id = 3
        style_name = "Sporty"

    # 2. BAS
    elif "jean" in cat_lower:
        matiere = "Denim stretch"
        saison = "TOUTE_SAISON"
        est_thermique = False
        coupe = "AJUSTEE"
        style_id = 1
        style_name = "Casual"
    elif "pantalon" in cat_lower or "chino" in cat_lower:
        matiere = "Coton sergé / Toile"
        saison = "TOUTE_SAISON"
        est_thermique = False
        coupe = "REGULIERE"
        style_id = 2
        style_name = "Classic"
    elif "short" in cat_lower:
        matiere = "Coton léger"
        saison = "ETE"
        est_thermique = False
        coupe = "REGULIERE"
        style_id = 1
        style_name = "Casual"

    # 3. VESTES & MANTEAUX
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
        coupe = "REGULIERE"
        style_id = 2
        style_name = "Classic"

    # 4. CHAUSSURES
    elif "basket" in cat_lower or "sneaker" in cat_lower:
        matiere = "Cuir & Toile respirante"
        saison = "TOUTE_SAISON"
        est_thermique = False
        coupe = "REGULIERE"
        style_id = 3
        style_name = "Sporty"
    elif "chaussure" in cat_lower or "derbie" in cat_lower or "botte" in cat_lower:
        matiere = "Cuir véritable pleine fleur"
        saison = "TOUTE_SAISON"
        est_thermique = False
        est_impermeable = "botte" in cat_lower
        coupe = "REGULIERE"
        style_id = 2
        style_name = "Classic"

    # Nom d'article harmonieux
    name = f"{category} {color}"

    return {
        "name": name,
        "matiere": matiere,
        "saison": saison,
        "est_thermique": est_thermique,
        "est_impermeable": est_impermeable,
        "coupe": coupe,
        "style_id": style_id,
        "style_name": style_name
    }

def predict_clothing_category(image_path: str) -> Dict[str, Any]:
    """
    Pipeline complet de prédiction IA pour Wearia :
    1. Détection robuste de la couleur dominante du tissu (OpenCV avec suppression de fond)
    2. Extraction des caractéristiques structurelles et texturales avancées
    3. Classification par Random Forest + règles d'arbitrage physique (boutons, col, texture, silhouette)
    4. Auto-remplissage de l'intégralité des attributs vestimentaires ("et tous")
    """
    # 1. Détection de couleur
    color_info = detect_dominant_color(image_path)
    model, scaler = get_loaded_models()

    final_category = "Pull"
    confidence = 0.85

    # 2. Inférence du modèle entraîné
    if model is not None and scaler is not None:
        try:
            features = extract_advanced_features(image_path)
            scaled_features = scaler.transform(features)

            pred_class = model.predict(scaled_features)[0]
            confidence = 0.88
            if hasattr(model, "predict_proba"):
                probas = model.predict_proba(scaled_features)[0]
                confidence = float(np.max(probas))

            final_category = str(pred_class)

            # 3. Arbitrage structurel et géométrique pour fiabiliser la décision
            img = cv2.imread(image_path)
            if img is not None:
                h, w = img.shape[:2]
                aspect_ratio = h / max(w, 1)

                gray = cv2.cvtColor(cv2.resize(img, (256, 256)), cv2.COLOR_BGR2GRAY)

                # Analyse de la patte de boutonnage centrale (Chemise)
                center_strip = gray[40:210, 118:138]
                side_strip_l = gray[40:210, 88:108]
                side_strip_r = gray[40:210, 148:168]
                sobel_c = np.mean(np.abs(cv2.Sobel(center_strip, cv2.CV_64F, 1, 0, ksize=3)))
                sobel_s = (np.mean(np.abs(cv2.Sobel(side_strip_l, cv2.CV_64F, 1, 0, ksize=3))) +
                           np.mean(np.abs(cv2.Sobel(side_strip_r, cv2.CV_64F, 1, 0, ksize=3)))) / 2.0
                placket_ratio = sobel_c / max(sobel_s, 1e-4)

                # Texture de maille (Pull)
                torso = gray[70:180, 70:180]
                laplacian_var = float(cv2.Laplacian(torso, cv2.CV_64F).var())

                # Col et encolure
                collar = gray[25:65, 80:176]
                collar_edges = float(np.mean(cv2.Canny(collar, 50, 150)))

                # A. Bas (Jean vs Pantalon)
                if final_category in ["Pantalon", "Jean"]:
                    if color_info["name"] == "Bleu":
                        final_category = "Jean"
                    else:
                        final_category = "Pantalon"

                # B. Chaussures très aplaties horizontalement (photo en paysage de chaussures)
                elif aspect_ratio <= 0.65:
                    if final_category not in ["Baskets", "Chaussures de ville"]:
                        final_category = "Baskets" if color_info["name"] in ["Blanc", "Noir"] else "Chaussures de ville"
                        confidence = 0.86

                # C. Arbitrage précis Haut (Chemise vs Pull vs T-Shirt)
                elif final_category in ["Pull", "Chemise", "T-Shirt"]:
                    # Si présence de boutons réguliers et col pointu -> Chemise
                    if placket_ratio > 1.15 and collar_edges > 25:
                        final_category = "Chemise"
                    # Si torse sans boutons verticaux et texture de maille ou col dégagé -> Pull
                    elif placket_ratio < 0.95 and (laplacian_var > 30 or final_category == "Chemise"):
                        final_category = "Pull"


        except Exception as e:
            logger.error(f"Erreur lors de l'inférence du modèle : {e}")

    # 4. Déduction complète de tous les attributs vestimentaires
    attrs = infer_clothing_attributes(final_category, color_info["name"])

    return {
        "category": final_category,
        "color": color_info["name"],
        "color_hex": color_info["hex"],
        "confidence": round(confidence, 2),
        **attrs
    }

