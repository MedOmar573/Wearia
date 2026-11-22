import re
import json
import logging
import hashlib
import httpx
from abc import ABC, abstractmethod
from typing import Optional, List, Dict, Any
from app.core.config import settings
from app.schemas.shopper import ShopperCriteria

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Prompt système amélioré : extraction exhaustive des critères
# ---------------------------------------------------------------------------
SYSTEM_PROMPT = """Tu es l'assistant IA Personnel Shopper de Wearia, spécialisé dans la mode en Tunisie.
Ton rôle est d'analyser la demande d'un utilisateur en langage naturel et d'extraire des critères de shopping précis sous forme de JSON strict.

RETOURNE UNIQUEMENT un objet JSON valide. Pas de texte, pas de markdown, pas d'explication.

Schéma JSON attendu :
{
  "style": "Streetwear" | "Chic" | "Décontracté" | "Classique" | "Sportswear" | "Bohème",
  "occasion": "UNIVERSITE" | "TRAVAIL" | "SORTIE" | "QUOTIDIEN" | "SPORT" | "EVENEMENT",
  "colors": ["Noir", "Blanc", "Bleu", "Gris", "Rouge", "Vert", "Beige", "Marron", "Rose", "Jaune", "Orange", "Bleu Marine"],
  "categories": ["haut", "bas", "chaussures", "veste", "accessoire", "robe"],
  "types_vetement": ["T-Shirt", "Pantalon", "Baskets", "Chemise", "Jean", "Hoodie", "Sweat", "Cargo", "Veste", "Robe", "Short", "Polo", "Pull", "Manteau"],
  "budget": 250.0,
  "currency": "TND",
  "search_queries": [
    "requete produit 1",
    "requete produit 2",
    "requete produit 3"
  ],
  "genre": "HOMME" | "FEMME" | "UNISEXE"
}

Règles IMPORTANTES :
1. "currency" = "TND" par défaut sauf mention explicite d'une autre devise.
2. Si aucun budget n'est mentionné, mets null. Sinon extrais le nombre exact (ex: "150 DT" → 150.0).
3. "search_queries" : génère 3 à 5 requêtes DISTINCTES et PRÉCISES pour chaque type de vêtement demandé.
   - Chaque requête doit contenir le type précis + couleur + style si mentionné.
   - Les requêtes doivent être variées : mélange français/anglais, termes synonymes.
4. "colors" : extraire TOUTES les couleurs souhaitées explicitement, sans inventer si non mentionné (laisser []).
5. "categories" et "types_vetement" : extraire tous les types mentionnés ou demandés.
6. Si l'utilisateur demande une "tenue complète" sans détails, composer Haut + Bas + Chaussures adaptés au style détecté.
7. "genre" : inférer du contexte si possible, sinon utiliser la valeur passée en paramètre.
8. Ne JAMAIS remplacer les critères de l'utilisateur par d'autres critères.
9. Ne JAMAIS inventer, deviner, réécrire ou inclure d'URL ou de lien boutique dans la réponse.
"""


def normalize_shopper_style(raw_style: Optional[str]) -> str:
    """Aligne les libellés de style UI (Casual, Sportif, Élégant...) avec la base Wearia."""
    if not raw_style:
        return "Décontracté"
    s = raw_style.strip().lower()
    if any(k in s for k in ("street", "urban", "urbain", "skate", "oversize")):
        return "Streetwear"
    if any(k in s for k in ("chic", "eleg", "élég", "soign")):
        return "Chic"
    if any(k in s for k in ("classi", "formel", "habil", "costume")):
        return "Classique"
    if any(k in s for k in ("sport", "gym", "running", "fitness")):
        return "Sportswear"
    if any(k in s for k in ("bohem", "bohèm", "boho", "vintage")):
        return "Bohème"
    if any(k in s for k in ("minimal",)):
        return "Minimaliste"
    if any(k in s for k in ("casual", "decontract", "décontract", "simple", "quotidien")):
        return "Décontracté"
    return raw_style.strip()


def normalize_shopper_occasion(raw_occasion: Optional[str]) -> str:
    """Normalise l'occasion (sans accents) vers l'enum canonique Wearia."""
    if not raw_occasion:
        return "QUOTIDIEN"
    o = raw_occasion.strip().lower()
    if any(k in o for k in ("universit", "fac", "cours", "etud", "étud")):
        return "UNIVERSITE"
    if any(k in o for k in ("travail", "bureau", "boulot", "reunion", "réunion", "stage", "pro", "entretien")):
        return "TRAVAIL"
    if any(k in o for k in ("evenement", "événement", "mariage", "gala", "ceremonie", "cérémonie")):
        return "EVENEMENT"
    if any(k in o for k in ("sortie", "soiree", "soirée", "fete", "fête", "club", "restaurant")):
        return "SORTIE"
    if any(k in o for k in ("sport", "gym", "running", "fitness", "course")):
        return "SPORT"
    return "QUOTIDIEN"


