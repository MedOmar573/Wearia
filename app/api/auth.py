from datetime import timedelta
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.database.connection import get_db
from app.models.user import Utilisateur
from app.schemas.auth import RegisterRequest, LoginRequest, Token
from app.schemas.user import UserResponse
from app.core.security import get_password_hash, verify_password, create_access_token
from app.core.config import settings

router = APIRouter(prefix="/auth", tags=["Authentification"])

@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def register(user_in: RegisterRequest, db: Session = Depends(get_db)):
    """
    Inscription d'un nouvel utilisateur (UC06).
    Vérifie l'unicité de l'email et la force du mot de passe (BR05).
    """
    existing_user = db.query(Utilisateur).filter(Utilisateur.email == user_in.email.lower()).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Un compte avec cette adresse email existe déjà."
        )

    if len(user_in.password) < 8:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Le mot de passe doit comporter au moins 8 caractères (BR05)."
        )

    new_user = Utilisateur(
        nom=user_in.nom,
        email=user_in.email.lower(),
        motDePasseHash=get_password_hash(user_in.password),
        ville="Tunis"
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return new_user

@router.post("/login", response_model=Token)
def login(login_in: LoginRequest, db: Session = Depends(get_db)):
    """
    Connexion utilisateur (UC07) et émission du jeton JWT.
    """
    user = db.query(Utilisateur).filter(Utilisateur.email == login_in.email.lower()).first()
    if not user or not verify_password(login_in.password, user.motDePasseHash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Adresse email ou mot de passe incorrect.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    token = create_access_token(
        subject=user.id,
        expires_delta=access_token_expires
    )
    return {"access_token": token, "token_type": "bearer"}

