"""
Suite de tests unitaires et d'intégration rapide pour l'AI Shopper Wearia.

Couvre :
1. Validation & normalisation stricte des URLs (liens invalides, catégories, domaines interdits, 404).
2. Normalisation des critères (occasion, style UI->DB, saison, couleurs souhaitées vs évitées, sans URL inventée).
3. Normaliseur produit ("Veste en Jean" -> Veste, "Pull&Bear" -> pas Pull, couleur brute prioritaire).
4. Filtrage strict & scoring multi-critères (budget, genre HOMME/FEMME sans crash MIXTE, saison, style, occasion, pièces demandées/exclues, couleurs).
5. Déduplication stricte (ID, URL normalisée multi-tailles/UTM, identité produit, exclusions de session).
6. Composition de tenues cohérentes (budget total, présence de veste/robe demandée, absence de doublons, explication/style cohérents).
"""

import asyncio
import sys
import unittest
from datetime import datetime
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import httpx

# Ajouter wearia_backend au PYTHONPATH si exécuté depuis la racine du dépôt
BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.ai.shopper_llm import (
    RuleBasedFallbackLLMProvider,
    _build_criteria_from_dict,
    normalize_shopper_occasion,
    normalize_shopper_season,
    normalize_shopper_style,
)
from app.models.enums import GenreCible
from app.schemas.shopper import ShopperCriteria
from app.scraper.normalizer import DataNormalizer
from app.services.product_search_service import (
    compute_article_score,
    extract_excluded_type_mentions,
    extract_requested_type_mentions,
    filter_and_group_articles,
    search_individual_articles,
)
from app.services.shopper_orchestrator import ShopperOrchestrator
from app.services.shopper_outfit_service import ShopperOutfitService
from app.services.shopper_validation import (
    _URL_HEALTH_CACHE,
    build_product_dedup_keys,
    is_valid_product_url,
    normalize_product_url,
    verify_urls_status,
)


def make_article(
    *,
    id: int,
    nom: str,
    prix: float,
    type_nom: str,
    categorie_nom: str,
    couleur_nom: str,
    style_nom: str = "Décontracté",
    genre: GenreCible = GenreCible.HOMME,
    vendeur: str = "Exist Tunisie",
    lien_achat: str = "",
    en_stock: bool = True,
    description: str = "",
) -> SimpleNamespace:
    if not lien_achat:
        slug = nom.lower().replace(" ", "-").replace("'", "")
        lien_achat = f"https://www.exist.com.tn/produits/{id}-{slug}.html"
    return SimpleNamespace(
        id=id,
        nom=nom,
        description=description,
        imageUrl=f"https://www.exist.com.tn/img/{id}.jpg",
        lienAchat=lien_achat,
        prix=prix,
        devise="TND",
        vendeur=vendeur,
        taillesDisponibles="M, L",
        enStock=en_stock,
        genreCible=genre,
        dateDerniereSynchro=datetime.utcnow(),
        type_vetement=SimpleNamespace(
            nom=type_nom,
            genreCible=genre,
            categorie=SimpleNamespace(nom=categorie_nom),
        ),
        couleur=SimpleNamespace(nom=couleur_nom),
        style=SimpleNamespace(libelle=style_nom),
    )


