import re
import logging
from typing import Optional, Dict, Any, Tuple
from sqlalchemy.orm import Session
from app.models.referentials import TypeVetement, Couleur, StyleVestimentaire

logger = logging.getLogger(__name__)

class DataNormalizer:
    """
    Normalise les données brutes extraites par le scraping afin de les aligner
    avec les référentiels de Wearia (Types, Couleurs, Styles, Prix TND).
    """

    @staticmethod
    def parse_price(raw_price: Any) -> float:
        """
        Convertit un texte de prix brut en float TND.
        Ex: '129,900 DT' -> 129.9, '89 TND' -> 89.0, '45.00' -> 45.0
        """
        if isinstance(raw_price, (int, float)):
            return round(float(raw_price), 2)
        
        if not raw_price or not isinstance(raw_price, str):
            return 0.0

        # Nettoyage
        cleaned = raw_price.replace("\xa0", " ").strip()
        # Trouver la partie numérique
        match = re.search(r"(\d+[\d\s]*(?:[.,]\d+)?)", cleaned)
        if match:
            num_str = match.group(1).replace(" ", "").replace(",", ".")
            try:
                val = float(num_str)
                # Cas typique en Tunisie : prix affiché en millimes (ex: 89000 pour 89 TND)
                if val > 1000 and "." not in num_str:
                    val = val / 1000.0
                return round(val, 2)
            except ValueError:
                return 0.0
        return 0.0

    @staticmethod
    def match_type_vetement(title: str, description: str, db: Session) -> Optional[TypeVetement]:
        """
        Associe l'article au TypeVetement adéquat parmi les 20 types de référence Wearia.
        """
        text = f"{title} {description}".lower()
        all_types = db.query(TypeVetement).all()

        # Priorité aux correspondances exactes ou spécifiques
        type_keywords = {
            "t-shirt": ["t-shirt", "tshirt", "tee-shirt", "tee shirt", "t shirt"],
            "polo": ["polo"],
            "chemise": ["chemise", "blouse", "chemisier"],
            "pull": ["pull", "tricot", "cardigan"],
            "sweat": ["sweat", "hoodie", "sweatshirt"],
            "jean": ["jean", "denim", "jeans"],
            "pantalon": ["pantalon", "cargo", "chino", "jogging", "jogger"],
            "short": ["short", "bermuda"],
            "jupe": ["jupe", "skirt"],
            "robe": ["robe", "dress", "combinaison"],
            "veste": ["veste", "blazer", "blouson", "bomber", "veste en jean"],
            "manteau": ["manteau", "trench", "doudoune", "parka"],
            "baskets": ["basket", "baskets", "sneaker", "sneakers", "tennis"],
            "bottes": ["botte", "bottes", "bottine", "bottines"],
            "chaussures de ville": ["chaussure", "mocassin", "derbie", "escarpin", "sandale"],
            "ceinture": ["ceinture"],
            "chapeau": ["chapeau", "casquette", "bonnet", "bob"],
            "sac": ["sac", "sacoche", "backpack", "pochette"],
            "écharpe": ["écharpe", "echarpe", "foulard"],
            "montre": ["montre", "watch"]
        }

        for std_type_name, keywords in type_keywords.items():
            if any(re.search(r"\b" + re.escape(kw) + r"\b", text) for kw in keywords):
                matched = next((t for t in all_types if t.nom.lower() == std_type_name.lower()), None)
                if matched:
                    return matched

        # Fallback par défaut : T-Shirt si indéterminé
        return next((t for t in all_types if t.nom == "T-Shirt"), all_types[0] if all_types else None)

    @staticmethod
    def match_couleur(title: str, description: str, db: Session) -> Optional[Couleur]:
        """
        Associe la couleur au référentiel Couleur de Wearia.
        """
        text = f"{title} {description}".lower()
        all_colors = db.query(Couleur).all()

        color_aliases = {
            "Noir": ["noir", "noire", "black", "sombre"],
            "Blanc": ["blanc", "blanche", "white", "ecru", "écru"],
            "Bleu Marine": ["marine", "navy", "bleu marine"],
            "Bleu": ["bleu", "blue", "cyan", "indigo"],
            "Gris": ["gris", "grise", "grey", "gray", "anthracite"],
            "Beige": ["beige", "sable", "camel", "nude"],
            "Marron": ["marron", "brun", "brown", "chocolat"],
            "Vert": ["vert", "verte", "green", "kaki", "olive"],
            "Rouge": ["rouge", "red", "bordeaux"],
            "Jaune": ["jaune", "yellow", "moutarde"],
            "Rose": ["rose", "pink"],
            "Orange": ["orange", "corail", "terracotta"]
        }

        for std_name, aliases in color_aliases.items():
            if any(re.search(r"\b" + re.escape(alias) + r"\b", text) for kw in aliases for alias in [kw]):
                matched = next((c for c in all_colors if c.nom.lower() == std_name.lower()), None)
                if matched:
                    return matched

        # Par défaut : Noir (couleur la plus neutre)
        return next((c for c in all_colors if c.nom == "Noir"), all_colors[0] if all_colors else None)

    @staticmethod
    def match_style(title: str, description: str, db: Session) -> Optional[StyleVestimentaire]:
        """
        Associe un StyleVestimentaire (Streetwear, Décontracté, Chic, etc.).
        """
        text = f"{title} {description}".lower()
        all_styles = db.query(StyleVestimentaire).all()

        if any(w in text for w in ["streetwear", "street", "cargo", "oversize", "hoodie", "skate"]):
            return next((s for s in all_styles if s.libelle == "Streetwear"), None)
        if any(w in text for w in ["chic", "élégant", "blazer", "costume", "chemise oxford"]):
            return next((s for s in all_styles if s.libelle == "Chic"), None)
        if any(w in text for w in ["sport", "jogging", "running", "training"]):
            return next((s for s in all_styles if s.libelle == "Sportswear"), None)
        if any(w in text for w in ["classique", "bureau", "polo"]):
            return next((s for s in all_styles if s.libelle == "Classique"), None)

        return next((s for s in all_styles if s.libelle == "Décontracté"), all_styles[0] if all_styles else None)
