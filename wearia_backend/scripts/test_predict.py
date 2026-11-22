"""
Script de diagnostic et de validation du pipeline IA Wearia (type + couleur).
Affiche pour chaque image de test : catégorie attendue vs détectée, couleur attendue vs détectée,
score de confiance, label brut ML et règle structurelle éventuellement appliquée.
"""

import logging
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

logging.basicConfig(level=logging.INFO, format="%(levelname)s | %(message)s")

from app.ai.predict import predict_clothing_category


def main():
    up = BASE_DIR / "uploads"

    # Jeu de test vérifié visuellement : (fichier, types acceptables, couleurs acceptables)
    test_cases = [
        ("0f411f15-ea68-4540-81b9-3dead15042a7.jpg", {"Pantalon"}, {"Rouge"}),
        ("7be263f9-1f27-4ba1-b791-738c13e2f13f.jpg", {"Pantalon"}, {"Vert"}),
        ("pantalon_noir.jpg", {"Pantalon"}, {"Rose", "Corail"}),
        ("8dc35d77-d4df-41c1-8c11-7faf063ad953.jpg", {"T-Shirt"}, {"Bleu Marine"}),
        ("4f7fa19c-4042-47ff-8b0e-f70994641311.jpg", {"T-Shirt"}, {"Beige", "Sable"}),
        ("tshirt_blanc.jpg", {"T-Shirt"}, {"Noir"}),
        ("0ccca783-4db6-42de-854a-dad612178a66.jpg", {"Chemise"}, {"Noir"}),
        ("45515059-a20e-4d8c-a55b-384a43fd06e5.jpg", {"Chemise"}, {"Bleu"}),
        ("pull_maille_beige.jpg", {"Pull", "Sweat"}, {"Blanc"}),
        ("chino_beige.jpg", {"Jean", "Pantalon"}, {"Bleu Marine", "Bleu"}),
        ("jean_slim_bleu.jpg", {"Jean", "Pantalon"}, {"Bleu", "Bleu Marine", "Noir"}),
        ("short_kaki.jpg", {"Short"}, {"Bleu"}),
        ("bomber_noir.jpg", {"Veste", "Manteau"}, {"Noir"}),
        ("blazer_marine.jpg", {"Veste", "Manteau"}, {"Bleu Marine", "Noir"}),
        ("462e8ef5-fe34-4487-84ea-3c263a83ca2b.jpg", {"Baskets"}, {"Noir"}),
        ("baskets_blanches.jpg", {"Baskets"}, {"Blanc", "Beige", "Gris"}),
        ("baskets_sport_noires.jpg", {"Baskets"}, {"Rouge"}),
        ("derbies_marron.jpg", {"Chaussures de ville"}, {"Marron", "Marron Foncé"}),
    ]

    print(
        f"\n{'IMAGE':32} | {'TYPE':19} | {'RAW_ML':15} | {'COLOR':12} | {'CONF':5} | {'TYPE_OK':7} | {'COL_OK':6}"
    )
    print("-" * 114)

    total = 0
    type_ok_cnt = 0
    col_ok_cnt = 0

    for fname, exp_types, exp_colors in test_cases:
        p = up / fname
        if not p.exists():
            continue
        total += 1
        res = predict_clothing_category(str(p))
        t_ok = res["category"] in exp_types
        c_ok = res["color"] in exp_colors
        type_ok_cnt += int(t_ok)
        col_ok_cnt += int(c_ok)
        print(
            f"{fname[:32]:32} | {res['category']:19} | {str(res.get('raw_category', '-'))[:15]:15} | "
            f"{res['color']:12} | {res['confidence']:5.2f} | {'OK' if t_ok else 'KO':7} | {'OK' if c_ok else 'KO':6}"
        )

    print("-" * 114)
    if total > 0:
        print(
            f"Score Type    : {type_ok_cnt}/{total} ({100.0 * type_ok_cnt / total:.1f}%)\n"
            f"Score Couleur : {col_ok_cnt}/{total} ({100.0 * col_ok_cnt / total:.1f}%)"
        )


if __name__ == "__main__":
    main()
