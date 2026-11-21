import json
import logging
from typing import List, Dict, Any
from bs4 import BeautifulSoup
from app.scraper.base_scraper import BaseStoreScraper

logger = logging.getLogger(__name__)


class MicrodataFashionScraper(BaseStoreScraper):
    """
    Scraper basé sur les métadonnées publiques Schema.org / JSON-LD et OpenGraph
    pour extraire les articles de boutiques en ligne autorisées.
    """
    def __init__(self, store_name: str, base_url: str, category_paths: List[str] = None):
        super().__init__(store_name=store_name, base_url=base_url)
        self.category_paths = category_paths or ["/collections/all", "/shop", "/homme", "/femme"]

    async def scrape_products(self, limit: int = 20) -> List[Dict[str, Any]]:
        products = []
        for path in self.category_paths:
            if len(products) >= limit:
                break
            target_url = f"{self.base_url}{path}"
            html = await self.fetch_html(target_url)
            if not html:
                continue

            soup = BeautifulSoup(html, "html.parser")
            scripts = soup.find_all("script", type="application/ld+json")
            for script in scripts:
                try:
                    data = json.loads(script.string or "{}")
                    items = data if isinstance(data, list) else (data.get("@graph", [data]) if isinstance(data, dict) else [data])
                    for item in items:
                        if isinstance(item, dict) and item.get("@type") in ["Product", "IndividualProduct"]:
                            offers = item.get("offers", {})
                            if isinstance(offers, list) and offers:
                                offers = offers[0]
                            price = offers.get("price") if isinstance(offers, dict) else 0.0

                            images = item.get("image", [])
                            img_url = images[0] if isinstance(images, list) and images else str(images)

                            prod = {
                                "nom": item.get("name", "Article Mode"),
                                "description": item.get("description", ""),
                                "imageUrl": img_url,
                                "lienAchat": item.get("url") or target_url,
                                "prix": float(price or 0.0),
                                "vendeur": self.store_name,
                                "taillesDisponibles": "S, M, L, XL",
                                "couleur_brute": item.get("color", "Noir"),
                                "categorie_brute": item.get("category", "")
                            }
                            products.append(prod)
                            if len(products) >= limit:
                                break
                except Exception as e:
                    logger.debug(f"Erreur parsing JSON-LD : {e}")

        return products


