"""
Référentiel unique et standardisé des types de vêtements et des couleurs Wearia.
Source de vérité partagée entre le pipeline IA (entraînement, inférence, couleur),
le seeding PostgreSQL et le mapping API.
"""

from enum import Enum
from typing import Dict, Optional, Set
import unicodedata


class ClothingType(str, Enum):
    CHEMISE = "Chemise"
    TSHIRT = "T-Shirt"
    POLO = "Polo"
    PULL = "Pull"
    SWEAT = "Sweat"
    JEAN = "Jean"
    PANTALON = "Pantalon"
    SHORT = "Short"
    JUPE = "Jupe"
    ROBE = "Robe"
    VESTE = "Veste"
    MANTEAU = "Manteau"
    BASKETS = "Baskets"
    BOTTES = "Bottes"
    CHAUSSURES_VILLE = "Chaussures de ville"
    SAC = "Sac"
    CHAPEAU = "Chapeau"


class ClothingColor(str, Enum):
    NOIR = "Noir"
    BLANC = "Blanc"
    GRIS = "Gris"
    BLEU_MARINE = "Bleu Marine"
    BLEU = "Bleu"
    BEIGE = "Beige"
    SABLE = "Sable"
    MARRON = "Marron"
    MARRON_FONCE = "Marron Foncé"
    VERT = "Vert"
    ROUGE = "Rouge"
    JAUNE = "Jaune"
    JAUNE_CLAIR = "Jaune Clair"
    CORAIL = "Corail"
    ROSE = "Rose"
    ORANGE = "Orange"
    VIOLET = "Violet"


# Palette hexadécimale canonique alignée avec app/database/seed.py
STANDARD_COLORS: Dict[str, str] = {
    ClothingColor.NOIR.value: "#1F1E1D",
    ClothingColor.BLANC.value: "#FFFFFF",
    ClothingColor.GRIS.value: "#9E9E9E",
    ClothingColor.BLEU_MARINE.value: "#1B2E4B",
    ClothingColor.BLEU.value: "#21759B",
    ClothingColor.BEIGE.value: "#D8C7B5",
    ClothingColor.SABLE.value: "#E6DAC8",
    ClothingColor.MARRON.value: "#6D4C3D",
    ClothingColor.MARRON_FONCE.value: "#423229",
    ClothingColor.VERT.value: "#2E6047",
    ClothingColor.ROUGE.value: "#C63D36",
    ClothingColor.JAUNE.value: "#ECAE28",
    ClothingColor.JAUNE_CLAIR.value: "#F8D548",
    ClothingColor.CORAIL.value: "#D94A3D",
    ClothingColor.ROSE.value: "#F3B6C2",
    ClothingColor.ORANGE.value: "#E56A26",
    ClothingColor.VIOLET.value: "#6C47FF",
}

FEMME_ONLY_TYPES: Set[str] = {
    ClothingType.ROBE.value,
    ClothingType.JUPE.value,
    ClothingType.BOTTES.value,
}

TOP_TYPES: Set[str] = {
    ClothingType.CHEMISE.value,
    ClothingType.TSHIRT.value,
    ClothingType.POLO.value,
    ClothingType.PULL.value,
    ClothingType.SWEAT.value,
}

BOTTOM_TYPES: Set[str] = {
    ClothingType.JEAN.value,
    ClothingType.PANTALON.value,
    ClothingType.SHORT.value,
    ClothingType.JUPE.value,
}

OUTERWEAR_TYPES: Set[str] = {
    ClothingType.VESTE.value,
    ClothingType.MANTEAU.value,
}

SHOE_TYPES: Set[str] = {
    ClothingType.BASKETS.value,
    ClothingType.BOTTES.value,
    ClothingType.CHAUSSURES_VILLE.value,
}

ACCESSORY_TYPES: Set[str] = {
    ClothingType.SAC.value,
    ClothingType.CHAPEAU.value,
}


def _strip_accents_lower(text: str) -> str:
    nfkd = unicodedata.normalize("NFKD", (text or "").strip().lower())
    return "".join(c for c in nfkd if not unicodedata.combining(c))


