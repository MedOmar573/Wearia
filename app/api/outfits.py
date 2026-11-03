from typing import List, Optional
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from app.database.connection import get_db
from app.api.deps import get_current_user
from app.models.user import Utilisateur
from app.models.outfit import Tenue, Feedback
from app.models.clothing import Vetement
from app.schemas.outfit import (
    TenueCreate, TenueResponse, FeedbackCreate, FeedbackResponse
)

router = APIRouter(tags=["Tenues & Favoris"])

@router.get("/outfits", response_model=List[TenueResponse])
def get_user_outfits(
    favoris_only: Optional[bool] = Query(False, description="Filtrer uniquement les tenues favorites"),
    current_user: Utilisateur = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Consulter l'historique ou les tenues favorites de l'utilisateur (UC10).
    """
    query = db.query(Tenue).filter(Tenue.utilisateur_id == current_user.id)
    if favoris_only:
        query = query.filter(Tenue.estFavorite == True)
    return query.order_by(Tenue.dateCreation.desc()).all()

@router.post("/outfits", response_model=TenueResponse, status_code=status.HTTP_201_CREATED)
def save_custom_outfit(
    outfit_in: TenueCreate,
    current_user: Utilisateur = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Enregistrer une tenue personnalisée ou composée manuellement (UC10).
    """
    # Vérifier que les vêtements appartiennent tous à l'utilisateur (BR06)
    vetements = db.query(Vetement).filter(
        Vetement.id.in_(outfit_in.vetement_ids),
        Vetement.utilisateur_id == current_user.id
    ).all()

    if len(vetements) != len(outfit_in.vetement_ids):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Certains vêtements sont introuvables ou n'appartiennent pas à votre dressing."
        )

    tenue = Tenue(
        utilisateur_id=current_user.id,
        datePrevue=outfit_in.datePrevue or datetime.utcnow().date(),
        occasion=outfit_in.occasion,
        temperatureCelsius=outfit_in.temperatureCelsius,
        precipitations=outfit_in.precipitations,
        descriptionMeteo=outfit_in.descriptionMeteo,
        explication=outfit_in.explication or "Tenue composée manuellement.",
        scoreCompatibilite=outfit_in.scoreCompatibilite,
        estGeneree=outfit_in.estGeneree,
        estFavorite=outfit_in.estFavorite,
        style_id=outfit_in.style_id,
        evenement_id=outfit_in.evenement_id
    )
    tenue.vetements = vetements

    db.add(tenue)
    db.commit()
    db.refresh(tenue)
    return tenue

@router.get("/outfits/{id}", response_model=TenueResponse)
def get_outfit_detail(
    id: int,
    current_user: Utilisateur = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Obtenir les détails complets d'une tenue.
    """
    tenue = db.query(Tenue).filter(
        Tenue.id == id,
        Tenue.utilisateur_id == current_user.id
    ).first()

    if not tenue:
        raise HTTPException(status_code=404, detail="Tenue introuvable.")
    return tenue

@router.put("/outfits/{id}", response_model=TenueResponse)
def update_outfit(
    id: int,
    estFavorite: Optional[bool] = None,
    marquee_portee: Optional[bool] = None,
    current_user: Utilisateur = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Modifier une tenue (ex: ajouter/retirer des favoris, marquer comme portée).
    """
    tenue = db.query(Tenue).filter(
        Tenue.id == id,
        Tenue.utilisateur_id == current_user.id
    ).first()

    if not tenue:
        raise HTTPException(status_code=404, detail="Tenue introuvable.")

    if estFavorite is not None:
        tenue.estFavorite = estFavorite
    if marquee_portee:
        tenue.datePortee = datetime.utcnow()

    db.commit()
    db.refresh(tenue)
    return tenue

@router.delete("/outfits/{id}", status_code=status.HTTP_200_OK)
def delete_outfit(
    id: int,
    current_user: Utilisateur = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Supprimer une tenue enregistrée (UC10).
    """
    tenue = db.query(Tenue).filter(
        Tenue.id == id,
        Tenue.utilisateur_id == current_user.id
    ).first()

    if not tenue:
        raise HTTPException(status_code=404, detail="Tenue introuvable.")

    db.delete(tenue)
    db.commit()
    return {"message": "Tenue supprimée avec succès."}

@router.get("/outfits/{id}/feedback", response_model=FeedbackResponse)
def get_outfit_feedback(
    id: int,
    current_user: Utilisateur = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Consulter l'évaluation d'une tenue.
    """
    tenue = db.query(Tenue).filter(
        Tenue.id == id,
        Tenue.utilisateur_id == current_user.id
    ).first()

    if not tenue or not tenue.feedback:
        raise HTTPException(status_code=404, detail="Aucun avis enregistré pour cette tenue.")
    return tenue.feedback

@router.post("/outfits/{id}/feedback", response_model=FeedbackResponse, status_code=status.HTTP_201_CREATED)
def submit_outfit_feedback(
    id: int,
    feedback_in: FeedbackCreate,
    current_user: Utilisateur = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Donner un avis sur une tenue recommandée (UC05 : AIME, MOYEN, PAS_POUR_MOI).
    """
    tenue = db.query(Tenue).filter(
        Tenue.id == id,
        Tenue.utilisateur_id == current_user.id
    ).first()

    if not tenue:
        raise HTTPException(status_code=404, detail="Tenue introuvable.")

    if tenue.feedback:
        tenue.feedback.appreciation = feedback_in.appreciation
        tenue.feedback.motifRejet = feedback_in.motifRejet
        tenue.feedback.dateFeedback = datetime.utcnow()
        db.commit()
        db.refresh(tenue.feedback)
        return tenue.feedback

    feedback = Feedback(
        tenue_id=tenue.id,
        appreciation=feedback_in.appreciation,
        motifRejet=feedback_in.motifRejet
    )
    db.add(feedback)
    db.commit()
    db.refresh(feedback)
    return feedback

@router.put("/feedback/{id}", response_model=FeedbackResponse)
def update_feedback(
    id: int,
    feedback_in: FeedbackCreate,
    current_user: Utilisateur = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Modifier une évaluation existante.
    """
    feedback = db.query(Feedback).join(Feedback.tenue).filter(
        Feedback.id == id,
        Tenue.utilisateur_id == current_user.id
    ).first()

    if not feedback:
        raise HTTPException(status_code=404, detail="Feedback introuvable.")

    feedback.appreciation = feedback_in.appreciation
    feedback.motifRejet = feedback_in.motifRejet
    db.commit()
    db.refresh(feedback)
    return feedback

@router.delete("/feedback/{id}", status_code=status.HTTP_200_OK)
def delete_feedback(
    id: int,
    current_user: Utilisateur = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Supprimer une évaluation.
    """
    feedback = db.query(Feedback).join(Feedback.tenue).filter(
        Feedback.id == id,
        Tenue.utilisateur_id == current_user.id
    ).first()

    if not feedback:
        raise HTTPException(status_code=404, detail="Feedback introuvable.")

    db.delete(feedback)
    db.commit()
    return {"message": "Avis supprimé avec succès."}

