import logging
from datetime import datetime, timedelta
from typing import Optional
from urllib.parse import urlparse
from sqlalchemy.orm import Session
from app.models.user import Utilisateur
from app.models.shopping import ArticleCatalogue
from app.schemas.shopper import ShopperCriteria, ShopperResultResponse, ShopperArticle
from app.ai.shopper_llm import ShopperLLMManager
from app.services.product_search_service import ProductSearchService, extract_requested_type_mentions
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
        forced_budget: Optional[float] = None,
        occasion: Optional[str] = None,
        style: Optional[str] = None,
        colors: Optional[list[str]] = None,
        avoided_colors: Optional[list[str]] = None,
        requested_types: Optional[list[str]] = None,
        season: Optional[str] = None,
        excluded_types: Optional[list[str]] = None,
        excluded_product_ids: Optional[list[int]] = None
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
        if occasion:
            criteres.occasion = occasion
        if style:
            criteres.style = style
        if colors:
            criteres.colors = colors
        criteres.avoided_colors = avoided_colors or []
        criteres.requested_types = requested_types or extract_requested_type_mentions(prompt)
        criteres.season = season
        criteres.excluded_types = excluded_types or []

        logger.info(f"[AI SHOPPER] Critères : {criteres.model_dump()}")

        # 3. Garder un catalogue frais sans relancer tout le scraping pour chaque
        # requête mobile. Une synchronisation récente reste valable 30 minutes.
        now = datetime.utcnow()
        allowed_domains = {
            urlparse(scraper.base_url).netloc
            for scraper in self.scraper_service.scrapers
            if not (effective_genre == "HOMME" and "femme" in scraper.store_name.lower())
            and not (effective_genre == "FEMME" and "homme" in scraper.store_name.lower())
        }
        sync_window_rows = db.query(ArticleCatalogue).filter(
            ArticleCatalogue.enStock == True,
            ArticleCatalogue.prix > 0,
            ArticleCatalogue.lienAchat.like("https://%")
        ).all()
        sync_window_rows = [
            row for row in sync_window_rows
            if row.dateDerniereSynchro
            and row.dateDerniereSynchro >= now - timedelta(minutes=30)
            and row.lienAchat
            and (not allowed_domains or urlparse(row.lienAchat).netloc in allowed_domains)
        ]
        sync_stats = {"verified_urls": []}
        if not sync_window_rows:
            sync_stats = await self.scraper_service.run_sync(db, target_gender=effective_genre)
            logger.info(f"[AI SHOPPER] Actualisation des sources réelles : {sync_stats}")
        else:
            logger.info("[AI SHOPPER] Catalogue déjà synchronisé récemment; réutilisation des offres vérifiées.")

        # Récupération des URLs vérifiées récemment pour le filtrage.
        recent_catalog_rows = db.query(ArticleCatalogue).filter(
            ArticleCatalogue.enStock == True,
            ArticleCatalogue.prix > 0,
            ArticleCatalogue.dateDerniereSynchro >= now - timedelta(hours=24),
            ArticleCatalogue.lienAchat.like("https://%")
        ).all()
        recently_verified_urls = [
            row.lienAchat for row in recent_catalog_rows
            if row.lienAchat and (not allowed_domains or urlparse(row.lienAchat).netloc in allowed_domains)
        ]
        verified_urls = list(dict.fromkeys(sync_stats.get("verified_urls", []) + recently_verified_urls))

        # 4. Recherche des articles
        grouped_items = ProductSearchService.search_products_by_criteria(
            db=db,
            criteres=criteres,
            user_gender=effective_genre,
            excluded_product_ids=excluded_product_ids or [],
            verified_product_urls=verified_urls
        )

        # 5. Composition des tenues
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
                categorieNom=it.type_vetement.categorie.nom if (it.type_vetement and it.type_vetement.categorie) else "Mode",
                verifieLe=it.dateDerniereSynchro
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