def normalize_shopper_season(raw_season: Optional[str]) -> Optional[str]:
    """Normalise la saison vers PRINTEMPS / ETE / AUTOMNE / HIVER (ou None)."""
    if not raw_season:
        return None
    s = raw_season.strip().lower()
    if any(k in s for k in ("ete", "été", "summer", "chaud", "plage")):
        return "ETE"
    if any(k in s for k in ("hiver", "winter", "froid", "neige")):
        return "HIVER"
    if any(k in s for k in ("automne", "autumn", "fall", "mi-saison")):
        return "AUTOMNE"
    if any(k in s for k in ("printemps", "spring")):
        return "PRINTEMPS"
    return None

# ---------------------------------------------------------------------------
# Classes
# ---------------------------------------------------------------------------

class BaseLLMProvider(ABC):
    @abstractmethod
    async def interpret_prompt(self, prompt: str, user_genre: Optional[str] = None) -> ShopperCriteria:
        pass

class OllamaLLMProvider(BaseLLMProvider):
    """
    Client pour exécuter un LLM local via Ollama (Qwen 3 / Qwen 2.5).
    """
    def __init__(self, base_url: str = None, model: str = None, timeout: int = None):
        self.base_url = (base_url or settings.OLLAMA_BASE_URL).rstrip("/")
        self.model = model or settings.OLLAMA_MODEL
        self.timeout = timeout or settings.LLM_TIMEOUT_SECONDS

    async def is_available(self) -> bool:
        try:
            async with httpx.AsyncClient(timeout=2.0) as client:
                res = await client.get(f"{self.base_url}/api/tags")
                return res.status_code == 200
        except Exception:
            return False

    async def interpret_prompt(self, prompt: str, user_genre: Optional[str] = None) -> ShopperCriteria:
        url = f"{self.base_url}/api/chat"
        genre_info = f" L'utilisateur est de genre {user_genre}." if user_genre else ""
        user_message = f"Demande : \"{prompt}\".{genre_info} Retourne uniquement le JSON demandé."

        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_message}
            ],
            "stream": False,
            "format": "json",
            "options": {
                "temperature": 0.1,
                "top_p": 0.9
            }
        }

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(url, json=payload)
            response.raise_for_status()
            data = response.json()
            raw_content = data.get("message", {}).get("content", "").strip()

            # Nettoyage markdown éventuel
            cleaned_json = re.sub(r"^```json\s*", "", raw_content, flags=re.MULTILINE)
            cleaned_json = re.sub(r"```$", "", cleaned_json, flags=re.MULTILINE).strip()

            parsed = json.loads(cleaned_json)
            return _build_criteria_from_dict(parsed, user_genre)


