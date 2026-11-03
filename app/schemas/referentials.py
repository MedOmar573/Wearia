from pydantic import BaseModel
from app.models.enums import GenreCible

class CategorieResponse(BaseModel):
    id: int
    nom: str

    class Config:
        from_attributes = True

class TypeVetementResponse(BaseModel):
    id: int
    nom: str
    genreCible: GenreCible
    estCoucheSuperieure: bool
    categorie_id: int

    class Config:
        from_attributes = True

class CouleurResponse(BaseModel):
    id: int
    nom: str
    codeHex: str

    class Config:
        from_attributes = True

class StyleVestimentaireResponse(BaseModel):
    id: int
    libelle: str

    class Config:
        from_attributes = True

