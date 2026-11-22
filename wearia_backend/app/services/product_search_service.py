import logging
import re
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Set, Tuple
from sqlalchemy.orm import Session

from app.ai.shopper_llm import (
    normalize_shopper_occasion,
    normalize_shopper_season,
    normalize_shopper_style,
)
from app.ai.taxonomy import normalize_clothing_color
from app.models.enums import GenreCible
from app.models.shopping import ArticleCatalogue
from app.schemas.shopper import ShopperCriteria
from app.services.shopper_validation import (
    build_product_dedup_keys,
    is_valid_product_url,
    normalize_product_url,
    normalize_text,
)

logger = logging.getLogger(__name__)

# Noms de marques pouvant contenir des noms de vêtements trompeurs ("Pull&Bear" -> "pull")
_BRAND_NOISE_RE = re.compile(r"\bpull\s*(?:&|and|et)?\s*bear\b", re.IGNORECASE)

REQUESTED_TYPE_DEFINITIONS = {
    "chemise": ("hauts", ("chemise", "chemises", "chemisier", "blouse", "sur chemise", "surchemise")),
    "t shirt": ("hauts", ("t shirt", "tshirt", "tee shirt", "tee-shirt", "t shirts", "tshirts", "debardeur")),
    "polo": ("hauts", ("polo", "polos")),
    "pull": ("hauts", ("pull", "pulls", "sous pull", "cardigan", "sweater", "tricot")),
    "sweat": ("hauts", ("sweat", "sweats", "hoodie", "sweatshirt", "sweat shirt")),
    "jean": ("bas", ("jean", "jeans", "denim")),
    "pantalon": ("bas", ("pantalon", "pantalons", "trousers")),
    "cargo": ("bas", ("cargo", "cargos")),
    "chino": ("bas", ("chino", "chinos")),
    "jogging": ("bas", ("jogging", "jogger", "joggers")),
    "short": ("bas", ("short", "shorts", "bermuda")),
    "jupe": ("bas", ("jupe", "jupes", "skirt")),
    "robe": ("robes", ("robe", "robes", "dress")),
    "baskets": ("chaussures", ("basket", "baskets", "sneaker", "sneakers", "tennis")),
    "bottes": ("chaussures", ("botte", "bottes", "bottine", "bottines", "boots")),
    "chaussures de ville": ("chaussures", ("chaussure de ville", "chaussures de ville", "mocassin", "mocassins", "derby", "derbies", "escarpin")),
    "veste": ("vestes", ("veste", "vestes", "blazer", "blazers", "blouson", "bomber", "jacket")),
    "manteau": ("vestes", ("manteau", "manteaux", "trench", "doudoune", "parka", "coat")),
    "chapeau": ("accessoires", ("chapeau", "chapeaux", "casquette", "casquettes", "bonnet", "bonnets", "bob", "fedora", "hat", "cap", "beanie")),
    "sac": ("accessoires", ("sac", "sacs", "sac a main", "sac a dos", "sacoche", "cabas", "pochette", "bag", "handbag", "backpack")),
    "ceinture": ("accessoires", ("ceinture", "ceintures", "belt")),
    "echarpe": ("accessoires", ("echarpe", "echarpes", "foulard", "scarf")),
    "montre": ("accessoires", ("montre", "montres", "watch")),
    "accessoire": ("accessoires", ("accessoire", "ceinture", "casquette", "chapeau", "sac", "montre", "echarpe", "bonnet")),
}

# Compatibilité Style UI/canonique -> libellés DB & types favoris / incompatibles
_STYLE_DB_EQUIVALENTS: Dict[str, Set[str]] = {
    "décontracté": {"décontracté", "casual", "streetwear"},
    "streetwear": {"streetwear", "décontracté", "sportswear"},
    "chic": {"chic", "classique"},
    "classique": {"classique", "chic"},
    "sportswear": {"sportswear", "streetwear"},
    "minimaliste": {"classique", "décontracté", "chic"},
    "bohème": {"bohème", "décontracté"},
}

_STYLE_CLASHING_DB: Dict[str, Set[str]] = {
    "chic": {"sportswear"},
    "classique": {"sportswear"},
    "sportswear": {"chic", "bohème"},
    "bohème": {"sportswear"},
}

# Compatibilité Occasion -> types favoris vs types incohérents
_OCCASION_PREFERENCES: Dict[str, Tuple[Set[str], Set[str]]] = {
    "TRAVAIL": (
        {"chemise", "polo", "pantalon", "chino", "veste", "blazer", "chaussures de ville", "mocassin", "derby", "pull", "robe", "jupe", "manteau"},
        {"jogging", "jogger", "short", "bermuda", "hoodie", "sweat", "debardeur"},
    ),
    "EVENEMENT": (
        {"chemise", "veste", "blazer", "pantalon", "chino", "chaussures de ville", "mocassin", "derby", "robe", "jupe", "manteau"},
        {"jogging", "jogger", "short", "bermuda", "hoodie", "sweat", "cargo", "debardeur"},
    ),
    "SPORT": (
        {"t shirt", "sweat", "hoodie", "jogging", "jogger", "short", "baskets", "debardeur"},
        {"chemise", "blazer", "costume", "chaussures de ville", "mocassin", "derby", "robe", "jupe", "manteau"},
    ),
    "UNIVERSITE": (
        {"t shirt", "sweat", "hoodie", "pull", "chemise", "polo", "jean", "pantalon", "cargo", "chino", "baskets", "veste"},
        {"costume", "escarpin"},
    ),
    "SORTIE": (
        {"chemise", "t shirt", "polo", "veste", "blazer", "jean", "pantalon", "cargo", "robe", "jupe", "baskets", "chaussures de ville", "bottes"},
        {"jogging", "jogger"},
    ),
    "QUOTIDIEN": (
        {"t shirt", "polo", "chemise", "pull", "sweat", "jean", "pantalon", "chino", "short", "baskets", "veste", "robe"},
        set(),
    ),
}

