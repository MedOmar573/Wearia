from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.database.connection import get_db
from app.api.deps import get_current_user
from app.models.user import Utilisateur
from app.models.planning import Evenement
from app.schemas.planning import (
    EvenementCreate, EvenementUpdate, EvenementResponse
)

router = APIRouter(prefix="/events", tags=["Planning & Événements"])

@router.get("", response_model=List[EvenementResponse])
def get_events(
    current_user: Utilisateur = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Lister les événements planifiés par l'utilisateur (UC03).
    """
    return db.query(Evenement).filter(
        Evenement.utilisateur_id == current_user.id
    ).order_by(Evenement.date.asc()).all()

@router.post("", response_model=EvenementResponse, status_code=status.HTTP_201_CREATED)
def create_event(
    event_in: EvenementCreate,
    current_user: Utilisateur = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Planifier un nouvel événement ponctuel (date + occasion).
    """
    new_event = Evenement(
        utilisateur_id=current_user.id,
        titre=event_in.titre,
        date=event_in.date,
        occasion=event_in.occasion
    )
    db.add(new_event)
    db.commit()
    db.refresh(new_event)
    return new_event

@router.put("/{id}", response_model=EvenementResponse)
def update_event(
    id: int,
    event_in: EvenementUpdate,
    current_user: Utilisateur = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Modifier un événement planifié.
    """
    event = db.query(Evenement).filter(
        Evenement.id == id,
        Evenement.utilisateur_id == current_user.id
    ).first()

    if not event:
        raise HTTPException(status_code=404, detail="Événement introuvable.")

    update_data = event_in.dict(exclude_unset=True)
    for field, val in update_data.items():
        setattr(event, field, val)

    db.commit()
    db.refresh(event)
    return event

@router.delete("/{id}", status_code=status.HTTP_200_OK)
def delete_event(
    id: int,
    current_user: Utilisateur = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Supprimer un événement ponctuel.
    """
    event = db.query(Evenement).filter(
        Evenement.id == id,
        Evenement.utilisateur_id == current_user.id
    ).first()

    if not event:
        raise HTTPException(status_code=404, detail="Événement introuvable.")

    db.delete(event)
    db.commit()
    return {"message": "Événement supprimé avec succès."}

