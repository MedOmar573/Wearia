from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.database.connection import get_db
from app.api.deps import get_current_user
from app.models.user import Utilisateur, PreferenceCouleur, PreferenceStyle
from app.schemas.user import (
    UserResponse, UserUpdate,
    PreferenceCouleurCreate, PreferenceCouleurResponse, ColorPreferencesBatch,
    PreferenceStyleCreate, PreferenceStyleResponse, StylePreferencesBatch
)
from app.models.enums import TypePreference

router = APIRouter(prefix="/users", tags=["Utilisateurs & Profil"])

@router.get("/me", response_model=UserResponse)
def get_current_user_profile(
    current_user: Utilisateur = Depends(get_current_user)
):
    """
    Consulter le profil de l'utilisateur connecté, ses mensurations et ses préférences (UC11).
    """
    return current_user

@router.put("/me", response_model=UserResponse)
def update_current_user_profile(
    user_update: UserUpdate,
    current_user: Utilisateur = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Modifier le profil de l'utilisateur connecté (UC11).
    """
    update_data = user_update.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(current_user, field, value)

    db.add(current_user)
    db.commit()
    db.refresh(current_user)
    return current_user

@router.delete("/me", status_code=status.HTTP_200_OK)
def delete_current_user_account(
    current_user: Utilisateur = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Supprimer le compte de l'utilisateur (UC11 & AJOUT Plan).
    """
    db.delete(current_user)
    db.commit()
    return {"message": "Compte utilisateur supprimé avec succès."}

@router.post("/me/preferences/colors", response_model=PreferenceCouleurResponse)
def add_color_preference(
    pref_in: PreferenceCouleurCreate,
    current_user: Utilisateur = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Ajouter une préférence de couleur (AIME / EVITE).
    """
    existing = db.query(PreferenceCouleur).filter(
        PreferenceCouleur.utilisateur_id == current_user.id,
        PreferenceCouleur.couleur_id == pref_in.couleur_id,
        PreferenceCouleur.typePreference == pref_in.typePreference
    ).first()
    if existing:
        return existing

    pref = PreferenceCouleur(
        utilisateur_id=current_user.id,
        couleur_id=pref_in.couleur_id,
        typePreference=pref_in.typePreference
    )
    db.add(pref)
    db.commit()
    db.refresh(pref)
    return pref

@router.post("/me/preferences/styles", response_model=PreferenceStyleResponse)
def add_style_preference(
    pref_in: PreferenceStyleCreate,
    current_user: Utilisateur = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Ajouter une préférence de style vestimentaire (AIME / EVITE).
    """
    existing = db.query(PreferenceStyle).filter(
        PreferenceStyle.utilisateur_id == current_user.id,
        PreferenceStyle.style_id == pref_in.style_id,
        PreferenceStyle.typePreference == pref_in.typePreference
    ).first()
    if existing:
        return existing

    pref = PreferenceStyle(
        utilisateur_id=current_user.id,
        style_id=pref_in.style_id,
        typePreference=pref_in.typePreference
    )
    db.add(pref)
    db.commit()
    db.refresh(pref)
    return pref

@router.put("/me/preferences/colors/batch", response_model=List[PreferenceCouleurResponse])
def set_color_preferences_batch(
    batch: ColorPreferencesBatch,
    current_user: Utilisateur = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Remplacer les préférences de couleurs de l'utilisateur par une nouvelle sélection.
    """
    db.query(PreferenceCouleur).filter(PreferenceCouleur.utilisateur_id == current_user.id).delete()
    for c_id in batch.liked_color_ids:
        db.add(PreferenceCouleur(
            utilisateur_id=current_user.id,
            couleur_id=c_id,
            typePreference=TypePreference.AIME
        ))
    for c_id in batch.avoided_color_ids:
        db.add(PreferenceCouleur(
            utilisateur_id=current_user.id,
            couleur_id=c_id,
            typePreference=TypePreference.EVITE
        ))
    db.commit()
    return db.query(PreferenceCouleur).filter(PreferenceCouleur.utilisateur_id == current_user.id).all()

@router.put("/me/preferences/styles/batch", response_model=List[PreferenceStyleResponse])
def set_style_preferences_batch(
    batch: StylePreferencesBatch,
    current_user: Utilisateur = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Remplacer les préférences de style de l'utilisateur par une nouvelle sélection.
    """
    db.query(PreferenceStyle).filter(PreferenceStyle.utilisateur_id == current_user.id).delete()
    for s_id in batch.style_ids:
        db.add(PreferenceStyle(
            utilisateur_id=current_user.id,
            style_id=s_id,
            typePreference=TypePreference.AIME
        ))
    db.commit()
    return db.query(PreferenceStyle).filter(PreferenceStyle.utilisateur_id == current_user.id).all()


