import logging
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
import httpx
from bs4 import BeautifulSoup
from app.scraper.compliance import ComplianceManager, USER_AGENT

logger = logging.getLogger(__name__)

class BaseStoreScraper(ABC):
    """
    Classe de base abstraite pour scraper un site e-commerce de prêt-à-porter.
    """
    def __init__(self, store_name: str, base_url: str):
        self.store_name = store_name
        self.base_url = base_url.rstrip("/")
        self.compliance = ComplianceManager(user_agent=USER_AGENT)

    @abstractmethod
    async def scrape_products(self, limit: int = 20) -> List[Dict[str, Any]]:
        """
        Extrait une liste de dictionnaires produits :
        {
            "nom": str,
            "description": str,
            "imageUrl": str,
            "lienAchat": str,
            "prix": float,
            "vendeur": str,
            "taillesDisponibles": str,
            "couleur_brute": str,
            "categorie_brute": str
        }
        """
        pass

    async def fetch_html(self, url: str) -> Optional[str]:
        """
        Télécharge le code HTML d'une page en respectant robots.txt et délais polis.
        """
        if not await self.compliance.can_fetch(url):
            logger.warning(f"URL non autorisée par le robots.txt : {url}")
            return None

        await self.compliance.polite_delay()

        headers = {
            "User-Agent": USER_AGENT,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "fr-FR,fr;q=0.9,en-US;q=0.8,en;q=0.7",
        }

        try:
            async with httpx.AsyncClient(timeout=10.0, follow_redirects=True) as client:
                res = await client.get(url, headers=headers)
                if res.status_code == 200:
                    return res.text
                else:
                    logger.warning(f"HTTP {res.status_code} pour l'URL {url}")
                    return None
        except Exception as e:
            logger.error(f"Erreur requête HTTP {url}: {e}")
            return None