class RuleBasedFallbackLLMProvider(BaseLLMProvider):
    """
    Extracteur sémantique haute fidélité — fallback garanti 100% disponible.
    Extrait tous les critères pertinents depuis le langage naturel.
    """
    async def interpret_prompt(self, prompt: str, user_genre: Optional[str] = None) -> ShopperCriteria:
        lower = prompt.lower()

        # 1. Budget — recherche spécifique TND/DT/dinars en priorité
        budget: Optional[float] = None
        specific_match = re.search(r"(\d+(?:[.,]\d+)?)\s*(?:tnd|dt|dinars?|dinar)", lower)
        if specific_match:
            budget = float(specific_match.group(1).replace(",", "."))
        elif "budget" in lower:
            b_match = re.search(r"budget\D{0,10}?(\d+(?:[.,]\d+)?)", lower)
            if b_match:
                budget = float(b_match.group(1).replace(",", "."))
        elif "moins de" in lower or "max" in lower or "maximum" in lower:
            m_match = re.search(r"(?:moins\s+de|max(?:imum)?)\s*(\d+(?:[.,]\d+)?)", lower)
            if m_match:
                budget = float(m_match.group(1).replace(",", "."))

        # 2. Devise
        currency = "TND"
        if "eur" in lower or "€" in lower:
            currency = "EUR"
        elif "usd" in lower or "$" in lower:
            currency = "USD"

        # 3. Genre
        effective_genre = user_genre or "HOMME"
        if any(w in lower for w in ["femme", "fille", "elle", "dame", "women", "woman", "girl"]):
            effective_genre = "FEMME"
        elif any(w in lower for w in ["homme", "garçon", "lui", "men", "man", "boy", "mec"]):
            effective_genre = "HOMME"
        elif any(w in lower for w in ["unisexe", "mixte", "unisex"]):
            effective_genre = "UNISEXE"

        # 4. Style vestimentaire
        style = "Décontracté"
        if any(w in lower for w in ["streetwear", "street", "urban", "urbain", "skate", "oversize", "baggy"]):
            style = "Streetwear"
        elif any(w in lower for w in ["chic", "élégant", "elegant", "soigné"]):
            style = "Chic"
        elif any(w in lower for w in ["classique", "costume", "habillé", "habille", "formel", "formal"]):
            style = "Classique"
        elif any(w in lower for w in ["sport", "sportswear", "gym", "running", "fitness", "training"]):
            style = "Sportswear"
        elif any(w in lower for w in ["bohème", "boheme", "boho", "vintage"]):
            style = "Bohème"
        elif any(w in lower for w in ["casual", "décontracté", "decontracte", "simple", "quotidien"]):
            style = "Décontracté"

        # 5. Occasion
        occasion = "QUOTIDIEN"
        if any(w in lower for w in ["université", "universite", "fac", "cours", "amphi", "etudes", "étudiant"]):
            occasion = "UNIVERSITE"
        elif any(w in lower for w in ["travail", "bureau", "boulot", "reunion", "stage", "entretien", "professionnel"]):
            occasion = "TRAVAIL"
        elif any(w in lower for w in ["soirée", "soiree", "fête", "fete", "anniversaire", "club", "sortie", "soir"]):
            occasion = "SORTIE"
        elif any(w in lower for w in ["mariage", "evenement", "événement", "gala", "cérémonie", "ceremonie"]):
            occasion = "EVENEMENT"
        elif any(w in lower for w in ["sport", "course", "fitness", "entrainement", "entraînement", "gym", "running"]):
            occasion = "SPORT"

        # 5b. Saison détectée depuis le prompt libre
        detected_season = normalize_shopper_season(lower)

        # 6. Couleurs — extraction stricte avec distinction souhaitées vs évitées
        color_vocab = {
            "bleu marine": "Bleu Marine", "marine": "Bleu Marine", "navy": "Bleu Marine",
            "marron foncé": "Marron Foncé", "marron fonce": "Marron Foncé",
            "jaune clair": "Jaune Clair",
            "noir": "Noir", "noire": "Noir", "noires": "Noir", "noirs": "Noir", "black": "Noir",
            "blanc": "Blanc", "blanche": "Blanc", "blanches": "Blanc", "blancs": "Blanc", "white": "Blanc",
            "bleu": "Bleu", "bleue": "Bleu", "bleues": "Bleu", "blue": "Bleu",
            "gris": "Gris", "grise": "Gris", "grises": "Gris", "grey": "Gris", "gray": "Gris",
            "rouge": "Rouge", "rouges": "Rouge", "red": "Rouge", "bordeaux": "Rouge",
            "vert": "Vert", "verte": "Vert", "vertes": "Vert", "green": "Vert",
            "kaki": "Vert", "khaki": "Vert", "olive": "Vert",
            "beige": "Beige", "sable": "Beige", "camel": "Beige",
            "marron": "Marron", "brun": "Marron", "brune": "Marron", "brown": "Marron",
            "chocolat": "Marron",
            "rose": "Rose", "pink": "Rose",
            "jaune": "Jaune", "yellow": "Jaune", "moutarde": "Jaune",
            "orange": "Orange", "corail": "Corail", "violet": "Violet", "mauve": "Violet",
        }
        detected_colors: List[str] = []
        avoided_colors: List[str] = []
        neg_color_re = re.compile(r"\b(?:sans|pas\s+de|pas\s+d|eviter|éviter|evite|évite|hors)\s+(?:du|de\s+la|de|le|la|les)?\s*$")
        matched_spans: List[tuple[int, int]] = []
        # Tester d'abord les expressions multi-mots (ex: "bleu marine") pour ne pas recouper "bleu"
        for word, std_color in sorted(color_vocab.items(), key=lambda x: -len(x[0])):
            for m in re.finditer(r"\b" + re.escape(word) + r"\b", lower):
                if any(m.start() >= s and m.end() <= e for s, e in matched_spans):
                    continue
                matched_spans.append((m.start(), m.end()))
                prefix = lower[max(0, m.start() - 24):m.start()]
                if neg_color_re.search(prefix):
                    if std_color not in avoided_colors:
                        avoided_colors.append(std_color)
                else:
                    if std_color not in detected_colors and std_color not in avoided_colors:
                        detected_colors.append(std_color)

        # 7. Catégories et Types — détection exhaustive (pas de elif, tous peuvent être présents)
        categories: List[str] = []
        types: List[str] = []

        def add(cat: str, typ: str):
            if cat not in categories:
                categories.append(cat)
            if typ not in types:
                types.append(typ)

        # Hauts
        if re.search(r"\b(t-?shirt|tee[-\s]?shirt)\b", lower):
            add("haut", "T-Shirt")
        if re.search(r"\bchemise\b", lower):
            add("haut", "Chemise")
        if re.search(r"\bpolo\b", lower):
            add("haut", "Polo")
        if re.search(r"\b(sweat|hoodie|sweatshirt)\b", lower):
            add("haut", "Hoodie")
        if re.search(r"\bpull\b", lower):
            add("haut", "Pull")
        if re.search(r"\bdébardeur\b", lower):
            add("haut", "T-Shirt")

        # Bas
        if re.search(r"\bjeans?\b", lower):
            add("bas", "Jean")
        if re.search(r"\b(cargo)\b", lower):
            add("bas", "Cargo")
        if re.search(r"\bpantalon\b", lower):
            add("bas", "Pantalon")
        if re.search(r"\b(jogger|jogging)\b", lower):
            add("bas", "Pantalon")
        if re.search(r"\bshort\b", lower):
            add("bas", "Short")
        if re.search(r"\bjupe\b", lower):
            add("bas", "Jupe")
        if re.search(r"\bchino\b", lower):
            add("bas", "Pantalon")

        # Chaussures
        if re.search(r"\b(baskets?|sneakers?|tennis)\b", lower):
            add("chaussures", "Baskets")
        if re.search(r"\bbottes?\b", lower):
            add("chaussures", "Bottes")
        if re.search(r"\b(chaussures?|mocassin|derby)\b", lower) and not re.search(r"\bbaskets?\b", lower):
            add("chaussures", "Chaussures de ville")

        # Vestes / Manteaux
        if re.search(r"\b(veste|blouson|bomber|blousons?)\b", lower):
            add("veste", "Veste")
        if re.search(r"\bblazers?\b", lower):
            add("veste", "Veste")
        if re.search(r"\bmanteau\b", lower):
            add("veste", "Manteau")

        # Robe
        if re.search(r"\bRobe\b", lower, re.IGNORECASE):
            add("robe", "Robe")

        # Compléter la tenue si l'utilisateur n'a pas demandé toutes les pièces
        # Toujours avoir Haut + Bas + Chaussures pour composer un outfit complet
        is_outfit_request = any(w in lower for w in ["tenue", "look", "outfit", "style complet", "habillé", "habille"])
        if not categories or is_outfit_request or ("bas" in categories and "haut" not in categories) or ("haut" in categories and "bas" not in categories):
            if "robe" not in categories:
                if "haut" not in categories:
                    if style == "Streetwear":
                        add("haut", "Hoodie" if "sweat" in lower or "hoodie" in lower else "T-Shirt")
                    elif style in ["Chic", "Classique"]:
                        add("haut", "Chemise")
                    else:
                        add("haut", "T-Shirt")
                if "bas" not in categories:
                    if style == "Streetwear":
                        add("bas", "Cargo" if "cargo" in lower else "Jean")
                    elif style == "Sportswear":
                        add("bas", "Pantalon")
                    else:
                        add("bas", "Jean")
                if "chaussures" not in categories:
                    if style in ["Chic", "Classique"]:
                        add("chaussures", "Chaussures de ville")
                    else:
                        add("chaussures", "Baskets")

        # 8. Génération des requêtes de recherche — dynamiques et diversifiées
        main_color = detected_colors[0].lower() if detected_colors else ""
        style_lower = style.lower()
        genre_term_fr = "homme" if effective_genre == "HOMME" else "femme" if effective_genre == "FEMME" else ""
        genre_term_en = "men" if effective_genre == "HOMME" else "women" if effective_genre == "FEMME" else ""

        search_queries: List[str] = []
        seen_queries = set()

        def add_query(q: str):
            q = q.strip()
            # Déduplique par hash normalisé
            key = re.sub(r"\s+", " ", q.lower())
            if key not in seen_queries and len(q) > 3:
                seen_queries.add(key)
                search_queries.append(q)

        for t in types:
            t_lower = t.lower()
            color_part = f" {main_color}" if main_color else ""
            genre_part_fr = f" {genre_term_fr}" if genre_term_fr else ""
            genre_part_en = f" {genre_term_en}" if genre_term_en else ""

            # Requêtes variées par type
            add_query(f"{t}{color_part}{genre_part_fr} {style_lower}".strip())
            add_query(f"{t}{color_part}{genre_part_fr}".strip())

            # Variante anglaise pour les principaux types
            type_en_map = {
                "t-shirt": "t-shirt", "chemise": "shirt", "polo": "polo",
                "hoodie": "hoodie", "pull": "sweater", "jean": "jeans",
                "cargo": "cargo pants", "pantalon": "trousers", "short": "shorts",
                "baskets": "sneakers", "bottes": "boots", "veste": "jacket",
                "manteau": "coat", "robe": "dress", "jupe": "skirt"
            }
            type_en = type_en_map.get(t_lower, t_lower)
            add_query(f"{main_color} {type_en}{genre_part_en}".strip())
            add_query(f"{style_lower} {type_en}{genre_part_en} {main_color}".strip())

        # Requêtes globales (tenue / look)
        if main_color:
            add_query(f"tenue {main_color} {genre_term_fr} {style_lower}".strip())
        add_query(f"vêtements {genre_term_fr} {style_lower} tunisie".strip())
        add_query(f"{style_lower} outfit {genre_term_en} {main_color}".strip())

        return ShopperCriteria(
            style=normalize_shopper_style(style),
            occasion=normalize_shopper_occasion(occasion),
            colors=detected_colors,
            avoided_colors=avoided_colors,
            season=detected_season,
            categories=list(dict.fromkeys(categories)),
            types_vetement=list(dict.fromkeys(types)),
            budget=budget,
            currency=currency,
            search_queries=list(dict.fromkeys(search_queries))[:6]  # max 6 requêtes
        )


