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

@router.post("/generate-outfits", response_model=ShopperResultResponse)
async def generate_shopper_outfits(
    request: ShopperPromptRequest,
    current_user: Optional[Utilisateur] = Depends(get_optional_current_user),
    db: Session = Depends(get_db)
):
    """
    Point d'entrée principal de l'AI Shopper :
    1. Analyse la demande en langage naturel avec le LLM (Qwen via Ollama)
    2. Extrait style, occasion, couleurs, catégories, budget (TND) et requêtes
    3. Cherche les produits réels correspondants dans la base e-commerce
    4. Compose des tenues intelligentes respectant strictement le budget
    5. Retourne les tenues classées par score de compatibilité
    """
    if not request.prompt or not request.prompt.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Le prompt utilisateur ne peut pas être vide."
        )

    return await orchestrator.process_request(
        prompt=request.prompt.strip(),
        db=db,
        user=current_user,
        forced_genre=request.genre,
        forced_budget=request.budget
    )

@router.post("/interpret", response_model=ShopperCriteria)
async def interpret_prompt_only(
    request: ShopperPromptRequest,
    current_user: Optional[Utilisateur] = Depends(get_optional_current_user)
):
    """
    Interprète le prompt utilisateur avec le LLM et renvoie uniquement la structure JSON des critères.
    """
    user_genre = request.genre or (current_user.genre.value.upper() if current_user and current_user.genre else "HOMME")
    return await orchestrator.llm_manager.interpret(request.prompt, user_genre=user_genre)

@router.post("/sync-catalog", response_model=Dict[str, Any])
async def sync_ecommerce_catalog(db: Session = Depends(get_db)):
    """
    Déclenche manuellement la synchronisation du moteur de scraping pour actualiser
    les articles du catalogue avec les prix, images et tailles réels.
    """
    return await scraper_service.run_sync(db)
