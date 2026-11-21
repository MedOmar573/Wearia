from typing import List, Optional
from pydantic import BaseModel, Field

class ShopperPromptRequest(BaseModel):
    prompt: str = Field(..., description="Demande en langage naturel de l'utilisateur")
    budget: Optional[float] = Field(None, description="Budget maximal en TND spécifié directement par l'utilisateur")
    genre: Optional[str] = Field(None, description="Genre optionnel (HOMME ou FEMME) pour restreindre la sélection")

class ShopperCriteria(BaseModel):
    style: str = Field("Décontracté", description="Style vestimentaire extrait (streetwear, chic, casual...)")
    occasion: str = Field("QUOTIDIEN", description="Occasion détectée (université, travail, soirée...)")
    colors: List[str] = Field(default_factory=list, description="Couleurs mentionnées (ex: noir, blanc)")
    categories: List[str] = Field(default_factory=list, description="Catégories identifiées (haut, bas, chaussures, veste)")
    types_vetement: List[str] = Field(default_factory=list, description="Types de vêtements précis (t-shirt, cargo, baskets)")
    budget: Optional[float] = Field(None, description="Budget maximal extrait")
    currency: str = Field("TND", description="Devise détectée")
    search_queries: List[str] = Field(default_factory=list, description="Requêtes de recherche e-commerce formulées")

class ShopperArticle(BaseModel):
    id: int
    nom: str
    imageUrl: str
    lienAchat: Optional[str] = None
    prix: float
    devise: str = "TND"
    vendeur: str
    taillesDisponibles: str = "S, M, L, XL"
    typeVetementNom: str
    couleurNom: str
    categorieNom: str

    class Config:
        from_attributes = True

class ShopperOutfit(BaseModel):
    id: int
    articles: List[ShopperArticle]
    prixTotal: float
    budgetMax: Optional[float] = None
    respecteBudget: bool = True
    scoreCompatibilite: int = 85
    harmonieCouleurs: str = "Harmonieuse"
    styleConcordance: str = "Streetwear"
    explication: str = ""

class ShopperResultResponse(BaseModel):
    prompt: str
    criteres: ShopperCriteria
    tenues: List[ShopperOutfit]
    articlesComplementaires: List[ShopperArticle] = []
    nbTenuesTrouvees: int = 0
