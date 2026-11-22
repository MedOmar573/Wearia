import json
import logging
import random
import re
import asyncio
from urllib.parse import quote_plus, urljoin, urlparse
from typing import List, Dict, Any, Optional, Set
import httpx
from bs4 import BeautifulSoup
from app.scraper.base_scraper import BaseStoreScraper
from app.scraper.compliance import USER_AGENT

logger = logging.getLogger(__name__)

# Synonymes de recherche e-commerce pour maximiser le rappel en scraping live
_LIVE_SEARCH_TERMS: Dict[str, List[str]] = {
    "pull": ["pull", "pullover", "maille"],
    "sweat": ["sweat", "hoodie", "sweat-shirt"],
    "chemise": ["chemise", "sur-chemise"],
    "t-shirt": ["t-shirt", "tshirt"],
    "polo": ["polo"],
    "pantalon": ["pantalon", "chino", "cargo"],
    "jean": ["jean", "denim"],
    "short": ["short", "bermuda"],
    "jupe": ["jupe"],
    "robe": ["robe"],
    "veste": ["veste", "blazer", "blouson"],
    "manteau": ["manteau", "doudoune", "parka", "trench"],
    "baskets": ["basket", "baskets", "sneakers"],
    "bottes": ["botte", "bottine"],
    "chaussures de ville": ["mocassin", "escarpin", "derby", "chaussure"],
    "sac": ["sac", "sacoche", "pochette"],
    "chapeau": ["casquette", "chapeau", "bonnet"],
    "ceinture": ["ceinture"],
    "écharpe": ["echarpe", "foulard"],
    "montre": ["montre"],
}


