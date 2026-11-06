import os
from pathlib import Path
from dotenv import load_dotenv

# Charger les variables du fichier .env
env_path = Path(__file__).resolve().parent.parent.parent / ".env"
load_dotenv(dotenv_path=env_path)

class Settings:
    PROJECT_NAME: str = os.getenv("PROJECT_NAME", "Wearia Backend API")
    VERSION: str = os.getenv("VERSION", "1.0.0")
    API_V1_STR: str = os.getenv("API_V1_STR", "")

    # Base de données
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL", 
        "postgresql+psycopg://postgres:postgres@localhost:5432/wearia_db"
    )
    USE_SQLITE_FALLBACK: bool = os.getenv("USE_SQLITE_FALLBACK", "True").lower() in ("true", "1", "yes")
    SQLITE_URL: str = os.getenv("SQLITE_URL", "sqlite:///./wearia.db")

    # JWT
    SECRET_KEY: str = os.getenv("SECRET_KEY", "wearia_secret_key_super_securisee_pour_projet_integration_l3dsi")
    ALGORITHM: str = os.getenv("ALGORITHM", "HS256")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "43200"))

    # Météo
    OPENWEATHERMAP_API_KEY: str = os.getenv("OPENWEATHERMAP_API_KEY", "")

    # Dossiers
    BASE_DIR: Path = Path(__file__).resolve().parent.parent.parent
    UPLOAD_DIR: Path = BASE_DIR / os.getenv("UPLOAD_DIR", "uploads")
    AI_MODELS_DIR: Path = BASE_DIR / os.getenv("AI_MODELS_DIR", "models")

settings = Settings()
# S'assurer que les dossiers nécessaires existent
settings.UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
settings.AI_MODELS_DIR.mkdir(parents=True, exist_ok=True)

