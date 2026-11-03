import sys
import time
from pathlib import Path

# Ajouter le chemin racine
ROOT = Path(__file__).resolve().parent
sys.path.append(str(ROOT))

from fastapi.testclient import TestClient
from app.main import app

def run_tests():
    client = TestClient(app)

    print("--- TEST 1: Root & Health ---")
    res_root = client.get("/")
    print("GET / :", res_root.status_code, res_root.json())
    assert res_root.status_code == 200

    print("\n--- TEST 2: OpenAPI & Docs ---")
    res_docs = client.get("/openapi.json")
    routes_count = len(res_docs.json().get("paths", {}))
    print(f"GET /openapi.json : {res_docs.status_code} ({routes_count} routes documentées)")
    assert res_docs.status_code == 200

    print("\n--- TEST 3: Référentiels (Seed automatique) ---")
    res_cats = client.get("/referentials/categories")
    cat_names = [c["nom"] for c in res_cats.json()]
    print(f"Catégories ({res_cats.status_code}) :", cat_names)
    assert len(res_cats.json()) >= 6

    res_types = client.get("/referentials/types")
    print(f"Types de vêtements ({res_types.status_code}) : {len(res_types.json())} types disponibles")
    assert len(res_types.json()) >= 10

    res_colors = client.get("/referentials/colors")
    print(f"Couleurs ({res_colors.status_code}) : {len(res_colors.json())} couleurs enregistrées")
    assert len(res_colors.json()) >= 10

    print("\n--- TEST 4: Inscription & Authentification JWT ---")
    email_test = f"testuser_{int(time.time())}@wearia.tn"
    reg_payload = {
        "nom": "Ameni Homri",
        "email": email_test,
        "password": "Password123!"
    }
    res_reg = client.post("/auth/register", json=reg_payload)
    print("Inscription :", res_reg.status_code, res_reg.json().get("email"))
    assert res_reg.status_code == 201

    login_payload = {
        "email": email_test,
        "password": "Password123!"
    }
    res_login = client.post("/auth/login", json=login_payload)
    print("Connexion :", res_login.status_code, "Jeton JWT généré")
    assert res_login.status_code == 200
    token = res_login.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    print("\n--- TEST 5: Profil Protégé (/users/me) ---")
    res_me = client.get("/users/me", headers=headers)
    print("Profil connecté :", res_me.status_code, res_me.json()["nom"], "-", res_me.json()["email"])
    assert res_me.status_code == 200

    print("\n--- TEST 6: Routine Hebdomadaire (BR09) ---")
    routine_payload = {
        "jourSemaine": "LUNDI",
        "occasion": "UNIVERSITE",
        "estActive": True
    }
    res_routine = client.post("/routines", json=routine_payload, headers=headers)
    print("Création routine :", res_routine.status_code, res_routine.json()["jourSemaine"], "->", res_routine.json()["occasion"])
    assert res_routine.status_code == 201

    print("\n--- TEST 7: Personal Shopper Catalogue ---")
    res_cat = client.get("/shopping/catalogue")
    print(f"Articles catalogue démo ({res_cat.status_code}) : {len(res_cat.json())} articles trouvés")
    assert len(res_cat.json()) >= 4

    print("\n" + "=" * 60)
    print("🎉 TOUS LES TESTS DE L'ÉTAPE 1 ONT RÉUSSI AVEC SUCCÈS !")
    print("=" * 60)

if __name__ == "__main__":
    run_tests()

