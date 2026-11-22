"""
Validation stricte des URLs produit et déduplication pour l'AI Shopper Wearia.
Garantit :
- Aucun lien inventé, vide, local, placeholder ou page de catégorie générique
- Normalisation canonique des URLs (suppression tracking UTM & fragments de taille)
- Vérification HTTP optionnelle avec cache TTL (filtrage des liens morts 404/410/5xx)
- Clés de déduplication strictes (ID, URL canonique, (vendeur, nom, couleur))
"""

import asyncio
import logging
import re
import time
import unicodedata
from typing import Dict, Iterable, List, Optional, Set, Tuple
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse

import httpx

logger = logging.getLogger(__name__)

# Domaines explicitement interdits (démo, locaux, placeholders)
_BLOCKED_HOSTS = {
    "localhost",
    "127.0.0.1",
    "0.0.0.0",
    "example.com",
    "www.example.com",
    "example.org",
    "example.net",
    "test.com",
    "shop.example",
    "placeholder.com",
}

# Paramètres de tracking à retirer lors de la normalisation d'URL
_TRACKING_PARAMS = {
    "utm_source", "utm_medium", "utm_campaign", "utm_term", "utm_content",
    "fbclid", "gclid", "mc_cid", "mc_eid", "ref", "source",
}

# Motifs connus de pages de catégories génériques (non fiches produit directes)
_CATEGORY_URL_PATTERNS = (
    re.compile(r"-c\d+\.html$", re.IGNORECASE),        # Pull&Bear / Bershka category URLs
    re.compile(r"-l\d+\.html$", re.IGNORECASE),        # Zara category URLs
    re.compile(r"/categorie-produit/", re.IGNORECASE), # WooCommerce category listing
    re.compile(r"/collections/(?:all|homme|femme)/?$", re.IGNORECASE),
)

# Titres d'un seul mot trop génériques (ex: "Chemise", "T-Shirt" sur Exist)
_GENERIC_SINGLE_TITLES = {
    "chemise", "t shirt", "tshirt", "pantalon", "jean", "veste", "pull",
    "sweat", "polo", "short", "jupe", "robe", "basket", "baskets", "manteau",
    "sur chemise", "pantalon en denim",
}

# Cache TTL de vérification HTTP des URLs : {canonical_url: (is_alive, checked_timestamp)}
_URL_HEALTH_CACHE: Dict[str, Tuple[bool, float]] = {}
_URL_CACHE_TTL_SECONDS = 1800  # 30 minutes


def normalize_text(value: Optional[str]) -> str:
    if not value:
        return ""
    ascii_text = unicodedata.normalize("NFKD", value.lower()).encode("ascii", "ignore").decode("ascii")
    return re.sub(r"[^a-z0-9]+", " ", ascii_text).strip()


def normalize_product_url(url: Optional[str], keep_color_fragment: bool = True) -> str:
    """
    Normalise une URL produit pour la comparaison et la déduplication :
    - Schéma + domaine en minuscules
    - Suppression des paramètres de tracking (utm_*, fbclid, ...)
    - Suppression des slashs finaux superflus
    - Nettoyage des fragments de taille PrestaShop (#/1032-taille-xl/7817-couleur-xxx)
      afin de regrouper deux tailles d'un même article comme un seul produit.
    """
    if not url or not isinstance(url, str):
        return ""
    raw = url.strip()
    if not raw or any(ch.isspace() for ch in raw):
        return ""

    parsed = urlparse(raw)
    if parsed.scheme.lower() not in ("http", "https") or not parsed.netloc:
        return ""

    scheme = parsed.scheme.lower()
    netloc = parsed.netloc.lower().rstrip(".")
    path = re.sub(r"/{2,}", "/", parsed.path or "/").rstrip("/") or "/"

    # Filtrer les paramètres de tracking
    clean_query_pairs = [
        (k, v) for k, v in parse_qsl(parsed.query, keep_blank_values=False)
        if k.lower() not in _TRACKING_PARAMS
    ]
    query = urlencode(sorted(clean_query_pairs))

    # Gérer le fragment PrestaShop : retirer le segment taille, conserver éventuellement la couleur
    fragment = ""
    if keep_color_fragment and parsed.fragment:
        parts = [p for p in parsed.fragment.split("/") if p]
        color_parts = [p for p in parts if "couleur" in p.lower() or "color" in p.lower()]
        if color_parts:
            fragment = "/" + "/".join(p.lower() for p in color_parts)

    return urlunparse((scheme, netloc, path, "", query, fragment))


