import asyncio
import logging
import zlib
from datetime import datetime
from types import SimpleNamespace
from typing import Any, Dict, List, Optional, Set
from urllib.parse import urlparse

from sqlalchemy.orm import Session

from app.ai.shopper_llm import (
    ShopperLLMManager,
    normalize_shopper_occasion,
    normalize_shopper_season,
    normalize_shopper_style,
)
from app.models.referentials import StyleVestimentaire
from app.models.user import Utilisateur
from app.schemas.shopper import ShopperArticle, ShopperCriteria, ShopperResultResponse
from app.scraper.normalizer import DataNormalizer
from app.scraper.scraper_service import ScraperService
from app.services.product_search_service import (
    extract_excluded_type_mentions,
    extract_requested_type_mentions,
    resolve_canonical_requested_type,
    search_individual_articles,
)
from app.services.shopper_validation import (
    is_valid_product_url,
    normalize_product_url,
)

logger = logging.getLogger(__name__)


def _merge_unique_str(primary: Optional[List[str]], secondary: Optional[List[str]]) -> List[str]:
    merged: List[str] = []
    seen: Set[str] = set()
    for src in (primary or [], secondary or []):
        for val in src:
            clean = (val or "").strip()
            if clean and clean.lower() not in seen:
                seen.add(clean.lower())
                merged.append(clean)
    return merged


def _stable_live_product_id(url: str) -> int:
    """Génère un identifiant entier positif déterministe à partir de l'URL produit canonique."""
    norm = normalize_product_url(url) or url
    return (zlib.crc32(norm.encode("utf-8")) & 0x7FFFFFFF) or 1


