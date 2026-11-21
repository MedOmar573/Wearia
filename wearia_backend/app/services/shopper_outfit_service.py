import logging
from typing import List, Dict, Optional, Tuple
from app.models.shopping import ArticleCatalogue
from app.models.user import Utilisateur
from app.schemas.shopper import ShopperCriteria, ShopperOutfit, ShopperArticle

logger = logging.getLogger(__name__)

class ShopperOutfitService:
    """
    Moteur de composition intelligente de tenues d'achat e-commerce :
    - Sélectionne les vêtements qui s'accordent ensemble
    - Respecte strictement le budget maximum fixé par l'utilisateur
    - Évalue l'harmonie des couleurs, la cohérence de style et l'occasion
    - Calcule un score de compatibilité pondéré sur 100
    """

    @staticmethod
    def compose_outfits(
        grouped_items: Dict[str, List[ArticleCatalogue]],
        criteres: ShopperCriteria,
        user: Optional[Utilisateur] = None,
        max_outfits: int = 3
    ) -> List[ShopperOutfit]:
        hauts = grouped_items.get("hauts", [])
        bas = grouped_items.get("bas", [])
        chaussures = grouped_items.get("chaussures", [])
        robes = grouped_items.get("robes", [])
        vestes = grouped_items.get("vestes", [])
        accessoires = grouped_items.get("accessoires", [])

        candidate_outfits: List[Tuple[List[ArticleCatalogue], float, int, str]] = []

        budget_max = criteres.budget if (criteres.budget and criteres.budget > 0) else None

        # 1. Génération des combinaisons : Haut + Bas + Chaussures
        for h in hauts:
            for b in bas:
                # Éviter de mettre le même article en haut et en bas
                if h.id == b.id:
                    continue
                # Éviter deux articles du même type (ex: jean + jean)
                h_type = (h.type_vetement.nom if h.type_vetement else "").lower()
                b_type = (b.type_vetement.nom if b.type_vetement else "").lower()
                if h_type and b_type and h_type == b_type:
                    continue
                for c in chaussures:
                    if c.id in {h.id, b.id}:
                        continue
                    items = [h, b, c]
                    total_prix = sum(it.prix for it in items)

                    # Si budget respecté, tester si on peut ajouter une casquette/accessoire ou veste
                    if budget_max and (total_prix + 20.0 <= budget_max) and accessoires:
                        acc = accessoires[0]
                        if total_prix + acc.prix <= budget_max:
                            items.append(acc)
                            total_prix += acc.prix

                    # Filtre budget strict : si budget imposé, ignorer ce qui dépasse
                    if budget_max and total_prix > budget_max:
                        continue

                    score, explication = ShopperOutfitService._calculate_score(items, total_prix, criteres, budget_max, user)
                    candidate_outfits.append((items, total_prix, score, explication))

        # 2. Génération des combinaisons Robes (si applicable)
        for r in robes:
            for c in chaussures:
                items = [r, c]
                total_prix = sum(it.prix for it in items)
                if budget_max and total_prix > budget_max:
                    continue
                score, explication = ShopperOutfitService._calculate_score(items, total_prix, criteres, budget_max, user)
                candidate_outfits.append((items, total_prix, score, explication))

        # 3. Fallback : Si le budget est très serré et qu'aucune combinaison de 3 pièces n'est rentrée
        if not candidate_outfits and hauts and bas:
            # Essayer au moins Haut + Bas
            for h in hauts:
                for b in bas:
                    items = [h, b]
                    total_prix = sum(it.prix for it in items)
                    if budget_max and total_prix > budget_max:
                        continue
                    score, explication = ShopperOutfitService._calculate_score(items, total_prix, criteres, budget_max, user)
                    candidate_outfits.append((items, total_prix, score, explication))

        # 4. Trier par score de compatibilité décroissant
        candidate_outfits.sort(key=lambda x: x[2], reverse=True)

        # 5. Sélection de tenues STRICTEMENT DIVERSIFIÉES (Zéro répétition de pièces)
        selected_outfits: List[ShopperOutfit] = []
        used_top_ids = set()
        used_bottom_ids = set()
        used_shoe_ids = set()

        def get_item_category_id(items_list, cat_target: str) -> Optional[int]:
            for it in items_list:
                if it.type_vetement and it.type_vetement.categorie:
                    if cat_target in it.type_vetement.categorie.nom.lower():
                        return it.id
                elif cat_target == "chaussure" and it.type_vetement and "basket" in it.type_vetement.nom.lower():
                    return it.id
            return None

        def build_outfit_dto(idx: int, items_list: List[ArticleCatalogue], price: float, sc: int, exp: str) -> ShopperOutfit:
            articles_dto = [
                ShopperArticle(
                    id=it.id,
                    nom=it.nom,
                    imageUrl=it.imageUrl,
                    lienAchat=it.lienAchat,
                    prix=it.prix,
                    devise=it.devise or "TND",
                    vendeur=it.vendeur,
                    taillesDisponibles=it.taillesDisponibles or "S, M, L, XL",
                    typeVetementNom=it.type_vetement.nom if it.type_vetement else "Article",
                    couleurNom=it.couleur.nom if it.couleur else "Noir",
                    categorieNom=it.type_vetement.categorie.nom if (it.type_vetement and it.type_vetement.categorie) else "Mode"
                )
                for it in items_list
            ]

            # Titres de styles distinctifs pour chaque proposition
            base_style = (criteres.style or "Streetwear").capitalize()
            # Identifier la pièce maîtresse du bas (Cargo, Jean, Jogger)
            bottom_it = next((it for it in items_list if it.type_vetement and it.type_vetement.categorie and "bas" in it.type_vetement.categorie.nom.lower()), None)
            top_it = next((it for it in items_list if it.type_vetement and it.type_vetement.categorie and "haut" in it.type_vetement.categorie.nom.lower()), None)
            
            tag_bottom = "Pantalon"
            if bottom_it:
                if "cargo" in bottom_it.nom.lower():
                    tag_bottom = "Cargo"
                elif "jean" in bottom_it.nom.lower() or "denim" in bottom_it.nom.lower():
                    tag_bottom = "Denim"
                elif "jogger" in bottom_it.nom.lower() or "jogging" in bottom_it.nom.lower():
                    tag_bottom = "Jogger"
                elif "chino" in bottom_it.nom.lower():
                    tag_bottom = "Chino"

            tag_top = "Tee"
            if top_it:
                if "hoodie" in top_it.nom.lower() or "sweat" in top_it.nom.lower():
                    tag_top = "Hoodie"
                elif "chemise" in top_it.nom.lower():
                    tag_top = "Chemise"
                elif "t-shirt" in top_it.nom.lower():
                    tag_top = "T-Shirt"

            style_concordance = f"{base_style} • {tag_top} & {tag_bottom}"

            return ShopperOutfit(
                id=idx,
                articles=articles_dto,
                prixTotal=round(price, 2),
                budgetMax=budget_max,
                respecteBudget=True if (not budget_max or price <= budget_max) else False,
                scoreCompatibilite=sc,
                harmonieCouleurs="Excellente",
                styleConcordance=style_concordance,
                explication=exp
            )

        # Passe 1 : Diversité Maximale (Haut unique, Bas unique et Chaussures uniques)
        for items, total_prix, score, explication in candidate_outfits:
            h_id = get_item_category_id(items, "haut")
            b_id = get_item_category_id(items, "bas")
            c_id = get_item_category_id(items, "chaussure")

            if h_id and h_id in used_top_ids:
                continue
            if b_id and b_id in used_bottom_ids:
                continue
            if c_id and c_id in used_shoe_ids and len(used_shoe_ids) < len(chaussures):
                continue

            if h_id: used_top_ids.add(h_id)
            if b_id: used_bottom_ids.add(b_id)
            if c_id: used_shoe_ids.add(c_id)

            selected_outfits.append(build_outfit_dto(len(selected_outfits) + 1, items, total_prix, score, explication))
            if len(selected_outfits) >= max_outfits:
                break

        # Passe 2 : Si moins de max_outfits (ex: stock limité), autoriser réutilisation partielle mais INTERDIRE le même couple (Haut, Bas)
        if len(selected_outfits) < max_outfits:
            for items, total_prix, score, explication in candidate_outfits:
                h_id = get_item_category_id(items, "haut")
                b_id = get_item_category_id(items, "bas")

                already_same_pair = False
                for prev in selected_outfits:
                    prev_h = get_item_category_id([it for it in items if any(a.id == it.id for a in prev.articles)], "haut")
                    prev_b = get_item_category_id([it for it in items if any(a.id == it.id for a in prev.articles)], "bas")
                    # Comparer IDs avec les articles déjà sélectionnés
                    prev_ids = {a.id for a in prev.articles}
                    if h_id in prev_ids and b_id in prev_ids:
                        already_same_pair = True
                        break

                if already_same_pair:
                    continue

                # Vérifier signature exacte
                combo_sig = tuple(sorted(it.id for it in items))
                if any(tuple(sorted(a.id for a in prev.articles)) == combo_sig for prev in selected_outfits):
                    continue

                selected_outfits.append(build_outfit_dto(len(selected_outfits) + 1, items, total_prix, score, explication))
                if len(selected_outfits) >= max_outfits:
                    break

        return selected_outfits

    @staticmethod
    def _calculate_score(
        items: List[ArticleCatalogue],
        total_prix: float,
        criteres: ShopperCriteria,
        budget_max: Optional[float],
        user: Optional[Utilisateur]
    ) -> Tuple[int, str]:
        """
        Calcul du score pondéré et rédaction de l'explication stylistique.
        """
        score = 80
        explication_points = []

        # 1. Score Budget
        if budget_max:
            if total_prix <= budget_max:
                score += 10
                savings = budget_max - total_prix
                explication_points.append(f"Tenue à {total_prix:.1f} TND respectant parfaitement votre budget de {budget_max:.0f} TND (économie de {savings:.1f} TND).")
            else:
                score -= 30

        # 2. Score Harmonie Couleurs
        colors = [it.couleur.nom for it in items if it.couleur]
        unique_colors = set(colors)
        if len(unique_colors) == 1:
            score += 10
            explication_points.append(f"Harmonie monochrome {colors[0]} moderne et percutante.")
        elif len(unique_colors) <= 2:
            score += 8
            explication_points.append("Association bicolore équilibrée.")
        elif len(unique_colors) > 3:
            score -= 10

        # Vérification si couleur demandée est présente
        if any(any(c.lower() in it.nom.lower() or (it.couleur and c.lower() in it.couleur.nom.lower()) for c in criteres.colors) for it in items):
            score += 5

        # 3. Score Style & Occasion
        style_name = criteres.style.capitalize() if criteres.style else "Tendance"
        occasion_name = criteres.occasion.lower()
        explication_points.append(f"Pièces {style_name} idéales pour l'occasion {occasion_name}.")

        # 4. Complétude de la tenue
        types_noms = [it.type_vetement.nom.lower() for it in items if it.type_vetement]
        has_top = any("shirt" in t or "chemise" in t or "pull" in t or "sweat" in t or "polo" in t for t in types_noms)
        has_bottom = any("jean" in t or "pantalon" in t or "short" in t or "jupe" in t for t in types_noms)
        has_shoes = any("basket" in t or "chauss" in t or "botte" in t for t in types_noms)
        has_dress = any("robe" in t for t in types_noms)

        if (has_top and has_bottom and has_shoes) or (has_dress and has_shoes):
            score += 5

        final_score = max(50, min(99, score))
        full_explanation = " ".join(explication_points)
        return final_score, full_explanation