# Mots-clés saisonniers : (incompatibles stricts, pénalisés, favorisés)
_SEASON_RULES: Dict[str, Tuple[Set[str], Set[str], Set[str]]] = {
    "ETE": (
        {"manteau", "doudoune", "parka", "trench", "sous pull", "col montant", "laine", "cachemire", "bottes", "bottine", "echarpe", "bonnet"},
        {"sweat", "hoodie", "pull", "molleton", "blouson"},
        {"t shirt", "polo", "short", "bermuda", "lin", "debardeur", "chemise", "robe", "jupe", "baskets", "coton"},
    ),
    "HIVER": (
        {"short", "bermuda", "debardeur", "sandale"},
        {"lin", "manches courtes"},
        {"pull", "sous pull", "sweat", "hoodie", "manteau", "veste", "doudoune", "parka", "laine", "molleton", "jean", "pantalon", "bottes", "chemise"},
    ),
    "AUTOMNE": (
        {"debardeur", "sandale"},
        {"short", "bermuda"},
        {"veste", "blouson", "chemise", "pull", "sweat", "jean", "pantalon", "chino", "baskets", "bottes", "sur chemise"},
    ),
    "PRINTEMPS": (
        {"doudoune", "parka", "bonnet", "echarpe"},
        {"manteau", "sous pull"},
        {"chemise", "t shirt", "polo", "veste", "jean", "pantalon", "chino", "robe", "jupe", "baskets", "coton"},
    ),
}


def _normalize_text(value: str) -> str:
    cleaned = _BRAND_NOISE_RE.sub(" ", value or "")
    return normalize_text(cleaned)


def extract_requested_type_mentions(text: str) -> List[str]:
    """Extrait les types de vêtements explicitement demandés dans la consigne libre."""
    normalized = _normalize_text(text)
    mentions = []
    negative_prefix = re.compile(
        r"\b(?:sans|ni|pas de|pas d|eviter|evite|ne veux pas de|ne veut pas de|hors)\s+(?:un|une|des|du|de la|les|le|la)?\s*$"
    )
    for canonical, (_, aliases) in REQUESTED_TYPE_DEFINITIONS.items():
        for alias in aliases:
            normalized_alias = _normalize_text(alias)
            match = re.search(rf"(?<!\w){re.escape(normalized_alias)}(?!\w)", normalized)
            if not match:
                continue
            if negative_prefix.search(normalized[max(0, match.start() - 32):match.start()]):
                continue
            mentions.append(canonical)
            break
    return list(dict.fromkeys(mentions))


def extract_excluded_type_mentions(text: str) -> List[str]:
    """Extrait les types de vêtements explicitement exclus dans la consigne libre ('sans jean', 'pas de baskets')."""
    normalized = _normalize_text(text)
    excluded = []
    negative_prefix = re.compile(
        r"\b(?:sans|ni|pas de|pas d|eviter|evite|ne veux pas de|ne veut pas de|hors)\s+(?:un|une|des|du|de la|les|le|la)?\s*$"
    )
    for canonical, (_, aliases) in REQUESTED_TYPE_DEFINITIONS.items():
        for alias in aliases:
            normalized_alias = _normalize_text(alias)
            match = re.search(rf"(?<!\w){re.escape(normalized_alias)}(?!\w)", normalized)
            if not match:
                continue
            if negative_prefix.search(normalized[max(0, match.start() - 32):match.start()]):
                excluded.append(canonical)
                break
    return list(dict.fromkeys(excluded))


def _requested_definitions(values: List[str]) -> Dict[str, List[Tuple[str, ...]]]:
    by_category: Dict[str, List[Tuple[str, ...]]] = {}
    for value in values or []:
        normalized = _normalize_text(value)
        if not normalized:
            continue
        for _, (category, aliases) in REQUESTED_TYPE_DEFINITIONS.items():
            normalized_aliases = tuple(_normalize_text(alias) for alias in aliases)
            if any(re.search(rf"(?<!\w){re.escape(alias)}(?!\w)", normalized) for alias in normalized_aliases):
                if normalized_aliases not in by_category.get(category, []):
                    by_category.setdefault(category, []).append(normalized_aliases)
    return by_category


def _matches_requested_type(item: ArticleCatalogue, alias_groups: List[Tuple[str, ...]]) -> bool:
    searchable = _normalize_text(
        " ".join((item.nom or "", item.type_vetement.nom if item.type_vetement else ""))
    )
    return any(
        re.search(rf"(?<!\w){re.escape(alias)}(?!\w)", searchable)
        for aliases in alias_groups
        for alias in aliases
    )


