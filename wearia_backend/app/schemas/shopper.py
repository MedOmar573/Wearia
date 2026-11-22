from typing import List, Optional
from datetime import datetime
from pydantic import BaseModel, Field


class ShopperPromptRequest(BaseModel):
    prompt: str = Field("", description="Précision libre facultative de l'utilisateur")
    type_vetement: Optional[str] = Field(
        None,
        description="Type de vêtement recherché (ex: Pull, Pantalon, Chemise, Jean, Veste, Short, Sac, Chapeau, Sweat...)",
    )
    style_id: Optional[int] = Field(
        None,
        description="Identifiant du style vestimentaire issu de la table styles_vestimentaires",
    )
    budget: Optional[float] = Field(None, description="Budget maximal en TND respecté strictement par article")
    genre: Optional[str] = Field(None, description="Genre du compte connecté (HOMME ou FEMME)")
    occasion: Optional[str] = None
    style: Optional[str] = None
    colors: List[str] = Field(default_factory=list)
    avoided_colors: List[str] = Field(default_factory=list)
    requested_types: List[str] = Field(default_factory=list, description="Types de produits demandés")
    season: Optional[str] = None
    excluded_types: List[str] = Field(default_factory=list)
    excluded_product_ids: List[int] = Field(default_factory=list)
    excluded_urls: List[str] = Field(default_factory=list)
    max_results: int = Field(12, ge=1, le=30, description="Nombre maximal de propositions individuelles")


class ShopperCriteria(BaseModel):
    style: str = Field("Décontracté", description="Style vestimentaire sélectionné")
    occasion: str = Field("QUOTIDIEN", description="Occasion éventuelle")
    colors: List[str] = Field(default_factory=list, description="Couleurs souhaitées")
    categories: List[str] = Field(default_factory=list, description="Catégories identifiées")
    types_vetement: List[str] = Field(default_factory=list, description="Types de vêtements ciblés")
    budget: Optional[float] = Field(None, description="Budget maximal strict")
    currency: str = Field("TND", description="Devise")
    search_queries: List[str] = Field(default_factory=list, description="Requêtes e-commerce")
    avoided_colors: List[str] = Field(default_factory=list)
    requested_types: List[str] = Field(default_factory=list)
    season: Optional[str] = None
    excluded_types: List[str] = Field(default_factory=list)


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
    styleNom: Optional[str] = None
    scoreCompatibilite: int = 85
    respecteBudget: bool = True
    explication: Optional[str] = None
    verifieLe: Optional[datetime] = None

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
    styleConcordance: str = "Décontracté"
    explication: str = ""


class ShopperResultResponse(BaseModel):
    prompt: str
    criteres: ShopperCriteria
    articles: List[ShopperArticle] = Field(
        default_factory=list,
        description="Ensemble de propositions individuelles du type demandé (hors combinaison multi-pièces)",
    )
    nbArticlesTrouves: int = 0
    typeDemande: Optional[str] = None
    styleDemande: Optional[str] = None
    genreUtilise: Optional[str] = None
    budgetMax: Optional[float] = None
    # Conservés pour rétrocompatibilité API (vides en mode sélection d'articles individuels)
    tenues: List[ShopperOutfit] = Field(default_factory=list)
    articlesComplementaires: List[ShopperArticle] = Field(default_factory=list)
    nbTenuesTrouvees: int = 0