class TestShopperValidation(unittest.TestCase):
    def test_valid_and_invalid_product_urls(self):
        valid_cases = [
            "https://www.exist.com.tn/chemises/51817-chemise.html#/1032-taille-xl/7817-couleur-bleu",
            "https://mabrouk.tn/produit/robe-midi-noire/",
        ]
        for url in valid_cases:
            ok, reason = is_valid_product_url(url)
            self.assertTrue(ok, f"URL valide rejetée ({reason}): {url}")

        invalid_cases = [
            "",
            None,
            "http://www.exist.com.tn/chemises/123-chemise.html",  # HTTP non HTTPS
            "https://localhost/produit/123",
            "https://127.0.0.1/produit/123",
            "https://example.com/produit/123",
            "https://www.exist.com.tn/",  # Racine sans fiche produit
            "https://www.pullandbear.com/tn/homme/jeans-c29013.html",  # Page catégorie
            "https://www.zara.com/tn/fr/homme-chemises-l737.html",  # Page catégorie
            "https://mabrouk.tn/categorie-produit/vetements-femmes/pulls-t-shirts/",  # Catégorie WooCommerce
            "https://www.exist.com.tn/chemise avec espace.html",
        ]
        for url in invalid_cases:
            ok, _ = is_valid_product_url(url)
            self.assertFalse(ok, f"URL invalide acceptée à tort : {url}")

    def test_allowed_domains_enforcement(self):
        ok, _ = is_valid_product_url(
            "https://www.exist.com.tn/p/123-chemise.html",
            allowed_domains={"www.exist.com.tn"},
        )
        self.assertTrue(ok)
        ok_bad, reason = is_valid_product_url(
            "https://www.fake-shop.tn/p/123-chemise.html",
            allowed_domains={"www.exist.com.tn"},
        )
        self.assertFalse(ok_bad)
        self.assertIn("domaine_non_autorise", reason)

    def test_normalize_url_strips_tracking_and_size_fragment(self):
        url_size_m = (
            "https://www.exist.com.tn/chemises/51817-chemise.html"
            "?utm_source=ig&fbclid=abc#/1030-taille-m/7817-couleur-bleu"
        )
        url_size_xl = (
            "HTTPS://WWW.EXIST.COM.TN/chemises/51817-chemise.html"
            "#/1032-taille-xl/7817-couleur-bleu"
        )
        url_other_color = (
            "https://www.exist.com.tn/chemises/51817-chemise.html"
            "#/1032-taille-xl/7818-couleur-noir"
        )
        self.assertEqual(normalize_product_url(url_size_m), normalize_product_url(url_size_xl))
        self.assertNotEqual(normalize_product_url(url_size_m), normalize_product_url(url_other_color))

    def test_verify_urls_status_filters_404_and_preserves_offline_none(self):
        _URL_HEALTH_CACHE.clear()
        alive_url = "https://www.exist.com.tn/p/100-ok.html"
        dead_url = "https://www.exist.com.tn/p/404-dead.html"
        offline_url = "https://www.exist.com.tn/p/offline.html"
        invalid_url = "https://example.com/fake-product"

        async def fake_head(url, headers=None):
            if "404-dead" in url:
                return SimpleNamespace(status_code=404)
            if "offline" in url:
                raise httpx.ConnectError("network down")
            return SimpleNamespace(status_code=200)

        fake_client = MagicMock()
        fake_client.__aenter__ = AsyncMock(return_value=fake_client)
        fake_client.__aexit__ = AsyncMock(return_value=None)
        fake_client.head = AsyncMock(side_effect=fake_head)
        fake_client.get = AsyncMock(side_effect=fake_head)

        with patch("app.services.shopper_validation.httpx.AsyncClient", return_value=fake_client):
            statuses = asyncio.run(
                verify_urls_status([alive_url, dead_url, offline_url, invalid_url], timeout=1.0)
            )

        self.assertIs(statuses[alive_url], True)
        self.assertIs(statuses[dead_url], False)
        self.assertIsNone(statuses[offline_url])
        self.assertIs(statuses[invalid_url], False)


class TestShopperCriteriaAndNormalizer(unittest.TestCase):
    def test_canonical_style_occasion_season_normalization(self):
        self.assertEqual(normalize_shopper_style("Casual"), "Décontracté")
        self.assertEqual(normalize_shopper_style("Sportif"), "Sportswear")
        self.assertEqual(normalize_shopper_style("Élégant"), "Chic")
        self.assertEqual(normalize_shopper_style("Minimaliste"), "Minimaliste")
        self.assertEqual(normalize_shopper_occasion("UNIVERSITÉ"), "UNIVERSITE")
        self.assertEqual(normalize_shopper_occasion("ÉVÉNEMENT"), "EVENEMENT")
        self.assertEqual(normalize_shopper_season("Été"), "ETE")
        self.assertEqual(normalize_shopper_season("Hiver"), "HIVER")

    def test_fallback_llm_extracts_season_negated_color_and_strips_urls(self):
        provider = RuleBasedFallbackLLMProvider()
        crit = asyncio.run(
            provider.interpret_prompt(
                "Tenue chic pour le travail en été, bleu marine, sans noir, budget 260 DT"
            )
        )
        self.assertEqual(crit.style, "Chic")
        self.assertEqual(crit.occasion, "TRAVAIL")
        self.assertEqual(crit.season, "ETE")
        self.assertEqual(crit.budget, 260.0)
        self.assertIn("Bleu Marine", crit.colors)
        self.assertIn("Noir", crit.avoided_colors)
        self.assertNotIn("Noir", crit.colors)

        built = _build_criteria_from_dict(
            {
                "style": "Élégant",
                "occasion": "TRAVAIL",
                "season": "Été",
                "search_queries": ["chemise lin", "https://invented-shop.com/fake"],
            }
        )
        self.assertEqual(built.style, "Chic")
        self.assertEqual(built.season, "ETE")
        self.assertEqual(built.search_queries, ["chemise lin"])

    def test_normalizer_type_and_raw_color_priority(self):
        types = [
            SimpleNamespace(id=1, nom="Pull"),
            SimpleNamespace(id=2, nom="Jean"),
            SimpleNamespace(id=3, nom="Veste"),
            SimpleNamespace(id=4, nom="Baskets"),
        ]
        couleurs = [
            SimpleNamespace(id=10, nom="Noir"),
            SimpleNamespace(id=11, nom="Bleu"),
            SimpleNamespace(id=12, nom="Bleu Marine"),
            SimpleNamespace(id=13, nom="Blanc"),
        ]

        db = MagicMock()
        db.query.return_value.all.side_effect = [types, types, types, couleurs, couleurs]

        # "Veste en Jean" doit être Veste, pas Jean
        self.assertEqual(DataNormalizer.match_type_vetement("Veste en Jean Brut", "", db).id, 3)
        # "Pull&Bear" dans le titre ne doit pas classer un Jean comme Pull
        self.assertEqual(DataNormalizer.match_type_vetement("Jean Baggy Pull&Bear", "", db).id, 2)
        self.assertEqual(DataNormalizer.match_type_vetement("Baskets Blanches Pull&Bear", "", db).id, 4)
        # Couleur brute structurée prioritaire et multi-mots avant mot simple
        self.assertEqual(
            DataNormalizer.match_couleur("Chemise", "", db, raw_color="bleu marine").id,
            12,
        )
        self.assertEqual(
            DataNormalizer.match_couleur("Chemise Classique", "", db, raw_color="blanc").id,
            13,
        )