def _canonical_color_key(color_name: Optional[str]) -> str:
    if not color_name:
        return ""
    return normalize_text(normalize_clothing_color(color_name))


def _colors_match_exact(item_color: Optional[str], target_color: str) -> bool:
    ic = _canonical_color_key(item_color)
    tc = _canonical_color_key(target_color)
    return bool(ic and tc and ic == tc)


def _article_category_key(art: ArticleCatalogue) -> str:
    """
    Détermine la catégorie canonique d'un article de façon fiable :
    - Supprime les noms de marque trompeurs ("Pull&Bear")
    - Teste les vestes/manteaux AVANT "jean" ("Veste en Jean" -> "vestes", jamais "bas")
    - Teste chaussures/robes avant hauts/bas
    """
    art_name = _normalize_text(art.nom or "")
    tv_nom = _normalize_text(art.type_vetement.nom if art.type_vetement else "")
    cat_nom_db = _normalize_text(
        art.type_vetement.categorie.nom if (art.type_vetement and art.type_vetement.categorie) else ""
    )
    combined = f"{art_name} {tv_nom}".strip()

    def has_any(text: str, words: Set[str]) -> bool:
        return any(re.search(rf"(?<!\w){re.escape(w)}(?!\w)", text) for w in words)

    vest_kw = {"veste", "blazer", "manteau", "blouson", "bomber", "doudoune", "parka", "trench"}
    shoe_kw = {"basket", "baskets", "sneaker", "sneakers", "botte", "bottes", "bottine", "chaussure", "chaussures", "mocassin", "derby", "derbies", "escarpin", "sandale"}
    robe_kw = {"robe", "dress", "combinaison"}
    bas_kw = {"jean", "jeans", "denim", "cargo", "pantalon", "jogger", "jogging", "short", "bermuda", "chino", "jupe"}
    haut_kw = {"t shirt", "tshirt", "chemise", "sur chemise", "surchemise", "polo", "pull", "sous pull", "sweat", "hoodie", "sweatshirt", "blouse", "debardeur", "cardigan"}
    acc_kw = {"casquette", "chapeau", "bonnet", "sacoche", "sac", "ceinture", "montre", "echarpe", "foulard"}

    # Priorité au titre produit pour éviter une mauvaise catégorie héritée en base
    for txt in (art_name, combined):
        if has_any(txt, vest_kw):
            return "vestes"
        if has_any(txt, shoe_kw):
            return "chaussures"
        if has_any(txt, robe_kw):
            return "robes"
        if has_any(txt, bas_kw):
            return "bas"
        if has_any(txt, haut_kw):
            return "hauts"
        if has_any(txt, acc_kw):
            return "accessoires"

    if "haut" in cat_nom_db:
        return "hauts"
    if "bas" in cat_nom_db:
        return "bas"
    if any(x in cat_nom_db for x in ("chaussure", "basket", "botte")):
        return "chaussures"
    if any(x in cat_nom_db for x in ("veste", "manteau")):
        return "vestes"
    if "robe" in cat_nom_db:
        return "robes"
    return "accessoires"


