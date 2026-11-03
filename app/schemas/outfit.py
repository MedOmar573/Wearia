from datetime import datetime, date
from typing import Optional, List
from pydantic import BaseModel, Field
from app.models.enums import Occasion, Appreciation
from app.schemas.clothing import VetementResponse

class FeedbackCreate(BaseModel):
    appreciation: Appreciation
    motifRejet: Optional[str] = None

class FeedbackResponse(BaseModel):
    id: int
    appreciation: Appreciation
    motifRejet: Optional[str] = None
    dateFeedback: datetime

    class Config:
        from_attributes = True

class OutfitItemSimple(BaseModel):
    id: int
    name: str
    category: Optional[str] = None
    color: Optional[str] = None
    image_url: Optional[str] = None

class RecommendationRequest(BaseModel):
    occasion: Optional[Occasion] = None # Si vide, déduit via BR09
    dateCible: Optional[date] = None # Par défaut date.today()
    temperature: Optional[float] = None # Si fourni manuellement
    precipitations: Optional[bool] = None # Si fourni manuellement

class RecommendationResponse(BaseModel):
    outfit_id: int
    occasion: Occasion
    temperature: Optional[float] = None
    weather: Optional[str] = None
    items: List[OutfitItemSimple]
    score: int = Field(..., ge=0, le=100)
    explanation: str

class TenueCreate(BaseModel):
    datePrevue: Optional[date] = None
    occasion: Occasion
    temperatureCelsius: Optional[float] = None
    precipitations: bool = False
    descriptionMeteo: Optional[str] = None
    explication: Optional[str] = None
    scoreCompatibilite: int = 100
    estGeneree: bool = False
    estFavorite: bool = False
    vetement_ids: List[int]
    style_id: Optional[int] = None
    evenement_id: Optional[int] = None

class TenueResponse(BaseModel):
    id: int
    dateCreation: datetime
    datePrevue: date
    datePortee: Optional[datetime] = None
    occasion: Occasion
    temperatureCelsius: Optional[float] = None
    precipitations: bool
    descriptionMeteo: Optional[str] = None
    explication: Optional[str] = None
    scoreCompatibilite: int
    estGeneree: bool
    estFavorite: bool
    utilisateur_id: int
    vetements: List[VetementResponse] = []
    feedback: Optional[FeedbackResponse] = None

    class Config:
        from_attributes = True