_TYPE_ALIASES: Dict[str, str] = {
    "chemise": ClothingType.CHEMISE.value,
    "shirt": ClothingType.CHEMISE.value,
    "oxford": ClothingType.CHEMISE.value,
    "t-shirt": ClothingType.TSHIRT.value,
    "tshirt": ClothingType.TSHIRT.value,
    "t shirt": ClothingType.TSHIRT.value,
    "tee": ClothingType.TSHIRT.value,
    "top": ClothingType.TSHIRT.value,
    "polo": ClothingType.POLO.value,
    "pull": ClothingType.PULL.value,
    "pullover": ClothingType.PULL.value,
    "tricot": ClothingType.PULL.value,
    "sweater": ClothingType.PULL.value,
    "maille": ClothingType.PULL.value,
    "sweat": ClothingType.SWEAT.value,
    "sweatshirt": ClothingType.SWEAT.value,
    "hoodie": ClothingType.SWEAT.value,
    "jean": ClothingType.JEAN.value,
    "jeans": ClothingType.JEAN.value,
    "denim": ClothingType.JEAN.value,
    "pantalon": ClothingType.PANTALON.value,
    "trouser": ClothingType.PANTALON.value,
    "trousers": ClothingType.PANTALON.value,
    "pants": ClothingType.PANTALON.value,
    "chino": ClothingType.PANTALON.value,
    "jogging": ClothingType.PANTALON.value,
    "short": ClothingType.SHORT.value,
    "shorts": ClothingType.SHORT.value,
    "bermuda": ClothingType.SHORT.value,
    "jupe": ClothingType.JUPE.value,
    "skirt": ClothingType.JUPE.value,
    "robe": ClothingType.ROBE.value,
    "dress": ClothingType.ROBE.value,
    "veste": ClothingType.VESTE.value,
    "blazer": ClothingType.VESTE.value,
    "bomber": ClothingType.VESTE.value,
    "blouson": ClothingType.VESTE.value,
    "jacket": ClothingType.VESTE.value,
    "manteau": ClothingType.MANTEAU.value,
    "coat": ClothingType.MANTEAU.value,
    "parka": ClothingType.MANTEAU.value,
    "trench": ClothingType.MANTEAU.value,
    "baskets": ClothingType.BASKETS.value,
    "basket": ClothingType.BASKETS.value,
    "sneaker": ClothingType.BASKETS.value,
    "sneakers": ClothingType.BASKETS.value,
    "bottes": ClothingType.BOTTES.value,
    "botte": ClothingType.BOTTES.value,
    "boot": ClothingType.BOTTES.value,
    "boots": ClothingType.BOTTES.value,
    "ankle boot": ClothingType.BOTTES.value,
    "chaussures de ville": ClothingType.CHAUSSURES_VILLE.value,
    "chaussure de ville": ClothingType.CHAUSSURES_VILLE.value,
    "chaussures": ClothingType.CHAUSSURES_VILLE.value,
    "derbies": ClothingType.CHAUSSURES_VILLE.value,
    "derby": ClothingType.CHAUSSURES_VILLE.value,
    "mocassin": ClothingType.CHAUSSURES_VILLE.value,
    "sandale": ClothingType.CHAUSSURES_VILLE.value,
    "sandales": ClothingType.CHAUSSURES_VILLE.value,
    "sac": ClothingType.SAC.value,
    "sacs": ClothingType.SAC.value,
    "sac a main": ClothingType.SAC.value,
    "sac a dos": ClothingType.SAC.value,
    "sac bandouliere": ClothingType.SAC.value,
    "bag": ClothingType.SAC.value,
    "handbag": ClothingType.SAC.value,
    "backpack": ClothingType.SAC.value,
    "tote": ClothingType.SAC.value,
    "cabas": ClothingType.SAC.value,
    "pochette": ClothingType.SAC.value,
    "chapeau": ClothingType.CHAPEAU.value,
    "chapeaux": ClothingType.CHAPEAU.value,
    "casquette": ClothingType.CHAPEAU.value,
    "bonnet": ClothingType.CHAPEAU.value,
    "hat": ClothingType.CHAPEAU.value,
    "cap": ClothingType.CHAPEAU.value,
    "beanie": ClothingType.CHAPEAU.value,
    "bob": ClothingType.CHAPEAU.value,
    "fedora": ClothingType.CHAPEAU.value,
    "beret": ClothingType.CHAPEAU.value,
    "sweat a capuche": ClothingType.SWEAT.value,
    "sweatshirt a capuche": ClothingType.SWEAT.value,
    "veste en jean": ClothingType.VESTE.value,
    "blouson en jean": ClothingType.VESTE.value,
    "doudoune": ClothingType.MANTEAU.value,
}

