import logging
import re
from typing import List, Dict, Optional, Tuple
from sqlalchemy.orm import Session
from app.models.shopping import ArticleCatalogue
from app.models.referentials import TypeVetement, Categorie, Couleur, StyleVestimentaire
from app.models.enums import GenreCible
from app.schemas.shopper import ShopperCriteria

logger = logging.getLogger(__name__)

class ProductSearchService:
    """
    Recherche et filtre les articles réels du catalogue correspondant aux critères extraits par le LLM.
    - Score de pertinence multi-critères amélioré
    - Pas de filtre budget trop restrictif par pièce individuelle
    - Diversité de vendeurs garantie
    - Utilisation des search_queries pour enrichir le scoring
    """

    @staticmethod
    def search_products_by_criteria(
        db: Session,
        criteres: ShopperCriteria,
        user_gender: Optional[str] = None
    ) -> Dict[str, List[ArticleCatalogue]]:
        """
        Recherche et organise les articles réels par catégorie.
        """
        query = db.query(ArticleCatalogue).filter(ArticleCatalogue.enStock == True)

        # Filtre budget : NE PAS appliquer 0.85 sur chaque pièce individuelle.
        # Le budget sera vérifié globalement lors de la composition de la tenue.
        # On applique juste un filtre souple : aucune pièce ne doit dépasser le budget total seul.
        if criteres.budget and criteres.budget > 0:
            # Une pièce individuelle ne peut pas coûter plus que le budget total (pas de 0.85)
            query = query.filter(ArticleCatalogue.prix <= criteres.budget)

        articles = query.all()
        logger.info(f"[SEARCH] {len(articles)} articles en base avant filtrage genre")

        # Filtrage genre
        filtered = []
        user_gender_upper = (user_gender or "HOMME").upper()

        for art in articles:
            tv = art.type_vetement
            if not tv:
                continue
            cat_nom = tv.categorie.nom.lower() if tv.categorie else ""
            type_nom = tv.nom.lower()

            art_nom_lower = (art.nom or "").lower()

            if user_gender_upper == "HOMME":
                # Exclure strictement les pièces féminines
                if tv.genreCible == GenreCible.FEMME:
                    continue
                if cat_nom in ["robe"] or type_nom in ["robe", "jupe", "bottes"]:
                    continue
                # Exclure les articles avec "femme" ou "women" dans le nom
                if any(w in art_nom_lower for w in ["femme", "women", "woman", "fille", "girl"]):
                    continue
            elif user_gender_upper == "FEMME":
                if tv.genreCible == GenreCible.HOMME:
                    continue
                # Exclure les articles avec "homme" ou "men" dans le nom (pas unisexe)
                if any(w in art_nom_lower for w in ["homme", " men ", "man "]) and tv.genreCible != GenreCible.UNISEXE:
                    continue

            filtered.append(art)

        logger.info(f"[SEARCH] {len(filtered)} articles après filtrage genre {user_gender_upper}")

        # Extraire les mots-clés des search_queries pour enrichir le scoring
        query_keywords = set()
        for sq in (criteres.search_queries or []):
            for word in re.split(r"[\s\-_]+", sq.lower()):
                if len(word) > 2:
                    query_keywords.add(word)

        # Score de pertinence multi-critères amélioré
        def relevance_score(item: ArticleCatalogue) -> Tuple[int, int]:
            score = 0
            vendor_diversity = 0  # utilisé pour décompte vendeurs

            item_nom_lower = (item.nom or "").lower()
            item_desc_lower = ""  # description non disponible dans le modèle

            # 1. Correspondance couleur (+60)
            if item.couleur:
                for c in criteres.colors:
                    if c.lower() in item.couleur.nom.lower() or item.couleur.nom.lower() in c.lower():
                        score += 60
                        break
                # Couleur dans le nom du produit (+15)
                for c in criteres.colors:
                    if c.lower() in item_nom_lower:
                        score += 15
                        break

            # 2. Correspondance type/catégorie (+50)
            if item.type_vetement:
                for t in criteres.types_vetement:
                    if t.lower() in item.type_vetement.nom.lower() or item.type_vetement.nom.lower() in t.lower():
                        score += 50
                        break
                # Catégorie demandée présente (+20)
                if item.type_vetement.categorie:
                    for cat in criteres.categories:
                        if cat.lower() in item.type_vetement.categorie.nom.lower():
                            score += 20
                            break

            # 3. Correspondance style (+30)
            if item.style and criteres.style:
                if criteres.style.lower() in (item.style.libelle or "").lower():
                    score += 30
                # Style dans le nom
                if criteres.style.lower() in item_nom_lower:
                    score += 10

            # 4. Mots-clés des search_queries dans le nom (+jusqu'à 40)
            if query_keywords:
                matched_keywords = sum(1 for kw in query_keywords if kw in item_nom_lower)
                score += min(40, matched_keywords * 8)

            # 5. Pénalité si prix = 0 (données incomplètes)
            if not item.prix or item.prix <= 0:
                score -= 100

            return score, 0

        # Trier par score
        filtered.sort(key=lambda a: relevance_score(a)[0], reverse=True)

        # Regrouper par catégorie
        grouped: Dict[str, List[ArticleCatalogue]] = {
            "hauts": [],
            "bas": [],
            "chaussures": [],
            "vestes": [],
            "robes": [],
            "accessoires": []
        }

        # Compteur de vendeurs par catégorie pour limiter la sur-représentation
        vendor_count_per_cat: Dict[str, Dict[str, int]] = {k: {} for k in grouped}
        MAX_SAME_VENDOR_PER_CAT = 2

        # Mots-clés de force majeure pour catégoriser par nom (surpasse la catégorie DB si mal initialisée)
        _BAS_KEYWORDS  = {"jean", "jeans", "denim", "cargo", "pantalon", "jogger", "jogging", "short", "bermuda", "chino", "jupe"}
        _HAUT_KEYWORDS = {"t-shirt", "tshirt", "chemise", "polo", "pull", "sweat", "hoodie", "sweatshirt", "blouse", "top", "débardeur"}
        _SHOE_KEYWORDS = {"basket", "baskets", "sneaker", "sneakers", "botte", "bottes", "chaussure", "chaussures", "mocassin", "derby"}
        _VEST_KEYWORDS = {"veste", "blazer", "manteau", "blouson", "bomber", "doudoune", "parka"}
        _ROBE_KEYWORDS = {"robe", "dress"}
        _ACC_KEYWORDS  = {"casquette", "chapeau", "bonnet", "sacoche", "sac ", "ceinture", "montre", "écharpe"}

        def _force_category(art_name: str, tv_nom: str, cat_nom_db: str) -> str:
            n = art_name.lower() + " " + tv_nom.lower()
            if any(k in n for k in _BAS_KEYWORDS):
                return "bas"
            if any(k in n for k in _SHOE_KEYWORDS):
                return "chaussures"
            if any(k in n for k in _VEST_KEYWORDS):
                return "vestes"
            if any(k in n for k in _ROBE_KEYWORDS):
                return "robes"
            if any(k in n for k in _HAUT_KEYWORDS):
                return "hauts"
            if any(k in n for k in _ACC_KEYWORDS):
                return "accessoires"
            # Fallback DB category
            if "haut" in cat_nom_db:
                return "hauts"
            if "bas" in cat_nom_db:
                return "bas"
            if any(x in cat_nom_db for x in ["chaussure", "basket", "botte"]):
                return "chaussures"
            if any(x in cat_nom_db for x in ["veste", "manteau"]):
                return "vestes"
            if "robe" in cat_nom_db:
                return "robes"
            return "accessoires"

        for art in filtered:
            cat_nom = art.type_vetement.categorie.nom.lower() if (art.type_vetement and art.type_vetement.categorie) else ""
            tv_nom  = art.type_vetement.nom.lower() if art.type_vetement else ""
            vendeur = (art.vendeur or "inconnu").lower()

            cat_key = _force_category(art.nom or "", tv_nom, cat_nom)

            # Exclure robes pour les hommes
            if cat_key == "robes" and user_gender_upper == "HOMME":
                cat_key = "accessoires"

            # Limiter vendeurs par catégorie
            vc = vendor_count_per_cat[cat_key]
            if vc.get(vendeur, 0) < MAX_SAME_VENDOR_PER_CAT:
                grouped[cat_key].append(art)
                vc[vendeur] = vc.get(vendeur, 0) + 1

        # Log de synthèse
        for cat, items in grouped.items():
            if items:
                logger.info(f"[SEARCH] {cat}: {len(items)} articles | "
                            f"vendeurs={list(set(a.vendeur for a in items))}")

        return grouped
