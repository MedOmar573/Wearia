import logging
from sqlalchemy.orm import Session
from app.models.referentials import Categorie, TypeVetement, Couleur, StyleVestimentaire
from app.models.enums import GenreCible
from app.models.shopping import ArticleCatalogue

logger = logging.getLogger(__name__)

def seed_database(db: Session):
    """
    Insère automatiquement les données de référence et le catalogue de démo
    si la base de données est vide.
    """
    # 1. Catégories
    categories_data = [
        "Haut", "Bas", "Robe", "Veste", "Chaussures", "Accessoire"
    ]
    cats_map = {}
    for name in categories_data:
        cat = db.query(Categorie).filter(Categorie.nom == name).first()
        if not cat:
            cat = Categorie(nom=name)
            db.add(cat)
            db.flush()
        cats_map[name] = cat

    # 2. Types de vêtements
    types_data = [
        ("Chemise", "Haut", GenreCible.MIXTE, False),
        ("T-Shirt", "Haut", GenreCible.MIXTE, False),
        ("Polo", "Haut", GenreCible.MIXTE, False),
        ("Pull", "Haut", GenreCible.MIXTE, True),
        ("Sweat", "Haut", GenreCible.MIXTE, True),
        ("Jean", "Bas", GenreCible.MIXTE, False),
        ("Pantalon", "Bas", GenreCible.MIXTE, False),
        ("Short", "Bas", GenreCible.MIXTE, False),
        ("Jupe", "Bas", GenreCible.FEMME, False),
        ("Robe", "Robe", GenreCible.FEMME, False),
        ("Veste", "Veste", GenreCible.MIXTE, True),
        ("Manteau", "Veste", GenreCible.MIXTE, True),
        ("Baskets", "Chaussures", GenreCible.MIXTE, False),
        ("Bottes", "Chaussures", GenreCible.FEMME, False),
        ("Chaussures de ville", "Chaussures", GenreCible.MIXTE, False),
    ]

    types_map = {}
    for nom, cat_name, genre, est_superieure in types_data:
        tv = db.query(TypeVetement).filter(TypeVetement.nom == nom).first()
        if not tv:
            tv = TypeVetement(
                nom=nom,
                categorie_id=cats_map[cat_name].id,
                genreCible=genre,
                estCoucheSuperieure=est_superieure
            )
            db.add(tv)
            db.flush()
        types_map[nom] = tv

    # 3. Couleurs standard
    colors_data = [
        ("Noir", "#1F1E1D"),
        ("Blanc", "#FFFFFF"),
        ("Gris", "#9E9E9E"),
        ("Bleu Marine", "#1B2E4B"),
        ("Bleu", "#21759B"),
        ("Beige", "#D8C7B5"),
        ("Sable", "#E6DAC8"),
        ("Marron", "#6D4C3D"),
        ("Vert", "#2E6047"),
        ("Rouge", "#C63D36"),
        ("Marron Foncé", "#423229"),
        ("Jaune", "#ECAE28"),
        ("Corail", "#D94A3D"),
        ("Rose", "#F3B6C2"),
        ("Orange", "#E56A26"),
        ("Jaune Clair", "#F8D548")
    ]
    colors_map = {}
    for nom, hex_code in colors_data:
        col = db.query(Couleur).filter(Couleur.nom == nom).first()
        if not col:
            col = Couleur(nom=nom, codeHex=hex_code)
            db.add(col)
            db.flush()
        colors_map[nom] = col

    # 4. Styles vestimentaires
    styles_data = [
        "Décontracté", "Classique", "Sportswear", "Streetwear", "Chic", "Bohème"
    ]
    for lib in styles_data:
        st = db.query(StyleVestimentaire).filter(StyleVestimentaire.libelle == lib).first()
        if not st:
            st = StyleVestimentaire(libelle=lib)
            db.add(st)
            db.flush()

    # 5. Articles du catalogue de démonstration (Personal Shopper)
    if db.query(ArticleCatalogue).count() == 0:
        demo_articles = [
            ArticleCatalogue(
                nom="Veste Imperméable Coupe-vent",
                imageUrl="https://images.unsplash.com/photo-1544441893-675973e31985?w=500",
                lienAchat="https://example.com/veste-impermeable",
                prix=129.99,
                vendeur="Wearia Store",
                taillesDisponibles="M, L, XL",
                type_vetement_id=types_map["Veste"].id,
                couleur_id=colors_map["Bleu Marine"].id
            ),
            ArticleCatalogue(
                nom="Jean Slim Confort Brut",
                imageUrl="https://images.unsplash.com/photo-1542272604-780c96856592?w=500",
                lienAchat="https://example.com/jean-slim",
                prix=89.00,
                vendeur="Denim Co",
                taillesDisponibles="38, 40, 42, 44",
                type_vetement_id=types_map["Jean"].id,
                couleur_id=colors_map["Bleu"].id
            ),
            ArticleCatalogue(
                nom="Chemise Oxford Blanche",
                imageUrl="https://images.unsplash.com/photo-1602810318383-e386cc2a3ccf?w=500",
                lienAchat="https://example.com/chemise-oxford",
                prix=59.50,
                vendeur="Classic Style",
                taillesDisponibles="S, M, L, XL",
                type_vetement_id=types_map["Chemise"].id,
                couleur_id=colors_map["Blanc"].id
            ),
            ArticleCatalogue(
                nom="Baskets Basses Cuir Blanc",
                imageUrl="https://images.unsplash.com/photo-1560769629-975ec94e6a86?w=500",
                lienAchat="https://example.com/baskets-blanches",
                prix=99.00,
                vendeur="Sneakers Lab",
                taillesDisponibles="40, 41, 42, 43, 44",
                type_vetement_id=types_map["Baskets"].id,
                couleur_id=colors_map["Blanc"].id
            )
        ]
        db.add_all(demo_articles)

    db.commit()
    logger.info("Données de référentiels et catalogue initialisées avec succès.")