class ShopperOrchestrator:
    """
    Orchestrateur AI Shopper en mode SCRAPING IMMÉDIAT À LA DEMANDE :
    - Ne dépend pas d'articles pré-stockés / périmés en base de données
    - Lance immédiatement une recherche live sur les boutiques e-commerce autorisées
      correspondant au genre du compte (HOMME ou FEMME) et au type demandé (pull, pantalon, robe, sac...)
    - Normalise les fiches produit extraites en temps réel à l'aide des référentiels BDD
      (StyleVestimentaire, TypeVetement, Couleur)
    - Filtre strictement par type demandé, genre, style BDD, couleurs préférées/évitées, budget max
      et déduplique les résultats avant retour API.
    """

    def __init__(self):
        self.llm_manager = ShopperLLMManager()
        self.scraper_service = ScraperService()

    def _build_live_candidate(
        self,
        raw: Dict[str, Any],
        db: Session,
        now: datetime,
    ) -> Optional[SimpleNamespace]:
        nom = (raw.get("nom") or "").strip()
        lien_achat = (raw.get("lienAchat") or "").strip()
        prix = DataNormalizer.parse_price(raw.get("prix"))
        if not nom or not lien_achat or prix <= 0:
            return None

        desc = (raw.get("description") or "").strip()
        raw_color = (raw.get("couleur_brute") or "").strip()

        type_obj = DataNormalizer.match_type_vetement(nom, desc, db)
        color_obj = DataNormalizer.match_couleur(nom, desc, db, raw_color=raw_color)
        style_obj = DataNormalizer.match_style(nom, desc, db)

        if not type_obj:
            return None

        return SimpleNamespace(
            id=_stable_live_product_id(lien_achat),
            nom=nom,
            description=desc,
            imageUrl=(raw.get("imageUrl") or "").strip(),
            lienAchat=lien_achat,
            prix=prix,
            devise="TND",
            vendeur=(raw.get("vendeur") or "Boutique").strip(),
            taillesDisponibles=(raw.get("taillesDisponibles") or "Selon boutique").strip(),
            enStock=True,
            dateDerniereSynchro=now,
            type_vetement=type_obj,
            couleur=color_obj,
            style=style_obj,
        )

    async def process_request(
        self,
        prompt: str,
        db: Session,
        user: Optional[Utilisateur] = None,
        forced_genre: Optional[str] = None,
        forced_budget: Optional[float] = None,
        type_vetement: Optional[str] = None,
        style_id: Optional[int] = None,
        occasion: Optional[str] = None,
        style: Optional[str] = None,
        colors: Optional[List[str]] = None,
        avoided_colors: Optional[List[str]] = None,
        requested_types: Optional[List[str]] = None,
        season: Optional[str] = None,
        excluded_types: Optional[List[str]] = None,
        excluded_product_ids: Optional[List[int]] = None,
        excluded_urls: Optional[List[str]] = None,
        max_results: int = 12,
    ) -> ShopperResultResponse:
        # 1. Genre effectif du compte connecté
        effective_genre = (forced_genre or "").strip().upper()
        if not effective_genre and user and user.genre:
            effective_genre = user.genre.value.upper()
        if effective_genre not in ("HOMME", "FEMME"):
            effective_genre = "HOMME"

        # 2. Résolution du style sélectionné depuis la base de données
        resolved_style_name = (style or "").strip()
        if style_id is not None:
            try:
                db_style = db.query(StyleVestimentaire).filter(StyleVestimentaire.id == style_id).first()
                if db_style and getattr(db_style, "libelle", None):
                    resolved_style_name = db_style.libelle.strip()
            except Exception as exc:
                logger.debug(f"[AI SHOPPER] Impossible de résoudre style_id={style_id} : {exc}")

        # 3. Type de vêtement demandé
        effective_type = (type_vetement or "").strip()
        if not effective_type and requested_types:
            effective_type = next((t.strip() for t in requested_types if t and t.strip()), "")
        if not effective_type and prompt:
            extracted_mentions = extract_requested_type_mentions(prompt)
            if extracted_mentions:
                effective_type = extracted_mentions[0]

        effective_prompt = (prompt or "").strip()
        if not effective_prompt:
            prompt_parts = [effective_type or "Article"]
            if resolved_style_name:
                prompt_parts.append(f"style {resolved_style_name}")
            if forced_budget and forced_budget > 0:
                prompt_parts.append(f"budget {forced_budget:.0f} TND")
            effective_prompt = " · ".join(prompt_parts)

        # 4. Consolidation des critères (type, style BDD, couleurs préférées/évitées, budget)
        logger.info(
            f"[AI SHOPPER LIVE] Requête : type='{effective_type}' style='{resolved_style_name}' "
            f"genre={effective_genre} budget={forced_budget} colors={colors} avoided={avoided_colors}"
        )
        criteres = await self.llm_manager.interpret(effective_prompt, user_genre=effective_genre)

        if forced_budget is not None and forced_budget > 0:
            criteres.budget = float(forced_budget)
        if occasion:
            criteres.occasion = normalize_shopper_occasion(occasion)
        if resolved_style_name:
            criteres.style = (
                resolved_style_name
                if resolved_style_name.lower() in ("tous", "all", "tous les styles")
                else normalize_shopper_style(resolved_style_name)
            )
        else:
            criteres.style = "Tous"
        criteres.season = normalize_shopper_season(season or criteres.season)

        merged_avoided = _merge_unique_str(avoided_colors, criteres.avoided_colors)
        avoided_lower = {c.lower() for c in merged_avoided}
        merged_colors = [
            c for c in _merge_unique_str(colors, criteres.colors)
            if c.lower() not in avoided_lower
        ]
        criteres.colors = merged_colors
        criteres.avoided_colors = merged_avoided

        merged_excluded_types = _merge_unique_str(excluded_types, extract_excluded_type_mentions(effective_prompt))
        criteres.excluded_types = merged_excluded_types

        if effective_type:
            criteres.requested_types = [effective_type]
            criteres.types_vetement = [effective_type]

        # 5. Sélection des boutiques correspondant au genre du compte connecté
        matching_scrapers = [
            scraper
            for scraper in self.scraper_service.scrapers
            if not (effective_genre == "HOMME" and "femme" in scraper.store_name.lower())
            and not (effective_genre == "FEMME" and "homme" in scraper.store_name.lower())
        ]
        allowed_domains: Set[str] = {
            (urlparse(scraper.base_url).hostname or "").lower()
            for scraper in matching_scrapers
        }
        allowed_domains.discard("")

        # 6. SCRAPING IMMÉDIAT EN DIRECT selon la demande exacte de l'utilisateur
        query_term = effective_type or (criteres.types_vetement[0] if criteres.types_vetement else effective_prompt)
        excluded_url_set = set(excluded_urls or [])

        async def _scrape_one(scraper):
            if hasattr(scraper, "search_live_products"):
                return await scraper.search_live_products(
                    query_type=query_term,
                    colors=criteres.colors,
                    extra_keywords=[],
                    excluded_urls=excluded_url_set,
                    limit=max(max_results + 6, 18),
                )
            return await scraper.scrape_products(limit=max_results)

        scraped_batches = await asyncio.gather(*(_scrape_one(s) for s in matching_scrapers), return_exceptions=True)

        now = datetime.utcnow()
        live_candidates: List[SimpleNamespace] = []
        verified_live_urls: List[str] = []

        for batch in scraped_batches:
            if isinstance(batch, Exception):
                logger.warning(f"[AI SHOPPER LIVE] Erreur scraper : {batch}")
                continue
            for raw in batch:
                url = (raw.get("lienAchat") or "").strip()
                url_ok, _ = is_valid_product_url(url, allowed_domains=allowed_domains or None, require_https=True)
                if not url_ok or not raw.get("verified_product_page", False):
                    continue
                candidate = self._build_live_candidate(raw, db, now)
                if candidate is not None:
                    live_candidates.append(candidate)
                    verified_live_urls.append(url)

        logger.info(
            f"[AI SHOPPER LIVE] {len(live_candidates)} article(s) scrapé(s) en direct "
            f"pour '{query_term}' (genre={effective_genre})"
        )

        # 7. Filtrage strict, scoring & déduplication sur les articles scrapés en direct
        matched_items = search_individual_articles(
            articles=live_candidates,
            requested_type=effective_type or None,
            criteres=criteres,
            user_gender=effective_genre,
            excluded_product_ids=excluded_product_ids or [],
            excluded_urls=excluded_urls or [],
            allowed_domains=allowed_domains or None,
            verified_product_urls=verified_live_urls,
            max_results=max_results,
        )

        budget_max = criteres.budget if (criteres.budget and criteres.budget > 0) else None
        articles_dto: List[ShopperArticle] = []
        for it, score, explanation in matched_items:
            url_ok, _ = is_valid_product_url(it.lienAchat, allowed_domains=allowed_domains or None, require_https=True)
            if not url_ok or not it.lienAchat:
                continue
            prix_val = round(float(it.prix or 0.0), 2)
            articles_dto.append(
                ShopperArticle(
                    id=it.id,
                    nom=it.nom,
                    imageUrl=it.imageUrl or "",
                    lienAchat=it.lienAchat.strip(),
                    prix=prix_val,
                    devise=it.devise or "TND",
                    vendeur=it.vendeur or "Boutique",
                    taillesDisponibles=it.taillesDisponibles or "Selon boutique",
                    typeVetementNom=it.type_vetement.nom if it.type_vetement else (effective_type or "Article"),
                    couleurNom=it.couleur.nom if it.couleur else "Neutre",
                    categorieNom=(
                        it.type_vetement.categorie.nom
                        if (it.type_vetement and it.type_vetement.categorie)
                        else "Mode"
                    ),
                    styleNom=it.style.libelle if it.style else None,
                    scoreCompatibilite=score,
                    respecteBudget=(budget_max is None or prix_val <= budget_max),
                    explication=explanation,
                    verifieLe=it.dateDerniereSynchro,
                )
            )

        logger.info(
            f"[AI SHOPPER LIVE] Résultat final : {len(articles_dto)} proposition(s) "
            f"| type='{effective_type or resolve_canonical_requested_type(effective_type)}' | genre={effective_genre}"
        )

        return ShopperResultResponse(
            prompt=effective_prompt,
            criteres=criteres,
            articles=articles_dto,
            nbArticlesTrouves=len(articles_dto),
            typeDemande=effective_type or None,
            styleDemande=resolved_style_name or criteres.style,
            genreUtilise=effective_genre,
            budgetMax=budget_max,
            tenues=[],
            articlesComplementaires=[],
            nbTenuesTrouvees=0,
        )