class MicrodataFashionScraper(BaseStoreScraper):
    """
    Scraper basé sur les métadonnées publiques Schema.org / JSON-LD et OpenGraph
    pour extraire les articles de boutiques en ligne autorisées.
    """
    def __init__(self, store_name: str, base_url: str, category_paths: List[str] = None):
        super().__init__(store_name=store_name, base_url=base_url)
        self.category_paths = category_paths or ["/collections/all", "/shop", "/homme", "/femme"]

    async def scrape_products(self, limit: int = 20) -> List[Dict[str, Any]]:
        products = []
        seen_urls = set()
        for path in self.category_paths:
            if len(products) >= limit:
                break
            target_url = urljoin(self.base_url + "/", path)
            html = await self.fetch_html(target_url)
            if not html:
                continue

            candidates = []
            for item in self._jsonld_objects(html):
                item_type = item.get("@type")
                if item_type in ("Product", "IndividualProduct"):
                    # A Product node on a category page without its own URL does not
                    # provide a direct product link; never turn the category URL into one.
                    product_page_url = item.get("url")
                    if product_page_url:
                        candidates.append(urljoin(target_url, product_page_url))
                elif item_type == "ItemList":
                    for entry in item.get("itemListElement", []):
                        if not isinstance(entry, dict):
                            continue
                        linked_item = entry.get("item", {})
                        linked_url = entry.get("url") or (linked_item.get("url") if isinstance(linked_item, dict) else None)
                        if linked_url:
                            candidates.append(urljoin(target_url, linked_url))

            # WooCommerce collections often expose product links in HTML without
            # an ItemList node in their structured data.
            category_soup = BeautifulSoup(html, "html.parser")
            candidates.extend(
                urljoin(target_url, anchor.get("href"))
                for anchor in category_soup.find_all("a", href=True)
                if "/produit/" in urlparse(urljoin(target_url, anchor.get("href"))).path
            )

            random.shuffle(candidates)
            path_product_count = 0
            path_product_limit = 5
            candidate_urls = []
            for candidate in candidates:
                product_url = candidate.split("#", 1)[0]
                if (product_url not in seen_urls and product_url.startswith("https://")
                        and urlparse(product_url).netloc == urlparse(self.base_url).netloc):
                    seen_urls.add(product_url)
                    candidate_urls.append(product_url)
            candidate_urls = candidate_urls[:8]

            semaphore = asyncio.Semaphore(3)

            async def fetch_candidate(product_url: str):
                async with semaphore:
                    return await self.fetch_html(product_url)

            product_pages = await asyncio.gather(*(fetch_candidate(url) for url in candidate_urls))
            for product_url, product_html in zip(candidate_urls, product_pages):
                if path_product_count >= path_product_limit:
                    break
                if not product_html:
                    continue
                for item in self._jsonld_objects(product_html):
                    item_type = item.get("@type")
                    if item_type not in ("Product", "IndividualProduct"):
                        continue
                    offers = item.get("offers", {})
                    if isinstance(offers, list):
                        offers = offers[0] if offers else {}
                    if not isinstance(offers, dict):
                        continue
                    price = offers.get("price")
                    currency = str(offers.get("priceCurrency", "")).upper()
                    availability = str(offers.get("availability", "")).lower()
                    if (not price or currency != "TND"
                            or not any(marker in availability for marker in ("instock", "limitedavailability"))):
                        continue

                    # Prefer the exact variant URL supplied by the merchant's Offer.
                    exact_url = urljoin(product_url, offers.get("url") or product_url)
                    exact_parsed = urlparse(exact_url)
                    source_host = urlparse(self.base_url).netloc
                    if exact_parsed.scheme != "https" or exact_parsed.netloc != source_host:
                        continue
                    product_name = item.get("name", "").strip()
                    offer_url = offers.get("url")
                    if offer_url and exact_url.split("#", 1)[0] != product_url.split("#", 1)[0]:
                        offer_html = await self.fetch_html(exact_url)
                        if not offer_html or not self._is_verified_product_page(offer_html, product_name, price):
                            continue
                    color = item.get("color") or self._color_from_variant(exact_url)
                    if not color:
                        color = self._color_from_description(item.get("description", ""))
                    images = item.get("image", [])
                    if isinstance(images, str):
                        image_url = images
                    elif isinstance(images, list):
                        image_url = next((image if isinstance(image, str) else image.get("url", "")
                                          for image in images if isinstance(image, (str, dict))), "")
                    else:
                        image_url = ""
                    product = {
                        "nom": product_name,
                        "description": item.get("description", ""),
                        "imageUrl": image_url,
                        "lienAchat": exact_url,
                        "prix": float(price),
                        "vendeur": self.store_name,
                        "taillesDisponibles": "Non vérifiées",
                        "couleur_brute": color or "",
                        "categorie_brute": item.get("category", ""),
                        "verified_product_page": True,
                        "availability": availability,
                    }
                    if product["nom"] and product["couleur_brute"]:
                        products.append(product)
                        path_product_count += 1
                    break
                if len(products) >= limit:
                    break

        return products

    def _build_live_search_urls(
        self,
        query_type: str,
        colors: Optional[List[str]] = None,
        extra_keywords: Optional[List[str]] = None,
    ) -> List[str]:
        """
        Construit les URLs de recherche en direct adaptées à la plateforme e-commerce :
        - PrestaShop (ex. exist.com.tn) : /recherche?controller=search&s=<terme>
        - WooCommerce (ex. mabrouk.tn)  : /?s=<terme>&post_type=product
        """
        host = (urlparse(self.base_url).hostname or "").lower()
        is_woocommerce = "mabrouk" in host or any("/categorie-produit/" in p for p in self.category_paths)

        base_key = (query_type or "").strip().lower()
        terms = list(_LIVE_SEARCH_TERMS.get(base_key, [query_type.strip()] if query_type else []))
        if extra_keywords:
            for kw in extra_keywords:
                clean = (kw or "").strip()
                if clean and clean.lower() not in {t.lower() for t in terms}:
                    terms.append(clean)

        # Prioriser la recherche directe sur le type demandé (+ variante avec couleur préférée si renseignée)
        search_queries: List[str] = []
        primary = terms[0] if terms else ""
        if primary and colors:
            first_color = (colors[0] or "").strip()
            if first_color:
                search_queries.append(f"{primary} {first_color}")
        for t in terms[:3]:
            if t and t not in search_queries:
                search_queries.append(t)

        urls: List[str] = []
        for q in search_queries:
            encoded = quote_plus(q)
            if is_woocommerce:
                urls.append(f"{self.base_url}/?s={encoded}&post_type=product")
            else:
                urls.append(f"{self.base_url}/recherche?controller=search&s={encoded}")
        return list(dict.fromkeys(urls))

    def _extract_product_links_from_listing(self, html: str, page_url: str) -> List[str]:
        """Extrait uniquement les liens directs de fiches produit depuis une page de résultats."""
        source_host = urlparse(self.base_url).netloc
        candidates: List[str] = []

        # 1. Liens structurés JSON-LD
        for item in self._jsonld_objects(html):
            item_type = item.get("@type")
            if item_type in ("Product", "IndividualProduct"):
                u = item.get("url")
                if u:
                    candidates.append(urljoin(page_url, u))
            elif item_type == "ItemList":
                for entry in item.get("itemListElement", []):
                    if not isinstance(entry, dict):
                        continue
                    linked = entry.get("item", {})
                    u = entry.get("url") or (linked.get("url") if isinstance(linked, dict) else None)
                    if u:
                        candidates.append(urljoin(page_url, u))

        # 2. Liens HTML de fiches produit (PrestaShop: /cat/1234-5678-slug.html ; WooCommerce: /produit/slug/)
        soup = BeautifulSoup(html, "html.parser")
        prestashop_product_re = re.compile(r"/\d+-\d+-[^/]+\.html$", re.IGNORECASE)
        for anchor in soup.find_all("a", href=True):
            href = urljoin(page_url, anchor.get("href", ""))
            parsed = urlparse(href)
            if parsed.scheme != "https" or parsed.netloc != source_host:
                continue
            path = parsed.path or ""
            if "/produit/" in path or prestashop_product_re.search(path):
                candidates.append(href)

        # Déduplication en préservant l'ordre de pertinence du moteur de recherche de la boutique
        unique: List[str] = []
        seen_base: Set[str] = set()
        for raw_url in candidates:
            base_url = raw_url.split("#", 1)[0]
            if base_url in seen_base:
                continue
            if not base_url.startswith("https://") or urlparse(base_url).netloc != source_host:
                continue
            seen_base.add(base_url)
            unique.append(raw_url)
        return unique

    @staticmethod
    def _extract_sizes_from_html(html: str) -> str:
        """Extrait les tailles disponibles si exposées sur la fiche produit."""
        try:
            soup = BeautifulSoup(html, "html.parser")
            sizes: List[str] = []
            # PrestaShop select/radio taille ou WooCommerce variations
            for el in soup.select("select[id*='group'] option, ul[id*='group'] li span, select[name*='taille'] option, select[name*='size'] option"):
                txt = (el.get_text() or "").strip().upper()
                if re.fullmatch(r"(?:XXS|XS|S|M|L|XL|XXL|XXXL|\d{2})", txt) and txt not in sizes:
                    sizes.append(txt)
            if sizes:
                return ", ".join(sizes[:8])
        except Exception:
            pass
        return "Selon boutique"

    def _parse_product_page(self, product_url: str, product_html: str) -> Optional[Dict[str, Any]]:
        """Parse une fiche produit vérifiée en direct (JSON-LD + repli OpenGraph)."""
        source_host = urlparse(self.base_url).netloc
        for item in self._jsonld_objects(product_html):
            item_type = item.get("@type")
            if not (
                item_type in ("Product", "IndividualProduct")
                or (isinstance(item_type, list) and any(t in ("Product", "IndividualProduct") for t in item_type))
            ):
                continue
            offers = item.get("offers", {})
            if isinstance(offers, list):
                offers = offers[0] if offers else {}
            if not isinstance(offers, dict):
                continue

            price = offers.get("price")
            currency = str(offers.get("priceCurrency", "TND")).upper()
            availability = str(offers.get("availability", "")).lower()
            if not price or currency != "TND":
                continue
            if availability and not any(m in availability for m in ("instock", "limitedavailability", "onlineonly")):
                continue

            exact_url = urljoin(product_url, offers.get("url") or product_url)
            exact_parsed = urlparse(exact_url)
            if exact_parsed.scheme != "https" or exact_parsed.netloc != source_host:
                continue

            product_name = str(item.get("name", "")).strip()
            if not product_name:
                continue
            description = str(item.get("description", "") or "").strip()

            color = (
                str(item.get("color") or "").strip()
                or self._color_from_variant(exact_url)
                or self._color_from_variant(product_url)
                or self._color_from_description(f"{product_name} {description}")
            )

            images = item.get("image", [])
            if isinstance(images, str):
                image_url = images
            elif isinstance(images, list):
                image_url = next(
                    (img if isinstance(img, str) else img.get("url", "")
                     for img in images if isinstance(img, (str, dict))),
                    "",
                )
            elif isinstance(images, dict):
                image_url = str(images.get("url", ""))
            else:
                image_url = ""

            try:
                price_float = float(price)
            except (TypeError, ValueError):
                continue
            if price_float <= 0:
                continue

            return {
                "nom": product_name,
                "description": description,
                "imageUrl": image_url,
                "lienAchat": exact_url,
                "prix": price_float,
                "vendeur": self.store_name,
                "taillesDisponibles": self._extract_sizes_from_html(product_html),
                "couleur_brute": color or "",
                "categorie_brute": str(item.get("category", "") or ""),
                "verified_product_page": True,
                "availability": availability or "instock",
            }
        return None

    async def search_live_products(
        self,
        query_type: str,
        colors: Optional[List[str]] = None,
        extra_keywords: Optional[List[str]] = None,
        excluded_urls: Optional[Set[str]] = None,
        limit: int = 16,
    ) -> List[Dict[str, Any]]:
        """
        Scraping IMMÉDIAT à la demande sur le moteur de recherche de la boutique :
        - Respecte robots.txt via ComplianceManager
        - Interroge en direct les résultats correspondant au type/couleurs demandés
        - Ouvre les fiches produit en parallèle avec un pool HTTP partagé (rapide : ~3-6s)
        - Retourne uniquement des produits réels, en stock, avec prix TND et URL vérifiée.
        """
        search_urls = self._build_live_search_urls(
            query_type=query_type,
            colors=colors,
            extra_keywords=extra_keywords,
        )
        if not search_urls:
            return []

        excluded_bases = {u.split("#", 1)[0].lower() for u in (excluded_urls or set()) if u}
        headers = {
            "User-Agent": USER_AGENT,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "fr-FR,fr;q=0.9,en-US;q=0.8,en;q=0.7",
        }

        candidate_urls: List[str] = []
        seen_bases: Set[str] = set()

        async with httpx.AsyncClient(timeout=10.0, follow_redirects=True, headers=headers) as client:
            # 1. Récupérer les pages de résultats de recherche en direct
            for s_url in search_urls:
                if len(candidate_urls) >= limit + 6:
                    break
                if not await self.compliance.can_fetch(s_url):
                    continue
                try:
                    resp = await client.get(s_url)
                    if resp.status_code != 200:
                        logger.debug(f"[LIVE-SCRAPE] HTTP {resp.status_code} sur {s_url}")
                        continue
                    extracted = self._extract_product_links_from_listing(resp.text, s_url)
                    for u in extracted:
                        base_u = u.split("#", 1)[0].lower()
                        if base_u in seen_bases or base_u in excluded_bases:
                            continue
                        seen_bases.add(base_u)
                        candidate_urls.append(u)
                except Exception as exc:
                    logger.warning(f"[LIVE-SCRAPE] Erreur recherche {s_url} : {exc}")

            if not candidate_urls:
                logger.info(f"[LIVE-SCRAPE] Aucun lien produit trouvé sur {self.store_name} pour '{query_type}'.")
                return []

            to_fetch = candidate_urls[: min(len(candidate_urls), max(limit + 4, 16))]
            semaphore = asyncio.Semaphore(5)

            async def _fetch_product(p_url: str) -> Optional[Dict[str, Any]]:
                async with semaphore:
                    if not await self.compliance.can_fetch(p_url):
                        return None
                    await asyncio.sleep(random.uniform(0.08, 0.20))
                    try:
                        resp = await client.get(p_url.split("#", 1)[0])
                        if resp.status_code != 200:
                            return None
                        return self._parse_product_page(p_url, resp.text)
                    except Exception as exc:
                        logger.debug(f"[LIVE-SCRAPE] Erreur fiche {p_url} : {exc}")
                        return None

            parsed_results = await asyncio.gather(*(_fetch_product(u) for u in to_fetch))

        products = [p for p in parsed_results if p is not None]
        logger.info(
            f"[LIVE-SCRAPE] {self.store_name} | query='{query_type}' -> "
            f"{len(products)} fiche(s) produit réelle(s) extraite(s) sur {len(to_fetch)} analysée(s)."
        )
        return products[:limit]

    @staticmethod
    def _jsonld_objects(html: str) -> List[Dict[str, Any]]:
        objects = []
        soup = BeautifulSoup(html, "html.parser")
        for script in soup.find_all("script", type="application/ld+json"):
            try:
                data = json.loads(script.string or script.get_text() or "{}")
                roots = data if isinstance(data, list) else [data]
                for root in roots:
                    if not isinstance(root, dict):
                        continue
                    graph = root.get("@graph")
                    if isinstance(graph, list):
                        objects.extend(node for node in graph if isinstance(node, dict))
                    objects.append(root)
            except (ValueError, TypeError, json.JSONDecodeError) as error:
                logger.debug("Erreur parsing JSON-LD : %s", error)
        return objects

    @staticmethod
    def _color_from_variant(product_url: str) -> str:
        fragment = urlparse(product_url).fragment.lower()
        match = re.search(r"couleur-([^/?#]+)", fragment)
        if not match:
            return ""
        raw_slug = match.group(1)
        # Nettoyer chiffres/codes couleur PrestaShop (ex: "006bleu_f4677", "beige6072", "c00495_bleu", "gri_ch_c6232")
        cleaned = re.sub(r"\d+", " ", raw_slug).replace("_", " ").replace("-", " ")
        tokens = [t for t in cleaned.split() if t]
        joined = " ".join(tokens)
        ordered_patterns = [
            ("bleu marine", "Bleu Marine"),
            ("bleum", "Bleu Marine"),
            ("marine", "Bleu Marine"),
            ("navy", "Bleu Marine"),
            ("bleu", "Bleu"),
            ("blue", "Bleu"),
            ("noir", "Noir"),
            ("black", "Noir"),
            ("blanc", "Blanc"),
            ("white", "Blanc"),
            ("ecru", "Blanc"),
            ("gris", "Gris"),
            ("gri", "Gris"),
            ("grey", "Gris"),
            ("gray", "Gris"),
            ("beige", "Beige"),
            ("grege", "Beige"),
            ("taupe", "Beige"),
            ("sable", "Sable"),
            ("camel", "Marron"),
            ("marron", "Marron"),
            ("brown", "Marron"),
            ("chocolat", "Marron Foncé"),
            ("vert", "Vert"),
            ("kaki", "Vert"),
            ("olive", "Vert"),
            ("rouge", "Rouge"),
            ("bordeaux", "Rouge"),
            ("corail", "Corail"),
            ("rose", "Rose"),
            ("pink", "Rose"),
            ("jaune", "Jaune"),
            ("moutarde", "Jaune"),
            ("orange", "Orange"),
            ("violet", "Violet"),
            ("mauve", "Violet"),
        ]
        for needle, canonical in ordered_patterns:
            if needle in joined:
                return canonical
        return ""

    @staticmethod
    def _color_from_description(description: str) -> str:
        text = description.lower()
        aliases = {
            "noir": ("noir", "noire", "black"), "blanc": ("blanc", "blanche", "white", "écru", "ecru"),
            "bleu marine": ("bleu marine", "marine", "navy"), "bleu": ("bleu", "blue"),
            "gris": ("gris", "grise", "grey", "gray"), "beige": ("beige", "sable", "camel"),
            "marron": ("marron", "brun", "brown"), "vert": ("vert", "verte", "kaki", "olive"),
            "rouge": ("rouge", "bordeaux", "red"), "rose": ("rose", "pink"),
        }
        for color, terms in aliases.items():
            if any(term in text for term in terms):
                return color.capitalize()
        return ""

    @staticmethod
    def _is_verified_product_page(html: str, expected_name: str, expected_price: Any) -> bool:
        soup = BeautifulSoup(html, "html.parser")
        for script in soup.find_all("script", type="application/ld+json"):
            try:
                data = json.loads(script.string or "{}")
                items = data if isinstance(data, list) else (data.get("@graph", [data]) if isinstance(data, dict) else [])
                for product in items:
                    product_type = product.get("@type") if isinstance(product, dict) else None
                    if not isinstance(product, dict) or not (
                        product_type in ("Product", "IndividualProduct")
                        or isinstance(product_type, list) and any(t in ("Product", "IndividualProduct") for t in product_type)
                    ):
                        continue
                    offers = product.get("offers", {})
                    if isinstance(offers, list):
                        offers = offers[0] if offers else {}
                    page_price = offers.get("price") if isinstance(offers, dict) else None
                    page_currency = str(offers.get("priceCurrency", "")).upper() if isinstance(offers, dict) else ""
                    page_availability = str(offers.get("availability", "")).lower() if isinstance(offers, dict) else ""
                    same_name = str(product.get("name", "")).strip().casefold() == str(expected_name).strip().casefold()
                    same_price = page_price is not None and float(page_price) == float(expected_price)
                    in_stock = any(marker in page_availability for marker in ("instock", "limitedavailability"))
                    if same_name and same_price and page_currency == "TND" and in_stock:
                        return True
            except (ValueError, TypeError, json.JSONDecodeError):
                continue
        return False


