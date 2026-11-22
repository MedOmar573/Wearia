"""
Tests de vérification de la détection v4 des catégories de vêtements Wearia :
- Taxonomie & alias (Short, Chemise, Manteau, Veste, Chapeau, Jean, Sac, Sweat)
- Modèle entraîné v4 (16 classes, 1792 descripteurs) sur photos réelles + silhouettes cibles
- Cohérence Homme vs Femme (Sac & Sweat reconnus dans les deux genres, Robe/Jupe/Bottes filtrés pour Homme)
"""

import sys
import tempfile
import unittest
from pathlib import Path

import cv2
import numpy as np

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.ai.predict import get_loaded_models, predict_clothing_category, reload_models
from app.ai.taxonomy import ClothingType, normalize_clothing_type
from app.ai.train_model import (
    load_fashion_mnist_data,
    synthesize_hat_image,
    synthesize_hoodie_from_pullover,
)


class TestClothingClassificationV4(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        reload_models()
        cls.uploads = BACKEND_ROOT / "uploads"
        cls.dataset = BACKEND_ROOT / "dataset"

    def test_taxonomy_includes_all_required_types_and_aliases(self):
        required = {
            "Short",
            "Chemise",
            "Manteau",
            "Veste",
            "Chapeau",
            "Jean",
            "Sac",
            "Sweat",
        }
        enum_values = {t.value for t in ClothingType}
        self.assertTrue(required.issubset(enum_values))

        # Aliases homme / femme / mixte
        self.assertEqual(normalize_clothing_type("sac à main", "FEMME"), "Sac")
        self.assertEqual(normalize_clothing_type("handbag", "FEMME"), "Sac")
        self.assertEqual(normalize_clothing_type("casquette", "HOMME"), "Chapeau")
        self.assertEqual(normalize_clothing_type("bonnet", "FEMME"), "Chapeau")
        self.assertEqual(normalize_clothing_type("hoodie", "HOMME"), "Sweat")
        self.assertEqual(normalize_clothing_type("hoodie", "FEMME"), "Sweat")
        self.assertEqual(normalize_clothing_type("veste en jean", "HOMME"), "Veste")
        self.assertEqual(normalize_clothing_type("doudoune", "FEMME"), "Manteau")
        self.assertEqual(normalize_clothing_type("Robe", "HOMME"), "Manteau")

    def test_trained_model_knows_all_16_classes(self):
        model, scaler = get_loaded_models()
        self.assertIsNotNone(model)
        self.assertIsNotNone(scaler)
        classes = set(str(c) for c in model.classes_)
        for expected in ("Short", "Chemise", "Manteau", "Veste", "Chapeau", "Jean", "Sac", "Sweat", "Pantalon", "T-Shirt", "Pull", "Robe", "Jupe", "Baskets", "Bottes", "Chaussures de ville"):
            self.assertIn(expected, classes, f"Classe manquante dans le modèle entraîné : {expected}")

    def test_real_images_detection_key_categories(self):
        cases = [
            ("short_kaki.jpg", "HOMME", "Short"),
            ("short_kaki.jpg", "FEMME", "Short"),
            ("jean_slim_bleu.jpg", "HOMME", "Jean"),
            ("jean_slim_bleu.jpg", "FEMME", "Jean"),
            ("chino_beige.jpg", "HOMME", "Jean"),  # Photo réelle : jean denim brut bleu marine (rivets cuivre)
            ("0f411f15-ea68-4540-81b9-3dead15042a7.jpg", "HOMME", "Pantalon"),
            ("pantalon_noir.jpg", "HOMME", "Pantalon"),
            ("bomber_noir.jpg", "HOMME", "Veste"),
            ("blazer_marine.jpg", "HOMME", "Veste"),
            ("0ccca783-4db6-42de-854a-dad612178a66.jpg", "HOMME", "Chemise"),
            ("45515059-a20e-4d8c-a55b-384a43fd06e5.jpg", "HOMME", "Chemise"),
            ("tshirt_blanc.jpg", "HOMME", "T-Shirt"),
            ("pull_maille_beige.jpg", "HOMME", "Pull"),
            ("baskets_blanches.jpg", "HOMME", "Baskets"),
            ("derbies_marron.jpg", "HOMME", "Chaussures de ville"),
        ]
        for filename, genre, expected in cases:
            path = self.uploads / filename
            if not path.exists():
                continue
            res = predict_clothing_category(str(path), user_genre=genre)
            self.assertEqual(
                res["category"],
                expected,
                f"Échec sur {filename} (genre={genre}) : attendu={expected}, obtenu={res['category']} "
                f"(raw={res.get('raw_category')}, rule={res.get('rule_applied')}, conf={res.get('confidence')})",
            )

    def test_synthetic_hat_bag_sweat_detection_homme_and_femme(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)

            # 1. Chapeau (fedora + casquette)
            hat_img = synthesize_hat_image("fedora")
            hat_path = tmp / "hat_test.png"
            cv2.imwrite(str(hat_path), cv2.cvtColor(hat_img, cv2.COLOR_RGB2BGR))
            for genre in ("HOMME", "FEMME"):
                res = predict_clothing_category(str(hat_path), user_genre=genre)
                self.assertEqual(res["category"], "Chapeau", f"Chapeau échoué pour {genre}: {res}")

            # 2. Sac (échantillon réel Fashion-MNIST label 8) + Sweat (hoodie mixte)
            imgs, lbls = load_fashion_mnist_data(self.dataset, max_samples_per_class=20)
            bag_img = next(img for img, lbl in zip(imgs, lbls) if lbl == "Sac")
            bag_path = tmp / "bag_test.png"
            cv2.imwrite(str(bag_path), cv2.cvtColor(bag_img, cv2.COLOR_RGB2BGR))
            for genre in ("FEMME", "HOMME"):
                res_bag = predict_clothing_category(str(bag_path), user_genre=genre)
                self.assertEqual(res_bag["category"], "Sac", f"Sac échoué pour {genre}: {res_bag}")

            sweat_img = next(img for img, lbl in zip(imgs, lbls) if lbl == "Sweat")
            sweat_path = tmp / "sweat_test.png"
            cv2.imwrite(str(sweat_path), cv2.cvtColor(sweat_img, cv2.COLOR_RGB2BGR))
            for genre in ("HOMME", "FEMME"):
                res_sweat = predict_clothing_category(str(sweat_path), user_genre=genre)
                self.assertEqual(res_sweat["category"], "Sweat", f"Sweat échoué pour {genre}: {res_sweat}")


if __name__ == "__main__":
    unittest.main(verbosity=2)