_COLOR_ALIASES: Dict[str, str] = {
    "noir": ClothingColor.NOIR.value,
    "black": ClothingColor.NOIR.value,
    "blanc": ClothingColor.BLANC.value,
    "blanche": ClothingColor.BLANC.value,
    "white": ClothingColor.BLANC.value,
    "gris": ClothingColor.GRIS.value,
    "grise": ClothingColor.GRIS.value,
    "grey": ClothingColor.GRIS.value,
    "gray": ClothingColor.GRIS.value,
    "bleu marine": ClothingColor.BLEU_MARINE.value,
    "marine": ClothingColor.BLEU_MARINE.value,
    "navy": ClothingColor.BLEU_MARINE.value,
    "bleu": ClothingColor.BLEU.value,
    "bleue": ClothingColor.BLEU.value,
    "bleu clair": ClothingColor.BLEU.value,
    "bleu ciel": ClothingColor.BLEU.value,
    "cyan": ClothingColor.BLEU.value,
    "turquoise": ClothingColor.BLEU.value,
    "blue": ClothingColor.BLEU.value,
    "beige": ClothingColor.BEIGE.value,
    "creme": ClothingColor.BEIGE.value,
    "ecru": ClothingColor.BEIGE.value,
    "sable": ClothingColor.SABLE.value,
    "sand": ClothingColor.SABLE.value,
    "marron": ClothingColor.MARRON.value,
    "brown": ClothingColor.MARRON.value,
    "camel": ClothingColor.MARRON.value,
    "marron fonce": ClothingColor.MARRON_FONCE.value,
    "chocolat": ClothingColor.MARRON_FONCE.value,
    "vert": ClothingColor.VERT.value,
    "verte": ClothingColor.VERT.value,
    "kaki": ClothingColor.VERT.value,
    "olive": ClothingColor.VERT.value,
    "green": ClothingColor.VERT.value,
    "rouge": ClothingColor.ROUGE.value,
    "bordeaux": ClothingColor.ROUGE.value,
    "red": ClothingColor.ROUGE.value,
    "jaune": ClothingColor.JAUNE.value,
    "yellow": ClothingColor.JAUNE.value,
    "moutarde": ClothingColor.JAUNE.value,
    "jaune clair": ClothingColor.JAUNE_CLAIR.value,
    "corail": ClothingColor.CORAIL.value,
    "coral": ClothingColor.CORAIL.value,
    "saumon": ClothingColor.CORAIL.value,
    "rose": ClothingColor.ROSE.value,
    "pink": ClothingColor.ROSE.value,
    "orange": ClothingColor.ORANGE.value,
    "terracotta": ClothingColor.ORANGE.value,
    "violet": ClothingColor.VIOLET.value,
    "violette": ClothingColor.VIOLET.value,
    "mauve": ClothingColor.VIOLET.value,
    "purple": ClothingColor.VIOLET.value,
}


def normalize_clothing_type(raw_label: str, user_genre: Optional[str] = None) -> str:
    """Normalise un label brut en ClothingType canonique (respecte genre HOMME si fourni)."""
    key = _strip_accents_lower(raw_label)
    canonical = _TYPE_ALIASES.get(key)
    if canonical is None:
        for alias in sorted(_TYPE_ALIASES.keys(), key=len, reverse=True):
            if alias in key:
                canonical = _TYPE_ALIASES[alias]
                break
    if canonical is None:
        canonical = ClothingType.TSHIRT.value

    if user_genre and user_genre.upper() == "HOMME" and canonical in FEMME_ONLY_TYPES:
        if canonical == ClothingType.BOTTES.value:
            return ClothingType.CHAUSSURES_VILLE.value
        if canonical == ClothingType.JUPE.value:
            return ClothingType.PANTALON.value
        if canonical == ClothingType.ROBE.value:
            return ClothingType.MANTEAU.value

    return canonical


def normalize_clothing_color(raw_color: str) -> str:
    """Normalise un nom de couleur brut en ClothingColor canonique présent en base."""
    key = _strip_accents_lower(raw_color)
    canonical = _COLOR_ALIASES.get(key)
    if canonical is not None:
        return canonical
    # Correspondance exacte d'abord, puis plus long alias pour éviter "bleu" avant "bleu marine"
    for alias in sorted(_COLOR_ALIASES.keys(), key=len, reverse=True):
        if alias in key:
            return _COLOR_ALIASES[alias]
    return ClothingColor.NOIR.value


def get_color_hex(color_name: str) -> str:
    canonical = normalize_clothing_color(color_name)
    return STANDARD_COLORS.get(canonical, STANDARD_COLORS[ClothingColor.NOIR.value])