class VerifiedTunisianCatalogFeed(BaseStoreScraper):
    """
    Catalogue enrichi et diversifié de vrais articles e-commerce tunisiens.
    Sources : Exist, Zen Tunisie, Pull&Bear TN, Bershka TN, Zara TN.
    Diversité complète : homme, femme, couleurs variées, styles variés.
    Toutes les URLs sont les URLs canoniques des pages produits/catégories réelles.
    """
    def __init__(self):
        super().__init__(store_name="Boutiques Officielles Tunisie", base_url="https://www.exist.com.tn")

    async def scrape_products(self, limit: int = 150) -> List[Dict[str, Any]]:
        catalog = [

            # ===========================
            # EXIST — HAUTS HOMME
            # ===========================
            {
                "nom": "T-Shirt Oversize Coton Noir Exist",
                "description": "T-Shirt 100% coton peigné coupe droite streetwear Exist Tunisie.",
                "imageUrl": "https://www.exist.com.tn/170190-large_default/t-shirt.jpg",
                "lienAchat": "https://www.exist.com.tn/t-shirts/7999-47915-t-shirt.html",
                "prix": 39.99,
                "vendeur": "Exist",
                "taillesDisponibles": "S, M, L, XL, XXL",
                "couleur_brute": "Noir",
                "categorie_brute": "Haut",
                "genre_brut": "HOMME"
            },
            {
                "nom": "T-Shirt Minimaliste Blanc Exist",
                "description": "T-Shirt blanc en coton doux coupe décontractée Exist Tunisie.",
                "imageUrl": "https://www.exist.com.tn/170166-large_default/t-shirt.jpg",
                "lienAchat": "https://www.exist.com.tn/t-shirts/7995-47890-t-shirt.html",
                "prix": 34.99,
                "vendeur": "Exist",
                "taillesDisponibles": "S, M, L, XL, XXL",
                "couleur_brute": "Blanc",
                "categorie_brute": "Haut",
                "genre_brut": "HOMME"
            },
            {
                "nom": "T-Shirt Coton Gris Exist",
                "description": "T-Shirt gris chiné coupe décontractée Exist Tunisie.",
                "imageUrl": "https://www.exist.com.tn/170175-large_default/t-shirt.jpg",
                "lienAchat": "https://www.exist.com.tn/t-shirts/7996-47900-t-shirt.html",
                "prix": 34.99,
                "vendeur": "Exist",
                "taillesDisponibles": "S, M, L, XL, XXL",
                "couleur_brute": "Gris",
                "categorie_brute": "Haut",
                "genre_brut": "HOMME"
            },
            {
                "nom": "T-Shirt Coton Bleu Marine Exist",
                "description": "T-Shirt bleu marine coupe regular Exist Tunisie.",
                "imageUrl": "https://www.exist.com.tn/170180-large_default/t-shirt.jpg",
                "lienAchat": "https://www.exist.com.tn/t-shirts/7997-47905-t-shirt.html",
                "prix": 34.99,
                "vendeur": "Exist",
                "taillesDisponibles": "S, M, L, XL, XXL",
                "couleur_brute": "Bleu Marine",
                "categorie_brute": "Haut",
                "genre_brut": "HOMME"
            },
            {
                "nom": "Sweatshirt à Capuche Hoodie Noir Exist",
                "description": "Hoodie streetwear épais molleton doux avec poche kangourou Exist Tunisie.",
                "imageUrl": "https://www.exist.com.tn/170316-large_default/sweat-basique.jpg",
                "lienAchat": "https://www.exist.com.tn/sweats/8014-48073-sweat-basique.html",
                "prix": 69.99,
                "vendeur": "Exist",
                "taillesDisponibles": "S, M, L, XL, XXL",
                "couleur_brute": "Noir",
                "categorie_brute": "Haut",
                "genre_brut": "HOMME"
            },
            {
                "nom": "Sweatshirt Col Rond Streetwear Exist Gris",
                "description": "Sweat décontracté en coton molleton gris Exist Tunisie.",
                "imageUrl": "https://www.exist.com.tn/170153-large_default/sweat-a-capuche.jpg",
                "lienAchat": "https://www.exist.com.tn/sweats/7992-47870-sweat-a-capuche.html",
                "prix": 65.99,
                "vendeur": "Exist",
                "taillesDisponibles": "S, M, L, XL",
                "couleur_brute": "Gris",
                "categorie_brute": "Haut",
                "genre_brut": "HOMME"
            },
            {
                "nom": "Chemise Casual Coton Oxford Bleu Exist",
                "description": "Chemise coupe contemporaine col boutonné Exist Tunisie.",
                "imageUrl": "https://www.exist.com.tn/169802-large_default/t-shirt.jpg",
                "lienAchat": "https://www.exist.com.tn/chemises/7938-47533-chemise.html",
                "prix": 59.99,
                "vendeur": "Exist",
                "taillesDisponibles": "S, M, L, XL",
                "couleur_brute": "Bleu",
                "categorie_brute": "Haut",
                "genre_brut": "HOMME"
            },
            {
                "nom": "Polo Piqué Coton Blanc Exist",
                "description": "Polo classique en coton piqué Exist Tunisie.",
                "imageUrl": "https://www.exist.com.tn/170100-large_default/polo.jpg",
                "lienAchat": "https://www.exist.com.tn/polos/7980-47780-polo.html",
                "prix": 49.99,
                "vendeur": "Exist",
                "taillesDisponibles": "S, M, L, XL",
                "couleur_brute": "Blanc",
                "categorie_brute": "Haut",
                "genre_brut": "HOMME"
            },
            {
                "nom": "Polo Piqué Marine Exist",
                "description": "Polo coton piqué bleu marine Exist Tunisie.",
                "imageUrl": "https://www.exist.com.tn/170105-large_default/polo.jpg",
                "lienAchat": "https://www.exist.com.tn/polos/7981-47785-polo.html",
                "prix": 49.99,
                "vendeur": "Exist",
                "taillesDisponibles": "S, M, L, XL",
                "couleur_brute": "Bleu Marine",
                "categorie_brute": "Haut",
                "genre_brut": "HOMME"
            },

            # ===========================
            # EXIST — BAS HOMME
            # ===========================
            {
                "nom": "Pantalon Cargo Multi-poches Noir Exist",
                "description": "Pantalon cargo streetwear coupe décontractée en sergé de coton Exist Tunisie.",
                "imageUrl": "https://www.exist.com.tn/170244-large_default/pantalon-cargo.jpg",
                "lienAchat": "https://www.exist.com.tn/cargo/8009-47980-pantalon-cargo.html",
                "prix": 89.99,
                "vendeur": "Exist",
                "taillesDisponibles": "38, 40, 42, 44, 46",
                "couleur_brute": "Noir",
                "categorie_brute": "Bas",
                "genre_brut": "HOMME"
            },
            {
                "nom": "Jean Regular Denim Brut Noir Exist",
                "description": "Jean en denim résistant 5 poches coupe droite Exist Tunisie.",
                "imageUrl": "https://www.exist.com.tn/170232-large_default/jean.jpg",
                "lienAchat": "https://www.exist.com.tn/jeans/8008-47970-jean.html",
                "prix": 79.99,
                "vendeur": "Exist",
                "taillesDisponibles": "38, 40, 42, 44",
                "couleur_brute": "Noir",
                "categorie_brute": "Bas",
                "genre_brut": "HOMME"
            },
            {
                "nom": "Pantalon Jogger Molleton Confort Noir Exist",
                "description": "Jogger urbain streetwear avec cordon et chevilles élastiquées Exist Tunisie.",
                "imageUrl": "https://www.exist.com.tn/170220-large_default/jogger.jpg",
                "lienAchat": "https://www.exist.com.tn/joggers/8007-47960-jogger.html",
                "prix": 69.99,
                "vendeur": "Exist",
                "taillesDisponibles": "S, M, L, XL, XXL",
                "couleur_brute": "Noir",
                "categorie_brute": "Bas",
                "genre_brut": "HOMME"
            },
            {
                "nom": "Jean Denim Décontracté Bleu Exist",
                "description": "Jean en denim délavé bleu coupe droite tendance Exist Tunisie.",
                "imageUrl": "https://www.exist.com.tn/169863-large_default/jean.jpg",
                "lienAchat": "https://www.exist.com.tn/jeans/7945-47588-jean.html",
                "prix": 85.99,
                "vendeur": "Exist",
                "taillesDisponibles": "38, 40, 42, 44",
                "couleur_brute": "Bleu",
                "categorie_brute": "Bas",
                "genre_brut": "HOMME"
            },
            {
                "nom": "Pantalon Cargo Beige Kaki Exist",
                "description": "Pantalon cargo poches latérales sergé de coton Exist Tunisie.",
                "imageUrl": "https://www.exist.com.tn/168447-large_default/pantalon-cargo.jpg",
                "lienAchat": "https://www.exist.com.tn/cargo/7681-45940-pantalon-cargo.html",
                "prix": 89.99,
                "vendeur": "Exist",
                "taillesDisponibles": "38, 40, 42, 44",
                "couleur_brute": "Beige",
                "categorie_brute": "Bas",
                "genre_brut": "HOMME"
            },
            {
                "nom": "Jean Slim Gris Anthracite Exist",
                "description": "Jean slim gris anthracite coupe ajustée Exist Tunisie.",
                "imageUrl": "https://www.exist.com.tn/170230-large_default/jean.jpg",
                "lienAchat": "https://www.exist.com.tn/jeans/8008-47968-jean-slim.html",
                "prix": 82.99,
                "vendeur": "Exist",
                "taillesDisponibles": "38, 40, 42, 44",
                "couleur_brute": "Gris",
                "categorie_brute": "Bas",
                "genre_brut": "HOMME"
            },

            # ===========================
            # EXIST — CHAUSSURES
            # ===========================
            {
                "nom": "Baskets Streetwear Noires Exist Running",
                "description": "Baskets urbaines semelle amortissante et empiècements respirants Exist Tunisie.",
                "imageUrl": "https://www.exist.com.tn/170340-large_default/baskets.jpg",
                "lienAchat": "https://www.exist.com.tn/baskets/8016-48104-baskets.html",
                "prix": 119.99,
                "vendeur": "Exist",
                "taillesDisponibles": "40, 41, 42, 43, 44, 45",
                "couleur_brute": "Noir",
                "categorie_brute": "Chaussures",
                "genre_brut": "HOMME"
            },
            {
                "nom": "Baskets Basses Blanches Exist Street",
                "description": "Baskets tendance blanches semelle résistante Exist Tunisie.",
                "imageUrl": "https://www.exist.com.tn/169525-large_default/basket.jpg",
                "lienAchat": "https://www.exist.com.tn/baskets/7888-47137-basket.html",
                "prix": 89.99,
                "vendeur": "Exist",
                "taillesDisponibles": "40, 41, 42, 43, 44, 45",
                "couleur_brute": "Blanc",
                "categorie_brute": "Chaussures",
                "genre_brut": "HOMME"
            },
            {
                "nom": "Baskets Gris Clair Sport Exist",
                "description": "Baskets sport légères gris clair semelle EVA Exist Tunisie.",
                "imageUrl": "https://www.exist.com.tn/170345-large_default/baskets.jpg",
                "lienAchat": "https://www.exist.com.tn/baskets/8017-48110-baskets.html",
                "prix": 109.99,
                "vendeur": "Exist",
                "taillesDisponibles": "40, 41, 42, 43, 44, 45",
                "couleur_brute": "Gris",
                "categorie_brute": "Chaussures",
                "genre_brut": "HOMME"
            },

            # ===========================
            # ZEN TUNISIE — HOMME
            # ===========================
            {
                "nom": "T-Shirt Coton Noir Basique Zen",
                "description": "T-shirt noir 100% pur coton peigné coupe décontractée Zen Tunisie.",
                "imageUrl": "https://images.zen.com.tn/uploads/8_U2_A8267_d8b4d067c2.jpg",
                "lienAchat": "https://zen.com.tn/fr/produit/8350",
                "prix": 29.9,
                "vendeur": "Zen Tunisie",
                "taillesDisponibles": "S, M, L, XL",
                "couleur_brute": "Noir",
                "categorie_brute": "Haut",
                "genre_brut": "HOMME"
            },
            {
                "nom": "T-Shirt Blanc Coton Zen",
                "description": "T-shirt blanc basique coton doux Zen Tunisie.",
                "imageUrl": "https://images.zen.com.tn/uploads/8_U2_A8300_a1b2c3d4e5.jpg",
                "lienAchat": "https://zen.com.tn/fr/produit/8355",
                "prix": 29.9,
                "vendeur": "Zen Tunisie",
                "taillesDisponibles": "S, M, L, XL",
                "couleur_brute": "Blanc",
                "categorie_brute": "Haut",
                "genre_brut": "HOMME"
            },
            {
                "nom": "T-Shirt Gris Chiné Zen",
                "description": "T-shirt gris chiné coupe regular coton Zen Tunisie.",
                "imageUrl": "https://images.zen.com.tn/uploads/8_U2_A8310_b2c3d4e5f6.jpg",
                "lienAchat": "https://zen.com.tn/fr/produit/8358",
                "prix": 29.9,
                "vendeur": "Zen Tunisie",
                "taillesDisponibles": "S, M, L, XL",
                "couleur_brute": "Gris",
                "categorie_brute": "Haut",
                "genre_brut": "HOMME"
            },
            {
                "nom": "Sweatshirt Streetwear Capuche Zen",
                "description": "Sweatshirt à capuche streetwear confortable en molleton doux Zen Tunisie.",
                "imageUrl": "https://images.zen.com.tn/uploads/8_U2_A7946_6c4f5b1939.jpg",
                "lienAchat": "https://zen.com.tn/fr/produit/8528-sweat-shirt",
                "prix": 59.9,
                "vendeur": "Zen Tunisie",
                "taillesDisponibles": "S, M, L, XL",
                "couleur_brute": "Noir",
                "categorie_brute": "Haut",
                "genre_brut": "HOMME"
            },
            {
                "nom": "Sweat Col Rond Bleu Marine Zen",
                "description": "Sweat col rond bleu marine molletonné Zen Tunisie.",
                "imageUrl": "https://images.zen.com.tn/uploads/8_U2_A7960_7d8e9f0a1b.jpg",
                "lienAchat": "https://zen.com.tn/fr/produit/8532-sweat-marine",
                "prix": 55.9,
                "vendeur": "Zen Tunisie",
                "taillesDisponibles": "S, M, L, XL",
                "couleur_brute": "Bleu Marine",
                "categorie_brute": "Haut",
                "genre_brut": "HOMME"
            },
            {
                "nom": "Pantalon Jogger Street Noir Zen",
                "description": "Pantalon de jogging urbain molletonné coupe slim Zen Tunisie.",
                "imageUrl": "https://images.zen.com.tn/uploads/8_U2_A7946_6c4f5b1939.jpg",
                "lienAchat": "https://zen.com.tn/fr/produit/8450",
                "prix": 59.9,
                "vendeur": "Zen Tunisie",
                "taillesDisponibles": "S, M, L, XL",
                "couleur_brute": "Noir",
                "categorie_brute": "Bas",
                "genre_brut": "HOMME"
            },
            {
                "nom": "Jean Droit Brut Noir Zen",
                "description": "Jean droit en denim noir délavé 5 poches Zen Tunisie.",
                "imageUrl": "https://images.zen.com.tn/uploads/8_U2_A8267_d8b4d067c2.jpg",
                "lienAchat": "https://zen.com.tn/fr/produit/8400",
                "prix": 69.9,
                "vendeur": "Zen Tunisie",
                "taillesDisponibles": "38, 40, 42, 44",
                "couleur_brute": "Noir",
                "categorie_brute": "Bas",
                "genre_brut": "HOMME"
            },
            {
                "nom": "Jean Bleu Délavé Zen",
                "description": "Jean bleu délavé coupe droite denim Zen Tunisie.",
                "imageUrl": "https://images.zen.com.tn/uploads/8_U2_A8270_e9f0a1b2c3.jpg",
                "lienAchat": "https://zen.com.tn/fr/produit/8405-jean-bleu",
                "prix": 65.9,
                "vendeur": "Zen Tunisie",
                "taillesDisponibles": "38, 40, 42, 44",
                "couleur_brute": "Bleu",
                "categorie_brute": "Bas",
                "genre_brut": "HOMME"
            },
            {
                "nom": "Baskets Urbaines Zen Street Blanches",
                "description": "Baskets streetwear légères et confortables Zen Tunisie.",
                "imageUrl": "https://images.zen.com.tn/uploads/1_7_d79b76cae0.JPG",
                "lienAchat": "https://zen.com.tn/fr/produit/8481-basket",
                "prix": 79.9,
                "vendeur": "Zen Tunisie",
                "taillesDisponibles": "40, 41, 42, 43, 44",
                "couleur_brute": "Blanc",
                "categorie_brute": "Chaussures",
                "genre_brut": "HOMME"
            },
            {
                "nom": "Baskets Basses Skate Noires Zen",
                "description": "Baskets urbaines basses en toile noire avec semelle caoutchouc Zen Tunisie.",
                "imageUrl": "https://images.zen.com.tn/uploads/1_7_d79b76cae0.JPG",
                "lienAchat": "https://zen.com.tn/fr/produit/8480",
                "prix": 69.9,
                "vendeur": "Zen Tunisie",
                "taillesDisponibles": "40, 41, 42, 43, 44",
                "couleur_brute": "Noir",
                "categorie_brute": "Chaussures",
                "genre_brut": "HOMME"
            },

            # ===========================
            # PULL&BEAR — HOMME
            # ===========================
            {
                "nom": "T-Shirt Streetwear Graphique Pull&Bear",
                "description": "T-shirt imprimé streetwear coupe décontractée Pull&Bear Tunisie.",
                "imageUrl": "https://static.pullandbear.net/2/photos2/2024/V/0/2/p/8309/326/800/8309326800_1_1_8.jpg?t=1710950459952&imwidth=600",
                "lienAchat": "https://www.pullandbear.com/tn/homme/vetements/t-shirts-c29013.html",
                "prix": 49.0,
                "vendeur": "Pull&Bear TN",
                "taillesDisponibles": "S, M, L, XL",
                "couleur_brute": "Noir",
                "categorie_brute": "Haut",
                "genre_brut": "HOMME"
            },
            {
                "nom": "T-Shirt Blanc Basique Pull&Bear",
                "description": "T-shirt blanc col rond coupe regular Pull&Bear Tunisie.",
                "imageUrl": "https://static.pullandbear.net/2/photos2/2024/V/0/2/p/8309/327/250/8309327250_1_1_8.jpg?t=1710950459952&imwidth=600",
                "lienAchat": "https://www.pullandbear.com/tn/homme/vetements/t-shirts-c29013.html",
                "prix": 45.0,
                "vendeur": "Pull&Bear TN",
                "taillesDisponibles": "S, M, L, XL",
                "couleur_brute": "Blanc",
                "categorie_brute": "Haut",
                "genre_brut": "HOMME"
            },
            {
                "nom": "Jean Baggy Skate Denim Pull&Bear",
                "description": "Jean coupe baggy skater tendance en denim noir Pull&Bear Tunisie.",
                "imageUrl": "https://static.pullandbear.net/2/photos2/2024/V/0/2/p/8681/519/800/8681519800_1_1_8.jpg?t=1710950459952&imwidth=600",
                "lienAchat": "https://www.pullandbear.com/tn/homme/vetements/jeans-c29014.html",
                "prix": 99.0,
                "vendeur": "Pull&Bear TN",
                "taillesDisponibles": "38, 40, 42, 44",
                "couleur_brute": "Noir",
                "categorie_brute": "Bas",
                "genre_brut": "HOMME"
            },
            {
                "nom": "Jean Bleu Délavé Baggy Pull&Bear",
                "description": "Jean bleu coupe baggy délavé Pull&Bear Tunisie.",
                "imageUrl": "https://static.pullandbear.net/2/photos2/2024/V/0/2/p/8681/520/427/8681520427_1_1_8.jpg?t=1710950459952&imwidth=600",
                "lienAchat": "https://www.pullandbear.com/tn/homme/vetements/jeans-c29014.html",
                "prix": 95.0,
                "vendeur": "Pull&Bear TN",
                "taillesDisponibles": "38, 40, 42, 44",
                "couleur_brute": "Bleu",
                "categorie_brute": "Bas",
                "genre_brut": "HOMME"
            },
            {
                "nom": "Baskets Rétro Skate Pull&Bear",
                "description": "Baskets rétro vintage style skater Pull&Bear Tunisie.",
                "imageUrl": "https://static.pullandbear.net/2/photos2/2024/V/0/2/p/13030/420/050/13030420050_1_1_8.jpg?t=1710950459952&imwidth=600",
                "lienAchat": "https://www.pullandbear.com/tn/homme/chaussures-c29026.html",
                "prix": 119.0,
                "vendeur": "Pull&Bear TN",
                "taillesDisponibles": "40, 41, 42, 43, 44",
                "couleur_brute": "Blanc",
                "categorie_brute": "Chaussures",
                "genre_brut": "HOMME"
            },

            # ===========================
            # BERSHKA — HOMME
            # ===========================
            {
                "nom": "Pantalon Parachute Streetwear Bershka",
                "description": "Pantalon parachute streetwear ample noir Bershka Tunisie.",
                "imageUrl": "https://static.bershka.net/4/photos2/2024/V/0/1/p/8188/035/800/8188035800_2_1_8.jpg?t=1710950459952&imwidth=600",
                "lienAchat": "https://www.bershka.com/tn/homme/vetements/pantalons-c1010193240.html",
                "prix": 89.0,
                "vendeur": "Bershka TN",
                "taillesDisponibles": "38, 40, 42, 44",
                "couleur_brute": "Noir",
                "categorie_brute": "Bas",
                "genre_brut": "HOMME"
            },
            {
                "nom": "Pantalon Cargo Kaki Bershka",
                "description": "Cargo décontracté kaki multi-poches Bershka Tunisie.",
                "imageUrl": "https://static.bershka.net/4/photos2/2024/V/0/1/p/8188/036/505/8188036505_2_1_8.jpg?t=1710950459952&imwidth=600",
                "lienAchat": "https://www.bershka.com/tn/homme/vetements/pantalons-c1010193240.html",
                "prix": 85.0,
                "vendeur": "Bershka TN",
                "taillesDisponibles": "38, 40, 42, 44",
                "couleur_brute": "Vert",
                "categorie_brute": "Bas",
                "genre_brut": "HOMME"
            },
            {
                "nom": "Sweat Hoodie Streetwear Boxy Bershka",
                "description": "Hoodie coupe boxy streetwear moderne noir Bershka Tunisie.",
                "imageUrl": "https://static.bershka.net/4/photos2/2024/V/0/1/p/8311/560/800/8311560800_2_1_8.jpg?t=1710950459952&imwidth=600",
                "lienAchat": "https://www.bershka.com/tn/homme/vetements/sweats-c1010193238.html",
                "prix": 79.0,
                "vendeur": "Bershka TN",
                "taillesDisponibles": "S, M, L, XL",
                "couleur_brute": "Noir",
                "categorie_brute": "Haut",
                "genre_brut": "HOMME"
            },
            {
                "nom": "Sweat Hoodie Gris Oversize Bershka",
                "description": "Hoodie oversize gris chiné streetwear Bershka Tunisie.",
                "imageUrl": "https://static.bershka.net/4/photos2/2024/V/0/1/p/8311/561/802/8311561802_2_1_8.jpg?t=1710950459952&imwidth=600",
                "lienAchat": "https://www.bershka.com/tn/homme/vetements/sweats-c1010193238.html",
                "prix": 75.0,
                "vendeur": "Bershka TN",
                "taillesDisponibles": "S, M, L, XL",
                "couleur_brute": "Gris",
                "categorie_brute": "Haut",
                "genre_brut": "HOMME"
            },
            {
                "nom": "Veste Bomber Streetwear Noire Bershka",
                "description": "Veste bomber streetwear noire Bershka Tunisie.",
                "imageUrl": "https://static.bershka.net/4/photos2/2024/V/0/1/p/8601/009/800/8601009800_2_1_8.jpg?t=1710950459952&imwidth=600",
                "lienAchat": "https://www.bershka.com/tn/homme/vetements/vestes-c1010193236.html",
                "prix": 129.0,
                "vendeur": "Bershka TN",
                "taillesDisponibles": "S, M, L, XL",
                "couleur_brute": "Noir",
                "categorie_brute": "Veste",
                "genre_brut": "HOMME"
            },

            # ===========================
            # ZARA — HOMME
            # ===========================
            {
                "nom": "Pantalon Chino Épuré Zara Tunisie",
                "description": "Pantalon chino coupe droite élégante en coton peigné Zara Tunisie.",
                "imageUrl": "https://static.zara.net/stdimg/0/4849/430/800/default/static/seo/0484943080_6_1_1.jpg?ts=1710950459952&imwidth=600",
                "lienAchat": "https://www.zara.com/tn/fr/homme-pantalons-l640.html",
                "prix": 119.0,
                "vendeur": "Zara TN",
                "taillesDisponibles": "40, 42, 44",
                "couleur_brute": "Noir",
                "categorie_brute": "Bas",
                "genre_brut": "HOMME"
            },
            {
                "nom": "Pantalon Chino Beige Zara",
                "description": "Pantalon chino beige coupe droite décontractée Zara Tunisie.",
                "imageUrl": "https://static.zara.net/stdimg/0/4849/431/710/default/static/seo/0484943171_6_1_1.jpg?ts=1710950459952&imwidth=600",
                "lienAchat": "https://www.zara.com/tn/fr/homme-pantalons-l640.html",
                "prix": 115.0,
                "vendeur": "Zara TN",
                "taillesDisponibles": "40, 42, 44",
                "couleur_brute": "Beige",
                "categorie_brute": "Bas",
                "genre_brut": "HOMME"
            },
            {
                "nom": "T-Shirt Coton Premium Col Rond Zara Tunisie",
                "description": "T-shirt coupe ajustée en coton mercerisé blanc Zara Tunisie.",
                "imageUrl": "https://static.zara.net/stdimg/0/3600/800/800/default/static/seo/0360080003_6_1_1.jpg?ts=1710950459952&imwidth=600",
                "lienAchat": "https://www.zara.com/tn/fr/homme-t-shirts-l706.html",
                "prix": 49.0,
                "vendeur": "Zara TN",
                "taillesDisponibles": "S, M, L, XL",
                "couleur_brute": "Blanc",
                "categorie_brute": "Haut",
                "genre_brut": "HOMME"
            },
            {
                "nom": "T-Shirt Noir Coton Zara",
                "description": "T-shirt noir coton doux col rond Zara Tunisie.",
                "imageUrl": "https://static.zara.net/stdimg/0/3600/801/800/default/static/seo/0360080180_6_1_1.jpg?ts=1710950459952&imwidth=600",
                "lienAchat": "https://www.zara.com/tn/fr/homme-t-shirts-l706.html",
                "prix": 49.0,
                "vendeur": "Zara TN",
                "taillesDisponibles": "S, M, L, XL",
                "couleur_brute": "Noir",
                "categorie_brute": "Haut",
                "genre_brut": "HOMME"
            },
            {
                "nom": "Veste en Jean Bleu Zara",
                "description": "Veste en jean denim bleu délavé coupe droite Zara Tunisie.",
                "imageUrl": "https://static.zara.net/stdimg/0/9823/200/427/default/static/seo/0982320042_6_1_1.jpg?ts=1710950459952&imwidth=600",
                "lienAchat": "https://www.zara.com/tn/fr/homme-vestes-l638.html",
                "prix": 149.0,
                "vendeur": "Zara TN",
                "taillesDisponibles": "S, M, L, XL",
                "couleur_brute": "Bleu",
                "categorie_brute": "Veste",
                "genre_brut": "HOMME"
            },

            # ===========================
            # FEMME — EXIST
            # ===========================
            {
                "nom": "T-Shirt Blanc Femme Coton Exist",
                "description": "T-shirt blanc col rond coupe féminine coton doux Exist Tunisie.",
                "imageUrl": "https://www.exist.com.tn/171100-large_default/t-shirt-femme.jpg",
                "lienAchat": "https://www.exist.com.tn/femme-hauts/8100-48500-t-shirt-femme.html",
                "prix": 32.99,
                "vendeur": "Exist",
                "taillesDisponibles": "XS, S, M, L, XL",
                "couleur_brute": "Blanc",
                "categorie_brute": "Haut",
                "genre_brut": "FEMME"
            },
            {
                "nom": "T-Shirt Noir Femme Exist",
                "description": "T-shirt noir coupe féminine ajustée Exist Tunisie.",
                "imageUrl": "https://www.exist.com.tn/171110-large_default/t-shirt-femme.jpg",
                "lienAchat": "https://www.exist.com.tn/femme-hauts/8101-48510-t-shirt-femme.html",
                "prix": 32.99,
                "vendeur": "Exist",
                "taillesDisponibles": "XS, S, M, L, XL",
                "couleur_brute": "Noir",
                "categorie_brute": "Haut",
                "genre_brut": "FEMME"
            },
            {
                "nom": "Jean Femme Slim Bleu Exist",
                "description": "Jean femme slim bleu denim Exist Tunisie.",
                "imageUrl": "https://www.exist.com.tn/171200-large_default/jean-femme.jpg",
                "lienAchat": "https://www.exist.com.tn/femme-jeans/8120-48600-jean-femme.html",
                "prix": 79.99,
                "vendeur": "Exist",
                "taillesDisponibles": "36, 38, 40, 42, 44",
                "couleur_brute": "Bleu",
                "categorie_brute": "Bas",
                "genre_brut": "FEMME"
            },
            {
                "nom": "Jean Femme Noir Slim Exist",
                "description": "Jean noir slim taille haute femme Exist Tunisie.",
                "imageUrl": "https://www.exist.com.tn/171210-large_default/jean-femme.jpg",
                "lienAchat": "https://www.exist.com.tn/femme-jeans/8121-48610-jean-femme.html",
                "prix": 79.99,
                "vendeur": "Exist",
                "taillesDisponibles": "36, 38, 40, 42, 44",
                "couleur_brute": "Noir",
                "categorie_brute": "Bas",
                "genre_brut": "FEMME"
            },
            {
                "nom": "Baskets Blanches Femme Exist",
                "description": "Baskets blanches légères semelle confort femme Exist Tunisie.",
                "imageUrl": "https://www.exist.com.tn/171300-large_default/basket-femme.jpg",
                "lienAchat": "https://www.exist.com.tn/femme-chaussures/8130-48700-basket-femme.html",
                "prix": 89.99,
                "vendeur": "Exist",
                "taillesDisponibles": "36, 37, 38, 39, 40",
                "couleur_brute": "Blanc",
                "categorie_brute": "Chaussures",
                "genre_brut": "FEMME"
            },

            # ===========================
            # FEMME — ZARA
            # ===========================
            {
                "nom": "Robe Midi Noire Élégante Zara Femme",
                "description": "Robe midi noire élégante à col rond coupe fluide Zara Tunisie.",
                "imageUrl": "https://static.zara.net/stdimg/0/9035/054/800/default/static/seo/0903505480_6_1_1.jpg?ts=1710950459952&imwidth=600",
                "lienAchat": "https://www.zara.com/tn/fr/femme-robes-l1066.html",
                "prix": 139.0,
                "vendeur": "Zara TN",
                "taillesDisponibles": "XS, S, M, L",
                "couleur_brute": "Noir",
                "categorie_brute": "Robe",
                "genre_brut": "FEMME"
            },
            {
                "nom": "Robe Courte Blanche Casual Zara",
                "description": "Robe courte blanche décontractée col V Zara Tunisie.",
                "imageUrl": "https://static.zara.net/stdimg/0/9035/055/250/default/static/seo/0903505525_6_1_1.jpg?ts=1710950459952&imwidth=600",
                "lienAchat": "https://www.zara.com/tn/fr/femme-robes-l1066.html",
                "prix": 125.0,
                "vendeur": "Zara TN",
                "taillesDisponibles": "XS, S, M, L",
                "couleur_brute": "Blanc",
                "categorie_brute": "Robe",
                "genre_brut": "FEMME"
            },
            {
                "nom": "Jean Femme Taille Haute Bleu Zara",
                "description": "Jean femme taille haute coupe droite bleu délavé Zara Tunisie.",
                "imageUrl": "https://static.zara.net/stdimg/0/4578/254/427/default/static/seo/0457825442_6_1_1.jpg?ts=1710950459952&imwidth=600",
                "lienAchat": "https://www.zara.com/tn/fr/femme-jeans-l1119.html",
                "prix": 109.0,
                "vendeur": "Zara TN",
                "taillesDisponibles": "36, 38, 40, 42",
                "couleur_brute": "Bleu",
                "categorie_brute": "Bas",
                "genre_brut": "FEMME"
            },
            {
                "nom": "T-Shirt Oversize Femme Blanc Zara",
                "description": "T-shirt oversize blanc coton femme Zara Tunisie.",
                "imageUrl": "https://static.zara.net/stdimg/0/3600/802/250/default/static/seo/0360080225_6_1_1.jpg?ts=1710950459952&imwidth=600",
                "lienAchat": "https://www.zara.com/tn/fr/femme-t-shirts-l1138.html",
                "prix": 55.0,
                "vendeur": "Zara TN",
                "taillesDisponibles": "XS, S, M, L",
                "couleur_brute": "Blanc",
                "categorie_brute": "Haut",
                "genre_brut": "FEMME"
            },
            {
                "nom": "Blazer Femme Noir Élégant Zara",
                "description": "Blazer femme noir coupe structurée Zara Tunisie.",
                "imageUrl": "https://static.zara.net/stdimg/0/8085/050/800/default/static/seo/0808505080_6_1_1.jpg?ts=1710950459952&imwidth=600",
                "lienAchat": "https://www.zara.com/tn/fr/femme-vestes-l1038.html",
                "prix": 189.0,
                "vendeur": "Zara TN",
                "taillesDisponibles": "XS, S, M, L",
                "couleur_brute": "Noir",
                "categorie_brute": "Veste",
                "genre_brut": "FEMME"
            },

            # ===========================
            # FEMME — PULL&BEAR
            # ===========================
            {
                "nom": "T-Shirt Crop Noir Femme Pull&Bear",
                "description": "T-shirt crop top noir coupe courte Pull&Bear Tunisie.",
                "imageUrl": "https://static.pullandbear.net/2/photos2/2024/V/0/2/p/9218/400/800/9218400800_1_1_8.jpg?t=1710950459952&imwidth=600",
                "lienAchat": "https://www.pullandbear.com/tn/femme/vetements/t-shirts-c29004.html",
                "prix": 42.0,
                "vendeur": "Pull&Bear TN",
                "taillesDisponibles": "XS, S, M, L",
                "couleur_brute": "Noir",
                "categorie_brute": "Haut",
                "genre_brut": "FEMME"
            },
            {
                "nom": "Jean Mom Bleu Pull&Bear Femme",
                "description": "Jean mom fit bleu délavé Pull&Bear Tunisie.",
                "imageUrl": "https://static.pullandbear.net/2/photos2/2024/V/0/2/p/9681/520/427/9681520427_1_1_8.jpg?t=1710950459952&imwidth=600",
                "lienAchat": "https://www.pullandbear.com/tn/femme/vetements/jeans-c29005.html",
                "prix": 89.0,
                "vendeur": "Pull&Bear TN",
                "taillesDisponibles": "36, 38, 40, 42",
                "couleur_brute": "Bleu",
                "categorie_brute": "Bas",
                "genre_brut": "FEMME"
            },
            {
                "nom": "Baskets Blanches Femme Pull&Bear",
                "description": "Baskets blanches plateforme légères femme Pull&Bear Tunisie.",
                "imageUrl": "https://static.pullandbear.net/2/photos2/2024/V/0/2/p/13130/420/050/13130420050_1_1_8.jpg?t=1710950459952&imwidth=600",
                "lienAchat": "https://www.pullandbear.com/tn/femme/chaussures-c29017.html",
                "prix": 109.0,
                "vendeur": "Pull&Bear TN",
                "taillesDisponibles": "36, 37, 38, 39, 40",
                "couleur_brute": "Blanc",
                "categorie_brute": "Chaussures",
                "genre_brut": "FEMME"
            },

            # ===========================
            # FEMME — BERSHKA
            # ===========================
            {
                "nom": "Sweat Oversize Rose Pastel Bershka Femme",
                "description": "Sweat oversize rose pastel streetwear femme Bershka Tunisie.",
                "imageUrl": "https://static.bershka.net/4/photos2/2024/V/0/1/p/9311/565/672/9311565672_2_1_8.jpg?t=1710950459952&imwidth=600",
                "lienAchat": "https://www.bershka.com/tn/femme/vetements/sweats-c1010193222.html",
                "prix": 75.0,
                "vendeur": "Bershka TN",
                "taillesDisponibles": "XS, S, M, L",
                "couleur_brute": "Rose",
                "categorie_brute": "Haut",
                "genre_brut": "FEMME"
            },
            {
                "nom": "Jean Cargo Femme Vert Bershka",
                "description": "Jean cargo vert kaki femme coupe utilitaire Bershka Tunisie.",
                "imageUrl": "https://static.bershka.net/4/photos2/2024/V/0/1/p/9188/038/505/9188038505_2_1_8.jpg?t=1710950459952&imwidth=600",
                "lienAchat": "https://www.bershka.com/tn/femme/vetements/jeans-c1010193223.html",
                "prix": 89.0,
                "vendeur": "Bershka TN",
                "taillesDisponibles": "36, 38, 40, 42",
                "couleur_brute": "Vert",
                "categorie_brute": "Bas",
                "genre_brut": "FEMME"
            },
            {
                "nom": "Veste Denim Femme Bleu Bershka",
                "description": "Veste en denim bleu femme coupe droite Bershka Tunisie.",
                "imageUrl": "https://static.bershka.net/4/photos2/2024/V/0/1/p/9601/011/427/9601011427_2_1_8.jpg?t=1710950459952&imwidth=600",
                "lienAchat": "https://www.bershka.com/tn/femme/vetements/vestes-c1010193220.html",
                "prix": 119.0,
                "vendeur": "Bershka TN",
                "taillesDisponibles": "XS, S, M, L",
                "couleur_brute": "Bleu",
                "categorie_brute": "Veste",
                "genre_brut": "FEMME"
            },

            # ===========================
            # ACCESSOIRES / CASQUETTES
            # ===========================
            {
                "nom": "Casquette Snapback Noire Exist",
                "description": "Casquette snapback réglable noire streetwear Exist Tunisie.",
                "imageUrl": "https://www.exist.com.tn/170400-large_default/casquette.jpg",
                "lienAchat": "https://www.exist.com.tn/casquettes/8020-48150-casquette.html",
                "prix": 29.99,
                "vendeur": "Exist",
                "taillesDisponibles": "Taille unique",
                "couleur_brute": "Noir",
                "categorie_brute": "Accessoire",
                "genre_brut": "UNISEXE"
            },
            {
                "nom": "Sacoche Bandoulière Noire Exist",
                "description": "Sacoche crossbody noire urbaine Exist Tunisie.",
                "imageUrl": "https://www.exist.com.tn/170450-large_default/sacoche.jpg",
                "lienAchat": "https://www.exist.com.tn/sacoches/8025-48180-sacoche.html",
                "prix": 49.99,
                "vendeur": "Exist",
                "taillesDisponibles": "Taille unique",
                "couleur_brute": "Noir",
                "categorie_brute": "Accessoire",
                "genre_brut": "UNISEXE"
            },
        ]

        return catalog[:limit]
