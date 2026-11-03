import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.core.config import settings
from app.database.connection import engine, SessionLocal
from app.database.base import Base
from app.database.seed import seed_database

# Importation de tous les modèles pour que SQLAlchemy génère les tables
import app.models

# Importation des routeurs d'API
from app.api import (
    auth, users, referentials, clothes, ai,
    routines, events, recommendations, outfits, shopping
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("wearia")

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="API REST & Moteur IA pour l'application mobile Wearia (Projet d'Intégration L3-DSI2)",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Configuration CORS pour permettre les requêtes d'Android (émulateur 10.0.2.2, Wi-Fi local, etc.)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Monter le dossier des photos uploadées en statique
app.mount("/uploads", StaticFiles(directory=settings.UPLOAD_DIR), name="uploads")

# Inclusion des routeurs
app.include_router(auth.router)
app.include_router(users.router)
app.include_router(referentials.router)
app.include_router(clothes.router)
app.include_router(ai.router)
app.include_router(routines.router)
app.include_router(events.router)
app.include_router(recommendations.router)
app.include_router(outfits.router)
app.include_router(shopping.router)

@app.on_event("startup")
def on_startup():
    logger.info("Démarrage de l'API Wearia...")
    # Création des tables si elles n'existent pas
    Base.metadata.create_all(bind=engine)
    logger.info("Tables de la base de données prêtes.")

    # Peuplement initial des référentiels
    db = SessionLocal()
    try:
        seed_database(db)
    finally:
        db.close()

@app.get("/", tags=["Santé"])
def root():
    return {
        "status": "healthy",
        "app": settings.PROJECT_NAME,
        "version": settings.VERSION,
        "docs": "/docs"
    }

