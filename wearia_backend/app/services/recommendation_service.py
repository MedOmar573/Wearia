from datetime import date, timedelta
from typing import List, Optional, Tuple, Dict
from sqlalchemy.orm import Session
from app.models.user import Utilisateur
from app.models.clothing import Vetement
from app.models.outfit import Tenue
from app.models.planning import RoutineHebdomadaire, Evenement
from app.models.referentials import Categorie
from app.models.enums import StatutVetement, Occasion, JourSemaine, Genre, GenreCible, TypePreference
from app.services.weather_service import WeatherService

JOURS_MAP = {
    0: JourSemaine.LUNDI,
    1: JourSemaine.MARDI,
    2: JourSemaine.MERCREDI,
    3: JourSemaine.JEUDI,
    4: JourSemaine.VENDREDI,
    5: JourSemaine.SAMEDI,
    6: JourSemaine.DIMANCHE
}

class RecommendationService:
    @staticmethod
    def determine_occasion_du_jour(
        user: Utilisateur,
        target_date: date,
        db: Session
    ) -> Occasion:
        """
        Implémente BR09 :
        L'occasion d'une tenue est celle de l'événement du jour s'il existe,
        sinon celle de la routine hebdomadaire du jour (ex. UNIVERSITE le lundi),
        sinon QUOTIDIEN.
        """
        # 1. Vérifier les événements ponctuels pour ce jour
        event = db.query(Evenement).filter(
            Evenement.utilisateur_id == user.id,
            Evenement.date == target_date
        ).first()
        if event:
            return event.occasion

        # 2. Vérifier la routine hebdomadaire pour ce jour de la semaine
        day_enum = JOURS_MAP.get(target_date.weekday(), JourSemaine.LUNDI)
        routine = db.query(RoutineHebdomadaire).filter(
            RoutineHebdomadaire.utilisateur_id == user.id,
            RoutineHebdomadaire.jourSemaine == day_enum,
            RoutineHebdomadaire.estActive == True
        ).first()
        if routine:
            return routine.occasion

        # 3. Défaut : QUOTIDIEN
        return Occasion.QUOTIDIEN

    @staticmethod
    def get_tenue_hier_ids(user: Utilisateur, target_date: date, db: Session) -> set:
        """
        Récupère l'ensemble des IDs des vêtements portés la veille (pour BR04).
        """
        hier = target_date - timedelta(days=1)
        tenue_hier = db.query(Tenue).filter(
            Tenue.utilisateur_id == user.id,
            Tenue.datePrevue == hier
        ).first()
        if tenue_hier and tenue_hier.vetements:
            return {v.id for v in tenue_hier.vetements}
        return set()

    @staticmethod
    def generate_recommendation(
        user: Utilisateur,
        db: Session,
        forced_occasion: Optional[Occasion] = None,
        target_date: Optional[date] = None,
        manual_temp: Optional[float] = None,
        manual_precip: Optional[bool] = None
    ) -> Tuple[Tenue, List[Vetement]]:
        """
        Moteur complet de recommandation selon BR01, BR02, BR03, BR04, BR08, BR09.
        """
        if target_date is None:
            target_date = date.today()

        # 1. Occasion (BR09)
        occasion = forced_occasion or RecommendationService.determine_occasion_du_jour(user, target_date, db)

        # 2. Météo
        if manual_temp is not None:
            temp = manual_temp
            precip = manual_precip if manual_precip is not None else False
            weather_desc = f"Manuel ({temp}°C)"
        else:
            weather_info = WeatherService.get_weather_for_city(user.ville or "Tunis")
            temp = weather_info["temperature"]
            precip = weather_info["precipitations"]
            weather_desc = weather_info["description"]

        # 3. Préférences personnelles de l'utilisateur (Profil, Genre, Couleurs, Styles, Morphologie)
        user_gender_str = user.genre.value.upper() if user.genre else None
        liked_color_ids = {pc.couleur_id for pc in user.preferences_couleur if pc.typePreference == TypePreference.AIME}
        avoided_color_ids = {pc.couleur_id for pc in user.preferences_couleur if pc.typePreference == TypePreference.EVITE}
        preferred_style_ids = {ps.style_id for ps in user.preferences_style if ps.typePreference == TypePreference.AIME}

        # Récupérer les vêtements disponibles (BR08)
        available_clothes_all: List[Vetement] = db.query(Vetement).filter(
            Vetement.utilisateur_id == user.id,
            Vetement.statut == StatutVetement.DISPONIBLE
        ).all()

        # Filtrer selon le genre de l'utilisateur (Homme vs Femme)
        available_clothes = []
        for v in available_clothes_all:
            cat_nom = v.type_vetement.categorie.nom.lower() if (v.type_vetement and v.type_vetement.categorie) else ""
            genre_cible = v.type_vetement.genreCible if v.type_vetement else GenreCible.MIXTE
            
            if user_gender_str == "HOMME":
                # Exclure les pièces exclusivement féminines ou catégories robe/jupe
                if genre_cible == GenreCible.FEMME or cat_nom in ["robe", "jupe"]:
                    continue
            elif user_gender_str == "FEMME":
                # Exclure les pièces exclusivement masculines
                if genre_cible == GenreCible.HOMME:
                    continue
            available_clothes.append(v)

        if not available_clothes:
            raise ValueError("Votre garde-robe ne contient aucun vêtement disponible adapté à votre profil. Ajoutez des pièces dans votre dressing !")

        # IDs de la veille pour BR04
        hier_ids = RecommendationService.get_tenue_hier_ids(user, target_date, db)

        # Fonction de pondération d'une pièce selon les préférences personnelles
        def piece_preference_score(v: Vetement) -> int:
            score_piece = 0
            # Priorité 1 : Pas porté hier
            if v.id not in hier_ids:
                score_piece += 100
            # Priorité 2 : Couleur préférée
            if v.couleur_id and v.couleur_id in liked_color_ids:
                score_piece += 50
            # Pénalité : Couleur évitée
            if v.couleur_id and v.couleur_id in avoided_color_ids:
                score_piece -= 60
            # Priorité 3 : Style vestimentaire favori
            if v.style_id and v.style_id in preferred_style_ids:
                score_piece += 30
            # Priorité 4 : Coupe préférée
            if user.coupePreferee and v.coupe and v.coupe.upper() == user.coupePreferee.value.upper():
                score_piece += 20
            return score_piece

        # Trier/Regrouper par catégorie avec pondération personnalisée
        hauts = []
        bas = []
        robes = []
        chaussures = []
        vestes_manteaux = []

        for v in available_clothes:
            cat_nom = v.type_vetement.categorie.nom.lower() if (v.type_vetement and v.type_vetement.categorie) else ""
            if "haut" in cat_nom:
                hauts.append(v)
            elif "bas" in cat_nom:
                bas.append(v)
            elif "robe" in cat_nom:
                if user_gender_str != "HOMME":
                    robes.append(v)
            elif "chaussure" in cat_nom or "basket" in cat_nom or "botte" in cat_nom:
                chaussures.append(v)
            elif "veste" in cat_nom or "manteau" in cat_nom or (v.type_vetement and v.type_vetement.estCoucheSuperieure):
                vestes_manteaux.append(v)

        hauts.sort(key=piece_preference_score, reverse=True)
        bas.sort(key=piece_preference_score, reverse=True)
        robes.sort(key=piece_preference_score, reverse=True)
        chaussures.sort(key=piece_preference_score, reverse=True)
        vestes_manteaux.sort(key=piece_preference_score, reverse=True)

        # 4. BR01 (Complétude) : (Haut + Bas OU Robe) + Chaussures
        selected_items: List[Vetement] = []
        use_robe = False

        if robes and user_gender_str != "HOMME" and (not hauts or not bas or len(robes) > len(bas)):
            selected_items.append(robes[0])
            use_robe = True
        elif hauts and bas:
            selected_items.extend([hauts[0], bas[0]])
        elif hauts:
            selected_items.append(hauts[0])
        elif bas:
            selected_items.append(bas[0])

        if chaussures:
            selected_items.append(chaussures[0])

        # 5. BR02 : Météo (si < 14°C ou pluie, couche supérieure obligatoire)
        needs_outerwear = (temp < 14.0) or precip
        has_outerwear = False

        if needs_outerwear:
            outer_candidates = [
                v for v in available_clothes 
                if (v.type_vetement and v.type_vetement.estCoucheSuperieure) 
                or v.estThermique 
                or v.estImpermeable
                or (v.type_vetement and "veste" in v.type_vetement.categorie.nom.lower())
            ]
            if outer_candidates:
                outer_candidates.sort(key=piece_preference_score, reverse=True)
                for cand in outer_candidates:
                    if cand.id not in [item.id for item in selected_items]:
                        selected_items.append(cand)
                        has_outerwear = True
                        break

        # 6. BR03 : Harmonie colorimétrique (max 3 teintes divergentes)
        colors = [item.couleur.nom.lower() for item in selected_items if item.couleur]
        unique_colors = set(colors)
        color_penalty = 0
        if len(unique_colors) > 3:
            color_penalty = (len(unique_colors) - 3) * 10

        # 7. Calcul du score de compatibilité sur 100
        score = 85
        explanation_parts = []

        # Complétude
        has_top = any("haut" in (v.type_vetement.categorie.nom.lower() if v.type_vetement and v.type_vetement.categorie else "") for v in selected_items)
        has_bottom = any("bas" in (v.type_vetement.categorie.nom.lower() if v.type_vetement and v.type_vetement.categorie else "") for v in selected_items)
        has_dress = any("robe" in (v.type_vetement.categorie.nom.lower() if v.type_vetement and v.type_vetement.categorie else "") for v in selected_items)
        has_shoes = any("chaussure" in (v.type_vetement.categorie.nom.lower() if v.type_vetement and v.type_vetement.categorie else "") for v in selected_items)

        if (has_top and has_bottom) or has_dress:
            score += 10
        else:
            score -= 20

        if has_shoes:
            score += 5
        else:
            score -= 15

        # Bonus Couleurs préférées
        matching_liked_colors = [
            item.couleur.nom for item in selected_items 
            if item.couleur and item.couleur_id in liked_color_ids
        ]
        if matching_liked_colors:
            score = min(100, score + 10)
            colors_formatted = ", ".join(list(set(matching_liked_colors)))
            explanation_parts.append(f"Mise en valeur de vos couleurs favorites ({colors_formatted}).")

        # Bonus Style préféré
        matching_styles = [
            item.style_vestimentaire.libelle for item in selected_items 
            if item.style_vestimentaire and item.style_id in preferred_style_ids
        ]
        if matching_styles:
            score = min(100, score + 5)
            explanation_parts.append(f"Style '{matching_styles[0]}' parfaitement aligné avec vos goûts.")

        # Prise en compte de la Morphologie (Taille, Poids, Coupe)
        if user.hauteurCm and user.poidsKg:
            fit_name = user.coupePreferee.value.capitalize() if user.coupePreferee else "Harmonieuse"
            explanation_parts.append(f"Coupe {fit_name.lower()} adaptée à votre silhouette ({user.hauteurCm} cm, {int(user.poidsKg)} kg).")

        # Météo
        if needs_outerwear and not has_outerwear:
            score -= 20
            explanation_parts.append(f"Météo fraîche ({temp:.1f}°C) : une couche chaude supplémentaire est conseillée.")
        elif needs_outerwear and has_outerwear:
            explanation_parts.append(f"Protection adaptée à la température de {temp:.1f}°C.")

        # Pénalité couleur
        score = max(20, min(100, score - color_penalty))

        # Explication finale personnalisée
        occasion_str = occasion.value.lower()
        base_explanation = f"Tenue composée pour votre journée '{occasion_str}' ({temp:.1f}°C, {weather_desc})."
        if explanation_parts:
            full_explanation = f"{base_explanation} {' '.join(explanation_parts)}"
        else:
            full_explanation = f"{base_explanation} Sélection équilibrée respectant votre profil et votre dressing."

        # Création et sauvegarde de la Tenue
        tenue = Tenue(
            utilisateur_id=user.id,
            datePrevue=target_date,
            occasion=occasion,
            temperatureCelsius=temp,
            precipitations=precip,
            descriptionMeteo=weather_desc,
            explication=full_explanation,
            scoreCompatibilite=score,
            estGeneree=True,
            estFavorite=False
        )
        tenue.vetements = selected_items

        db.add(tenue)
        db.commit()
        db.refresh(tenue)

        return tenue, selected_items

