import re
import logging
import unicodedata
from typing import Optional, Any
from sqlalchemy.orm import Session
from app.models.referentials import TypeVetement, Couleur, StyleVestimentaire

logger = logging.getLogger(__name__)

# Noms de marques pouvant contenir des noms de vêtements trompeurs ("Pull&Bear" -> "pull")
_BRAND_NOISE_PATTERNS = (
    re.compile(r"\bpull\s*(?:&|and|et)?\s*bear\b", re.IGNORECASE),
)


def _clean_for_matching(text: str) -> str:
    cleaned = text or ""
    for pat in _BRAND_NOISE_PATTERNS:
        cleaned = pat.sub(" ", cleaned)
    ascii_text = unicodedata.normalize("NFKD", cleaned.lower()).encode("ascii", "ignore").decode("ascii")
    return re.sub(r"[^a-z0-9]+", " ", ascii_text).strip()


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

        cleaned = raw_price.replace("\xa0", " ").strip()
        match = re.search(r"(\d+[\d\s]*(?:[.,]\d+)?)", cleaned)
        if match:
            num_str = match.group(1).replace(" ", "").replace(",", ".")
            try:
                val = float(num_str)
                if val > 1000 and "." not in num_str:
                    val = val / 1000.0
                return round(val, 2)
            except ValueError:
                return 0.0
        return 0.0

    @staticmethod
    def match_type_vetement(title: str, description: str, db: Session) -> Optional[TypeVetement]:
        """
        Associe l'article au TypeVetement adéquat :
        - Priorité au titre produit avant la description (évite les faux positifs marketing)
        - Supprime les noms de marque trompeurs ("Pull&Bear")
        - Teste les pièces composées (ex: "veste en jean" -> Veste, "sur-chemise" -> Chemise/Veste)
          avant les mots génériques ("jean").
        """
        title_clean = _clean_for_matching(title)
        full_clean = _clean_for_matching(f"{title} {description}")
        all_types = db.query(TypeVetement).all()

        # Ordre de priorité strict : pièces composées & chaussures/vestes avant matières ("jean"/"denim")
        type_keywords = [
            ("Veste", ["veste en jean", "veste", "blazer", "blouson", "bomber", "jacket"]),
            ("Manteau", ["manteau", "trench", "doudoune", "parka", "coat"]),
            ("Robe", ["robe", "dress", "combinaison"]),
            ("Baskets", ["basket", "baskets", "sneaker", "sneakers", "tennis"]),
            ("Bottes", ["botte", "bottes", "bottine", "bottines", "boots"]),
            ("Chaussures de ville", ["chaussure de ville", "chaussures de ville", "mocassin", "derby", "derbies", "escarpin", "sandale"]),
            ("Short", ["short", "shorts", "bermuda"]),
            ("Jupe", ["jupe", "skirt"]),
            ("Jean", ["pantalon en denim", "pantalon jean", "pantalon jeans", "jean", "jeans", "denim"]),
            ("Pantalon", ["pantalon", "cargo", "chino", "jogging", "jogger", "trousers"]),
            ("Chemise", ["sur chemise", "surchemise", "chemise", "chemises", "blouse", "chemisier"]),
            ("Sweat", ["sweatshirt", "sweat shirt", "sweat", "hoodie"]),
            ("Pull", ["sous pull", "pull col polo", "pull", "pullover", "tricot", "cardigan", "sweater"]),
            ("Polo", ["polo", "polos"]),
            ("Sac", ["sac a main", "sac a dos", "sac bandouliere", "sac cabas", "sac bourse", "sacoche", "sac", "sacs", "cabas", "pochette", "handbag", "backpack", "bag"]),
            ("Chapeau", ["chapeau", "chapeaux", "casquette", "casquettes", "bonnet", "bonnets", "bob", "fedora", "hat", "cap", "beanie"]),
            ("Ceinture", ["ceinture", "ceintures", "belt"]),
            ("Écharpe", ["echarpe", "echarpes", "foulard", "scarf"]),
            ("Montre", ["montre", "montres", "watch"]),
            ("T-Shirt", ["t shirt", "tshirt", "tee shirt", "debardeur", "top"]),
        ]

        # 1. D'abord sur le titre uniquement (bien plus fiable)
        for text_source in (title_clean, full_clean):
            for std_type_name, keywords in type_keywords:
                if any(re.search(rf"(?<!\w){re.escape(kw)}(?!\w)", text_source) for kw in keywords):
                    matched = next((t for t in all_types if t.nom.lower() == std_type_name.lower()), None)
                    if matched:
                        return matched

        return next((t for t in all_types if t.nom == "T-Shirt"), all_types[0] if all_types else None)

    @staticmethod
    def match_couleur(
        title: str,
        description: str,
        db: Session,
        raw_color: str = "",
    ) -> Optional[Couleur]:
        """
        Associe la couleur au référentiel Couleur de Wearia.
        Priorité :
        1. Couleur brute structurée (`raw_color` issue de JSON-LD ou variante URL)
        2. Titre produit
        3. Description produit
        Expressions multi-mots ('bleu marine', 'marron fonce') testées avant les mots simples.
        """
        all_colors = db.query(Couleur).all()

        # Ordre : multi-mots d'abord pour éviter que "bleu" capture "bleu marine"
        color_aliases = [
            ("Bleu Marine", ["bleu marine", "navy", "marine"]),
            ("Marron Foncé", ["marron fonce", "chocolat"]),
            ("Jaune Clair", ["jaune clair"]),
            ("Noir", ["noir", "noire", "noirs", "noires", "black"]),
            ("Blanc", ["blanc", "blanche", "blancs", "blanches", "white", "ecru", "ivoire"]),
            ("Bleu", ["bleu", "bleue", "bleus", "bleues", "blue", "cyan", "indigo", "ciel", "denim"]),
            ("Gris", ["gris", "grise", "grey", "gray", "anthracite", "chine"]),
            ("Beige", ["beige", "camel", "nude", "taupe", "grege"]),
            ("Sable", ["sable", "sand"]),
            ("Marron", ["marron", "brun", "brune", "brown", "cognac"]),
            ("Vert", ["vert", "verte", "verts", "vertes", "green", "kaki", "khaki", "olive"]),
            ("Rouge", ["rouge", "rouges", "red", "bordeaux", "grenat"]),
            ("Corail", ["corail", "coral", "saumon"]),
            ("Rose", ["rose", "roses", "pink", "fushia", "fuchsia"]),
            ("Jaune", ["jaune", "yellow", "moutarde"]),
            ("Orange", ["orange", "terracotta"]),
            ("Violet", ["violet", "violette", "mauve", "purple", "lilas"]),
        ]

        sources = [
            _clean_for_matching(raw_color),
            _clean_for_matching(title),
            _clean_for_matching(description),
        ]

        for src in sources:
            if not src:
                continue
            for std_name, aliases in color_aliases:
                if any(re.search(rf"(?<!\w){re.escape(alias)}(?!\w)", src) for alias in aliases):
                    matched = next((c for c in all_colors if c.nom.lower() == std_name.lower()), None)
                    if matched:
                        return matched

        return None

    @staticmethod
    def match_style(title: str, description: str, db: Session) -> Optional[StyleVestimentaire]:
        """Associe un StyleVestimentaire (Streetwear, Décontracté, Chic, Classique, Sportswear)."""
        text = _clean_for_matching(f"{title} {description}")
        all_styles = db.query(StyleVestimentaire).all()

        if any(w in text for w in ["streetwear", "street", "cargo", "oversize", "hoodie", "skate", "baggy", "parachute"]):
            return next((s for s in all_styles if s.libelle == "Streetwear"), None)
        if any(w in text for w in ["chic", "elegant", "blazer", "costume", "escarpin", "mocassin", "plis", "soiree", "midi"]):
            return next((s for s in all_styles if s.libelle == "Chic"), None)
        if any(w in text for w in ["sport", "jogging", "jogger", "running", "training", "fitness"]):
            return next((s for s in all_styles if s.libelle == "Sportswear"), None)
        if any(w in text for w in ["classique", "bureau", "polo", "oxford", "chino", "chemise", "derby"]):
            return next((s for s in all_styles if s.libelle == "Classique"), None)

        return next((s for s in all_styles if s.libelle == "Décontracté"), all_styles[0] if all_styles else None)
