from datetime import date
from typing import Optional
from pydantic import BaseModel
from app.models.enums import JourSemaine, Occasion

class RoutineHebdomadaireCreate(BaseModel):
    jourSemaine: JourSemaine
    occasion: Occasion
    estActive: bool = True

class RoutineHebdomadaireUpdate(BaseModel):
    occasion: Optional[Occasion] = None
    estActive: Optional[bool] = None

class RoutineHebdomadaireResponse(BaseModel):
    id: int
    jourSemaine: JourSemaine
    occasion: Occasion
    estActive: bool
    utilisateur_id: int

    class Config:
        from_attributes = True

class EvenementCreate(BaseModel):
    titre: str
    date: date
    occasion: Occasion

class EvenementUpdate(BaseModel):
    titre: Optional[str] = None
    date: Optional[date] = None
    occasion: Optional[Occasion] = None

class EvenementResponse(BaseModel):
    id: int
    titre: str
    date: date
    occasion: Occasion
    utilisateur_id: int

    class Config:
        from_attributes = True

