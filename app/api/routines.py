from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.database.connection import get_db
from app.api.deps import get_current_user
from app.models.user import Utilisateur
from app.models.planning import RoutineHebdomadaire
from app.schemas.planning import (
    RoutineHebdomadaireCreate, RoutineHebdomadaireUpdate, RoutineHebdomadaireResponse
)

router = APIRouter(prefix="/routines", tags=["Planning & Routines Hebdomadaires"])

@router.get("", response_model=List[RoutineHebdomadaireResponse])
def get_routines(
    current_user: Utilisateur = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Lister les routines hebdomadaires de l'utilisateur (ex. Lundi = Université).
    """
    return db.query(RoutineHebdomadaire).filter(
        RoutineHebdomadaire.utilisateur_id == current_user.id
    ).all()

@router.post("", response_model=RoutineHebdomadaireResponse, status_code=status.HTTP_201_CREATED)
def create_routine(
    routine_in: RoutineHebdomadaireCreate,
    current_user: Utilisateur = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Définir une routine pour un jour de la semaine (unicité jour/utilisateur).
    """
    existing = db.query(RoutineHebdomadaire).filter(
        RoutineHebdomadaire.utilisateur_id == current_user.id,
        RoutineHebdomadaire.jourSemaine == routine_in.jourSemaine
    ).first()

    if existing:
        existing.occasion = routine_in.occasion
        existing.estActive = routine_in.estActive
        db.commit()
        db.refresh(existing)
        return existing

    new_routine = RoutineHebdomadaire(
        utilisateur_id=current_user.id,
        jourSemaine=routine_in.jourSemaine,
        occasion=routine_in.occasion,
        estActive=routine_in.estActive
    )
    db.add(new_routine)
    db.commit()
    db.refresh(new_routine)
    return new_routine

@router.put("/{id}", response_model=RoutineHebdomadaireResponse)
def update_routine(
    id: int,
    routine_in: RoutineHebdomadaireUpdate,
    current_user: Utilisateur = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Mettre à jour ou activer/désactiver une routine hebdomadaire.
    """
    routine = db.query(RoutineHebdomadaire).filter(
        RoutineHebdomadaire.id == id,
        RoutineHebdomadaire.utilisateur_id == current_user.id
    ).first()

    if not routine:
        raise HTTPException(status_code=404, detail="Routine introuvable.")

    if routine_in.occasion is not None:
        routine.occasion = routine_in.occasion
    if routine_in.estActive is not None:
        routine.estActive = routine_in.estActive

    db.commit()
    db.refresh(routine)
    return routine

@router.delete("/{id}", status_code=status.HTTP_200_OK)
def delete_routine(
    id: int,
    current_user: Utilisateur = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Supprimer une routine hebdomadaire.
    """
    routine = db.query(RoutineHebdomadaire).filter(
        RoutineHebdomadaire.id == id,
        RoutineHebdomadaire.utilisateur_id == current_user.id
    ).first()

    if not routine:
        raise HTTPException(status_code=404, detail="Routine introuvable.")

    db.delete(routine)
    db.commit()
    return {"message": "Routine supprimée avec succès."}

