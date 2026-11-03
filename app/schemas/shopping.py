from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel
from app.models.enums import Occasion
from app.schemas.referentials import TypeVetementResponse, CouleurResponse

class ArticleCatalogueResponse(BaseModel):
    id: int
    nom: str
    imageUrl: str
    lienAchat: Optional[str] = None
    prix: float
    vendeur: str
    taillesDisponibles: str
    type_vetement: TypeVetementResponse
    couleur: CouleurResponse

    class Config:
        from_attributes = True

class DemandeAchatCreate(BaseModel):
    besoin: str
    occasion: Occasion = Occasion.QUOTIDIEN
    style_id: Optional[int] = None

class SuggestionAchatResponse(BaseModel):
    id: int
    motifSuggestion: str
    article: ArticleCatalogueResponse

    class Config:
        from_attributes = True

class DemandeAchatResponse(BaseModel):
    id: int
    besoin: str
    occasion: Occasion
    dateDemande: datetime
    suggestions: List[SuggestionAchatResponse] = []

    class Config:
        from_attributes = True