def compute_article_score(item: ArticleCatalogue, criteres: ShopperCriteria) -> int:
    """
    Score explicite et transparent d'un article vis-à-vis de TOUS les critères :
    couleurs, types demandés, style, occasion, saison, mots-clés et budget.
    """
    score = 0
    item_nom_norm = _normalize_text(item.nom or "")
    tv_nom_norm = _normalize_text(item.type_vetement.nom if item.type_vetement else "")
    searchable = f"{item_nom_norm} {tv_nom_norm}".strip()
    item_color_nom = item.couleur.nom if item.couleur else ""

    # 1. Couleurs souhaitées (+65 exact / +15 mention nom)
    if criteres.colors:
        matched_color = False
        for target_c in criteres.colors:
            if _colors_match_exact(item_color_nom, target_c):
                score += 65
                matched_color = True
                break
        if not matched_color:
            for target_c in criteres.colors:
                tc_norm = _canonical_color_key(target_c)
                if tc_norm and re.search(rf"(?<!\w){re.escape(tc_norm)}(?!\w)", item_nom_norm):
                    score += 30
                    break

    # 2. Types / pièces souhaitées (+55 si type explicitement demandé, +35 si type détecté)
    req_defs = _requested_definitions(criteres.requested_types)
    if req_defs:
        all_req_aliases = [grp for grps in req_defs.values() for grp in grps]
        if _matches_requested_type(item, all_req_aliases):
            score += 55

    if criteres.types_vetement:
        for t in criteres.types_vetement:
            t_norm = _normalize_text(t)
            if t_norm and (t_norm == tv_nom_norm or re.search(rf"(?<!\w){re.escape(t_norm)}(?!\w)", searchable)):
                score += 35
                break

    # 3. Style (avec mapping canonique Casual<->Décontracté, Sportif<->Sportswear, Élégant<->Chic)
    norm_style = normalize_shopper_style(criteres.style).lower()
    item_style = (item.style.libelle or "").strip().lower() if item.style else ""
    accepted_styles = _STYLE_DB_EQUIVALENTS.get(norm_style, {norm_style})
    clashing_styles = _STYLE_CLASHING_DB.get(norm_style, set())
    if item_style:
        if item_style in accepted_styles:
            score += 40
        elif item_style in clashing_styles:
            score -= 25
    if norm_style and norm_style in item_nom_norm:
        score += 10

    # 4. Occasion (+35 si adapté, -30 si incohérent)
    norm_occ = normalize_shopper_occasion(criteres.occasion)
    good_occ_kw, bad_occ_kw = _OCCASION_PREFERENCES.get(norm_occ, (set(), set()))
    if any(re.search(rf"(?<!\w){re.escape(k)}(?!\w)", searchable) for k in bad_occ_kw):
        score -= 35
    elif any(re.search(rf"(?<!\w){re.escape(k)}(?!\w)", searchable) for k in good_occ_kw):
        score += 35

    # 5. Saison (+30 si adapté, -35 si pénalisé)
    norm_season = normalize_shopper_season(criteres.season)
    if norm_season and norm_season in _SEASON_RULES:
        hard_bad, soft_bad, good_season = _SEASON_RULES[norm_season]
        if any(re.search(rf"(?<!\w){re.escape(k)}(?!\w)", searchable) for k in hard_bad):
            score -= 60
        elif any(re.search(rf"(?<!\w){re.escape(k)}(?!\w)", searchable) for k in soft_bad):
            score -= 30
        elif any(re.search(rf"(?<!\w){re.escape(k)}(?!\w)", searchable) for k in good_season):
            score += 30

    # 6. Mots-clés search_queries (max +25)
    query_keywords = {
        w for sq in (criteres.search_queries or [])
        for w in re.split(r"[\s\-_]+", _normalize_text(sq))
        if len(w) > 2
    }
    if query_keywords:
        matched_kw = sum(1 for kw in query_keywords if kw in item_nom_norm)
        score += min(25, matched_kw * 6)

    # 7. Efficacité prix si budget serré
    if criteres.budget and criteres.budget > 0 and item.prix:
        if item.prix <= criteres.budget * 0.45:
            score += 8

    return score


