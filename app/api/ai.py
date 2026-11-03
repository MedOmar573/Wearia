import os
import uuid
import shutil
from pathlib import Path
from fastapi import APIRouter, Depends, UploadFile, File, HTTPException, status
from sqlalchemy.orm import Session
from app.database.connection import get_db
from app.api.deps import get_current_user
from app.models.user import Utilisateur
from app.models.referentials import Categorie, TypeVetement, Couleur
from app.schemas.ai import ClassifyResponse
from app.ai.predict import predict_clothing_category
from app.core.config import settings

router = APIRouter(prefix="/ai", tags=["Intelligence Artificielle"])

@router.post("/classify", response_model=ClassifyResponse)
async def classify_clothing_image(
    file: UploadFile = File(...),
    current_user: Utilisateur = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Analyse une photo de vêtement (UC01) :
    1. Enregistre le fichier dans le dossier uploads/
    2. Détecte la couleur dominante (OpenCV)
    3. Extrait les caractéristiques HOG et prédit la catégorie via KNN (scikit-learn)
    4. Retourne la catégorie prédite, la couleur, la confiance et l'URL de l'image.
    """
    # Vérification de l'extension
    ext = Path(file.filename).suffix.lower()
    if ext not in [".jpg", ".jpeg", ".png", ".webp"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Format d'image non supporté. Veuillez envoyer un fichier JPG, PNG ou WebP."
        )

    # Nom de fichier unique pour éviter les collisions
    unique_filename = f"{uuid.uuid4()}{ext}"
    file_path = settings.UPLOAD_DIR / unique_filename

    try:
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erreur lors de la sauvegarde de l'image : {str(e)}"
        )

    # Prédiction par le modèle IA et OpenCV
    prediction = predict_clothing_category(str(file_path))

    # Recherche directe du TYPE DE VÊTEMENT (TypeVetement) pour sélection automatique dans l'app
    type_match = db.query(TypeVetement).filter(TypeVetement.nom.ilike(f"%{prediction['category']}%")).first()
    if not type_match:
        cat_lower = prediction['category'].lower()
        if "pull" in cat_lower or "tricot" in cat_lower:
            type_match = db.query(TypeVetement).filter(TypeVetement.nom == "Pull").first()
        elif "chemise" in cat_lower:
            type_match = db.query(TypeVetement).filter(TypeVetement.nom == "Chemise").first()
        elif "t-shirt" in cat_lower or "tshirt" in cat_lower:
            type_match = db.query(TypeVetement).filter(TypeVetement.nom == "T-Shirt").first()
        elif "veste" in cat_lower or "blazer" in cat_lower:
            type_match = db.query(TypeVetement).filter(TypeVetement.nom == "Veste").first()
        elif "jean" in cat_lower:
            type_match = db.query(TypeVetement).filter(TypeVetement.nom == "Jean").first()
        elif "bas" in cat_lower or "pantalon" in cat_lower:
            type_match = db.query(TypeVetement).filter(TypeVetement.nom == "Pantalon").first()
        else:
            type_match = db.query(TypeVetement).first()

    color_match = db.query(Couleur).filter(Couleur.nom.ilike(f"%{prediction['color']}%")).first()
    if not color_match:
        color_match = db.query(Couleur).filter(Couleur.nom == "Noir").first()

    image_url = f"/uploads/{unique_filename}"

    return ClassifyResponse(
        category=prediction["category"],
        color=prediction["color"],
        confidence=prediction["confidence"],
        image_url=image_url,
        color_hex=prediction.get("color_hex"),
        suggested_type_id=type_match.id if type_match else 4,
        suggested_color_id=color_match.id if color_match else 1,
        name=prediction.get("name"),
        matiere=prediction.get("matiere"),
        coupe=prediction.get("coupe"),
        saison=prediction.get("saison"),
        est_thermique=prediction.get("est_thermique"),
        est_impermeable=prediction.get("est_impermeable"),
        style_id=prediction.get("style_id"),
        style_name=prediction.get("style_name")
    )

