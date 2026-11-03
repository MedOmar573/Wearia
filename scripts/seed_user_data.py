import os
import sys
from datetime import date, datetime, timedelta

# Ajouter le chemin du backend
sys.path.insert(0, r"c:\Users\DELL\Desktop\L3DSI\projet\Wearia\wearia_backend")

from app.database.connection import SessionLocal
from app.models.user import Utilisateur, PreferenceCouleur, PreferenceStyle
from app.models.clothing import Vetement, tenue_vetements
from app.models.outfit import Tenue, Feedback
from app.models.planning import RoutineHebdomadaire, Evenement
from app.models.referentials import Categorie, TypeVetement, Couleur, StyleVestimentaire
from app.models.shopping import ArticleCatalogue
from app.models.enums import (
    Genre, Coupe, Saison, StatutVetement, Occasion, 
    JourSemaine, Appreciation, TypePreference, GenreCible
)

def seed_mohamed_omar_ben_hamda():
    db = SessionLocal()
    try:
        print("=== DEBUT DU RECHARGEMENT DES DONNEES POUR MOHAMED OMAR BEN HAMDA ===")
        
        # 1. Récupérer ou mettre à jour l'utilisateur
        user = db.query(Utilisateur).filter(Utilisateur.email == "benhamdaomar21@gmail.com").first()
        if not user:
            user = db.query(Utilisateur).filter(Utilisateur.nom.ilike("%Mohamed Omar%")).first()
            
        if not user:
            print("Création de l'utilisateur Mohamed Omar Ben Hamda...")
            from app.core.security import get_password_hash
            user = Utilisateur(
                nom="Mohamed Omar Ben Hamda",
                email="benhamdaomar21@gmail.com",
                motDePasseHash=get_password_hash("04508468"),
                genre=Genre.HOMME,
                dateNaissance=date(2001, 5, 14),
                ville="Tunis",
                hauteurCm=182,
                poidsKg=76.0,
                tourEpaules=112.0,
                tourPoitrine=100.0,
                tourTaille=82.0,
                tourHanches=96.0,
                tailleVestimentaire="L",
                coupePreferee=Coupe.REGULIERE,
                consentementRGPD=True
            )
            db.add(user)
            db.flush()
        else:
            print(f"Mise à jour du profil de l'utilisateur ID={user.id} ({user.nom})...")
            user.nom = "Mohamed Omar Ben Hamda"
            user.genre = Genre.HOMME
            user.ville = "Tunis"
            user.hauteurCm = 182
            user.poidsKg = 76.0
            user.tailleVestimentaire = "L"
            user.coupePreferee = Coupe.REGULIERE
            user.dateNaissance = date(2001, 5, 14)
            db.flush()

        user_id = user.id

        # 2. Dictionnaires des référentiels
        types_map = {t.nom: t for t in db.query(TypeVetement).all()}
        colors_map = {c.nom: c for c in db.query(Couleur).all()}
        styles_map = {s.libelle: s for s in db.query(StyleVestimentaire).all()}

        # 3. Mettre à jour les routines hebdomadaires
        print("Mise à jour des routines hebdomadaires...")
        db.query(RoutineHebdomadaire).filter(RoutineHebdomadaire.utilisateur_id == user_id).delete()
        routines_schedule = [
            (JourSemaine.LUNDI, Occasion.UNIVERSITE),
            (JourSemaine.MARDI, Occasion.TRAVAIL),
            (JourSemaine.MERCREDI, Occasion.UNIVERSITE),
            (JourSemaine.JEUDI, Occasion.TRAVAIL),
            (JourSemaine.VENDREDI, Occasion.QUOTIDIEN),
            (JourSemaine.SAMEDI, Occasion.SORTIE),
            (JourSemaine.DIMANCHE, Occasion.SPORT),
        ]
        for jour, occ in routines_schedule:
            db.add(RoutineHebdomadaire(
                utilisateur_id=user_id,
                jourSemaine=jour,
                occasion=occ,
                estActive=True
            ))

        # 4. Mettre à jour les préférences de styles et de couleurs
        print("Mise à jour des préférences de style et couleurs...")
        db.query(PreferenceCouleur).filter(PreferenceCouleur.utilisateur_id == user_id).delete()
        db.query(PreferenceStyle).filter(PreferenceStyle.utilisateur_id == user_id).delete()

        pref_colors = ["Bleu Marine", "Blanc", "Noir", "Gris", "Beige", "Bleu"]
        for cname in pref_colors:
            if cname in colors_map:
                db.add(PreferenceCouleur(
                    utilisateur_id=user_id,
                    couleur_id=colors_map[cname].id,
                    typePreference=TypePreference.AIME
                ))

        pref_styles = ["Classique", "Décontracté", "Chic", "Streetwear"]
        for sname in pref_styles:
            if sname in styles_map:
                db.add(PreferenceStyle(
                    utilisateur_id=user_id,
                    style_id=styles_map[sname].id,
                    typePreference=TypePreference.AIME
                ))

        # 5. Nettoyer les anciens vêtements pour recharger une garde-robe propre et cohérente
        print("Nettoyage des anciens vêtements et tenues...")
        # Supprimer les liens tenues
        user_tenues = db.query(Tenue).filter(Tenue.utilisateur_id == user_id).all()
        for t in user_tenues:
            db.delete(t)
        db.flush()

        # Supprimer les anciens vêtements
        db.query(Vetement).filter(Vetement.utilisateur_id == user_id).delete()
        db.flush()

        # 6. Insérer les 17 vêtements réalistes avec leurs photos
        print("Insertion des 17 nouveaux vêtements avec photos de haute qualité...")
        clothes_data = [
            # HAUTS
            {
                "nom": "Chemise Oxford Blanche",
                "photoUrl": "/uploads/chemise_oxford_blanche.jpg",
                "matiere": "100% Coton Oxford",
                "coupe": Coupe.REGULIERE,
                "saison": Saison.TOUTE_SAISON,
                "estThermique": False,
                "estImpermeable": False,
                "type": "Chemise",
                "couleur": "Blanc",
                "style": "Classique"
            },
            {
                "nom": "T-Shirt Noir Minimaliste",
                "photoUrl": "/uploads/tshirt_noir.jpg",
                "matiere": "Coton biologique doux",
                "coupe": Coupe.REGULIERE,
                "saison": Saison.ETE,
                "estThermique": False,
                "estImpermeable": False,
                "type": "T-Shirt",
                "couleur": "Noir",
                "style": "Décontracté"
            },
            {
                "nom": "Polo Bleu Marine Piqué",
                "photoUrl": "/uploads/polo_marine.jpg",
                "matiere": "Piqué de coton respirant",
                "coupe": Coupe.AJUSTEE,
                "saison": Saison.ETE,
                "estThermique": False,
                "estImpermeable": False,
                "type": "Polo",
                "couleur": "Bleu Marine",
                "style": "Classique"
            },
            {
                "nom": "Pull Maille Côtelée Beige",
                "photoUrl": "/uploads/pull_maille_beige.jpg",
                "matiere": "Laine mérinos mélangée",
                "coupe": Coupe.REGULIERE,
                "saison": Saison.HIVER,
                "estThermique": True,
                "estImpermeable": False,
                "type": "Pull",
                "couleur": "Beige",
                "style": "Décontracté"
            },
            {
                "nom": "Sweat à Capuche Gris Urbain",
                "photoUrl": "/uploads/sweat_capuche_gris.jpg",
                "matiere": "Coton molleton épais",
                "coupe": Coupe.OVERSIZE,
                "saison": Saison.AUTOMNE,
                "estThermique": True,
                "estImpermeable": False,
                "type": "Sweat",
                "couleur": "Gris",
                "style": "Sportswear"
            },
            {
                "nom": "T-Shirt Blanc Col Rond",
                "photoUrl": "/uploads/tshirt_blanc.jpg",
                "matiere": "Coton peigné",
                "coupe": Coupe.REGULIERE,
                "saison": Saison.ETE,
                "estThermique": False,
                "estImpermeable": False,
                "type": "T-Shirt",
                "couleur": "Blanc",
                "style": "Décontracté"
            },

            # BAS
            {
                "nom": "Jean Slim Brut Bleu Foncé",
                "photoUrl": "/uploads/jean_slim_bleu.jpg",
                "matiere": "Denim stretch 12oz",
                "coupe": Coupe.AJUSTEE,
                "saison": Saison.TOUTE_SAISON,
                "estThermique": False,
                "estImpermeable": False,
                "type": "Jean",
                "couleur": "Bleu",
                "style": "Décontracté"
            },
            {
                "nom": "Pantalon Chino Beige Sable",
                "photoUrl": "/uploads/chino_beige.jpg",
                "matiere": "Coton sergé doux",
                "coupe": Coupe.REGULIERE,
                "saison": Saison.PRINTEMPS,
                "estThermique": False,
                "estImpermeable": False,
                "type": "Pantalon",
                "couleur": "Beige",
                "style": "Classique"
            },
            {
                "nom": "Pantalon Habillé Noir",
                "photoUrl": "/uploads/pantalon_noir.jpg",
                "matiere": "Laine froide & viscose",
                "coupe": Coupe.AJUSTEE,
                "saison": Saison.TOUTE_SAISON,
                "estThermique": False,
                "estImpermeable": False,
                "type": "Pantalon",
                "couleur": "Noir",
                "style": "Chic"
            },
            {
                "nom": "Short Casual Vert Kaki",
                "photoUrl": "/uploads/short_kaki.jpg",
                "matiere": "Coton léger ripstop",
                "coupe": Coupe.REGULIERE,
                "saison": Saison.ETE,
                "estThermique": False,
                "estImpermeable": False,
                "type": "Short",
                "couleur": "Vert",
                "style": "Décontracté"
            },

            # VESTES & MANTEAUX
            {
                "nom": "Veste Bomber Noire Urbaine",
                "photoUrl": "/uploads/bomber_noir.jpg",
                "matiere": "Nylon déperlant coupe-vent",
                "coupe": Coupe.REGULIERE,
                "saison": Saison.AUTOMNE,
                "estThermique": True,
                "estImpermeable": True,
                "type": "Veste",
                "couleur": "Noir",
                "style": "Streetwear"
            },
            {
                "nom": "Blazer Tailleur Bleu Marine",
                "photoUrl": "/uploads/blazer_marine.jpg",
                "matiere": "Laine peignée stretch",
                "coupe": Coupe.AJUSTEE,
                "saison": Saison.TOUTE_SAISON,
                "estThermique": False,
                "estImpermeable": False,
                "type": "Veste",
                "couleur": "Bleu Marine",
                "style": "Chic"
            },
            {
                "nom": "Veste en Jean Vintage Bleu",
                "photoUrl": "/uploads/veste_jean.jpg",
                "matiere": "100% Coton denim",
                "coupe": Coupe.REGULIERE,
                "saison": Saison.PRINTEMPS,
                "estThermique": False,
                "estImpermeable": False,
                "type": "Veste",
                "couleur": "Bleu",
                "style": "Décontracté"
            },
            {
                "nom": "Manteau Long Laine Gris Anthracite",
                "photoUrl": "/uploads/manteau_gris.jpg",
                "matiere": "Drap de laine chaud",
                "coupe": Coupe.REGULIERE,
                "saison": Saison.HIVER,
                "estThermique": True,
                "estImpermeable": False,
                "type": "Manteau",
                "couleur": "Gris",
                "style": "Classique"
            },

            # CHAUSSURES
            {
                "nom": "Baskets Basses Cuir Blanc",
                "photoUrl": "/uploads/baskets_blanches.jpg",
                "matiere": "Cuir de vachette lisse",
                "coupe": Coupe.REGULIERE,
                "saison": Saison.TOUTE_SAISON,
                "estThermique": False,
                "estImpermeable": False,
                "type": "Baskets",
                "couleur": "Blanc",
                "style": "Décontracté"
            },
            {
                "nom": "Derbies Habillées Cuir Marron",
                "photoUrl": "/uploads/derbies_marron.jpg",
                "matiere": "Cuir véritable pleine fleur",
                "coupe": Coupe.REGULIERE,
                "saison": Saison.TOUTE_SAISON,
                "estThermique": False,
                "estImpermeable": False,
                "type": "Chaussures de ville",
                "couleur": "Marron",
                "style": "Chic"
            },
            {
                "nom": "Sneakers Running Noir Performance",
                "photoUrl": "/uploads/baskets_sport_noires.jpg",
                "matiere": "Mesh respirant & semelle EVA",
                "coupe": Coupe.REGULIERE,
                "saison": Saison.TOUTE_SAISON,
                "estThermique": False,
                "estImpermeable": False,
                "type": "Baskets",
                "couleur": "Noir",
                "style": "Sportswear"
            }
        ]

        inserted_clothes = []
        for cd in clothes_data:
            v = Vetement(
                nom=cd["nom"],
                photoUrl=cd["photoUrl"],
                matiere=cd["matiere"],
                coupe=cd["coupe"],
                saison=cd["saison"],
                estThermique=cd["estThermique"],
                estImpermeable=cd["estImpermeable"],
                statut=StatutVetement.DISPONIBLE,
                utilisateur_id=user_id,
                type_vetement_id=types_map[cd["type"]].id,
                couleur_id=colors_map[cd["couleur"]].id,
                style_id=styles_map[cd["style"]].id if cd["style"] in styles_map else None,
                dateAjout=datetime.utcnow()
            )
            db.add(v)
            inserted_clothes.append(v)

        db.flush()
        print(f"{len(inserted_clothes)} vêtements insérés avec succès.")

        # Map pour accès rapide par nom
        vmap = {v.nom: v for v in inserted_clothes}

        # 7. Créer de superbes tenues recommandées / historiques pour tester les écrans Tenues
        print("Génération de 3 tenues complètes de démonstration...")

        # Tenue 1 : Aujourd'hui (Université - Casual Chic)
        tenue_today = Tenue(
            utilisateur_id=user_id,
            datePrevue=date.today(),
            dateCreation=datetime.utcnow(),
            occasion=Occasion.UNIVERSITE,
            temperatureCelsius=18.5,
            precipitations=False,
            descriptionMeteo="Ciel dégagé, 18°C",
            scoreCompatibilite=96,
            explication="Harmonie parfaite entre la chemise blanche oxford, le jean brut et la veste bomber noire pour une journée universitaire.",
            estGeneree=True,
            estFavorite=True,
            style_id=styles_map["Décontracté"].id
        )
        tenue_today.vetements.extend([
            vmap["Chemise Oxford Blanche"],
            vmap["Jean Slim Brut Bleu Foncé"],
            vmap["Veste Bomber Noire Urbaine"],
            vmap["Baskets Basses Cuir Blanc"]
        ])
        db.add(tenue_today)

        # Tenue 2 : Hier (Travail - Chic)
        tenue_yesterday = Tenue(
            utilisateur_id=user_id,
            datePrevue=date.today() - timedelta(days=1),
            datePortee=datetime.utcnow() - timedelta(days=1),
            dateCreation=datetime.utcnow() - timedelta(days=1),
            occasion=Occasion.TRAVAIL,
            temperatureCelsius=20.0,
            precipitations=False,
            descriptionMeteo="Ensoleillé, 20°C",
            scoreCompatibilite=98,
            explication="Élégance formelle garantie avec le blazer bleu marine, chino beige et derbies marron patinées.",
            estGeneree=True,
            estFavorite=True,
            style_id=styles_map["Chic"].id
        )
        tenue_yesterday.vetements.extend([
            vmap["Polo Bleu Marine Piqué"],
            vmap["Pantalon Chino Beige Sable"],
            vmap["Blazer Tailleur Bleu Marine"],
            vmap["Derbies Habillées Cuir Marron"]
        ])
        db.add(tenue_yesterday)

        # Feedback positif pour la tenue d'hier
        db.flush()
        fb = Feedback(
            tenue_id=tenue_yesterday.id,
            appreciation=Appreciation.AIME,
            dateFeedback=datetime.utcnow() - timedelta(days=1)
        )
        db.add(fb)

        # Tenue 3 : Avant-hier (Sortie / Sportswear)
        tenue_prev = Tenue(
            utilisateur_id=user_id,
            datePrevue=date.today() - timedelta(days=2),
            datePortee=datetime.utcnow() - timedelta(days=2),
            dateCreation=datetime.utcnow() - timedelta(days=2),
            occasion=Occasion.SORTIE,
            temperatureCelsius=16.0,
            precipitations=False,
            descriptionMeteo="Nuageux, 16°C",
            scoreCompatibilite=92,
            explication="Confort streetwear optimal avec le sweat à capuche gris, jean et sneakers de running.",
            estGeneree=True,
            estFavorite=False,
            style_id=styles_map["Sportswear"].id
        )
        tenue_prev.vetements.extend([
            vmap["Sweat à Capuche Gris Urbain"],
            vmap["Jean Slim Brut Bleu Foncé"],
            vmap["Sneakers Running Noir Performance"]
        ])
        db.add(tenue_prev)

        # 8. Mettre à jour les articles du catalogue avec photos HD locales ou directes
        print("Mise à jour du catalogue d'articles Personal Shopper...")
        db.query(ArticleCatalogue).delete()
        catalog_items = [
            ArticleCatalogue(
                nom="Veste Imperméable Coupe-vent Noire",
                imageUrl="/uploads/bomber_noir.jpg",
                lienAchat="https://example.com/veste-impermeable",
                prix=129.99,
                vendeur="Wearia Store",
                taillesDisponibles="M, L, XL",
                type_vetement_id=types_map["Veste"].id,
                couleur_id=colors_map["Noir"].id
            ),
            ArticleCatalogue(
                nom="Jean Slim Denim Brut",
                imageUrl="/uploads/jean_slim_bleu.jpg",
                lienAchat="https://example.com/jean-slim",
                prix=89.00,
                vendeur="Denim Studio",
                taillesDisponibles="38, 40, 42, 44",
                type_vetement_id=types_map["Jean"].id,
                couleur_id=colors_map["Bleu"].id
            ),
            ArticleCatalogue(
                nom="Chemise Oxford Blanche Coupe Ajustée",
                imageUrl="/uploads/chemise_oxford_blanche.jpg",
                lienAchat="https://example.com/chemise-oxford",
                prix=59.50,
                vendeur="Classic Tailor",
                taillesDisponibles="S, M, L, XL",
                type_vetement_id=types_map["Chemise"].id,
                couleur_id=colors_map["Blanc"].id
            ),
            ArticleCatalogue(
                nom="Baskets Basses Cuir Blanc Minimalistes",
                imageUrl="/uploads/baskets_blanches.jpg",
                lienAchat="https://example.com/baskets-blanches",
                prix=99.00,
                vendeur="Sneakers Lab",
                taillesDisponibles="40, 41, 42, 43, 44",
                type_vetement_id=types_map["Baskets"].id,
                couleur_id=colors_map["Blanc"].id
            ),
            ArticleCatalogue(
                nom="Blazer Laine Peignée Bleu Marine",
                imageUrl="/uploads/blazer_marine.jpg",
                lienAchat="https://example.com/blazer-marine",
                prix=189.00,
                vendeur="Sartorial Paris",
                taillesDisponibles="48, 50, 52, 54",
                type_vetement_id=types_map["Veste"].id,
                couleur_id=colors_map["Bleu Marine"].id
            ),
            ArticleCatalogue(
                nom="Derbies Cuir Patiné Marron Foncé",
                imageUrl="/uploads/derbies_marron.jpg",
                lienAchat="https://example.com/derbies-marron",
                prix=149.00,
                vendeur="Bottega Artisans",
                taillesDisponibles="41, 42, 43, 44",
                type_vetement_id=types_map["Chaussures de ville"].id,
                couleur_id=colors_map["Marron"].id
            )
        ]
        db.add_all(catalog_items)

        db.commit()
        print("=== RECHARGEMENT REUSSI AVEC SUCCES ! ===")
        print(f"Utilisateur : {user.nom} ({user.email})")
        print(f"Total vêtements dans le dressing : {len(inserted_clothes)}")
        print(f"Total routines configurées : {len(routines_schedule)}")
        print(f"Total tenues prêtes : 3")
        print(f"Total articles catalogue : {len(catalog_items)}")

    except Exception as e:
        db.rollback()
        print(f"ERREUR lors du rechargement : {e}")
        raise e
    finally:
        db.close()

if __name__ == "__main__":
    seed_mohamed_omar_ben_hamda()

