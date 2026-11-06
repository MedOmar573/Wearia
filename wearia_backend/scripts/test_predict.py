import sys
from pathlib import Path
sys.path.insert(0, r"c:\Users\DELL\Desktop\L3DSI\projet\Wearia\wearia_backend")

from app.ai.predict import predict_clothing_category

up = Path(r"c:\Users\DELL\Desktop\L3DSI\projet\Wearia\wearia_backend\uploads")
test_cases = [
    "pull_maille_beige.jpg",
    "chemise_oxford_blanche.jpg",
    "tshirt_noir.jpg",
    "bomber_noir.jpg",
    "pantalon_noir.jpg",
    "jean_slim_bleu.jpg",
    "baskets_blanches.jpg",
    "derbies_marron.jpg"
]

print(f"{'IMAGE':30} | {'CATEGORY':15} | {'COLOR':12} | {'CONFIDENCE':10}")
print("-" * 75)
for tc in test_cases:
    p = up / tc
    if p.exists():
        res = predict_clothing_category(str(p))
        print(f"{tc:30} | {res['category']:15} | {res['color']:12} | {res['confidence']}")

