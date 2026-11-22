import logging
import shutil
import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, UploadFile, File, HTTPException, Query, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.database.connection import get_db
from app.api.deps import get_current_user
from app.models.clothing import Vetement
from app.models.user import Utilisateur
from app.models.referentials import TypeVetement, Couleur
from app.schemas.ai import ClassifyResponse
from app.ai.predict import predict_clothing_category
from app.ai.taxonomy import normalize_clothing_color, normalize_clothing_type
from app.core.config import settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/ai", tags=["Intelligence Artificielle"])


def _resolve_db_type(db: Session, category_name: str, user_genre: str | None) -> TypeVetement | None:
    """Résout un ClothingType canonique vers TypeVetement par correspondance exacte d'abord."""
    canonical = normalize_clothing_type(category_name, user_genre=user_genre)

    # 1. Correspondance exacte insensible à la casse (évite les faux matchs par sous-chaîne)
    exact = db.query(TypeVetement).filter(func.lower(TypeVetement.nom) == canonical.lower()).first()
    if exact:
        return exact

    # 2. Repli contrôlé par sous-chaîne puis défaut T-Shirt
    partial = db.query(TypeVetement).filter(TypeVetement.nom.ilike(f"%{canonical}%")).first()
    if partial:
        return partial

    return (
        db.query(TypeVetement).filter(func.lower(TypeVetement.nom) == "t-shirt").first()
        or db.query(TypeVetement).first()
    )


def _resolve_db_color(db: Session, color_name: str) -> Couleur | None:
    """
    Résout un ClothingColor canonique vers Couleur par correspondance EXACTE d'abord.
    Corrige notamment la collision 'Bleu' -> 'Bleu Marine' due au ilike('%Bleu%').
    """
    canonical = normalize_clothing_color(color_name)

    # 1. Correspondance exacte insensible à la casse
    exact = db.query(Couleur).filter(func.lower(Couleur.nom) == canonical.lower()).first()
    if exact:
        return exact

    # 2. Repli uniquement si la couleur canonique n'est pas encore présente en base
    partial = db.query(Couleur).filter(Couleur.nom.ilike(f"%{canonical}%")).first()
    if partial:
        return partial

    return (
        db.query(Couleur).filter(func.lower(Couleur.nom) == "noir").first()
        or db.query(Couleur).first()
    )


@router.post("/classify", response_model=ClassifyResponse)
async def classify_clothing_image(
    file: UploadFile = File(...),
    current_user: Utilisateur = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Analyse une photo de vêtement (UC01) :
    1. Enregistre le fichier dans le dossier uploads/
    2. Prétraitement unifié (EXIF, RGB, segmentation) + couleur dominante (CIELAB/HSV)
    3. Classification type de vêtement (ML + géométrie bbox + Active Learning v2)
    4. Mapping strict vers les référentiels PostgreSQL TypeVetement et Couleur.
    """
    ext = Path(file.filename or "upload.jpg").suffix.lower()
    if ext not in [".jpg", ".jpeg", ".png", ".webp"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Format d'image non supporté. Veuillez envoyer un fichier JPG, PNG ou WebP.",
        )

    unique_filename = f"{uuid.uuid4()}{ext}"
    file_path = settings.UPLOAD_DIR / unique_filename

    try:
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erreur lors de la sauvegarde de l'image : {str(e)}",
        )

    user_genre = current_user.genre.value if getattr(current_user, "genre", None) else None

    # Prédiction par la pipeline IA unifiée
    prediction = predict_clothing_category(str(file_path), user_genre=user_genre)

    canonical_category = normalize_clothing_type(prediction["category"], user_genre=user_genre)
    canonical_color = normalize_clothing_color(prediction["color"])

    type_match = _resolve_db_type(db, canonical_category, user_genre=user_genre)
    color_match = _resolve_db_color(db, canonical_color)

    suggested_type_id = prediction.get("learned_type_id") or (type_match.id if type_match else 2)
    suggested_color_id = prediction.get("learned_color_id") or (color_match.id if color_match else 1)

    logger.info(
        f"[AI-API] user={current_user.id}({user_genre}) file={unique_filename} | "
        f"raw_type='{prediction.get('raw_category', canonical_category)}' -> mapped_type='{canonical_category}' (db_id={suggested_type_id}, db_nom='{type_match.nom if type_match else None}') | "
        f"color='{canonical_color}' (db_id={suggested_color_id}, db_nom='{color_match.nom if color_match else None}') | "
        f"conf={prediction['confidence']}"
    )

    image_url = f"/uploads/{unique_filename}"

    return ClassifyResponse(
        category=canonical_category,
        color=canonical_color,
        confidence=prediction["confidence"],
        image_url=image_url,
        color_hex=color_match.codeHex if color_match else prediction.get("color_hex"),
        suggested_type_id=suggested_type_id,
        suggested_color_id=suggested_color_id,
        name=prediction.get("name") or f"{canonical_category} {canonical_color}",
        matiere=prediction.get("matiere"),
        coupe=prediction.get("coupe"),
        saison=prediction.get("saison"),
        est_thermique=prediction.get("est_thermique"),
        est_impermeable=prediction.get("est_impermeable"),
        style_id=prediction.get("style_id"),
        style_name=prediction.get("style_name"),
    )


@router.delete("/temp-upload", status_code=status.HTTP_200_OK)
def delete_temp_uploaded_image(
    image_url: str = Query(..., description="Chemin relatif /uploads/<uuid>.jpg de la photo temporaire"),
    current_user: Utilisateur = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Supprime une photo de test temporaire non enregistrée lorsqu'un utilisateur
    reprend une nouvelle photo de vêtement.
    Ne supprime jamais un fichier référencé par un vêtement existant en base.
    """
    filename = Path(image_url).name
    if not filename or filename != image_url.lstrip("/").split("/")[-1]:
        return {"deleted": False, "reason": "invalid_path"}

    # Sécurité : ne supprimer que des fichiers UUID générés par /ai/classify
    stem = Path(filename).stem
    try:
        uuid.UUID(stem)
    except ValueError:
        return {"deleted": False, "reason": "not_temp_upload"}

    normalized_url = f"/uploads/{filename}"
    still_used = db.query(Vetement).filter(Vetement.photoUrl == normalized_url).first()
    if still_used:
        return {"deleted": False, "reason": "referenced_in_wardrobe"}

    target_path = settings.UPLOAD_DIR / filename
    if target_path.exists() and target_path.is_file():
        try:
            target_path.unlink()
            logger.info(f"[AI-API] Photo temporaire supprimée : {filename} (user={current_user.id})")
            return {"deleted": True}
        except OSError as exc:
            logger.warning(f"[AI-API] Impossible de supprimer {filename} : {exc}")
            return {"deleted": False, "reason": "io_error"}
    return {"deleted": False, "reason": "not_found"}
