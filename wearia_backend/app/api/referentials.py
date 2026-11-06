from typing import List, Optional
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.database.connection import get_db
from app.models.referentials import Categorie, TypeVetement, Couleur, StyleVestimentaire
from app.models.enums import GenreCible
from app.schemas.referentials import (
    CategorieResponse, TypeVetementResponse, CouleurResponse, StyleVestimentaireResponse
)

router = APIRouter(prefix="/referentials", tags=["Référentiels"])

@router.get("/categories", response_model=List[CategorieResponse])
def get_categories(
    genre: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """
    Retourne la liste des catégories de vêtements (Haut, Bas, Robe, Veste, Chaussures, etc.).
    Si genre=HOMME, filtre les catégories purement féminines (ex: Robe).
    """
    categories = db.query(Categorie).all()
    if genre and genre.upper() == "HOMME":
        valid_cat_ids = [
            cid[0] for cid in db.query(TypeVetement.categorie_id).filter(
                (TypeVetement.genreCible == GenreCible.MIXTE) | 
                (TypeVetement.genreCible == GenreCible.HOMME)
            ).distinct().all()
        ]
        categories = [c for c in categories if c.id in valid_cat_ids]
    return categories

@router.get("/types", response_model=List[TypeVetementResponse])
def get_types_vetement(
    categorie_id: Optional[int] = None,
    genre: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """
    Retourne la liste des types de vêtements, filtrables par catégorie ou genre (BR: genreCible).
    """
    query = db.query(TypeVetement)
    if categorie_id:
        query = query.filter(TypeVetement.categorie_id == categorie_id)
    if genre:
        # Afficher types mixtes OU correspondant au genre demandé
        genre_upper = genre.upper()
        query = query.filter(
            (TypeVetement.genreCible == GenreCible.MIXTE) | 
            (TypeVetement.genreCible == genre_upper)
        )
    return query.all()

@router.get("/colors", response_model=List[CouleurResponse])
def get_colors(db: Session = Depends(get_db)):
    """
    Retourne la liste des couleurs disponibles.
    """
    return db.query(Couleur).all()

@router.get("/styles", response_model=List[StyleVestimentaireResponse])
def get_styles(db: Session = Depends(get_db)):
    """
    Retourne la liste des styles vestimentaires de référence.
    """
    return db.query(StyleVestimentaire).all()

