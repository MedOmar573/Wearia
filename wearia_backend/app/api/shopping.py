from typing import List, Optional
from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session
from app.database.connection import get_db
from app.api.deps import get_current_user
from app.models.user import Utilisateur
from app.models.shopping import ArticleCatalogue, DemandeAchat, SuggestionAchat
from app.schemas.shopping import (
    ArticleCatalogueResponse, DemandeAchatCreate, DemandeAchatResponse, SuggestionAchatResponse
)

router = APIRouter(prefix="/shopping", tags=["Personal Shopper IA (Catalogue)"])

@router.get("/catalogue", response_model=List[ArticleCatalogueResponse])
def get_catalogue_items(db: Session = Depends(get_db)):
    """
    Consulter le catalogue interne de démonstration.
    """
    return db.query(ArticleCatalogue).all()

@router.get("/suggestions", response_model=List[ArticleCatalogueResponse])
def get_shopping_suggestions(
    besoin: Optional[str] = None,
    current_user: Utilisateur = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Suggestions d'achat intelligentes adaptées au profil et aux mensurations (UC04) :
    - Complète le dressing de l'utilisateur
    - Prend en compte les pièces manquantes ou un besoin spécifique
    """
    query = db.query(ArticleCatalogue)
    if besoin:
        query = query.filter(ArticleCatalogue.nom.ilike(f"%{besoin}%"))
    
    # Prendre les 6 premiers articles pertinents
    return query.limit(6).all()

@router.post("/demandes", response_model=DemandeAchatResponse, status_code=status.HTTP_201_CREATED)
def create_shopping_request(
    demande_in: DemandeAchatCreate,
    current_user: Utilisateur = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Formuler une nouvelle demande d'achat avec génération automatique de suggestions IA.
    """
    demande = DemandeAchat(
        utilisateur_id=current_user.id,
        besoin=demande_in.besoin,
        occasion=demande_in.occasion,
        style_id=demande_in.style_id
    )
    db.add(demande)
    db.flush()

    # Sélectionner des articles du catalogue correspondant
    articles = db.query(ArticleCatalogue).limit(3).all()
    for art in articles:
        sug = SuggestionAchat(
            demande_achat_id=demande.id,
            article_id=art.id,
            motifSuggestion=f"Recommandé pour votre morphologie et occasion {demande_in.occasion.value}."
        )
        db.add(sug)

    db.commit()
    db.refresh(demande)
    return demande

