from enum import Enum

class Genre(str, Enum):
    HOMME = "HOMME"
    FEMME = "FEMME"

class GenreCible(str, Enum):
    HOMME = "HOMME"
    FEMME = "FEMME"
    MIXTE = "MIXTE"

class Saison(str, Enum):
    PRINTEMPS = "PRINTEMPS"
    ETE = "ETE"
    AUTOMNE = "AUTOMNE"
    HIVER = "HIVER"
    TOUTE_SAISON = "TOUTE_SAISON"

class StatutVetement(str, Enum):
    DISPONIBLE = "DISPONIBLE"
    SALE = "SALE"
    EN_LAVAGE = "EN_LAVAGE"
    INDISPONIBLE = "INDISPONIBLE"

class Occasion(str, Enum):
    QUOTIDIEN = "QUOTIDIEN"
    UNIVERSITE = "UNIVERSITE"
    TRAVAIL = "TRAVAIL"
    SORTIE = "SORTIE"
    EVENEMENT = "EVENEMENT"
    SPORT = "SPORT"

class Coupe(str, Enum):
    AJUSTEE = "AJUSTEE"
    REGULIERE = "REGULIERE"
    OVERSIZE = "OVERSIZE"

class JourSemaine(str, Enum):
    LUNDI = "LUNDI"
    MARDI = "MARDI"
    MERCREDI = "MERCREDI"
    JEUDI = "JEUDI"
    VENDREDI = "VENDREDI"
    SAMEDI = "SAMEDI"
    DIMANCHE = "DIMANCHE"

class Appreciation(str, Enum):
    AIME = "AIME"
    MOYEN = "MOYEN"
    PAS_POUR_MOI = "PAS_POUR_MOI"

class TypePreference(str, Enum):
    AIME = "AIME"
    EVITE = "EVITE"

