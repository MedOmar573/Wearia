import logging
from typing import Optional
from sqlalchemy.orm import Session
from app.models.user import Utilisateur
from app.models.shopping import ArticleCatalogue
from app.schemas.shopper import ShopperCriteria, ShopperResultResponse, ShopperArticle
from app.ai.shopper_llm import ShopperLLMManager
from app.services.product_search_service import ProductSearchService
from app.services.shopper_outfit_service import ShopperOutfitService
from app.scraper.scraper_service import ScraperService

logger = logging.getLogger(__name__)

class ShopperOrchestrator:
    """
    Orchestrateur central de l'AI Shopper :
    Utilisateur → LLM → ShopperCriteria → ProductSearch → OutfitCompose → Résultats.
    """
    def __init__(self):
        self.llm_manager = ShopperLLMManager()
        self.scraper_service = ScraperService()

    async def process_request(
        self,
        prompt: str,
        db: Session,
        user: Optional[Utilisateur] = None,
        forced_genre: Optional[str] = None,
        forced_budget: Optional[float] = None
    ) -> ShopperResultResponse:

        # 1. Genre effectif
        effective_genre = forced_genre
        if not effective_genre and user and user.genre:
            effective_genre = user.genre.value.upper()
        if not effective_genre:
            effective_genre = "HOMME"

        # 2. Interprétation du prompt
        logger.info(f"[AI SHOPPER] Interprétation : '{prompt}' (genre={effective_genre})")
        criteres = await self.llm_manager.interpret(prompt, user_genre=effective_genre)

        # Budget forcé depuis UI > LLM
        if forced_budget is not None and forced_budget > 0:
            criteres.budget = float(forced_budget)

        logger.info(f"[AI SHOPPER] Critères : {criteres.model_dump()}")

        # 3. Synchronisation du catalogue si nécessaire
        # Déclenche toujours une synchro si la DB est vide ou très petite
        total_articles = db.query(ArticleCatalogue).count()
        if total_articles < 30:
            logger.info(f"[AI SHOPPER] Catalogue insuffisant ({total_articles} articles) → sync...")
            await self.scraper_service.run_sync(db)
            total_articles = db.query(ArticleCatalogue).count()
            logger.info(f"[AI SHOPPER] Après sync : {total_articles} articles en base")

        # 4. Recherche des articles
        grouped_items = ProductSearchService.search_products_by_criteria(
            db=db,
            criteres=criteres,
            user_gender=effective_genre
        )

        # 5. Fallback : si trop peu de résultats, re-sync et re-chercher
        total_found = sum(len(v) for v in grouped_items.values())
        if total_found < 5:
            logger.warning(f"[AI SHOPPER] Seulement {total_found} articles trouvés → re-sync...")
            await self.scraper_service.run_sync(db)
            grouped_items = ProductSearchService.search_products_by_criteria(
                db=db,
                criteres=criteres,
                user_gender=effective_genre
            )

        # 6. Composition des tenues
        outfits = ShopperOutfitService.compose_outfits(
            grouped_items=grouped_items,
            criteres=criteres,
            user=user,
            max_outfits=3
        )

        # 7. Articles complémentaires (accessoires + vestes)
        complementaires_raw = grouped_items.get("accessoires", []) + grouped_items.get("vestes", [])
        complementaires = [
            ShopperArticle(
                id=it.id,
                nom=it.nom,
                imageUrl=it.imageUrl or "",
                lienAchat=it.lienAchat or "",
                prix=it.prix or 0.0,
                devise=it.devise or "TND",
                vendeur=it.vendeur or "Boutique",
                taillesDisponibles=it.taillesDisponibles or "S, M, L, XL",
                typeVetementNom=it.type_vetement.nom if it.type_vetement else "Article",
                couleurNom=it.couleur.nom if it.couleur else "Neutre",
                categorieNom=it.type_vetement.categorie.nom if (it.type_vetement and it.type_vetement.categorie) else "Mode"
            )
            for it in complementaires_raw[:4]
        ]

        logger.info(f"[AI SHOPPER] Résultat : {len(outfits)} tenues, {len(complementaires)} complémentaires")

        return ShopperResultResponse(
            prompt=prompt,
            criteres=criteres,
            tenues=outfits,
            articlesComplementaires=complementaires,
            nbTenuesTrouvees=len(outfits)
        )
