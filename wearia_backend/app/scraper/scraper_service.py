import logging
from datetime import datetime
from typing import List, Dict, Any
from sqlalchemy.orm import Session
from app.models.shopping import ArticleCatalogue
from app.core.config import settings
from app.scraper.normalizer import DataNormalizer
from app.scraper.stores.fashion_store_scraper import MicrodataFashionScraper
from app.services.shopper_validation import is_valid_product_url, normalize_product_url

logger = logging.getLogger(__name__)

class ScraperService:
    """
    Service coordinateur du scraping e-commerce :
    - Lance les scrapers configurés
    - Normalise chaque produit
    - Synchronise et persiste les produits dans `articles_catalogue`
    """
    def __init__(self):
        # Configure authorized, real shops through WEARIA_SHOPPER_STORES:
        # "Shop|https://shop.example|/catalog,/men"; semicolon separates shops.
        # Do not seed the product catalogue with hand-written/demo product claims.
        self.scrapers = []
        for entry in settings.WEARIA_SHOPPER_STORES.split(";"):
            parts = [part.strip() for part in entry.split("|", 2)]
            if len(parts) == 3 and parts[0] and parts[1].startswith("https://"):
                paths = [path.strip() for path in parts[2].split(",") if path.strip()]
                self.scrapers.append(MicrodataFashionScraper(parts[0], parts[1], paths))

    async def run_sync(self, db: Session, limit_per_store: int = 50, target_gender: str = None) -> Dict[str, Any]:
        stats = {"total_scraped": 0, "articles_ajoutes": 0, "articles_mis_a_jour": 0, "erreurs": 0, "verified_urls": []}

        for scraper in self.scrapers:
            source_name = scraper.store_name.lower()
            if target_gender == "HOMME" and "femme" in source_name:
                continue
            if target_gender == "FEMME" and "homme" in source_name:
                continue
            try:
                logger.info(f"Démarrage du scraping pour {scraper.store_name}...")
                raw_items = await scraper.scrape_products(limit=limit_per_store)
                stats["total_scraped"] += len(raw_items)

                for raw in raw_items:
                    try:
                        nom = raw.get("nom", "").strip()
                        if not nom:
                            continue

                        prix = DataNormalizer.parse_price(raw.get("prix"))
                        image_url = raw.get("imageUrl", "")
                        lien_achat = raw.get("lienAchat", "")
                        vendeur = raw.get("vendeur", scraper.store_name)
                        tailles = raw.get("taillesDisponibles", "S, M, L, XL")
                        desc = raw.get("description", "")

                        # A catalog item is usable only when product metadata supplied a
                        # direct, syntactically valid HTTPS product URL and a positive price.
                        url_ok, url_reason = is_valid_product_url(lien_achat, require_https=True)
                        if (not url_ok or prix <= 0
                                or not raw.get("verified_product_page", False)):
                            logger.debug(f"Article ignoré ('{nom}') : {url_reason}, prix={prix}")
                            continue

                        # Résolution référentiels (utiliser couleur_brute extraite de la fiche/variante !)
                        raw_color = raw.get("couleur_brute", "")
                        type_vetement = DataNormalizer.match_type_vetement(nom, desc, db)
                        couleur = DataNormalizer.match_couleur(nom, desc, db, raw_color=raw_color)
                        style = DataNormalizer.match_style(nom, desc, db)

                        if not type_vetement or not couleur:
                            continue

                        # Vérifier si l'article existe déjà (par lien d'achat exact ou normalisé)
                        existing = None
                        if lien_achat:
                            existing = db.query(ArticleCatalogue).filter(ArticleCatalogue.lienAchat == lien_achat).first()
                        if not existing and lien_achat:
                            norm_target = normalize_product_url(lien_achat)
                            base_url = lien_achat.split("#", 1)[0]
                            candidates = db.query(ArticleCatalogue).filter(
                                ArticleCatalogue.lienAchat.like(f"{base_url}%")
                            ).all()
                            existing = next(
                                (c for c in candidates if normalize_product_url(c.lienAchat) == norm_target),
                                None,
                            )

                        if existing:
                            existing.nom = nom
                            existing.prix = prix
                            existing.imageUrl = image_url
                            existing.lienAchat = lien_achat
                            existing.taillesDisponibles = tailles
                            existing.vendeur = vendeur
                            existing.enStock = True
                            existing.type_vetement_id = type_vetement.id
                            existing.couleur_id = couleur.id
                            existing.dateDerniereSynchro = datetime.utcnow()
                            if style:
                                existing.style_id = style.id
                            stats["articles_mis_a_jour"] += 1
                        else:
                            new_article = ArticleCatalogue(
                                nom=nom,
                                imageUrl=image_url,
                                lienAchat=lien_achat,
                                prix=prix,
                                vendeur=vendeur,
                                taillesDisponibles=tailles,
                                devise="TND",
                                enStock=True,
                                dateDerniereSynchro=datetime.utcnow(),
                                type_vetement_id=type_vetement.id,
                                couleur_id=couleur.id,
                                style_id=style.id if style else None
                            )
                            db.add(new_article)
                            stats["articles_ajoutes"] += 1
                        stats["verified_urls"].append(lien_achat)

                    except Exception as e_item:
                        logger.error(f"Erreur enregistrement produit '{raw.get('nom')}': {e_item}")
                        stats["erreurs"] += 1

                db.commit()
            except Exception as e_scraper:
                logger.error(f"Erreur exécution scraper {scraper.store_name}: {e_scraper}")
                stats["erreurs"] += 1

        logger.info(f"Fin de synchronisation e-commerce : {stats}")
        return stats
