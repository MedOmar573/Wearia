import cv2
import numpy as np
import joblib
from pathlib import Path
import sys
sys.path.insert(0, r"c:\Users\DELL\Desktop\L3DSI\projet\Wearia\wearia_backend")

from app.core.config import settings
from app.ai.feature_extraction import extract_advanced_features
from app.ai.color_detection import detect_dominant_color

def smart_predict_clothing(image_path: str):
    img = cv2.imread(image_path)
    if img is None:
        return {"category": "Pull", "color": "Noir", "confidence": 0.5}

    h, w = img.shape[:2]
    aspect_ratio = h / max(w, 1)

    # 1. Couleur
    color_info = detect_dominant_color(image_path)

    # 2. Modèle ML (Random Forest 2730 images)
    model_path = settings.AI_MODELS_DIR / "knn_model.joblib"
    scaler_path = settings.AI_MODELS_DIR / "scaler.joblib"

    model = joblib.load(model_path)
    scaler = joblib.load(scaler_path)

    feats = extract_advanced_features(image_path)
    scaled = scaler.transform(feats)
    pred_class = model.predict(scaled)[0]
    probas = model.predict_proba(scaled)[0]
    class_idx = list(model.classes_).index(pred_class)
    conf = float(probas[class_idx])

    # 3. Descripteurs structurels deterministes
    # Analyse torse et col
    gray = cv2.cvtColor(cv2.resize(img, (256, 256)), cv2.COLOR_BGR2GRAY)
    
    # Colonne centrale (patte de boutonnage chemise)
    center_strip = gray[50:200, 118:138]
    side_strip_l = gray[50:200, 80:100]
    side_strip_r = gray[50:200, 156:176]
    
    sobel_c = np.mean(np.abs(cv2.Sobel(center_strip, cv2.CV_64F, 1, 0, ksize=3)))
    sobel_s = (np.mean(np.abs(cv2.Sobel(side_strip_l, cv2.CV_64F, 1, 0, ksize=3))) +
               np.mean(np.abs(cv2.Sobel(side_strip_r, cv2.CV_64F, 1, 0, ksize=3)))) / 2.0
    placket_ratio = sobel_c / max(sobel_s, 1e-5)

    # Texture de maille (tricot pull vs tissu plat)
    torso_patch = gray[80:180, 80:180]
    laplacian_var = float(cv2.Laplacian(torso_patch, cv2.CV_64F).var())

    # Decision hybride robuste :
    final_category = pred_class

    # A. Silhouette fortement allongee -> Pantalon ou Jean
    if aspect_ratio >= 1.45:
        if final_category in ["Chemise", "Pull", "T-Shirt", "Veste"]:
            final_category = "Jean" if color_info["name"] == "Bleu" else "Pantalon"
            conf = 0.88

    # B. Silhouette fortement aplatie horizontalement -> Chaussures
    elif aspect_ratio <= 0.65:
        if final_category not in ["Baskets", "Chaussures de ville"]:
            final_category = "Baskets" if color_info["name"] in ["Blanc", "Noir"] else "Chaussures de ville"
            conf = 0.86

    # C. Distinguer un Haut (Pull vs Chemise vs T-Shirt)
    elif final_category in ["Pull", "Chemise", "T-Shirt"]:
        # Si forte patte de boutonnage verticale continue -> Chemise
        if placket_ratio > 1.05 and conf < 0.70:
            final_category = "Chemise"
        # Si torse sans boutons et texture de tricot/maille -> Pull
        elif placket_ratio < 0.85 and laplacian_var > 15:
            final_category = "Pull"

    return {
        "category": final_category,
        "color": color_info["name"],
        "color_hex": color_info["hex"],
        "confidence": round(conf, 2)
    }

up = Path(r"c:\Users\DELL\Desktop\L3DSI\projet\Wearia\wearia_backend\uploads")
test_list = [
    "pull_maille_beige.jpg",
    "chemise_oxford_blanche.jpg",
    "tshirt_noir.jpg",
    "4f7fa19c-4042-47ff-8b0e-f70994641311.jpg",
    "ef46b243-d92e-42be-b0b3-fb4f06f57ad2.jpg",
    "bomber_noir.jpg",
    "pantalon_noir.jpg",
    "jean_slim_bleu.jpg",
    "baskets_blanches.jpg",
    "derbies_marron.jpg"
]

print(f"{'IMAGE':32} | {'CATEGORY':15} | {'COLOR':12} | {'CONF'}")
print("-" * 72)
for f in test_list:
    p = up / f
    if p.exists():
        r = smart_predict_clothing(str(p))
        print(f"{f:32} | {r['category']:15} | {r['color']:12} | {r['confidence']}")

