import logging
from typing import Optional, Dict, Any
from fastapi import APIRouter, Depends, status, HTTPException
from sqlalchemy.orm import Session
from app.database.connection import get_db
from app.api.deps import get_optional_current_user
from app.models.user import Utilisateur
from app.schemas.shopper import (
    ShopperPromptRequest, ShopperResultResponse, ShopperCriteria
)
from app.services.shopper_orchestrator import ShopperOrchestrator
from app.scraper.scraper_service import ScraperService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/shopper", tags=["AI Shopper & E-Commerce"])
orchestrator = ShopperOrchestrator()
scraper_service = ScraperService()


async def _run_shopper_search(
    request: ShopperPromptRequest,
    current_user: Optional[Utilisateur],
    db: Session,
) -> ShopperResultResponse:
    has_type = bool(
        (request.type_vetement and request.type_vetement.strip())
        or any(t.strip() for t in (request.requested_types or []))
    )
    has_prompt = bool(request.prompt and request.prompt.strip())
    if not has_type and not has_prompt:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Veuillez choisir un type de vêtement ou saisir une demande.",
        )

    return await orchestrator.process_request(
        prompt=(request.prompt or "").strip(),
        db=db,
        user=current_user,
        forced_genre=request.genre,
        forced_budget=request.budget,
        type_vetement=request.type_vetement,
        style_id=request.style_id,
        occasion=request.occasion,
        style=request.style,
        colors=request.colors,
        avoided_colors=request.avoided_colors,
        requested_types=request.requested_types,
        season=request.season,
        excluded_types=request.excluded_types,
        excluded_product_ids=request.excluded_product_ids,
        excluded_urls=request.excluded_urls,
        max_results=request.max_results,
    )


@router.post("/generate-outfits", response_model=ShopperResultResponse)
@router.post("/search-articles", response_model=ShopperResultResponse)
async def generate_shopper_proposals(
    request: ShopperPromptRequest,
    current_user: Optional[Utilisateur] = Depends(get_optional_current_user),
    db: Session = Depends(get_db),
):
    """
    Point d'entrée principal de l'AI Shopper (sélection d'articles individuels) :
    1. Utilise le genre du compte connecté (HOMME ou FEMME, + compatibilité MIXTE)
    2. Filtre strictement sur le type de vêtement demandé et le budget maximum
    3. Résout le style depuis la base de données et filtre les styles incompatibles
    4. Déduplique les résultats et vérifie la validité réelle des liens produits
    5. Retourne une liste d'articles individuels du type demandé (sans combinaison multi-pièces)
    """
    return await _run_shopper_search(request, current_user, db)


@router.post("/interpret", response_model=ShopperCriteria)
async def interpret_prompt_only(
    request: ShopperPromptRequest,
    current_user: Optional[Utilisateur] = Depends(get_optional_current_user),
):
    """
    Interprète le prompt utilisateur et renvoie uniquement la structure JSON des critères.
    """
    user_genre = request.genre or (
        current_user.genre.value.upper() if current_user and current_user.genre else "HOMME"
    )
    return await orchestrator.llm_manager.interpret(request.prompt or "", user_genre=user_genre)


@router.post("/sync-catalog", response_model=Dict[str, Any])
async def sync_ecommerce_catalog(db: Session = Depends(get_db)):
    """
    Déclenche manuellement la synchronisation du moteur de scraping pour actualiser
    les articles du catalogue avec les prix, images et tailles réels.
    """
    return await scraper_service.run_sync(db)