class TestFilteringScoringDedupAndComposition(unittest.TestCase):
    def _build_catalog(self):
        return [
            # Hauts Homme
            make_article(
                id=1,
                nom="Chemise Lin Bleu Marine",
                prix=95.0,
                type_nom="Chemise",
                categorie_nom="Hauts",
                couleur_nom="Bleu Marine",
                style_nom="Chic",
            ),
            make_article(
                id=2,
                nom="T-Shirt Coton Blanc",
                prix=45.0,
                type_nom="T-Shirt",
                categorie_nom="Hauts",
                couleur_nom="Blanc",
                style_nom="Décontracté",
            ),
            make_article(
                id=3,
                nom="Hoodie Molleton Noir",
                prix=110.0,
                type_nom="Sweat",
                categorie_nom="Hauts",
                couleur_nom="Noir",
                style_nom="Sportswear",
            ),
            make_article(
                id=4,
                nom="T-Shirt Sport Respirant Gris",
                prix=55.0,
                type_nom="T-Shirt",
                categorie_nom="Hauts",
                couleur_nom="Gris",
                style_nom="Sportswear",
            ),
            # Bas Homme
            make_article(
                id=10,
                nom="Pantalon Chino Beige",
                prix=110.0,
                type_nom="Pantalon",
                categorie_nom="Bas",
                couleur_nom="Beige",
                style_nom="Chic",
            ),
            make_article(
                id=11,
                nom="Jean Slim Bleu",
                prix=99.0,
                type_nom="Jean",
                categorie_nom="Bas",
                couleur_nom="Bleu",
                style_nom="Décontracté",
            ),
            make_article(
                id=12,
                nom="Jogging Running Noir",
                prix=75.0,
                type_nom="Jogging",
                categorie_nom="Bas",
                couleur_nom="Noir",
                style_nom="Sportswear",
            ),
            make_article(
                id=13,
                nom="Short d'Été Lin Beige",
                prix=65.0,
                type_nom="Short",
                categorie_nom="Bas",
                couleur_nom="Beige",
                style_nom="Décontracté",
            ),
            # Chaussures Homme
            make_article(
                id=20,
                nom="Mocassins Cuir Marron",
                prix=120.0,
                type_nom="Chaussures de ville",
                categorie_nom="Chaussures",
                couleur_nom="Marron",
                style_nom="Chic",
            ),
            make_article(
                id=21,
                nom="Baskets Blanches Minimalistes",
                prix=115.0,
                type_nom="Baskets",
                categorie_nom="Chaussures",
                couleur_nom="Blanc",
                style_nom="Décontracté",
            ),
            make_article(
                id=22,
                nom="Baskets Running Grises",
                prix=105.0,
                type_nom="Baskets",
                categorie_nom="Chaussures",
                couleur_nom="Gris",
                style_nom="Sportswear",
            ),
            make_article(
                id=23,
                nom="Bottes Hiver Cuir Noir",
                prix=180.0,
                type_nom="Bottes",
                categorie_nom="Chaussures",
                couleur_nom="Noir",
                style_nom="Classique",
            ),
            # Vestes / Manteaux Homme
            make_article(
                id=30,
                nom="Veste Blazer Bleu Marine",
                prix=160.0,
                type_nom="Veste",
                categorie_nom="Vestes",
                couleur_nom="Bleu Marine",
                style_nom="Chic",
            ),
            make_article(
                id=31,
                nom="Manteau Laine Hiver Noir",
                prix=290.0,
                type_nom="Manteau",
                categorie_nom="Vestes",
                couleur_nom="Noir",
                style_nom="Classique",
            ),
            # Articles Femme & Mixte
            make_article(
                id=40,
                nom="Robe Midi Lin Beige",
                prix=135.0,
                type_nom="Robe",
                categorie_nom="Robes",
                couleur_nom="Beige",
                style_nom="Chic",
                genre=GenreCible.FEMME,
                vendeur="Mabrouk Femme",
                lien_achat="https://mabrouk.tn/produit/robe-midi-lin-beige/",
            ),
            make_article(
                id=41,
                nom="Baskets Femme Blanches",
                prix=95.0,
                type_nom="Baskets",
                categorie_nom="Chaussures",
                couleur_nom="Blanc",
                style_nom="Décontracté",
                genre=GenreCible.FEMME,
                vendeur="Mabrouk Femme",
                lien_achat="https://mabrouk.tn/produit/baskets-femme-blanches/",
            ),
            make_article(
                id=42,
                nom="Chemise Homme Oversize Mixte",
                prix=80.0,
                type_nom="Chemise",
                categorie_nom="Hauts",
                couleur_nom="Blanc",
                style_nom="Décontracté",
                genre=GenreCible.MIXTE,
                vendeur="Mabrouk Femme",
                lien_achat="https://mabrouk.tn/produit/chemise-oversize/",
            ),
        ]

    def test_strict_criteria_work_elegant_summer_avoid_black_budget(self):
        catalog = self._build_catalog()
        criteres = ShopperCriteria(
            style="Élégant",
            occasion="TRAVAIL",
            season="Été",
            colors=["Bleu Marine"],
            avoided_colors=["Noir"],
            requested_types=["chemise"],
            budget=350.0,
        )
        grouped = filter_and_group_articles(catalog, criteres, user_gender="HOMME")

        # Aucun article noir ne doit passer
        for items in grouped.values():
            for it in items:
                self.assertNotEqual(it.couleur.nom.lower(), "noir")

        # Aucune pièce d'hiver (manteau laine, bottes) ne doit passer en été
        all_names = [it.nom.lower() for items in grouped.values() for it in items]
        self.assertFalse(any("manteau" in n or "bottes" in n for n in all_names))

        # Hauts doit ne contenir que des chemises (pièce demandée)
        self.assertEqual([it.id for it in grouped["hauts"]], [1])

        outfits = ShopperOutfitService.compose_outfits(grouped, criteres, max_outfits=3)
        self.assertGreaterEqual(len(outfits), 1)
        top = outfits[0]
        self.assertLessEqual(top.prixTotal, 350.0)
        self.assertTrue(top.respecteBudget)
        # Meilleure tenue Travail + Élégant : Chemise Bleu Marine (1) + Chino Beige (10) + Mocassins (20)
        self.assertEqual({a.id for a in top.articles}, {1, 10, 20})

    def test_winter_blocks_summer_shorts_and_scoring_prefers_sport(self):
        catalog = self._build_catalog()
        criteres = ShopperCriteria(
            style="Sportif",
            occasion="SPORT",
            season="Hiver",
            budget=260.0,
        )
        grouped = filter_and_group_articles(catalog, criteres, user_gender="HOMME")
        bas_ids = [it.id for it in grouped["bas"]]
        self.assertNotIn(13, bas_ids, "Le short d'été doit être bloqué en hiver")

        outfits = ShopperOutfitService.compose_outfits(grouped, criteres, max_outfits=2)
        self.assertGreaterEqual(len(outfits), 1)
        # La tenue la mieux classée pour SPORT + Sportif doit privilégier Jogging + Baskets Running
        best_ids = {a.id for a in outfits[0].articles}
        self.assertIn(12, best_ids)
        self.assertIn(22, best_ids)

    def test_requested_veste_is_included_and_missing_requested_piece_returns_empty(self):
        catalog = self._build_catalog()
        criteres_veste = ShopperCriteria(
            style="Chic",
            occasion="EVENEMENT",
            requested_types=["chemise", "veste"],
            budget=500.0,
        )
        grouped = filter_and_group_articles(catalog, criteres_veste, user_gender="HOMME")
        outfits = ShopperOutfitService.compose_outfits(grouped, criteres_veste, max_outfits=2)
        self.assertGreaterEqual(len(outfits), 1)
        for outfit in outfits:
            self.assertLessEqual(outfit.prixTotal, 500.0)
            types = {a.typeVetementNom.lower() for a in outfit.articles}
            self.assertIn("veste", types)
            self.assertIn("chemise", types)

        # Demander une pièce absente du catalogue (ex: jupe pour Homme) => [] (jamais de tenue inventée)
        criteres_missing = ShopperCriteria(
            style="Chic",
            occasion="SORTIE",
            requested_types=["jupe"],
            budget=500.0,
        )
        grouped_missing = filter_and_group_articles(catalog, criteres_missing, user_gender="HOMME")
        outfits_missing = ShopperOutfitService.compose_outfits(grouped_missing, criteres_missing)
        self.assertEqual(outfits_missing, [])

    def test_femme_gender_no_unisexe_crash_and_robe_concordance(self):
        catalog = self._build_catalog()
        criteres = ShopperCriteria(
            style="Élégant",
            occasion="SORTIE",
            requested_types=["robe"],
            budget=300.0,
        )
        # Doit filtrer proprement sans AttributeError (GenreCible.MIXTE)
        grouped = filter_and_group_articles(catalog, criteres, user_gender="FEMME")
        self.assertEqual([it.id for it in grouped["robes"]], [40])
        self.assertEqual(grouped["hauts"], [])  # Chemise "Homme" MIXTE exclue pour FEMME

        outfits = ShopperOutfitService.compose_outfits(grouped, criteres, max_outfits=2)
        self.assertEqual(len(outfits), 1)
        self.assertIn("Robe", outfits[0].styleConcordance)
        self.assertNotIn("Tee & Pantalon", outfits[0].styleConcordance)

    def test_strict_deduplication_id_url_identity_and_session_exclusions(self):
        dup_items = [
            make_article(
                id=101,
                nom="T-Shirt Essentiel Blanc",
                prix=49.0,
                type_nom="T-Shirt",
                categorie_nom="Hauts",
                couleur_nom="Blanc",
                lien_achat="https://www.exist.com.tn/t-shirts/101-tshirt.html#/1030-taille-m/7001-couleur-blanc",
            ),
            # Même produit avec taille différente + UTM -> doit être dédupliqué par URL normalisée
            make_article(
                id=102,
                nom="T-Shirt Essentiel Blanc XL",
                prix=49.0,
                type_nom="T-Shirt",
                categorie_nom="Hauts",
                couleur_nom="Blanc",
                lien_achat="https://www.exist.com.tn/t-shirts/101-tshirt.html?utm_source=app#/1032-taille-xl/7001-couleur-blanc",
            ),
            # Même vendeur + nom + couleur sous une autre URL -> doit être dédupliqué par identité
            make_article(
                id=103,
                nom="T-Shirt Essentiel Blanc",
                prix=49.0,
                type_nom="T-Shirt",
                categorie_nom="Hauts",
                couleur_nom="Blanc",
                lien_achat="https://www.exist.com.tn/t-shirts/103-autre-fiche.html",
            ),
            # Produit distinct
            make_article(
                id=104,
                nom="Polo Piqué Bleu",
                prix=65.0,
                type_nom="Polo",
                categorie_nom="Hauts",
                couleur_nom="Bleu",
                lien_achat="https://www.exist.com.tn/polos/104-polo-bleu.html",
            ),
            # Produit avec URL invalide (catégorie) -> doit être exclu
            make_article(
                id=105,
                nom="T-Shirt Lien Catégorie",
                prix=40.0,
                type_nom="T-Shirt",
                categorie_nom="Hauts",
                couleur_nom="Blanc",
                lien_achat="https://www.pullandbear.com/tn/homme/tshirts-c29013.html",
            ),
        ]

        criteres = ShopperCriteria(style="Décontracté", occasion="QUOTIDIEN", budget=250.0)
        grouped = filter_and_group_articles(dup_items, criteres, user_gender="HOMME")
        self.assertEqual([it.id for it in grouped["hauts"]], [101, 104])

        # Exclure par URL avec une autre taille/UTM doit exclure l'article 101 en session
        grouped_session = filter_and_group_articles(
            dup_items,
            criteres,
            user_gender="HOMME",
            excluded_urls=[
                "https://www.exist.com.tn/t-shirts/101-tshirt.html?fbclid=xyz#/1031-taille-l/7001-couleur-blanc"
            ],
        )
        self.assertEqual([it.id for it in grouped_session["hauts"]], [104])

    def test_single_item_shopper_returns_only_requested_type_respecting_genre_style_budget_and_dedup(self):
        items = [
            make_article(
                id=501,
                nom="Pull Maille Fine Bleu Marine",
                prix=95.0,
                type_nom="Pull",
                categorie_nom="Hauts",
                couleur_nom="Bleu Marine",
                style_nom="Classique",
                genre=GenreCible.MIXTE,
                vendeur="Exist Tunisie Homme",
                lien_achat="https://www.exist.com.tn/pulls/501-pull-marine.html#/1030-taille-m/7001-couleur-bleu",
            ),
            # Doublon même produit taille différente + UTM -> doit être dédupliqué
            make_article(
                id=502,
                nom="Pull Maille Fine Bleu Marine XL",
                prix=95.0,
                type_nom="Pull",
                categorie_nom="Hauts",
                couleur_nom="Bleu Marine",
                style_nom="Classique",
                genre=GenreCible.MIXTE,
                vendeur="Exist Tunisie Homme",
                lien_achat="https://www.exist.com.tn/pulls/501-pull-marine.html?utm_source=fb#/1032-taille-xl/7001-couleur-bleu",
            ),
            make_article(
                id=503,
                nom="Pull Col Rond Coton Gris",
                prix=120.0,
                type_nom="Pull",
                categorie_nom="Hauts",
                couleur_nom="Gris",
                style_nom="Décontracté",
                genre=GenreCible.MIXTE,
                vendeur="Exist Tunisie Homme",
                lien_achat="https://www.exist.com.tn/pulls/503-pull-gris.html",
            ),
            # Hors budget (220 > 150) -> exclu
            make_article(
                id=504,
                nom="Pull Cachemire Luxe Noir",
                prix=220.0,
                type_nom="Pull",
                categorie_nom="Hauts",
                couleur_nom="Noir",
                style_nom="Chic",
                genre=GenreCible.MIXTE,
                vendeur="Exist Tunisie Homme",
                lien_achat="https://www.exist.com.tn/pulls/504-pull-luxe.html",
            ),
            # Style incompatible (Sportswear vs Classique) -> exclu
            make_article(
                id=505,
                nom="Pull Training Technique",
                prix=85.0,
                type_nom="Pull",
                categorie_nom="Hauts",
                couleur_nom="Gris",
                style_nom="Sportswear",
                genre=GenreCible.MIXTE,
                vendeur="Exist Tunisie Homme",
                lien_achat="https://www.exist.com.tn/pulls/505-pull-sport.html",
            ),
            # Boutique Femme -> exclu pour HOMME, inclus pour FEMME
            make_article(
                id=506,
                nom="Pull Maille Femme Beige",
                prix=110.0,
                type_nom="Pull",
                categorie_nom="Hauts",
                couleur_nom="Beige",
                style_nom="Classique",
                genre=GenreCible.FEMME,
                vendeur="Mabrouk Femme",
                lien_achat="https://mabrouk.tn/produit/pull-maille-femme-beige/",
            ),
            # Autre type (Pantalon, Baskets, Veste en Jean) -> JAMAIS retourné quand on demande "Pull"
            make_article(
                id=507,
                nom="Pantalon Chino Beige",
                prix=90.0,
                type_nom="Pantalon",
                categorie_nom="Bas",
                couleur_nom="Beige",
                style_nom="Classique",
                genre=GenreCible.MIXTE,
                vendeur="Exist Tunisie Homme",
                lien_achat="https://www.exist.com.tn/pantalons/507-chino.html",
            ),
            make_article(
                id=508,
                nom="Veste en Jean Brut",
                prix=130.0,
                type_nom="Veste",
                categorie_nom="Vestes",
                couleur_nom="Bleu",
                style_nom="Décontracté",
                genre=GenreCible.MIXTE,
                vendeur="Exist Tunisie Homme",
                lien_achat="https://www.exist.com.tn/vestes/508-veste-jean.html",
            ),
            make_article(
                id=509,
                nom="Jean Slim Bleu",
                prix=105.0,
                type_nom="Jean",
                categorie_nom="Bas",
                couleur_nom="Bleu",
                style_nom="Décontracté",
                genre=GenreCible.MIXTE,
                vendeur="Exist Tunisie Homme",
                lien_achat="https://www.exist.com.tn/jeans/509-jean-slim.html",
            ),
        ]

        # 1. Recherche HOMME : Pull + Classique + budget 150 TND
        criteres_pull = ShopperCriteria(style="Classique", budget=150.0, requested_types=["Pull"])
        res_homme = search_individual_articles(items, "Pull", criteres_pull, user_gender="HOMME")
        ids_homme = [a.id for a, _, _ in res_homme]
        self.assertEqual(ids_homme, [501, 503])  # 501 (Classique exact) en premier, 502 dédupliqué, 504 hors budget, 505 Sportswear exclu, 506 Femme exclu, 507/508/509 autres types exclus
        for art, score, _ in res_homme:
            self.assertEqual(art.type_vetement.nom, "Pull")
            self.assertLessEqual(art.prix, 150.0)
            self.assertGreaterEqual(score, 55)

        # 2. Recherche FEMME : Pull + Classique + budget 150 TND
        res_femme = search_individual_articles(items, "Pull", criteres_pull, user_gender="FEMME")
        self.assertEqual([a.id for a, _, _ in res_femme], [506])

        # 3. Anti-collision inter-catégories : "Jean" ne renvoie PAS "Veste en Jean"
        criteres_jean = ShopperCriteria(style="Décontracté", budget=150.0, requested_types=["Jean"])
        res_jean = search_individual_articles(items, "Jean", criteres_jean, user_gender="HOMME")
        self.assertEqual([a.id for a, _, _ in res_jean], [509])

        # 4. Exclusions de session : exclure 501 ne renvoie plus 501 ni son doublon 502
        res_next = search_individual_articles(
            items,
            "Pull",
            criteres_pull,
            user_gender="HOMME",
            excluded_product_ids=[501],
            excluded_urls=["https://www.exist.com.tn/pulls/501-pull-marine.html#/1030-taille-m/7001-couleur-bleu"],
        )
        self.assertEqual([a.id for a, _, _ in res_next], [503])

    def test_orchestrator_scrapes_live_on_demand_without_reading_stale_db_catalog(self):
        # Fiches retournées en direct par search_live_products (AUCUNE lecture d'ArticleCatalogue en BDD)
        live_scraped_raw = [
            {
                "nom": "Pull Maille Fine Bleu Marine",
                "description": "Pull classique col rond coton bleu marine",
                "imageUrl": "https://www.exist.com.tn/img/pull1.jpg",
                "lienAchat": "https://www.exist.com.tn/pulls/9001-pull-marine.html#/1030-taille-m/7001-couleur-bleu_marine",
                "prix": 95.0,
                "vendeur": "Exist Tunisie Homme",
                "taillesDisponibles": "M, L, XL",
                "couleur_brute": "Bleu Marine",
                "categorie_brute": "Pulls",
                "verified_product_page": True,
            },
            # Doublon taille différente -> doit être dédupliqué
            {
                "nom": "Pull Maille Fine Bleu Marine",
                "description": "Pull classique col rond coton bleu marine",
                "imageUrl": "https://www.exist.com.tn/img/pull1.jpg",
                "lienAchat": "https://www.exist.com.tn/pulls/9001-pull-marine.html?utm_source=ig#/1032-taille-xl/7001-couleur-bleu_marine",
                "prix": 95.0,
                "vendeur": "Exist Tunisie Homme",
                "taillesDisponibles": "XL",
                "couleur_brute": "Bleu Marine",
                "categorie_brute": "Pulls",
                "verified_product_page": True,
            },
            # Autre type (Pantalon) -> exclu car on demande "Pull"
            {
                "nom": "Pantalon Chino Beige",
                "description": "Pantalon chino coupe droite",
                "imageUrl": "https://www.exist.com.tn/img/chino.jpg",
                "lienAchat": "https://www.exist.com.tn/pantalons/9002-chino.html",
                "prix": 90.0,
                "vendeur": "Exist Tunisie Homme",
                "taillesDisponibles": "40, 42",
                "couleur_brute": "Beige",
                "categorie_brute": "Bas",
                "verified_product_page": True,
            },
            # Hors budget (220 > 150) -> exclu
            {
                "nom": "Pull Cachemire Luxe",
                "description": "Pull haut de gamme gris",
                "imageUrl": "https://www.exist.com.tn/img/pull_luxe.jpg",
                "lienAchat": "https://www.exist.com.tn/pulls/9003-pull-luxe.html",
                "prix": 220.0,
                "vendeur": "Exist Tunisie Homme",
                "taillesDisponibles": "M, L",
                "couleur_brute": "Gris",
                "categorie_brute": "Pulls",
                "verified_product_page": True,
            },
            # Couleur évitée (Noir) -> exclu
            {
                "nom": "Pull Col Roulé Noir",
                "description": "Pull noir chaud",
                "imageUrl": "https://www.exist.com.tn/img/pull_noir.jpg",
                "lienAchat": "https://www.exist.com.tn/pulls/9004-pull-noir.html",
                "prix": 110.0,
                "vendeur": "Exist Tunisie Homme",
                "taillesDisponibles": "M, L",
                "couleur_brute": "Noir",
                "categorie_brute": "Pulls",
                "verified_product_page": True,
            },
            # Deuxième pull valide
            {
                "nom": "Pull Coton Gris Chiné",
                "description": "Pull classique gris chiné",
                "imageUrl": "https://www.exist.com.tn/img/pull_gris.jpg",
                "lienAchat": "https://www.exist.com.tn/pulls/9005-pull-gris.html",
                "prix": 115.0,
                "vendeur": "Exist Tunisie Homme",
                "taillesDisponibles": "S, M, L",
                "couleur_brute": "Gris",
                "categorie_brute": "Pulls",
                "verified_product_page": True,
            },
        ]

        orchestrator = ShopperOrchestrator()
        orchestrator.llm_manager = MagicMock()
        orchestrator.llm_manager.interpret = AsyncMock(
            return_value=ShopperCriteria(
                style="Classique",
                occasion="QUOTIDIEN",
                requested_types=["Pull"],
                budget=150.0,
            )
        )

        fake_scraper = MagicMock()
        fake_scraper.store_name = "Exist Tunisie Homme"
        fake_scraper.base_url = "https://www.exist.com.tn"
        fake_scraper.search_live_products = AsyncMock(return_value=live_scraped_raw)
        orchestrator.scraper_service = MagicMock()
        orchestrator.scraper_service.scrapers = [fake_scraper]

        # Référentiels uniquement (aucune table ArticleCatalogue requêtée)
        types_ref = [
            SimpleNamespace(id=4, nom="Pull", genreCible=GenreCible.MIXTE, categorie=SimpleNamespace(nom="Haut")),
            SimpleNamespace(id=7, nom="Pantalon", genreCible=GenreCible.MIXTE, categorie=SimpleNamespace(nom="Bas")),
        ]
        colors_ref = [
            SimpleNamespace(id=1, nom="Noir"),
            SimpleNamespace(id=3, nom="Gris"),
            SimpleNamespace(id=4, nom="Bleu Marine"),
            SimpleNamespace(id=6, nom="Beige"),
        ]
        styles_ref = [
            SimpleNamespace(id=1, libelle="Décontracté"),
            SimpleNamespace(id=2, libelle="Classique"),
            SimpleNamespace(id=5, libelle="Chic"),
        ]

        def fake_query(model):
            name = getattr(model, "__name__", "")
            if name == "ArticleCatalogue":
                raise AssertionError("Le mode scraping live ne doit pas dépendre d'ArticleCatalogue !")
            q = MagicMock()
            q.filter.return_value = q
            if name == "StyleVestimentaire":
                q.first.return_value = styles_ref[1]
                q.all.return_value = styles_ref
            elif name == "TypeVetement":
                q.all.return_value = types_ref
            elif name == "Couleur":
                q.all.return_value = colors_ref
            else:
                q.all.return_value = []
            return q

        fake_db = MagicMock()
        fake_db.query.side_effect = fake_query

        res = asyncio.run(
            orchestrator.process_request(
                prompt="",
                db=fake_db,
                forced_genre="HOMME",
                forced_budget=150.0,
                type_vetement="Pull",
                style_id=2,
                colors=["Bleu Marine"],
                avoided_colors=["Noir"],
            )
        )

        # Le scraper live a bien été appelé immédiatement avec "Pull"
        fake_scraper.search_live_products.assert_awaited_once()
        self.assertEqual(res.tenues, [])
        self.assertEqual(res.nbTenuesTrouvees, 0)
        self.assertEqual(res.nbArticlesTrouves, 2)
        self.assertEqual(res.typeDemande, "Pull")
        self.assertEqual(res.styleDemande, "Classique")
        # Bleu Marine (couleur préférée) classé en premier, Gris en second ; Noir, Pantalon, Hors budget et doublon exclus
        self.assertEqual([a.nom for a in res.articles], ["Pull Maille Fine Bleu Marine", "Pull Coton Gris Chiné"])
        for art in res.articles:
            self.assertEqual(art.typeVetementNom, "Pull")
            self.assertLessEqual(art.prix, 150.0)
            self.assertTrue(is_valid_product_url(art.lienAchat)[0])

    def test_extract_requested_and_excluded_mentions(self):
        req = extract_requested_type_mentions("Je veux une chemise et une veste sans jogging ni short")
        excl = extract_excluded_type_mentions("Je veux une chemise et une veste sans jogging ni short")
        self.assertIn("chemise", req)
        self.assertIn("veste", req)
        self.assertIn("jogging", excl)
        self.assertIn("short", excl)
        self.assertNotIn("jogging", req)

    def test_multiple_outfits_have_no_repeated_products_and_dynamic_harmony(self):
        catalog = self._build_catalog()
        criteres = ShopperCriteria(
            style="Casual",
            occasion="QUOTIDIEN",
            budget=350.0,
        )
        grouped = filter_and_group_articles(catalog, criteres, user_gender="HOMME")
        outfits = ShopperOutfitService.compose_outfits(grouped, criteres, max_outfits=3)
        self.assertGreaterEqual(len(outfits), 2)

        seen_ids = set()
        seen_urls = set()
        for outfit in outfits:
            for art in outfit.articles:
                self.assertNotIn(art.id, seen_ids, "Doublon d'ID entre deux tenues proposées")
                norm_u = normalize_product_url(art.lienAchat)
                self.assertNotIn(norm_u, seen_urls, "Doublon d'URL entre deux tenues proposées")
                seen_ids.add(art.id)
                seen_urls.add(norm_u)

        # Palette de 3 couleurs vives distinctes => harmonie "Contrastée" (non codée en dur "Excellente")
        clashing_items = [
            make_article(id=301, nom="T-Shirt Rouge", prix=50.0, type_nom="T-Shirt", categorie_nom="Hauts", couleur_nom="Rouge"),
            make_article(id=302, nom="Pantalon Vert", prix=80.0, type_nom="Pantalon", categorie_nom="Bas", couleur_nom="Vert"),
            make_article(id=303, nom="Baskets Jaune", prix=90.0, type_nom="Baskets", categorie_nom="Chaussures", couleur_nom="Jaune"),
        ]
        _, _, harmony_clash, _ = ShopperOutfitService._calculate_score(
            clashing_items, 220.0, criteres, 300.0, None
        )
        self.assertEqual(harmony_clash, "Contrastée")


if __name__ == "__main__":
    unittest.main(verbosity=2)
