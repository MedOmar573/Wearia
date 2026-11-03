from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.database.connection import get_db
from app.api.deps import get_current_user
from app.models.user import Utilisateur
from app.schemas.outfit import RecommendationRequest, RecommendationResponse, OutfitItemSimple
from app.services.recommendation_service import RecommendationService

router = APIRouter(prefix="/recommendations", tags=["Recommandations IA"])

@router.post("", response_model=RecommendationResponse, status_code=status.HTTP_200_OK)
def get_outfit_recommendation(
    req: RecommendationRequest = None,
    current_user: Utilisateur = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Génère une proposition de tenue optimisée (UC02, UC03) :
    - Détermine l'occasion (Événement > Routine > QUOTIDIEN selon BR09)
    - Analyse la météo locale (OpenWeatherMap)
    - Applique les règles métier (BR01 à BR04, BR08)
    - Calcule le score de compatibilité /100 et génère l'explication.
    """
    occasion = req.occasion if req else None
    date_cible = req.dateCible if req else None
    temp = req.temperature if req else None
    precip = req.precipitations if req else None

    try:
        tenue, items = RecommendationService.generate_recommendation(
            user=current_user,
            db=db,
            forced_occasion=occasion,
            target_date=date_cible,
            manual_temp=temp,
            manual_precip=precip
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

    formatted_items = [
        OutfitItemSimple(
            id=item.id,
            name=item.nom,
            category=item.type_vetement.categorie.nom if (item.type_vetement and item.type_vetement.categorie) else None,
            color=item.couleur.nom if item.couleur else None,
            image_url=item.photoUrl
        )
        for item in items
    ]

    return RecommendationResponse(
        outfit_id=tenue.id,
        occasion=tenue.occasion,
        temperature=tenue.temperatureCelsius,
        weather=tenue.descriptionMeteo,
        items=formatted_items,
        score=tenue.scoreCompatibilite,
        explanation=tenue.explication or "Tenue recommandée adaptée à vos préférences."
    )