def filter_and_group_articles(
    articles: List[ArticleCatalogue],
    criteres: ShopperCriteria,
    user_gender: Optional[str] = None,
    excluded_product_ids: Optional[List[int]] = None,
    excluded_urls: Optional[List[str]] = None,
    allowed_domains: Optional[Set[str]] = None,
    verified_product_urls: Optional[List[str]] = None,
) -> Dict[str, List[ArticleCatalogue]]:
    """
    Filtre strictement, score, déduplique et regroupe les articles par catégorie.
    Fonction pure (testable directement sans base de données).
    """
    user_gender_upper = (user_gender or "HOMME").upper()
    excluded_id_set = set(excluded_product_ids or [])
    excluded_url_set = {normalize_product_url(u) for u in (excluded_urls or []) if u}
    verified_url_set = (
        {normalize_product_url(u) for u in verified_product_urls if u}
        if verified_product_urls is not None
        else None
    )

    # Propager les exclusions de session aux doublons d'identité (même vendeur + nom + couleur sous une autre URL)
    excluded_identity_set: Set[str] = set()
    if excluded_id_set or excluded_url_set:
        for art in articles:
            norm_url = normalize_product_url(art.lienAchat)
            if art.id in excluded_id_set or (norm_url and norm_url in excluded_url_set):
                keys = build_product_dedup_keys(
                    product_id=art.id,
                    name=art.nom,
                    vendor=art.vendeur,
                    color=art.couleur.nom if art.couleur else "",
                    url=art.lienAchat,
                )
                if keys["url_key"]:
                    excluded_url_set.add(keys["url_key"])
                if keys["identity_key"]:
                    excluded_identity_set.add(keys["identity_key"])

    requested_by_category = _requested_definitions(criteres.requested_types)
    explicitly_requested_tokens = {
        alias
        for groups in requested_by_category.values()
        for grp in groups
        for alias in grp
    }
    excluded_type_aliases = [
        grp for groups in _requested_definitions(criteres.excluded_types).values() for grp in groups
    ]
    raw_excluded_terms = [_normalize_text(t) for t in (criteres.excluded_types or []) if _normalize_text(t)]
    norm_season = normalize_shopper_season(criteres.season)
    season_hard_bad = _SEASON_RULES.get(norm_season, (set(), set(), set()))[0] if norm_season else set()

    filtered: List[ArticleCatalogue] = []

    for art in articles:
        if not art.enStock or not art.prix or art.prix <= 0:
            continue

        # 1. Validation stricte de l'URL produit (aucun lien vide, local, inventé ou page catégorie)
        url_ok, reason = is_valid_product_url(art.lienAchat, allowed_domains=allowed_domains, require_https=True)
        if not url_ok:
            logger.debug(f"[SEARCH] Article id={art.id} rejeté (URL invalide: {reason}) : {art.lienAchat}")
            continue

        norm_url = normalize_product_url(art.lienAchat)
        if verified_url_set is not None and norm_url not in verified_url_set:
            continue

        # 2. Exclusion session courante (par ID, URL normalisée ou identité produit)
        if art.id in excluded_id_set:
            continue
        if norm_url and norm_url in excluded_url_set:
            continue
        if excluded_identity_set:
            art_keys = build_product_dedup_keys(
                product_id=art.id,
                name=art.nom,
                vendor=art.vendeur,
                color=art.couleur.nom if art.couleur else "",
                url=art.lienAchat,
            )
            if art_keys["identity_key"] and art_keys["identity_key"] in excluded_identity_set:
                continue

        # 3. Budget individuel maximal (aucune pièce seule ne dépasse le budget total)
        if criteres.budget and criteres.budget > 0 and art.prix > criteres.budget:
            continue

        tv = art.type_vetement
        if not tv:
            continue

        cat_key = _article_category_key(art)
        art_nom_norm = _normalize_text(art.nom or "")
        tv_nom_norm = _normalize_text(tv.nom or "")
        searchable = f"{art_nom_norm} {tv_nom_norm}".strip()

        # 4. Exclusions explicites de types (alias + termes directs)
        if excluded_type_aliases and _matches_requested_type(art, excluded_type_aliases):
            continue
        if any(re.search(rf"(?<!\w){re.escape(term)}(?!\w)", searchable) for term in raw_excluded_terms):
            continue

        # 5. Couleurs évitées (correspondance canonique exacte)
        if art.couleur and any(_colors_match_exact(art.couleur.nom, blocked) for blocked in (criteres.avoided_colors or [])):
            continue

        # 6. Filtrage strict du genre (correction GenreCible.MIXTE)
        source_name = (art.vendeur or "").lower()
        if user_gender_upper == "FEMME" and "homme" in source_name:
            continue
        if user_gender_upper == "HOMME" and "femme" in source_name:
            continue

        if user_gender_upper == "HOMME":
            if tv.genreCible == GenreCible.FEMME:
                continue
            if cat_key == "robes" or tv_nom_norm in {"robe", "jupe", "bottes"}:
                continue
            if any(re.search(rf"(?<!\w){w}(?!\w)", art_nom_norm) for w in ("femme", "women", "woman", "fille", "girl")):
                continue
        elif user_gender_upper == "FEMME":
            if tv.genreCible == GenreCible.HOMME:
                continue
            if any(re.search(rf"(?<!\w){w}(?!\w)", art_nom_norm) for w in ("homme", "men", "man")):
                continue

        # 7. Exclusion saisonnière forte (ex: doudoune/manteau en été, short/débardeur en hiver)
        # Sauf si l'utilisateur a explicitement demandé ce type précis !
        if season_hard_bad:
            hits_hard_bad = [
                kw for kw in season_hard_bad
                if re.search(rf"(?<!\w){re.escape(kw)}(?!\w)", searchable)
            ]
            if hits_hard_bad and not any(kw in explicitly_requested_tokens for kw in hits_hard_bad):
                continue

        # 8. Filtre strict des pièces souhaitées sur leur catégorie propre
        category_requests = requested_by_category.get(cat_key)
        if category_requests and not _matches_requested_type(art, category_requests):
            continue

        filtered.append(art)

    # Tri par score multi-critères décroissant (puis prix croissant en cas d'égalité)
    scored_pairs = [(compute_article_score(a, criteres), a) for a in filtered]
    scored_pairs.sort(key=lambda pair: (pair[0], -(pair[1].prix or 0.0)), reverse=True)

    # 9. Déduplication stricte (ID + URL normalisée + identité vendeur/nom/couleur)
    seen_ids: Set[str] = set()
    seen_urls: Set[str] = set()
    seen_identities: Set[str] = set()
    deduped: List[ArticleCatalogue] = []

    for _, art in scored_pairs:
        keys = build_product_dedup_keys(
            product_id=art.id,
            name=art.nom,
            vendor=art.vendeur,
            color=art.couleur.nom if art.couleur else "",
            url=art.lienAchat,
        )
        if (
            (keys["id_key"] and keys["id_key"] in seen_ids)
            or (keys["url_key"] and keys["url_key"] in seen_urls)
            or (keys["identity_key"] and keys["identity_key"] in seen_identities)
        ):
            continue
        if keys["id_key"]:
            seen_ids.add(keys["id_key"])
        if keys["url_key"]:
            seen_urls.add(keys["url_key"])
        if keys["identity_key"]:
            seen_identities.add(keys["identity_key"])
        deduped.append(art)

    # 10. Regroupement par catégorie avec diversité vendeur maîtrisée
    grouped: Dict[str, List[ArticleCatalogue]] = {
        "hauts": [],
        "bas": [],
        "chaussures": [],
        "vestes": [],
        "robes": [],
        "accessoires": [],
    }
    vendor_count_per_cat: Dict[str, Dict[str, int]] = {k: {} for k in grouped}
    distinct_vendors = max(1, len({(item.vendeur or "inconnu").lower() for item in deduped}))
    max_same_vendor_per_cat = max(6, min(12, 12 // distinct_vendors))

    for art in deduped:
        cat_key = _article_category_key(art)
        if cat_key == "robes" and user_gender_upper == "HOMME":
            continue
        vendeur = (art.vendeur or "inconnu").lower()
        vc = vendor_count_per_cat[cat_key]
        if vc.get(vendeur, 0) < max_same_vendor_per_cat:
            grouped[cat_key].append(art)
            vc[vendeur] = vc.get(vendeur, 0) + 1

    for cat, items in grouped.items():
        if items:
            logger.info(
                f"[SEARCH] {cat}: {len(items)} articles uniques | "
                f"vendeurs={sorted({a.vendeur for a in items})}"
            )

    return grouped


def resolve_canonical_requested_type(raw_type: Optional[str]) -> Optional[str]:
    """Résout un type de vêtement saisi ou sélectionné en clé canonique REQUESTED_TYPE_DEFINITIONS."""
    norm = _normalize_text(raw_type or "")
    if not norm:
        return None
    if norm in REQUESTED_TYPE_DEFINITIONS:
        return norm
    # Trier par longueur d'alias décroissante pour éviter les collisions
    candidates: List[Tuple[int, str]] = []
    for canonical, (_, aliases) in REQUESTED_TYPE_DEFINITIONS.items():
        for alias in aliases:
            na = _normalize_text(alias)
            if na and (norm == na or re.search(rf"(?<!\w){re.escape(na)}(?!\w)", norm)):
                candidates.append((len(na), canonical))
    if candidates:
        candidates.sort(key=lambda x: x[0], reverse=True)
        return candidates[0][1]
    return norm


def _matches_single_requested_type(item: ArticleCatalogue, target_type: str) -> bool:
    """
    Vérifie strictement qu'un article correspond au type unique demandé par l'utilisateur.
    Évite les faux positifs inter-catégories (ex: 'Veste en Jean' ne correspond PAS à 'jean',
    'Pull&Bear' ne correspond PAS à 'pull', 'T-Shirt' ne correspond PAS à 'pull').
    """
    canonical_target = resolve_canonical_requested_type(target_type)
    if not canonical_target:
        return True

    tv_nom_norm = _normalize_text(item.type_vetement.nom if item.type_vetement else "")
    art_nom_norm = _normalize_text(item.nom or "")
    item_cat = _article_category_key(item)

    if canonical_target in REQUESTED_TYPE_DEFINITIONS:
        expected_cat, aliases = REQUESTED_TYPE_DEFINITIONS[canonical_target]
        # Protection anti-collision inter-catégories ("Veste en Jean" -> vestes, jamais bas/jean)
        if item_cat != expected_cat:
            # Cas particulier : un jogging/chino/cargo/jean appartient à "bas"
            return False

        # 1. Correspondance directe sur le type_vetement normalisé en base
        if tv_nom_norm == canonical_target:
            return True

        # 2. Correspondance exacte sur les alias de ce type précis (titre ou type DB)
        searchable = f"{art_nom_norm} {tv_nom_norm}".strip()
        norm_aliases = tuple(_normalize_text(a) for a in aliases if _normalize_text(a))
        if any(re.search(rf"(?<!\w){re.escape(a)}(?!\w)", searchable) for a in norm_aliases):
            # Pour "pantalon" pur : accepter pantalon/chino/cargo/jogging mais pas un pur "jean"
            # sauf si le titre mentionne explicitement "pantalon"
            if canonical_target == "pantalon" and tv_nom_norm == "jean" and "pantalon" not in art_nom_norm:
                return False
            return True
        return False

    # Type personnalisé non listé : correspondance exacte mot entier sur type DB ou titre
    searchable = f"{art_nom_norm} {tv_nom_norm}".strip()
    return bool(re.search(rf"(?<!\w){re.escape(canonical_target)}(?!\w)", searchable))


def search_individual_articles(
    articles: List[ArticleCatalogue],
    requested_type: Optional[str],
    criteres: ShopperCriteria,
    user_gender: Optional[str] = None,
    excluded_product_ids: Optional[List[int]] = None,
    excluded_urls: Optional[List[str]] = None,
    allowed_domains: Optional[Set[str]] = None,
    verified_product_urls: Optional[List[str]] = None,
    max_results: int = 12,
    strict_style: bool = False,
) -> List[Tuple[ArticleCatalogue, int, str]]:
    """
    Moteur de sélection d'articles individuels du même type (AI Shopper).
    Ne compose JAMAIS de tenue multi-pièces : retourne une liste dédupliquée
    d'articles du type demandé respectant strictement :
    - genre du compte (HOMME ou FEMME, + articles MIXTE compatibles)
    - type de vêtement demandé
    - budget maximum strict (prix <= budget)
    - style sélectionné depuis la BDD (filtrage des styles incompatibles + priorisation)
    - URL produit valide & vérifiée
    - déduplication stricte (ID, URL normalisée, identité produit + exclusions session)
    """
    user_gender_upper = (user_gender or "HOMME").upper()
    excluded_id_set = set(excluded_product_ids or [])
    excluded_url_set = {normalize_product_url(u) for u in (excluded_urls or []) if u}
    verified_url_set = (
        {normalize_product_url(u) for u in verified_product_urls if u}
        if verified_product_urls is not None
        else None
    )

    # Propager exclusions session aux doublons d'identité
    excluded_identity_set: Set[str] = set()
    if excluded_id_set or excluded_url_set:
        for art in articles:
            norm_url = normalize_product_url(art.lienAchat)
            if art.id in excluded_id_set or (norm_url and norm_url in excluded_url_set):
                keys = build_product_dedup_keys(
                    product_id=art.id,
                    name=art.nom,
                    vendor=art.vendeur,
                    color=art.couleur.nom if art.couleur else "",
                    url=art.lienAchat,
                )
                if keys["url_key"]:
                    excluded_url_set.add(keys["url_key"])
                if keys["identity_key"]:
                    excluded_identity_set.add(keys["identity_key"])

    raw_style = (criteres.style or "").strip()
    has_explicit_style = bool(raw_style and raw_style.lower() not in ("tous", "all", "tous les styles"))
    norm_style = normalize_shopper_style(raw_style).lower() if has_explicit_style else ""
    accepted_styles = _STYLE_DB_EQUIVALENTS.get(norm_style, {norm_style}) if norm_style else set()
    clashing_styles = _STYLE_CLASHING_DB.get(norm_style, set()) if norm_style else set()

    budget_max = criteres.budget if (criteres.budget and criteres.budget > 0) else None
    canonical_type = resolve_canonical_requested_type(requested_type) if requested_type else None

    eligible: List[ArticleCatalogue] = []
    for art in articles:
        if not art.enStock or not art.prix or art.prix <= 0:
            continue

        # 1. URL produit strictement valide et vérifiée
        url_ok, _ = is_valid_product_url(art.lienAchat, allowed_domains=allowed_domains, require_https=True)
        if not url_ok:
            continue
        norm_url = normalize_product_url(art.lienAchat)
        if verified_url_set is not None and norm_url not in verified_url_set:
            continue

        # 2. Exclusions de session
        if art.id in excluded_id_set or (norm_url and norm_url in excluded_url_set):
            continue
        if excluded_identity_set:
            ak = build_product_dedup_keys(
                product_id=art.id,
                name=art.nom,
                vendor=art.vendeur,
                color=art.couleur.nom if art.couleur else "",
                url=art.lienAchat,
            )
            if ak["identity_key"] and ak["identity_key"] in excluded_identity_set:
                continue

        # 3. Budget maximum strict
        if budget_max is not None and float(art.prix) > float(budget_max):
            continue

        tv = art.type_vetement
        if not tv:
            continue

        # 4. Filtrage strict du genre (compte connecté + MIXTE)
        source_name = (art.vendeur or "").lower()
        art_nom_norm = _normalize_text(art.nom or "")
        tv_nom_norm = _normalize_text(tv.nom or "")
        cat_key = _article_category_key(art)

        if user_gender_upper == "FEMME":
            if "homme" in source_name or tv.genreCible == GenreCible.HOMME:
                continue
            if any(re.search(rf"(?<!\w){w}(?!\w)", art_nom_norm) for w in ("homme", "men", "man")):
                continue
        else:  # HOMME
            if "femme" in source_name or tv.genreCible == GenreCible.FEMME:
                continue
            if cat_key == "robes" or tv_nom_norm in {"robe", "jupe", "bottes"}:
                continue
            if any(re.search(rf"(?<!\w){w}(?!\w)", art_nom_norm) for w in ("femme", "women", "woman", "fille", "girl")):
                continue

        # 5. Filtrage STRICT sur le type de vêtement demandé
        if canonical_type and not _matches_single_requested_type(art, canonical_type):
            continue

        # 6. Couleurs évitées
        if art.couleur and any(_colors_match_exact(art.couleur.nom, blocked) for blocked in (criteres.avoided_colors or [])):
            continue

        # 7. Styles incompatibles exclus (ex: Sportswear exclu si Chic demandé)
        item_style_lower = (art.style.libelle or "").strip().lower() if art.style else ""
        if norm_style and item_style_lower:
            if item_style_lower in clashing_styles:
                continue
            if strict_style and item_style_lower not in accepted_styles:
                continue

        eligible.append(art)

    # Scoring & classement (style exact BDD > style compatible > couleurs souhaitées > mots-clés > budget)
    ranked: List[Tuple[float, int, ArticleCatalogue, str]] = []
    for art in eligible:
        raw_score = float(compute_article_score(art, criteres))
        item_style_label = (art.style.libelle or "").strip() if art.style else ""
        item_style_lower = item_style_label.lower()

        style_match_label = ""
        if norm_style and item_style_lower:
            if item_style_lower == norm_style:
                raw_score += 55.0
                style_match_label = f"Style {item_style_label}"
            elif item_style_lower in accepted_styles:
                raw_score += 20.0
                style_match_label = f"Style compatible ({item_style_label})"
            else:
                raw_score -= 10.0
                style_match_label = f"Style {item_style_label}"
        elif item_style_label:
            style_match_label = f"Style {item_style_label}"

        # Score d'affichage 55..99
        display_score = max(55, min(99, int(round(62 + raw_score * 0.22))))

        parts = [art.type_vetement.nom if art.type_vetement else (requested_type or "Article")]
        if style_match_label:
            parts.append(style_match_label)
        if budget_max is not None:
            savings = max(0.0, float(budget_max) - float(art.prix))
            parts.append(f"Dans votre budget ({art.prix:.2f} / {budget_max:.0f} TND, −{savings:.0f} TND)")
        else:
            parts.append(f"{art.prix:.2f} TND")
        explanation = " · ".join(parts)

        ranked.append((raw_score, display_score, art, explanation))

    ranked.sort(key=lambda row: (row[0], -float(row[2].prix or 0.0)), reverse=True)

    # 8. Déduplication stricte (ID, URL normalisée, identité produit)
    seen_ids: Set[str] = set()
    seen_urls: Set[str] = set()
    seen_identities: Set[str] = set()
    results: List[Tuple[ArticleCatalogue, int, str]] = []

    for _, display_score, art, explanation in ranked:
        keys = build_product_dedup_keys(
            product_id=art.id,
            name=art.nom,
            vendor=art.vendeur,
            color=art.couleur.nom if art.couleur else "",
            url=art.lienAchat,
        )
        if (
            (keys["id_key"] and keys["id_key"] in seen_ids)
            or (keys["url_key"] and keys["url_key"] in seen_urls)
            or (keys["identity_key"] and keys["identity_key"] in seen_identities)
        ):
            continue
        if keys["id_key"]:
            seen_ids.add(keys["id_key"])
        if keys["url_key"]:
            seen_urls.add(keys["url_key"])
        if keys["identity_key"]:
            seen_identities.add(keys["identity_key"])

        results.append((art, display_score, explanation))
        if len(results) >= max_results:
            break

    return results


class ProductSearchService:
    """
    Recherche et filtre les articles réels vérifiés du catalogue correspondant aux critères.
    """

    @staticmethod
    def search_products_by_criteria(
        db: Session,
        criteres: ShopperCriteria,
        user_gender: Optional[str] = None,
        excluded_product_ids: Optional[List[int]] = None,
        verified_product_urls: Optional[List[str]] = None,
        excluded_urls: Optional[List[str]] = None,
        allowed_domains: Optional[Set[str]] = None,
    ) -> Dict[str, List[ArticleCatalogue]]:
        if not verified_product_urls:
            logger.warning("[SEARCH] Aucune URL vérifiée disponible pour la recherche.")
            return {
                "hauts": [],
                "bas": [],
                "chaussures": [],
                "vestes": [],
                "robes": [],
                "accessoires": [],
            }

        query = db.query(ArticleCatalogue).filter(
            ArticleCatalogue.enStock == True,
            ArticleCatalogue.prix > 0,
            ArticleCatalogue.dateDerniereSynchro >= datetime.utcnow() - timedelta(hours=24),
            ArticleCatalogue.lienAchat.like("https://%"),
            ArticleCatalogue.lienAchat.in_(verified_product_urls),
        )
        if excluded_product_ids:
            query = query.filter(~ArticleCatalogue.id.in_(excluded_product_ids))
        if criteres.budget and criteres.budget > 0:
            query = query.filter(ArticleCatalogue.prix <= criteres.budget)

        articles = query.all()
        logger.info(f"[SEARCH] {len(articles)} articles vérifiés chargés depuis la base.")

        return filter_and_group_articles(
            articles=articles,
            criteres=criteres,
            user_gender=user_gender,
            excluded_product_ids=excluded_product_ids,
            excluded_urls=excluded_urls,
            allowed_domains=allowed_domains,
            verified_product_urls=verified_product_urls,
        )

    @staticmethod
    def search_articles_for_type(
        db: Session,
        requested_type: Optional[str],
        criteres: ShopperCriteria,
        user_gender: Optional[str] = None,
        excluded_product_ids: Optional[List[int]] = None,
        verified_product_urls: Optional[List[str]] = None,
        excluded_urls: Optional[List[str]] = None,
        allowed_domains: Optional[Set[str]] = None,
        max_results: int = 12,
    ) -> List[Tuple[ArticleCatalogue, int, str]]:
        if not verified_product_urls:
            logger.warning("[SEARCH] Aucune URL vérifiée disponible pour la recherche d'articles.")
            return []

        query = db.query(ArticleCatalogue).filter(
            ArticleCatalogue.enStock == True,
            ArticleCatalogue.prix > 0,
            ArticleCatalogue.lienAchat.like("https://%"),
            ArticleCatalogue.lienAchat.in_(verified_product_urls),
        )
        if excluded_product_ids:
            query = query.filter(~ArticleCatalogue.id.in_(excluded_product_ids))
        if criteres.budget and criteres.budget > 0:
            query = query.filter(ArticleCatalogue.prix <= criteres.budget)

        articles = query.all()
        logger.info(
            f"[SEARCH-SINGLE] {len(articles)} articles candidats chargés | "
            f"type='{requested_type}' genre={user_gender} style='{criteres.style}' budget={criteres.budget}"
        )

        return search_individual_articles(
            articles=articles,
            requested_type=requested_type,
            criteres=criteres,
            user_gender=user_gender,
            excluded_product_ids=excluded_product_ids,
            excluded_urls=excluded_urls,
            allowed_domains=allowed_domains,
            verified_product_urls=verified_product_urls,
            max_results=max_results,
        )
