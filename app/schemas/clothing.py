from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field
from app.models.enums import Coupe, Saison, StatutVetement
from app.schemas.referentials import TypeVetementResponse, CouleurResponse, StyleVestimentaireResponse

class VetementBase(BaseModel):
    nom: str = Field(..., min_length=2, max_length=120)
    matiere: Optional[str] = None
    coupe: Coupe = Coupe.REGULIERE
    saison: Saison = Saison.TOUTE_SAISON
    estThermique: bool = False
    estImpermeable: bool = False
    statut: StatutVetement = StatutVetement.DISPONIBLE
    type_vetement_id: int
    couleur_id: int
    style_id: Optional[int] = None

class VetementCreate(VetementBase):
    photoUrl: str # BR07: obligatoire

class VetementUpdate(BaseModel):
    nom: Optional[str] = None
    photoUrl: Optional[str] = None
    matiere: Optional[str] = None
    coupe: Optional[Coupe] = None
    saison: Optional[Saison] = None
    estThermique: Optional[bool] = None
    estImpermeable: Optional[bool] = None
    statut: Optional[StatutVetement] = None
    type_vetement_id: Optional[int] = None
    couleur_id: Optional[int] = None
    style_id: Optional[int] = None

class VetementResponse(BaseModel):
    id: int
    nom: str
    photoUrl: str
    matiere: Optional[str] = None
    coupe: Coupe
    saison: Saison
    estThermique: bool
    estImpermeable: bool
    statut: StatutVetement
    dateAjout: datetime
    utilisateur_id: int

    type_vetement: TypeVetementResponse
    couleur: CouleurResponse
    style_vestimentaire: Optional[StyleVestimentaireResponse] = None

    class Config:
        from_attributes = True