def is_valid_product_url(
    url: Optional[str],
    allowed_domains: Optional[Set[str]] = None,
    require_https: bool = True,
) -> Tuple[bool, str]:
    """
    Valide rigoureusement qu'une URL produit est réelle, bien formée et exploitable :
    - Schéma https (ou http si require_https=False)
    - Domaine valide avec TLD, hors domaines locaux/placeholder
    - Chemin non vide (pas une page d'accueil racine "/")
    - Pas d'URL de page catégorie générique
    - Optionnellement restreinte aux domaines boutiques autorisés
    """
    if not url or not isinstance(url, str):
        return False, "url_vide"

    raw = url.strip()
    if not raw or any(ch.isspace() for ch in raw):
        return False, "url_espaces_invalides"

    try:
        parsed = urlparse(raw)
    except Exception:
        return False, "url_malformee"

    scheme = parsed.scheme.lower()
    if require_https and scheme != "https":
        return False, f"schema_non_https:{scheme}"
    if not require_https and scheme not in ("http", "https"):
        return False, f"schema_invalide:{scheme}"

    host = (parsed.hostname or "").lower().strip(".")
    if not host or "." not in host or host in _BLOCKED_HOSTS:
        return False, f"domaine_invalide:{host}"

    if allowed_domains:
        normalized_allowed = {d.lower().strip(".") for d in allowed_domains if d}
        if host not in normalized_allowed:
            return False, f"domaine_non_autorise:{host}"

    path = (parsed.path or "").strip()
    if not path or path == "/":
        return False, "chemin_vide_racine"

    for pattern in _CATEGORY_URL_PATTERNS:
        if pattern.search(path):
            return False, "url_categorie_generique"

    return True, "ok"


async def verify_urls_status(
    urls: Iterable[str],
    timeout: float = 4.0,
    max_concurrency: int = 6,
) -> Dict[str, Optional[bool]]:
    """
    Vérifie l'accessibilité réelle d'un lot d'URLs via HEAD (repli GET si 405/403)
    avec cache TTL de 30 minutes.
    Retourne pour chaque URL :
    - True  : URL valide et accessible (HTTP 2xx/3xx)
    - False : URL invalide ou lien mort confirmé (HTTP 4xx/5xx)
    - None  : Vérification impossible (timeout ou coupure réseau, sans erreur HTTP confirmée)
    """
    now = time.time()
    results: Dict[str, Optional[bool]] = {}
    to_check: List[Tuple[str, str]] = []

    for raw_url in urls:
        valid, _ = is_valid_product_url(raw_url)
        if not valid:
            results[raw_url] = False
            continue
        base_url = raw_url.split("#", 1)[0]
        cached = _URL_HEALTH_CACHE.get(base_url)
        if cached and (now - cached[1]) < _URL_CACHE_TTL_SECONDS:
            results[raw_url] = cached[0]
        else:
            to_check.append((raw_url, base_url))

    if not to_check:
        return results

    semaphore = asyncio.Semaphore(max_concurrency)
    headers = {
        "User-Agent": "WeariaShopperBot/1.0 (+https://wearia.app)",
        "Accept": "text/html,application/xhtml+xml;q=0.9,*/*;q=0.8",
    }

    async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
        async def _probe(raw_url: str, base_url: str) -> Tuple[str, str, Optional[bool]]:
            async with semaphore:
                try:
                    resp = await client.head(base_url, headers=headers)
                    if resp.status_code in (403, 405):
                        resp = await client.get(base_url, headers=headers)
                    alive = 200 <= resp.status_code < 400
                    if not alive:
                        logger.warning(f"[URL-CHECK] Lien mort HTTP {resp.status_code} : {base_url}")
                    return raw_url, base_url, alive
                except httpx.TimeoutException:
                    logger.debug(f"[URL-CHECK] Timeout sur {base_url}")
                    return raw_url, base_url, None
                except Exception as exc:
                    logger.debug(f"[URL-CHECK] Erreur réseau sur {base_url} : {exc}")
                    return raw_url, base_url, None

        checked = await asyncio.gather(*(_probe(r, b) for r, b in to_check))
        for raw_url, base_url, alive in checked:
            if alive is not None:
                _URL_HEALTH_CACHE[base_url] = (alive, time.time())
            results[raw_url] = alive

    return results


async def verify_urls_live(
    urls: Iterable[str],
    timeout: float = 4.0,
    max_concurrency: int = 6,
) -> Dict[str, bool]:
    """Compatibilité booléenne : True uniquement si HTTP 2xx/3xx confirmé."""
    statuses = await verify_urls_status(urls, timeout=timeout, max_concurrency=max_concurrency)
    return {url: bool(status) for url, status in statuses.items()}


def build_product_dedup_keys(
    product_id: Optional[int],
    name: Optional[str],
    vendor: Optional[str],
    color: Optional[str],
    url: Optional[str],
) -> Dict[str, str]:
    """
    Construit les 3 clés de déduplication strictes d'un article :
    - id_key : identifiant produit unique
    - url_key : URL normalisée (sans tracking ni taille)
    - identity_key : (vendeur, nom normalisé, couleur) si le nom est spécifique
      (si le nom est générique type "Chemise", s'appuie sur url_key pour ne pas
       fusionner deux chemises distinctes du même vendeur).
    """
    url_key = normalize_product_url(url, keep_color_fragment=True)
    norm_name = normalize_text(name)
    norm_vendor = normalize_text(vendor)
    norm_color = normalize_text(color)

    if norm_name in _GENERIC_SINGLE_TITLES or len(norm_name) <= 4:
        identity_key = f"{norm_vendor}|{norm_name}|{norm_color}|{url_key}"
    else:
        identity_key = f"{norm_vendor}|{norm_name}|{norm_color}"

    return {
        "id_key": str(product_id) if product_id is not None else "",
        "url_key": url_key,
        "identity_key": identity_key,
    }