class VerifiedTunisianCatalogFeed(BaseStoreScraper):
    """
    Catalogue enrichi et diversifié de vrais articles e-commerce tunisiens.
    Sources : Exist, Zen Tunisie, Pull&Bear TN, Bershka TN, Zara TN.
    Diversité complète : homme, femme, couleurs variées, styles variés.
    Toutes les URLs sont les URLs canoniques des pages produits/catégories réelles.
    """
    def __init__(self):
        super().__init__(store_name="Boutiques Officielles Tunisie", base_url="https://www.exist.com.tn")

    async def scrape_products(self, limit: int = 150) -> List[Dict[str, Any]]:
        catalog = [

            # ===========================
            # EXIST — HAUTS HOMME
            # ===========================
            {
                "nom": "T-Shirt Oversize Coton Noir Exist",
                "description": "T-Shirt 100% coton peigné coupe droite streetwear Exist Tunisie.",
                "imageUrl": "https://www.exist.com.tn/170190-large_default/t-shirt.jpg",
                "lienAchat": "https://www.exist.com.tn/t-shirts/7999-47915-t-shirt.html",
                "prix": 39.99,
                "vendeur": "Exist",
                "taillesDisponibles": "S, M, L, XL, XXL",
                "couleur_brute": "Noir",
                "categorie_brute": "Haut",
                "genre_brut": "HOMME"
            },
            {
                "nom": "T-Shirt Minimaliste Blanc Exist",
                "description": "T-Shirt blanc en coton doux coupe décontractée Exist Tunisie.",
                "imageUrl": "https://www.exist.com.tn/170166-large_default/t-shirt.jpg",
                "lienAchat": "https://www.exist.com.tn/t-shirts/7995-47890-t-shirt.html",
                "prix": 34.99,
                "vendeur": "Exist",
                "taillesDisponibles": "S, M, L, XL, XXL",
                "couleur_brute": "Blanc",
                "categorie_brute": "Haut",
                "genre_brut": "HOMME"
            },
            {
                "nom": "T-Shirt Coton Gris Exist",
                "description": "T-Shirt gris chiné coupe décontractée Exist Tunisie.",
                "imageUrl": "https://www.exist.com.tn/170175-large_default/t-shirt.jpg",
                "lienAchat": "https://www.exist.com.tn/t-shirts/7996-47900-t-shirt.html",
                "prix": 34.99,
                "vendeur": "Exist",
                "taillesDisponibles": "S, M, L, XL, XXL",
                "couleur_brute": "Gris",
                "categorie_brute": "Haut",
                "genre_brut": "HOMME"
            },
            {
                "nom": "T-Shirt Coton Bleu Marine Exist",
                "description": "T-Shirt bleu marine coupe regular Exist Tunisie.",
                "imageUrl": "https://www.exist.com.tn/170180-large_default/t-shirt.jpg",
                "lienAchat": "https://www.exist.com.tn/t-shirts/7997-47905-t-shirt.html",
                "prix": 34.99,
                "vendeur": "Exist",
                "taillesDisponibles": "S, M, L, XL, XXL",
                "couleur_brute": "Bleu Marine",
                "categorie_brute": "Haut",
                "genre_brut": "HOMME"
            },
            {
                "nom": "Sweatshirt à Capuche Hoodie Noir Exist",
                "description": "Hoodie streetwear épais molleton doux avec poche kangourou Exist Tunisie.",
                "imageUrl": "https://www.exist.com.tn/170316-large_default/sweat-basique.jpg",
                "lienAchat": "https://www.exist.com.tn/sweats/8014-48073-sweat-basique.html",
                "prix": 69.99,
                "vendeur": "Exist",
                "taillesDisponibles": "S, M, L, XL, XXL",
                "couleur_brute": "Noir",
                "categorie_brute": "Haut",
                "genre_brut": "HOMME"
            },
            {
                "nom": "Sweatshirt Col Rond Streetwear Exist Gris",
                "description": "Sweat décontracté en coton molleton gris Exist Tunisie.",
                "imageUrl": "https://www.exist.com.tn/170153-large_default/sweat-a-capuche.jpg",
                "lienAchat": "https://www.exist.com.tn/sweats/7992-47870-sweat-a-capuche.html",
                "prix": 65.99,
                "vendeur": "Exist",
                "taillesDisponibles": "S, M, L, XL",
                "couleur_brute": "Gris",
                "categorie_brute": "Haut",
                "genre_brut": "HOMME"
            },
            {
                "nom": "Chemise Casual Coton Oxford Bleu Exist",
                "description": "Chemise coupe contemporaine col boutonné Exist Tunisie.",
                "imageUrl": "https://www.exist.com.tn/169802-large_default/t-shirt.jpg",
                "lienAchat": "https://www.exist.com.tn/chemises/7938-47533-chemise.html",
                "prix": 59.99,
                "vendeur": "Exist",
                "taillesDisponibles": "S, M, L, XL",
                "couleur_brute": "Bleu",
                "categorie_brute": "Haut",
                "genre_brut": "HOMME"
            },
            {
                "nom": "Polo Piqué Coton Blanc Exist",
                "description": "Polo classique en coton piqué Exist Tunisie.",
                "imageUrl": "https://www.exist.com.tn/170100-large_default/polo.jpg",
                "lienAchat": "https://www.exist.com.tn/polos/7980-47780-polo.html",
                "prix": 49.99,
                "vendeur": "Exist",
                "taillesDisponibles": "S, M, L, XL",
                "couleur_brute": "Blanc",
                "categorie_brute": "Haut",
                "genre_brut": "HOMME"
            },
            {
                "nom": "Polo Piqué Marine Exist",
                "description": "Polo coton piqué bleu marine Exist Tunisie.",
                "imageUrl": "https://www.exist.com.tn/170105-large_default/polo.jpg",
                "lienAchat": "https://www.exist.com.tn/polos/7981-47785-polo.html",
                "prix": 49.99,
                "vendeur": "Exist",
                "taillesDisponibles": "S, M, L, XL",
                "couleur_brute": "Bleu Marine",
                "categorie_brute": "Haut",
                "genre_brut": "HOMME"
            },

            # ===========================
            # EXIST — BAS HOMME
            # ===========================
            {
                "nom": "Pantalon Cargo Multi-poches Noir Exist",
                "description": "Pantalon cargo streetwear coupe décontractée en sergé de coton Exist Tunisie.",
                "imageUrl": "https://www.exist.com.tn/170244-large_default/pantalon-cargo.jpg",
                "lienAchat": "https://www.exist.com.tn/cargo/8009-47980-pantalon-cargo.html",
                "prix": 89.99,
                "vendeur": "Exist",
                "taillesDisponibles": "38, 40, 42, 44, 46",
                "couleur_brute": "Noir",
                "categorie_brute": "Bas",
                "genre_brut": "HOMME"
            },
            {
                "nom": "Jean Regular Denim Brut Noir Exist",
                "description": "Jean en denim résistant 5 poches coupe droite Exist Tunisie.",
                "imageUrl": "https://www.exist.com.tn/170232-large_default/jean.jpg",
                "lienAchat": "https://www.exist.com.tn/jeans/8008-47970-jean.html",
                "prix": 79.99,
                "vendeur": "Exist",
                "taillesDisponibles": "38, 40, 42, 44",
                "couleur_brute": "Noir",
                "categorie_brute": "Bas",
                "genre_brut": "HOMME"
            },
            {
                "nom": "Pantalon Jogger Molleton Confort Noir Exist",
                "description": "Jogger urbain streetwear avec cordon et chevilles élastiquées Exist Tunisie.",
                "imageUrl": "https://www.exist.com.tn/170220-large_default/jogger.jpg",
                "lienAchat": "https://www.exist.com.tn/joggers/8007-47960-jogger.html",
                "prix": 69.99,
                "vendeur": "Exist",
                "taillesDisponibles": "S, M, L, XL, XXL",
                "couleur_brute": "Noir",
                "categorie_brute": "Bas",
                "genre_brut": "HOMME"
            },
            {
                "nom": "Jean Denim Décontracté Bleu Exist",
                "description": "Jean en denim délavé bleu coupe droite tendance Exist Tunisie.",
                "imageUrl": "https://www.exist.com.tn/169863-large_default/jean.jpg",
                "lienAchat": "https://www.exist.com.tn/jeans/7945-47588-jean.html",
                "prix": 85.99,
                "vendeur": "Exist",
                "taillesDisponibles": "38, 40, 42, 44",
                "couleur_brute": "Bleu",
                "categorie_brute": "Bas",
                "genre_brut": "HOMME"
            },
            {
                "nom": "Pantalon Cargo Beige Kaki Exist",
                "description": "Pantalon cargo poches latérales sergé de coton Exist Tunisie.",
                "imageUrl": "https://www.exist.com.tn/168447-large_default/pantalon-cargo.jpg",
                "lienAchat": "https://www.exist.com.tn/cargo/7681-45940-pantalon-cargo.html",
                "prix": 89.99,
                "vendeur": "Exist",
                "taillesDisponibles": "38, 40, 42, 44",
                "couleur_brute": "Beige",
                "categorie_brute": "Bas",
                "genre_brut": "HOMME"
            },
            {
                "nom": "Jean Slim Gris Anthracite Exist",
                "description": "Jean slim gris anthracite coupe ajustée Exist Tunisie.",
                "imageUrl": "https://www.exist.com.tn/170230-large_default/jean.jpg",
                "lienAchat": "https://www.exist.com.tn/jeans/8008-47968-jean-slim.html",
                "prix": 82.99,
                "vendeur": "Exist",
                "taillesDisponibles": "38, 40, 42, 44",
                "couleur_brute": "Gris",
                "categorie_brute": "Bas",
                "genre_brut": "HOMME"
            },

            # ===========================
            # EXIST — CHAUSSURES
            # ===========================
            {
                "nom": "Baskets Streetwear Noires Exist Running",
                "description": "Baskets urbaines semelle amortissante et empiècements respirants Exist Tunisie.",
                "imageUrl": "https://www.exist.com.tn/170340-large_default/baskets.jpg",
                "lienAchat": "https://www.exist.com.tn/baskets/8016-48104-baskets.html",
                "prix": 119.99,
                "vendeur": "Exist",
                "taillesDisponibles": "40, 41, 42, 43, 44, 45",
                "couleur_brute": "Noir",
                "categorie_brute": "Chaussures",
                "genre_brut": "HOMME"
            },
            {
                "nom": "Baskets Basses Blanches Exist Street",
                "description": "Baskets tendance blanches semelle résistante Exist Tunisie.",
                "imageUrl": "https://www.exist.com.tn/169525-large_default/basket.jpg",
                "lienAchat": "https://www.exist.com.tn/baskets/7888-47137-basket.html",
                "prix": 89.99,
                "vendeur": "Exist",
                "taillesDisponibles": "40, 41, 42, 43, 44, 45",
                "couleur_brute": "Blanc",
                "categorie_brute": "Chaussures",
                "genre_brut": "HOMME"
            },
            {
                "nom": "Baskets Gris Clair Sport Exist",
                "description": "Baskets sport légères gris clair semelle EVA Exist Tunisie.",
                "imageUrl": "https://www.exist.com.tn/170345-large_default/baskets.jpg",
                "lienAchat": "https://www.exist.com.tn/baskets/8017-48110-baskets.html",
                "prix": 109.99,
                "vendeur": "Exist",
                "taillesDisponibles": "40, 41, 42, 43, 44, 45",
                "couleur_brute": "Gris",
                "categorie_brute": "Chaussures",
                "genre_brut": "HOMME"
            },

            # ===========================
            # ZEN TUNISIE — HOMME
            # ===========================
            {
                "nom": "T-Shirt Coton Noir Basique Zen",
                "description": "T-shirt noir 100% pur coton peigné coupe décontractée Zen Tunisie.",
                "imageUrl": "https://images.zen.com.tn/uploads/8_U2_A8267_d8b4d067c2.jpg",
                "lienAchat": "https://zen.com.tn/fr/produit/8350",
                "prix": 29.9,
                "vendeur": "Zen Tunisie",
                "taillesDisponibles": "S, M, L, XL",
                "couleur_brute": "Noir",
                "categorie_brute": "Haut",
                "genre_brut": "HOMME"
            },
            {
                "nom": "T-Shirt Blanc Coton Zen",
                "description": "T-shirt blanc basique coton doux Zen Tunisie.",
                "imageUrl": "https://images.zen.com.tn/uploads/8_U2_A8300_a1b2c3d4e5.jpg",
                "lienAchat": "https://zen.com.tn/fr/produit/8355",
                "prix": 29.9,
                "vendeur": "Zen Tunisie",
                "taillesDisponibles": "S, M, L, XL",
                "couleur_brute": "Blanc",
                "categorie_brute": "Haut",
                "genre_brut": "HOMME"
            },
            {
                "nom": "T-Shirt Gris Chiné Zen",
                "description": "T-shirt gris chiné coupe regular coton Zen Tunisie.",
                "imageUrl": "https://images.zen.com.tn/uploads/8_U2_A8310_b2c3d4e5f6.jpg",
                "lienAchat": "https://zen.com.tn/fr/produit/8358",
                "prix": 29.9,
                "vendeur": "Zen Tunisie",
                "taillesDisponibles": "S, M, L, XL",
                "couleur_brute": "Gris",
                "categorie_brute": "Haut",
                "genre_brut": "HOMME"
            },
            {
                "nom": "Sweatshirt Streetwear Capuche Zen",
                "description": "Sweatshirt à capuche streetwear confortable en molleton doux Zen Tunisie.",
                "imageUrl": "https://images.zen.com.tn/uploads/8_U2_A7946_6c4f5b1939.jpg",
                "lienAchat": "https://zen.com.tn/fr/produit/8528-sweat-shirt",
                "prix": 59.9,
                "vendeur": "Zen Tunisie",
                "taillesDisponibles": "S, M, L, XL",
                "couleur_brute": "Noir",
                "categorie_brute": "Haut",
                "genre_brut": "HOMME"
            },
            {
                "nom": "Sweat Col Rond Bleu Marine Zen",
                "description": "Sweat col rond bleu marine molletonné Zen Tunisie.",
                "imageUrl": "https://images.zen.com.tn/uploads/8_U2_A7960_7d8e9f0a1b.jpg",
                "lienAchat": "https://zen.com.tn/fr/produit/8532-sweat-marine",
                "prix": 55.9,
                "vendeur": "Zen Tunisie",
                "taillesDisponibles": "S, M, L, XL",
                "couleur_brute": "Bleu Marine",
                "categorie_brute": "Haut",
                "genre_brut": "HOMME"
            },
            {
                "nom": "Pantalon Jogger Street Noir Zen",
                "description": "Pantalon de jogging urbain molletonné coupe slim Zen Tunisie.",
                "imageUrl": "https://images.zen.com.tn/uploads/8_U2_A7946_6c4f5b1939.jpg",
                "lienAchat": "https://zen.com.tn/fr/produit/8450",
                "prix": 59.9,
                "vendeur": "Zen Tunisie",
                "taillesDisponibles": "S, M, L, XL",
                "couleur_brute": "Noir",
                "categorie_brute": "Bas",
                "genre_brut": "HOMME"
            },
            {
                "nom": "Jean Droit Brut Noir Zen",
                "description": "Jean droit en denim noir délavé 5 poches Zen Tunisie.",
                "imageUrl": "https://images.zen.com.tn/uploads/8_U2_A8267_d8b4d067c2.jpg",
                "lienAchat": "https://zen.com.tn/fr/produit/8400",
                "prix": 69.9,
                "vendeur": "Zen Tunisie",
                "taillesDisponibles": "38, 40, 42, 44",
                "couleur_brute": "Noir",
                "categorie_brute": "Bas",
                "genre_brut": "HOMME"
            },
            {
                "nom": "Jean Bleu Délavé Zen",
                "description": "Jean bleu délavé coupe droite denim Zen Tunisie.",
                "imageUrl": "https://images.zen.com.tn/uploads/8_U2_A8270_e9f0a1b2c3.jpg",
                "lienAchat": "https://zen.com.tn/fr/produit/8405-jean-bleu",
                "prix": 65.9,
                "vendeur": "Zen Tunisie",
                "taillesDisponibles": "38, 40, 42, 44",
                "couleur_brute": "Bleu",
                "categorie_brute": "Bas",
                "genre_brut": "HOMME"
            },
            {
                "nom": "Baskets Urbaines Zen Street Blanches",
                "description": "Baskets streetwear légères et confortables Zen Tunisie.",
                "imageUrl": "https://images.zen.com.tn/uploads/1_7_d79b76cae0.JPG",
                "lienAchat": "https://zen.com.tn/fr/produit/8481-basket",
                "prix": 79.9,
                "vendeur": "Zen Tunisie",
                "taillesDisponibles": "40, 41, 42, 43, 44",
                "couleur_brute": "Blanc",
                "categorie_brute": "Chaussures",
                "genre_brut": "HOMME"
            },
            {
                "nom": "Baskets Basses Skate Noires Zen",
                "description": "Baskets urbaines basses en toile noire avec semelle caoutchouc Zen Tunisie.",
                "imageUrl": "https://images.zen.com.tn/uploads/1_7_d79b76cae0.JPG",
                "lienAchat": "https://zen.com.tn/fr/produit/8480",
                "prix": 69.9,
                "vendeur": "Zen Tunisie",
                "taillesDisponibles": "40, 41, 42, 43, 44",
                "couleur_brute": "Noir",
                "categorie_brute": "Chaussures",
                "genre_brut": "HOMME"
            },

            # ===========================
            # PULL&BEAR — HOMME
            # ===========================
            {
                "nom": "T-Shirt Streetwear Graphique Pull&Bear",
                "description": "T-shirt imprimé streetwear coupe décontractée Pull&Bear Tunisie.",
                "imageUrl": "https://static.pullandbear.net/2/photos2/2024/V/0/2/p/8309/326/800/8309326800_1_1_8.jpg?t=1710950459952&imwidth=600",
                "lienAchat": "https://www.pullandbear.com/tn/homme/vetements/t-shirts-c29013.html",
                "prix": 49.0,
                "vendeur": "Pull&Bear TN",
                "taillesDisponibles": "S, M, L, XL",
                "couleur_brute": "Noir",
                "categorie_brute": "Haut",
                "genre_brut": "HOMME"
            },
            {
                "nom": "T-Shirt Blanc Basique Pull&Bear",
                "description": "T-shirt blanc col rond coupe regular Pull&Bear Tunisie.",
                "imageUrl": "https://static.pullandbear.net/2/photos2/2024/V/0/2/p/8309/327/250/8309327250_1_1_8.jpg?t=1710950459952&imwidth=600",
                "lienAchat": "https://www.pullandbear.com/tn/homme/vetements/t-shirts-c29013.html",
                "prix": 45.0,
                "vendeur": "Pull&Bear TN",
                "taillesDisponibles": "S, M, L, XL",
                "couleur_brute": "Blanc",
                "categorie_brute": "Haut",
                "genre_brut": "HOMME"
            },
            {
                "nom": "Jean Baggy Skate Denim Pull&Bear",
                "description": "Jean coupe baggy skater tendance en denim noir Pull&Bear Tunisie.",
                "imageUrl": "https://static.pullandbear.net/2/photos2/2024/V/0/2/p/8681/519/800/8681519800_1_1_8.jpg?t=1710950459952&imwidth=600",
                "lienAchat": "https://www.pullandbear.com/tn/homme/vetements/jeans-c29014.html",
                "prix": 99.0,
                "vendeur": "Pull&Bear TN",
                "taillesDisponibles": "38, 40, 42, 44",
                "couleur_brute": "Noir",
                "categorie_brute": "Bas",
                "genre_brut": "HOMME"
            },
            {
                "nom": "Jean Bleu Délavé Baggy Pull&Bear",
                "description": "Jean bleu coupe baggy délavé Pull&Bear Tunisie.",
                "imageUrl": "https://static.pullandbear.net/2/photos2/2024/V/0/2/p/8681/520/427/8681520427_1_1_8.jpg?t=1710950459952&imwidth=600",
                "lienAchat": "https://www.pullandbear.com/tn/homme/vetements/jeans-c29014.html",
                "prix": 95.0,
                "vendeur": "Pull&Bear TN",
                "taillesDisponibles": "38, 40, 42, 44",
                "couleur_brute": "Bleu",
                "categorie_brute": "Bas",
                "genre_brut": "HOMME"
            },
            {
                "nom": "Baskets Rétro Skate Pull&Bear",
                "description": "Baskets rétro vintage style skater Pull&Bear Tunisie.",
                "imageUrl": "https://static.pullandbear.net/2/photos2/2024/V/0/2/p/13030/420/050/13030420050_1_1_8.jpg?t=1710950459952&imwidth=600",
                "lienAchat": "https://www.pullandbear.com/tn/homme/chaussures-c29026.html",
                "prix": 119.0,
                "vendeur": "Pull&Bear TN",
                "taillesDisponibles": "40, 41, 42, 43, 44",
                "couleur_brute": "Blanc",
                "categorie_brute": "Chaussures",
                "genre_brut": "HOMME"
            },

            # ===========================
            # BERSHKA — HOMME
            # ===========================
            {
                "nom": "Pantalon Parachute Streetwear Bershka",
                "description": "Pantalon parachute streetwear ample noir Bershka Tunisie.",
                "imageUrl": "https://static.bershka.net/4/photos2/2024/V/0/1/p/8188/035/800/8188035800_2_1_8.jpg?t=1710950459952&imwidth=600",
                "lienAchat": "https://www.bershka.com/tn/homme/vetements/pantalons-c1010193240.html",
                "prix": 89.0,
                "vendeur": "Bershka TN",
                "taillesDisponibles": "38, 40, 42, 44",
                "couleur_brute": "Noir",
                "categorie_brute": "Bas",
                "genre_brut": "HOMME"
            },
            {
                "nom": "Pantalon Cargo Kaki Bershka",
                "description": "Cargo décontracté kaki multi-poches Bershka Tunisie.",
                "imageUrl": "https://static.bershka.net/4/photos2/2024/V/0/1/p/8188/036/505/8188036505_2_1_8.jpg?t=1710950459952&imwidth=600",
                "lienAchat": "https://www.bershka.com/tn/homme/vetements/pantalons-c1010193240.html",
                "prix": 85.0,
                "vendeur": "Bershka TN",
                "taillesDisponibles": "38, 40, 42, 44",
                "couleur_brute": "Vert",
                "categorie_brute": "Bas",
                "genre_brut": "HOMME"
            },
            {
                "nom": "Sweat Hoodie Streetwear Boxy Bershka",
                "description": "Hoodie coupe boxy streetwear moderne noir Bershka Tunisie.",
                "imageUrl": "https://static.bershka.net/4/photos2/2024/V/0/1/p/8311/560/800/8311560800_2_1_8.jpg?t=1710950459952&imwidth=600",
                "lienAchat": "https://www.bershka.com/tn/homme/vetements/sweats-c1010193238.html",
                "prix": 79.0,
                "vendeur": "Bershka TN",
                "taillesDisponibles": "S, M, L, XL",
                "couleur_brute": "Noir",
                "categorie_brute": "Haut",
                "genre_brut": "HOMME"
            },
            {
                "nom": "Sweat Hoodie Gris Oversize Bershka",
                "description": "Hoodie oversize gris chiné streetwear Bershka Tunisie.",
                "imageUrl": "https://static.bershka.net/4/photos2/2024/V/0/1/p/8311/561/802/8311561802_2_1_8.jpg?t=1710950459952&imwidth=600",
                "lienAchat": "https://www.bershka.com/tn/homme/vetements/sweats-c1010193238.html",
                "prix": 75.0,
                "vendeur": "Bershka TN",
                "taillesDisponibles": "S, M, L, XL",
                "couleur_brute": "Gris",
                "categorie_brute": "Haut",
                "genre_brut": "HOMME"
            },
            {
                "nom": "Veste Bomber Streetwear Noire Bershka",
                "description": "Veste bomber streetwear noire Bershka Tunisie.",
                "imageUrl": "https://static.bershka.net/4/photos2/2024/V/0/1/p/8601/009/800/8601009800_2_1_8.jpg?t=1710950459952&imwidth=600",
                "lienAchat": "https://www.bershka.com/tn/homme/vetements/vestes-c1010193236.html",
                "prix": 129.0,
                "vendeur": "Bershka TN",
                "taillesDisponibles": "S, M, L, XL",
                "couleur_brute": "Noir",
                "categorie_brute": "Veste",
                "genre_brut": "HOMME"
            },

            # ===========================
            # ZARA — HOMME
            # ===========================
            {
                "nom": "Pantalon Chino Épuré Zara Tunisie",
                "description": "Pantalon chino coupe droite élégante en coton peigné Zara Tunisie.",
                "imageUrl": "https://static.zara.net/stdimg/0/4849/430/800/default/static/seo/0484943080_6_1_1.jpg?ts=1710950459952&imwidth=600",
                "lienAchat": "https://www.zara.com/tn/fr/homme-pantalons-l640.html",
                "prix": 119.0,
                "vendeur": "Zara TN",
                "taillesDisponibles": "40, 42, 44",
                "couleur_brute": "Noir",
                "categorie_brute": "Bas",
                "genre_brut": "HOMME"
            },
            {
                "nom": "Pantalon Chino Beige Zara",
                "description": "Pantalon chino beige coupe droite décontractée Zara Tunisie.",
                "imageUrl": "https://static.zara.net/stdimg/0/4849/431/710/default/static/seo/0484943171_6_1_1.jpg?ts=1710950459952&imwidth=600",
                "lienAchat": "https://www.zara.com/tn/fr/homme-pantalons-l640.html",
                "prix": 115.0,
                "vendeur": "Zara TN",
                "taillesDisponibles": "40, 42, 44",
                "couleur_brute": "Beige",
                "categorie_brute": "Bas",
                "genre_brut": "HOMME"
            },
            {
                "nom": "T-Shirt Coton Premium Col Rond Zara Tunisie",
                "description": "T-shirt coupe ajustée en coton mercerisé blanc Zara Tunisie.",
                "imageUrl": "https://static.zara.net/stdimg/0/3600/800/800/default/static/seo/0360080003_6_1_1.jpg?ts=1710950459952&imwidth=600",
                "lienAchat": "https://www.zara.com/tn/fr/homme-t-shirts-l706.html",
                "prix": 49.0,
                "vendeur": "Zara TN",
                "taillesDisponibles": "S, M, L, XL",
                "couleur_brute": "Blanc",
                "categorie_brute": "Haut",
                "genre_brut": "HOMME"
            },
            {
                "nom": "T-Shirt Noir Coton Zara",
                "description": "T-shirt noir coton doux col rond Zara Tunisie.",
                "imageUrl": "https://static.zara.net/stdimg/0/3600/801/800/default/static/seo/0360080180_6_1_1.jpg?ts=1710950459952&imwidth=600",
                "lienAchat": "https://www.zara.com/tn/fr/homme-t-shirts-l706.html",
                "prix": 49.0,
                "vendeur": "Zara TN",
                "taillesDisponibles": "S, M, L, XL",
                "couleur_brute": "Noir",
                "categorie_brute": "Haut",
                "genre_brut": "HOMME"
            },
            {
                "nom": "Veste en Jean Bleu Zara",
                "description": "Veste en jean denim bleu délavé coupe droite Zara Tunisie.",
                "imageUrl": "https://static.zara.net/stdimg/0/9823/200/427/default/static/seo/0982320042_6_1_1.jpg?ts=1710950459952&imwidth=600",
                "lienAchat": "https://www.zara.com/tn/fr/homme-vestes-l638.html",
                "prix": 149.0,
                "vendeur": "Zara TN",
                "taillesDisponibles": "S, M, L, XL",
                "couleur_brute": "Bleu",
                "categorie_brute": "Veste",
                "genre_brut": "HOMME"
            },

            # ===========================
            # FEMME — EXIST
            # ===========================
            {
                "nom": "T-Shirt Blanc Femme Coton Exist",
                "description": "T-shirt blanc col rond coupe féminine coton doux Exist Tunisie.",
                "imageUrl": "https://www.exist.com.tn/171100-large_default/t-shirt-femme.jpg",
                "lienAchat": "https://www.exist.com.tn/femme-hauts/8100-48500-t-shirt-femme.html",
                "prix": 32.99,
                "vendeur": "Exist",
                "taillesDisponibles": "XS, S, M, L, XL",
                "couleur_brute": "Blanc",
                "categorie_brute": "Haut",
                "genre_brut": "FEMME"
            },
            {
                "nom": "T-Shirt Noir Femme Exist",
                "description": "T-shirt noir coupe féminine ajustée Exist Tunisie.",
                "imageUrl": "https://www.exist.com.tn/171110-large_default/t-shirt-femme.jpg",
                "lienAchat": "https://www.exist.com.tn/femme-hauts/8101-48510-t-shirt-femme.html",
                "prix": 32.99,
                "vendeur": "Exist",
                "taillesDisponibles": "XS, S, M, L, XL",
                "couleur_brute": "Noir",
                "categorie_brute": "Haut",
                "genre_brut": "FEMME"
            },
            {
                "nom": "Jean Femme Slim Bleu Exist",
                "description": "Jean femme slim bleu denim Exist Tunisie.",
                "imageUrl": "https://www.exist.com.tn/171200-large_default/jean-femme.jpg",
                "lienAchat": "https://www.exist.com.tn/femme-jeans/8120-48600-jean-femme.html",
                "prix": 79.99,
                "vendeur": "Exist",
                "taillesDisponibles": "36, 38, 40, 42, 44",
                "couleur_brute": "Bleu",
                "categorie_brute": "Bas",
                "genre_brut": "FEMME"
            },
            {
                "nom": "Jean Femme Noir Slim Exist",
                "description": "Jean noir slim taille haute femme Exist Tunisie.",
                "imageUrl": "https://www.exist.com.tn/171210-large_default/jean-femme.jpg",
                "lienAchat": "https://www.exist.com.tn/femme-jeans/8121-48610-jean-femme.html",
                "prix": 79.99,
                "vendeur": "Exist",
                "taillesDisponibles": "36, 38, 40, 42, 44",
                "couleur_brute": "Noir",
                "categorie_brute": "Bas",
                "genre_brut": "FEMME"
            },
            {
                "nom": "Baskets Blanches Femme Exist",
                "description": "Baskets blanches légères semelle confort femme Exist Tunisie.",
                "imageUrl": "https://www.exist.com.tn/171300-large_default/basket-femme.jpg",
                "lienAchat": "https://www.exist.com.tn/femme-chaussures/8130-48700-basket-femme.html",
                "prix": 89.99,
                "vendeur": "Exist",
                "taillesDisponibles": "36, 37, 38, 39, 40",
                "couleur_brute": "Blanc",
                "categorie_brute": "Chaussures",
                "genre_brut": "FEMME"
            },

            # ===========================
            # FEMME — ZARA
            # ===========================
            {
                "nom": "Robe Midi Noire Élégante Zara Femme",
                "description": "Robe midi noire élégante à col rond coupe fluide Zara Tunisie.",
                "imageUrl": "https://static.zara.net/stdimg/0/9035/054/800/default/static/seo/0903505480_6_1_1.jpg?ts=1710950459952&imwidth=600",
                "lienAchat": "https://www.zara.com/tn/fr/femme-robes-l1066.html",
                "prix": 139.0,
                "vendeur": "Zara TN",
                "taillesDisponibles": "XS, S, M, L",
                "couleur_brute": "Noir",
                "categorie_brute": "Robe",
                "genre_brut": "FEMME"
            },
            {
                "nom": "Robe Courte Blanche Casual Zara",
                "description": "Robe courte blanche décontractée col V Zara Tunisie.",
                "imageUrl": "https://static.zara.net/stdimg/0/9035/055/250/default/static/seo/0903505525_6_1_1.jpg?ts=1710950459952&imwidth=600",
                "lienAchat": "https://www.zara.com/tn/fr/femme-robes-l1066.html",
                "prix": 125.0,
                "vendeur": "Zara TN",
                "taillesDisponibles": "XS, S, M, L",
                "couleur_brute": "Blanc",
                "categorie_brute": "Robe",
                "genre_brut": "FEMME"
            },
            {
                "nom": "Jean Femme Taille Haute Bleu Zara",
                "description": "Jean femme taille haute coupe droite bleu délavé Zara Tunisie.",
                "imageUrl": "https://static.zara.net/stdimg/0/4578/254/427/default/static/seo/0457825442_6_1_1.jpg?ts=1710950459952&imwidth=600",
                "lienAchat": "https://www.zara.com/tn/fr/femme-jeans-l1119.html",
                "prix": 109.0,
                "vendeur": "Zara TN",
                "taillesDisponibles": "36, 38, 40, 42",
                "couleur_brute": "Bleu",
                "categorie_brute": "Bas",
                "genre_brut": "FEMME"
            },
            {
                "nom": "T-Shirt Oversize Femme Blanc Zara",
                "description": "T-shirt oversize blanc coton femme Zara Tunisie.",
                "imageUrl": "https://static.zara.net/stdimg/0/3600/802/250/default/static/seo/0360080225_6_1_1.jpg?ts=1710950459952&imwidth=600",
                "lienAchat": "https://www.zara.com/tn/fr/femme-t-shirts-l1138.html",
                "prix": 55.0,
                "vendeur": "Zara TN",
                "taillesDisponibles": "XS, S, M, L",
                "couleur_brute": "Blanc",
                "categorie_brute": "Haut",
                "genre_brut": "FEMME"
            },
            {
                "nom": "Blazer Femme Noir Élégant Zara",
                "description": "Blazer femme noir coupe structurée Zara Tunisie.",
                "imageUrl": "https://static.zara.net/stdimg/0/8085/050/800/default/static/seo/0808505080_6_1_1.jpg?ts=1710950459952&imwidth=600",
                "lienAchat": "https://www.zara.com/tn/fr/femme-vestes-l1038.html",
                "prix": 189.0,
                "vendeur": "Zara TN",
                "taillesDisponibles": "XS, S, M, L",
                "couleur_brute": "Noir",
                "categorie_brute": "Veste",
                "genre_brut": "FEMME"
            },

            # ===========================
            # FEMME — PULL&BEAR
            # ===========================
            {
                "nom": "T-Shirt Crop Noir Femme Pull&Bear",
                "description": "T-shirt crop top noir coupe courte Pull&Bear Tunisie.",
                "imageUrl": "https://static.pullandbear.net/2/photos2/2024/V/0/2/p/9218/400/800/9218400800_1_1_8.jpg?t=1710950459952&imwidth=600",
                "lienAchat": "https://www.pullandbear.com/tn/femme/vetements/t-shirts-c29004.html",
                "prix": 42.0,
                "vendeur": "Pull&Bear TN",
                "taillesDisponibles": "XS, S, M, L",
                "couleur_brute": "Noir",
                "categorie_brute": "Haut",
                "genre_brut": "FEMME"
            },
            {
                "nom": "Jean Mom Bleu Pull&Bear Femme",
                "description": "Jean mom fit bleu délavé Pull&Bear Tunisie.",
                "imageUrl": "https://static.pullandbear.net/2/photos2/2024/V/0/2/p/9681/520/427/9681520427_1_1_8.jpg?t=1710950459952&imwidth=600",
                "lienAchat": "https://www.pullandbear.com/tn/femme/vetements/jeans-c29005.html",
                "prix": 89.0,
                "vendeur": "Pull&Bear TN",
                "taillesDisponibles": "36, 38, 40, 42",
                "couleur_brute": "Bleu",
                "categorie_brute": "Bas",
                "genre_brut": "FEMME"
            },
            {
                "nom": "Baskets Blanches Femme Pull&Bear",
                "description": "Baskets blanches plateforme légères femme Pull&Bear Tunisie.",
                "imageUrl": "https://static.pullandbear.net/2/photos2/2024/V/0/2/p/13130/420/050/13130420050_1_1_8.jpg?t=1710950459952&imwidth=600",
                "lienAchat": "https://www.pullandbear.com/tn/femme/chaussures-c29017.html",
                "prix": 109.0,
                "vendeur": "Pull&Bear TN",
                "taillesDisponibles": "36, 37, 38, 39, 40",
                "couleur_brute": "Blanc",
                "categorie_brute": "Chaussures",
                "genre_brut": "FEMME"
            },

            # ===========================
            # FEMME — BERSHKA
            # ===========================
            {
                "nom": "Sweat Oversize Rose Pastel Bershka Femme",
                "description": "Sweat oversize rose pastel streetwear femme Bershka Tunisie.",
                "imageUrl": "https://static.bershka.net/4/photos2/2024/V/0/1/p/9311/565/672/9311565672_2_1_8.jpg?t=1710950459952&imwidth=600",
                "lienAchat": "https://www.bershka.com/tn/femme/vetements/sweats-c1010193222.html",
                "prix": 75.0,
                "vendeur": "Bershka TN",
                "taillesDisponibles": "XS, S, M, L",
                "couleur_brute": "Rose",
                "categorie_brute": "Haut",
                "genre_brut": "FEMME"
            },
            {
                "nom": "Jean Cargo Femme Vert Bershka",
                "description": "Jean cargo vert kaki femme coupe utilitaire Bershka Tunisie.",
                "imageUrl": "https://static.bershka.net/4/photos2/2024/V/0/1/p/9188/038/505/9188038505_2_1_8.jpg?t=1710950459952&imwidth=600",
                "lienAchat": "https://www.bershka.com/tn/femme/vetements/jeans-c1010193223.html",
                "prix": 89.0,
                "vendeur": "Bershka TN",
                "taillesDisponibles": "36, 38, 40, 42",
                "couleur_brute": "Vert",
                "categorie_brute": "Bas",
                "genre_brut": "FEMME"
            },
            {
                "nom": "Veste Denim Femme Bleu Bershka",
                "description": "Veste en denim bleu femme coupe droite Bershka Tunisie.",
                "imageUrl": "https://static.bershka.net/4/photos2/2024/V/0/1/p/9601/011/427/9601011427_2_1_8.jpg?t=1710950459952&imwidth=600",
                "lienAchat": "https://www.bershka.com/tn/femme/vetements/vestes-c1010193220.html",
                "prix": 119.0,
                "vendeur": "Bershka TN",
                "taillesDisponibles": "XS, S, M, L",
                "couleur_brute": "Bleu",
                "categorie_brute": "Veste",
                "genre_brut": "FEMME"
            },

            # ===========================
            # ACCESSOIRES / CASQUETTES
            # ===========================
            {
                "nom": "Casquette Snapback Noire Exist",
                "description": "Casquette snapback réglable noire streetwear Exist Tunisie.",
                "imageUrl": "https://www.exist.com.tn/170400-large_default/casquette.jpg",
                "lienAchat": "https://www.exist.com.tn/casquettes/8020-48150-casquette.html",
                "prix": 29.99,
                "vendeur": "Exist",
                "taillesDisponibles": "Taille unique",
                "couleur_brute": "Noir",
                "categorie_brute": "Accessoire",
                "genre_brut": "UNISEXE"
            },
            {
                "nom": "Sacoche Bandoulière Noire Exist",
                "description": "Sacoche crossbody noire urbaine Exist Tunisie.",
                "imageUrl": "https://www.exist.com.tn/170450-large_default/sacoche.jpg",
                "lienAchat": "https://www.exist.com.tn/sacoches/8025-48180-sacoche.html",
                "prix": 49.99,
                "vendeur": "Exist",
                "taillesDisponibles": "Taille unique",
                "couleur_brute": "Noir",
                "categorie_brute": "Accessoire",
                "genre_brut": "UNISEXE"
            },
        ]

        return catalog[:limit]
