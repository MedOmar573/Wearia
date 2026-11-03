from datetime import date, datetime
from typing import Optional, List
from pydantic import BaseModel, EmailStr, field_validator
from app.models.enums import Genre, Coupe, TypePreference
from app.schemas.referentials import CouleurResponse, StyleVestimentaireResponse

class PreferenceCouleurCreate(BaseModel):
    couleur_id: int
    typePreference: TypePreference = TypePreference.AIME

class ColorPreferencesBatch(BaseModel):
    liked_color_ids: List[int] = []
    avoided_color_ids: List[int] = []

class PreferenceCouleurResponse(BaseModel):
    id: int
    couleur: CouleurResponse
    typePreference: TypePreference

    class Config:
        from_attributes = True

class PreferenceStyleCreate(BaseModel):
    style_id: int
    typePreference: TypePreference = TypePreference.AIME

class StylePreferencesBatch(BaseModel):
    style_ids: List[int] = []

class PreferenceStyleResponse(BaseModel):
    id: int
    style: StyleVestimentaireResponse
    typePreference: TypePreference

    class Config:
        from_attributes = True

class UserUpdate(BaseModel):
    nom: Optional[str] = None
    genre: Optional[Genre] = None
    dateNaissance: Optional[date] = None
    ville: Optional[str] = None
    hauteurCm: Optional[int] = None
    poidsKg: Optional[float] = None
    tourEpaules: Optional[float] = None
    tourPoitrine: Optional[float] = None
    tourTaille: Optional[float] = None
    tourHanches: Optional[float] = None
    tailleVestimentaire: Optional[str] = None
    coupePreferee: Optional[Coupe] = None
    consentementRGPD: Optional[bool] = None

    @field_validator("coupePreferee", mode="before")
    @classmethod
    def normalize_coupe(cls, v):
        if v is None:
            return None
        if isinstance(v, Coupe):
            return v
        v_str = str(v).strip().upper()
        mapping = {
            "FITTED": Coupe.AJUSTEE,
            "SLIM": Coupe.AJUSTEE,
            "AJUSTEE": Coupe.AJUSTEE,
            "REGULAR": Coupe.REGULIERE,
            "REGULIERE": Coupe.REGULIERE,
            "CLASSIQUE": Coupe.REGULIERE,
            "OVERSIZED": Coupe.OVERSIZE,
            "OVERSIZE": Coupe.OVERSIZE,
            "LARGE": Coupe.OVERSIZE,
        }
        return mapping.get(v_str, v)

    @field_validator("genre", mode="before")
    @classmethod
    def normalize_genre(cls, v):
        if v is None:
            return None
        if isinstance(v, Genre):
            return v
        v_str = str(v).strip().upper()
        if "HOMME" in v_str or v_str in ["MAN", "MALE", "H", "M"]:
            return Genre.HOMME
        if "FEMME" in v_str or v_str in ["WOMAN", "FEMALE", "F", "W"]:
            return Genre.FEMME
        return v

class UserResponse(BaseModel):
    id: int
    nom: str
    email: EmailStr
    genre: Optional[Genre] = None
    dateNaissance: Optional[date] = None
    ville: str
    hauteurCm: Optional[int] = None
    poidsKg: Optional[float] = None
    tourEpaules: Optional[float] = None
    tourPoitrine: Optional[float] = None
    tourTaille: Optional[float] = None
    tourHanches: Optional[float] = None
    tailleVestimentaire: Optional[str] = None
    coupePreferee: Optional[Coupe] = None
    consentementRGPD: bool
    dateCreation: datetime

    preferences_couleur: List[PreferenceCouleurResponse] = []
    preferences_style: List[PreferenceStyleResponse] = []

    class Config:
        from_attributes = True

