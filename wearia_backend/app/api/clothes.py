from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from app.database.connection import get_db
from app.api.deps import get_current_user
from app.models.user import Utilisateur
from app.models.clothing import Vetement
from app.models.enums import Saison, StatutVetement
from app.schemas.clothing import VetementCreate, VetementUpdate, VetementResponse

router = APIRouter(prefix="/clothes", tags=["Dressing (Vêtements)"])

@router.get("", response_model=List[VetementResponse])
def get_user_clothes(
    categorie_id: Optional[int] = Query(None, description="Filtrer par catégorie"),
    couleur_id: Optional[int] = Query(None, description="Filtrer par couleur"),
    saison: Optional[Saison] = Query(None, description="Filtrer par saison"),
    statut: Optional[StatutVetement] = Query(None, description="Filtrer par statut (DISPONIBLE, SALE...)"),
    search: Optional[str] = Query(None, description="Recherche par nom ou matière"),
    current_user: Utilisateur = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Consulter et filtrer la liste des vêtements du dressing (UC09, UC10, UC12).
    """
    query = db.query(Vetement).filter(Vetement.utilisateur_id == current_user.id)

    if categorie_id:
        query = query.join(Vetement.type_vetement).filter(Vetement.type_vetement.has(categorie_id=categorie_id))
    if couleur_id:
        query = query.filter(Vetement.couleur_id == couleur_id)
    if saison:
        query = query.filter(Vetement.saison == saison)
    if statut:
        query = query.filter(Vetement.statut == statut)
    if search:
        query = query.filter(
            (Vetement.nom.ilike(f"%{search}%")) |
            (Vetement.matiere.ilike(f"%{search}%"))
        )

    return query.order_by(Vetement.dateAjout.desc()).all()

@router.post("", response_model=VetementResponse, status_code=status.HTTP_201_CREATED)
def create_clothing(
    clothing_in: VetementCreate,
    current_user: Utilisateur = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Ajouter un vêtement au dressing (UC09, BR07).
    """
    if not clothing_in.photoUrl or not clothing_in.type_vetement_id or not clothing_in.couleur_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Une photo, un type de vêtement et une couleur dominante sont obligatoires (BR07)."
        )

    vetement = Vetement(
        nom=clothing_in.nom,
        photoUrl=clothing_in.photoUrl,
        matiere=clothing_in.matiere,
        coupe=clothing_in.coupe,
        saison=clothing_in.saison,
        estThermique=clothing_in.estThermique,
        estImpermeable=clothing_in.estImpermeable,
        statut=clothing_in.statut,
        type_vetement_id=clothing_in.type_vetement_id,
        couleur_id=clothing_in.couleur_id,
        style_id=clothing_in.style_id,
        utilisateur_id=current_user.id
    )

    db.add(vetement)
    db.commit()
    db.refresh(vetement)
    return vetement

@router.get("/{id}", response_model=VetementResponse)
def get_clothing_detail(
    id: int,
    current_user: Utilisateur = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Obtenir le détail d'un vêtement spécifique (BR06 : appartient à l'utilisateur).
    """
    vetement = db.query(Vetement).filter(
        Vetement.id == id,
        Vetement.utilisateur_id == current_user.id
    ).first()

    if not vetement:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Vêtement introuvable."
        )
    return vetement

@router.put("/{id}", response_model=VetementResponse)
def update_clothing(
    id: int,
    clothing_in: VetementUpdate,
    current_user: Utilisateur = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Modifier les attributs d'un vêtement (statut, nom, coupe, etc.).
    """
    vetement = db.query(Vetement).filter(
        Vetement.id == id,
        Vetement.utilisateur_id == current_user.id
    ).first()

    if not vetement:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Vêtement introuvable."
        )

    update_dict = clothing_in.dict(exclude_unset=True)
    for field, value in update_dict.items():
        setattr(vetement, field, value)

    db.add(vetement)
    db.commit()
    db.refresh(vetement)
    return vetement

@router.delete("/{id}", status_code=status.HTTP_200_OK)
def delete_clothing(
    id: int,
    current_user: Utilisateur = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Supprimer un vêtement du dressing (UC09, BR07).
    """
    vetement = db.query(Vetement).filter(
        Vetement.id == id,
        Vetement.utilisateur_id == current_user.id
    ).first()

    if not vetement:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Vêtement introuvable."
        )

    db.delete(vetement)
    db.commit()
    return {"message": "Vêtement supprimé avec succès."}