def _build_criteria_from_dict(d: dict, user_genre: Optional[str] = None) -> ShopperCriteria:
    """
    Construit un ShopperCriteria depuis un dict JSON (réponse Ollama).
    Gère les champs manquants, normalise style/occasion/saison et ne conserve aucune URL.
    """
    def safe_list(val, default=None):
        if isinstance(val, list):
            return [str(v) for v in val if v]
        if isinstance(val, str) and val:
            return [val]
        return default or []

    def safe_str(val, default=""):
        return str(val).strip() if val else default

    def safe_float(val):
        if val is None:
            return None
        try:
            return float(val)
        except (TypeError, ValueError):
            return None

    colors = safe_list(d.get("colors"), [])
    avoided_colors = safe_list(d.get("avoided_colors"), [])
    categories = safe_list(d.get("categories"), [])
    types = safe_list(d.get("types_vetement"), [])
    queries = [q for q in safe_list(d.get("search_queries"), []) if "http://" not in q.lower() and "https://" not in q.lower()]

    return ShopperCriteria(
        style=normalize_shopper_style(safe_str(d.get("style"), "Décontracté")),
        occasion=normalize_shopper_occasion(safe_str(d.get("occasion"), "QUOTIDIEN")),
        colors=colors,
        avoided_colors=avoided_colors,
        season=normalize_shopper_season(d.get("season")),
        categories=categories,
        types_vetement=types,
        budget=safe_float(d.get("budget")),
        currency=safe_str(d.get("currency"), "TND"),
        search_queries=queries[:6]
    )


class ShopperLLMManager:
    """
    Gestionnaire orchestrateur du LLM.
    Tente Ollama d'abord, bascule sur le moteur rule-based en fallback.
    """
    def __init__(self):
        self.ollama_provider = OllamaLLMProvider()
        self.fallback_provider = RuleBasedFallbackLLMProvider()

    async def interpret(self, prompt: str, user_genre: Optional[str] = None) -> ShopperCriteria:
        try:
            if await self.ollama_provider.is_available():
                logger.info("[LLM] Connexion Ollama active → interprétation LLM...")
                result = await self.ollama_provider.interpret_prompt(prompt, user_genre)
                logger.info(f"[LLM] Critères Ollama : {result.model_dump()}")
                return result
        except Exception as e:
            logger.warning(f"[LLM] Ollama non disponible ({e}), bascule sur moteur sémantique.")

        logger.info("[LLM] Interprétation avec moteur rule-based...")
        result = await self.fallback_provider.interpret_prompt(prompt, user_genre)
        logger.info(f"[LLM] Critères rule-based : {result.model_dump()}")
        return result
