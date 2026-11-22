import logging
from typing import Dict, List, Optional, Set, Tuple

from app.ai.shopper_llm import (
    normalize_shopper_occasion,
    normalize_shopper_season,
    normalize_shopper_style,
)
from app.models.shopping import ArticleCatalogue
from app.models.user import Utilisateur
from app.schemas.shopper import ShopperArticle, ShopperCriteria, ShopperOutfit
from app.services.product_search_service import (
    _article_category_key,
    _colors_match_exact,
    _requested_definitions,
    compute_article_score,
)
from app.services.shopper_validation import build_product_dedup_keys, is_valid_product_url

logger = logging.getLogger(__name__)

_NEUTRAL_COLORS = {"noir", "blanc", "gris", "beige", "sable", "bleu marine"}

_SEASON_LABELS = {
    "ETE": "été",
    "HIVER": "hiver",
    "AUTOMNE": "automne",
    "PRINTEMPS": "printemps",
}


class ShopperOutfitService:
    """
    Moteur de composition intelligente de tenues d'achat e-commerce :
    - Respecte strictement le budget maximum fixé par l'utilisateur
    - Garantit la présence des pièces explicitement demandées (y compris vestes/manteaux/robes/accessoires)
    - Évalue la cohérence globale (couleurs demandées, harmonie, style, occasion, saison)
    - Applique une déduplication stricte (ID, URL normalisée et identité produit)
    """

    @staticmethod
    def _outfit_has_unique_pieces(items: List[ArticleCatalogue]) -> bool:
        ids: Set[str] = set()
        urls: Set[str] = set()
        identities: Set[str] = set()
        for it in items:
            keys = build_product_dedup_keys(
                product_id=it.id,
                name=it.nom,
                vendor=it.vendeur,
                color=it.couleur.nom if it.couleur else "",
                url=it.lienAchat,
            )
            if (
                (keys["id_key"] and keys["id_key"] in ids)
                or (keys["url_key"] and keys["url_key"] in urls)
                or (keys["identity_key"] and keys["identity_key"] in identities)
            ):
                return False
            if keys["id_key"]:
                ids.add(keys["id_key"])
            if keys["url_key"]:
                urls.add(keys["url_key"])
            if keys["identity_key"]:
                identities.add(keys["identity_key"])
        return True

    @staticmethod
    def _satisfies_requested_categories(
        items: List[ArticleCatalogue],
        requested_categories: Set[str],
    ) -> bool:
        if not requested_categories:
            return True
        present = {_article_category_key(it) for it in items}
        return requested_categories.issubset(present)

    @staticmethod
    def compose_outfits(
        grouped_items: Dict[str, List[ArticleCatalogue]],
        criteres: ShopperCriteria,
        user: Optional[Utilisateur] = None,
        max_outfits: int = 3,
    ) -> List[ShopperOutfit]:
        # Limiter le produit cartésien aux meilleurs articles déjà triés par score
        hauts = grouped_items.get("hauts", [])[:12]
        bas = grouped_items.get("bas", [])[:12]
        chaussures = grouped_items.get("chaussures", [])[:10]
        robes = grouped_items.get("robes", [])[:10]
        vestes = grouped_items.get("vestes", [])[:10]
        accessoires = grouped_items.get("accessoires", [])[:8]

        budget_max = criteres.budget if (criteres.budget and criteres.budget > 0) else None
        requested_map = _requested_definitions(criteres.requested_types)
        requested_cats = set(requested_map.keys())

        wants_robe = "robes" in requested_cats
        wants_veste = "vestes" in requested_cats
        wants_acc = "accessoires" in requested_cats
        allow_separates = not (wants_robe and not (requested_cats & {"hauts", "bas"}))
        allow_robes = (not requested_cats) or wants_robe

        # Si une catégorie explicitement demandée n'a aucun article valide, ne pas
        # fabriquer de fausses tenues qui ignorent la demande.
        cat_pools = {
            "hauts": hauts,
            "bas": bas,
            "chaussures": chaussures,
            "robes": robes,
            "vestes": vestes,
            "accessoires": accessoires,
        }
        for req_cat in requested_cats:
            if not cat_pools.get(req_cat):
                logger.info(
                    f"[OUTFIT] Aucun article disponible pour la catégorie demandée '{req_cat}'."
                )
                return []

        candidate_outfits: List[Tuple[List[ArticleCatalogue], float, float, int, str, str]] = []

        def try_add_candidate(items: List[ArticleCatalogue]):
            if not items:
                return
            if not ShopperOutfitService._outfit_has_unique_pieces(items):
                return
            if not ShopperOutfitService._satisfies_requested_categories(items, requested_cats):
                return
            total_prix = round(sum(float(it.prix) for it in items), 2)
            if budget_max is not None and total_prix > budget_max:
                return
            rank_score, display_score, harmony, explication = ShopperOutfitService._calculate_score(
                items, total_prix, criteres, budget_max, user
            )
            candidate_outfits.append((items, total_prix, rank_score, display_score, harmony, explication))

        # ── 1. Combinaisons avec VESTE / MANTEAU (si demandé) ────────────────
        if wants_veste:
            if allow_separates and hauts and bas and chaussures:
                for v in vestes[:6]:
                    for h in hauts[:6]:
                        for b in bas[:6]:
                            for c in chaussures[:5]:
                                try_add_candidate([h, b, v, c])
            if allow_robes and robes and chaussures:
                for v in vestes[:6]:
                    for r in robes[:6]:
                        for c in chaussures[:5]:
                            try_add_candidate([r, v, c])
            # Fallback 3 pièces (Haut + Bas + Veste) si budget serré pour 4 pièces
            if not candidate_outfits and allow_separates and hauts and bas:
                for v in vestes[:8]:
                    for h in hauts[:8]:
                        for b in bas[:8]:
                            try_add_candidate([h, b, v])
            if not candidate_outfits and allow_robes and robes:
                for v in vestes[:8]:
                    for r in robes[:8]:
                        try_add_candidate([r, v])
            if not candidate_outfits and not (requested_cats - {"vestes"}):
                for v in vestes:
                    if hauts:
                        for h in hauts[:4]:
                            try_add_candidate([h, v])
                    if not candidate_outfits:
                        try_add_candidate([v])

        # ── 2. Combinaisons standard : Haut + Bas + Chaussures ───────────────
        if not wants_veste and allow_separates:
            if hauts and bas and chaussures:
                for h in hauts:
                    for b in bas:
                        for c in chaussures:
                            if wants_acc and accessoires:
                                for a in accessoires[:4]:
                                    try_add_candidate([h, b, c, a])
                            else:
                                try_add_candidate([h, b, c])

        # ── 3. Combinaisons Robe + Chaussures ────────────────────────────────
        if not wants_veste and allow_robes and robes:
            if chaussures:
                for r in robes:
                    for c in chaussures:
                        if wants_acc and accessoires:
                            for a in accessoires[:4]:
                                try_add_candidate([r, c, a])
                        else:
                            try_add_candidate([r, c])

        # ── 4. Fallbacks respectant STRICTEMENT budget & pièces demandées ────
        if not candidate_outfits:
            if allow_separates and hauts and bas and "chaussures" not in requested_cats:
                for h in hauts:
                    for b in bas:
                        if wants_acc and accessoires:
                            for a in accessoires[:4]:
                                try_add_candidate([h, b, a])
                        else:
                            try_add_candidate([h, b])

            if not candidate_outfits and allow_robes and robes and "chaussures" not in requested_cats:
                for r in robes:
                    try_add_candidate([r])

            # Si l'utilisateur n'a demandé qu'une seule catégorie précise (ex: uniquement "baskets" ou "chemise")
            if not candidate_outfits and len(requested_cats) == 1:
                only_cat = next(iter(requested_cats))
                for item in cat_pools.get(only_cat, []):
                    try_add_candidate([item])

        # ── 5. Tri par score brut (non plafonné) décroissant puis prix croissant ──
        candidate_outfits.sort(key=lambda x: (x[2], -x[1]), reverse=True)

        # ── 6. Sélection strictement dédupliquée entre tenues ────────────────
        selected_outfits: List[ShopperOutfit] = []
        used_ids: Set[str] = set()
        used_urls: Set[str] = set()
        used_identities: Set[str] = set()
        seen_combinations: Set[Tuple[str, ...]] = set()

        for items, total_prix, _rank_score, score, harmony, explication in candidate_outfits:
            item_keys = [
                build_product_dedup_keys(
                    product_id=it.id,
                    name=it.nom,
                    vendor=it.vendeur,
                    color=it.couleur.nom if it.couleur else "",
                    url=it.lienAchat,
                )
                for it in items
            ]

            combo_sig = tuple(sorted(k["url_key"] or k["identity_key"] or k["id_key"] for k in item_keys))
            if combo_sig in seen_combinations:
                continue

            # Aucun article ne peut être répété d'une tenue à l'autre (ID, URL ou identité)
            if any(
                (k["id_key"] and k["id_key"] in used_ids)
                or (k["url_key"] and k["url_key"] in used_urls)
                or (k["identity_key"] and k["identity_key"] in used_identities)
                for k in item_keys
            ):
                continue

            outfit_dto = ShopperOutfitService._build_outfit_dto(
                idx=len(selected_outfits) + 1,
                items_list=items,
                price=total_prix,
                score=score,
                harmony=harmony,
                explication=explication,
                criteres=criteres,
                budget_max=budget_max,
            )
            selected_outfits.append(outfit_dto)

            for k in item_keys:
                if k["id_key"]:
                    used_ids.add(k["id_key"])
                if k["url_key"]:
                    used_urls.add(k["url_key"])
                if k["identity_key"]:
                    used_identities.add(k["identity_key"])
            seen_combinations.add(combo_sig)

            if len(selected_outfits) >= max_outfits:
                break

        return selected_outfits

    @staticmethod
    def _build_outfit_dto(
        idx: int,
        items_list: List[ArticleCatalogue],
        price: float,
        score: int,
        harmony: str,
        explication: str,
        criteres: ShopperCriteria,
        budget_max: Optional[float],
    ) -> ShopperOutfit:
        articles_dto = []
        for it in items_list:
            url_ok, _ = is_valid_product_url(it.lienAchat, require_https=True)
            safe_url = it.lienAchat.strip() if (url_ok and it.lienAchat) else None
            articles_dto.append(
                ShopperArticle(
                    id=it.id,
                    nom=it.nom,
                    imageUrl=it.imageUrl or "",
                    lienAchat=safe_url,
                    prix=round(float(it.prix), 2),
                    devise=it.devise or "TND",
                    vendeur=it.vendeur or "Boutique",
                    taillesDisponibles=it.taillesDisponibles or "Non vérifiées",
                    typeVetementNom=it.type_vetement.nom if it.type_vetement else "Article",
                    couleurNom=it.couleur.nom if it.couleur else "Neutre",
                    categorieNom=(
                        it.type_vetement.categorie.nom
                        if (it.type_vetement and it.type_vetement.categorie)
                        else "Mode"
                    ),
                    verifieLe=it.dateDerniereSynchro,
                )
            )

        # Titre cohérent basé sur les vraies pièces de la tenue
        base_style = normalize_shopper_style(criteres.style)
        piece_tags: List[str] = []
        for it in items_list:
            tag = it.type_vetement.nom if it.type_vetement else "Pièce"
            nom_l = (it.nom or "").lower()
            if "cargo" in nom_l:
                tag = "Cargo"
            elif "chino" in nom_l:
                tag = "Chino"
            elif "hoodie" in nom_l:
                tag = "Hoodie"
            elif "blazer" in nom_l:
                tag = "Blazer"
            elif "bomber" in nom_l:
                tag = "Bomber"
            if tag not in piece_tags:
                piece_tags.append(tag)

        pieces_summary = " & ".join(piece_tags[:3]) if piece_tags else "Tenue complète"
        style_concordance = f"{base_style} • {pieces_summary}"

        return ShopperOutfit(
            id=idx,
            articles=articles_dto,
            prixTotal=round(price, 2),
            budgetMax=budget_max,
            respecteBudget=(budget_max is None or price <= budget_max),
            scoreCompatibilite=score,
            harmonieCouleurs=harmony,
            styleConcordance=style_concordance,
            explication=explication,
        )

    @staticmethod
    def _calculate_score(
        items: List[ArticleCatalogue],
        total_prix: float,
        criteres: ShopperCriteria,
        budget_max: Optional[float],
        user: Optional[Utilisateur],
    ) -> Tuple[float, int, str, str]:
        """
        Score explicite intégrant TOUS les critères :
        - Score moyen d'adéquation pièce-par-pièce (style, occasion, saison, types, couleurs)
        - Pénalité de cohérence si une pièce de la tenue est incohérente (ex: short au travail)
        - Respect strict du budget
        - Présence des couleurs souhaitées + harmonie chromatique réelle
        - Complétude de la tenue
        Retourne (rank_score_non_plafonne, display_score_45_99, harmony, explication).
        """
        score = 55.0
        explication_points: List[str] = []

        # 1. Adéquation moyenne et cohérence minimale pièce-par-pièce (style, occasion, saison, couleurs, types)
        item_scores = [compute_article_score(it, criteres) for it in items]
        avg_item_score = sum(item_scores) / max(len(item_scores), 1)
        min_item_score = min(item_scores) if item_scores else 0.0
        score += avg_item_score * 0.20
        if min_item_score < 0:
            # Pénalise fortement une pièce incohérente au lieu de la masquer par la moyenne
            score += min_item_score * 0.50

        # 2. Respect du budget
        if budget_max is not None:
            if total_prix <= budget_max:
                score += 10
                savings = budget_max - total_prix
                explication_points.append(
                    f"Tenue à {total_prix:.1f} TND dans votre budget de {budget_max:.0f} TND "
                    f"(économie de {savings:.1f} TND)."
                )
            else:
                score -= 35

        # 3. Couleurs demandées & harmonie chromatique réelle
        colors = [it.couleur.nom for it in items if it.couleur and it.couleur.nom]
        unique_colors_lower = {c.lower() for c in colors}
        non_neutral_colors = {c for c in unique_colors_lower if c not in _NEUTRAL_COLORS}

        if len(unique_colors_lower) <= 1:
            harmony = "Excellente"
            score += 6
            if colors:
                explication_points.append(f"Harmonie monochrome {colors[0]}.")
        elif len(non_neutral_colors) <= 1 and len(unique_colors_lower) <= 3:
            harmony = "Excellente"
            score += 8
            explication_points.append("Association de couleurs équilibrée avec teintes neutres.")
        elif len(non_neutral_colors) == 2 and len(unique_colors_lower) <= 3:
            harmony = "Harmonieuse"
            score += 4
            explication_points.append("Association bicolore harmonieuse.")
        else:
            harmony = "Contrastée"
            score -= 8

        if criteres.colors:
            color_hits = sum(
                1 for it in items
                if it.couleur and any(_colors_match_exact(it.couleur.nom, tc) for tc in criteres.colors)
            )
            if color_hits >= 2:
                score += 14
                explication_points.append(f"Met en valeur vos couleurs ({', '.join(criteres.colors[:2])}).")
            elif color_hits == 1:
                score += 8
                explication_points.append(f"Intègre votre couleur souhaitée ({', '.join(criteres.colors[:2])}).")
            else:
                score -= 14

        # 4. Explication explicite Style / Occasion / Saison
        style_label = normalize_shopper_style(criteres.style)
        occ_label = normalize_shopper_occasion(criteres.occasion).lower()
        season_norm = normalize_shopper_season(criteres.season)
        season_part = f" pour la saison {_SEASON_LABELS[season_norm]}" if season_norm in _SEASON_LABELS else ""
        explication_points.append(
            f"Sélection {style_label} adaptée à l'occasion {occ_label}{season_part}."
        )

        # 5. Bonus de complétude
        present_cats = {_article_category_key(it) for it in items}
        if {"hauts", "bas", "chaussures"}.issubset(present_cats) or {"robes", "chaussures"}.issubset(present_cats):
            score += 5

        display_score = max(45, min(99, int(round(score))))
        return round(score, 2), display_score, harmony, " ".join(explication_points)
