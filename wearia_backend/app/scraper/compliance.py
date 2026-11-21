import asyncio
import logging
import random
import urllib.robotparser
from urllib.parse import urlparse
import httpx

logger = logging.getLogger(__name__)

USER_AGENT = "WeariaBot/1.0 (+https://wearia.app/bot; AI Shopper Academic Project)"

class ComplianceManager:
    """
    Gestionnaire de conformité éthique et légale pour le scraping :
    - Vérifie robots.txt avant toute requête
    - Respecte les directives Disallow / Allow
    - Applique des délais polis (rate limiting) pour ne pas saturer les serveurs cibles
    - Ne contourne aucun système de protection technique
    """
    def __init__(self, user_agent: str = USER_AGENT):
        self.user_agent = user_agent
        self._parsers = {}

    async def can_fetch(self, url: str) -> bool:
        """
        Vérifie si l'URL est autorisée selon le robots.txt du domaine.
        """
        try:
            parsed = urlparse(url)
            domain = f"{parsed.scheme}://{parsed.netloc}"

            if domain not in self._parsers:
                robots_url = f"{domain}/robots.txt"
                rp = urllib.robotparser.RobotFileParser()
                async with httpx.AsyncClient(timeout=5.0) as client:
                    try:
                        res = await client.get(robots_url, headers={"User-Agent": self.user_agent})
                        if res.status_code == 200:
                            rp.parse(res.text.splitlines())
                        else:
                            # Si 404 sur robots.txt, la racine autorise par défaut
                            rp.allow_all = True
                    except Exception as e:
                        logger.warning(f"Impossible de récupérer robots.txt pour {domain} ({e}), accès prudent supposé.")
                        rp.allow_all = True
                self._parsers[domain] = rp

            rp = self._parsers[domain]
            is_allowed = rp.can_fetch(self.user_agent, url)
            if not is_allowed:
                logger.warning(f"[ROBOTS.TXT DISALLOW] Scraping bloqué par conformité pour : {url}")
            return is_allowed
        except Exception as e:
            logger.error(f"Erreur vérification conformité pour {url}: {e}")
            return False

    async def polite_delay(self, min_seconds: float = 1.0, max_seconds: float = 2.0):
        """
        Pause courtoise aléatoire entre deux requêtes e-commerce.
        """
        delay = random.uniform(min_seconds, max_seconds)
        await asyncio.sleep(delay)
