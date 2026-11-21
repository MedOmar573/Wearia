from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.database.connection import get_db
from app.models.user import Utilisateur
from app.models.otp import EmailOTP
from app.schemas.auth import (
    RegisterRequest, LoginRequest, AuthStepResponse, 
    VerifyOtpRequest, ResendOtpRequest, AuthTokenResponse
)
from app.core.security import get_password_hash, verify_password, create_access_token
from app.core.email import generate_otp, send_otp_email
from app.core.config import settings

router = APIRouter(prefix="/auth", tags=["Authentification"])

@router.post("/register", response_model=AuthStepResponse, status_code=status.HTTP_201_CREATED)
def register(user_in: RegisterRequest, db: Session = Depends(get_db)):
    """
    Étape 1 Inscription (UC06) :
    1. Vérifie l'unicité de l'email et la force du mot de passe (BR05).
    2. Crée l'utilisateur (avec is_verified=False).
    3. Génère et envoie un code OTP à 6 chiffres par email.
    """
    clean_email = user_in.email.lower().strip()

    existing_user = db.query(Utilisateur).filter(Utilisateur.email == clean_email).first()
    if existing_user and getattr(existing_user, "is_verified", True):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Un compte avec cette adresse email existe déjà."
        )

    if len(user_in.password) < 8:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Le mot de passe doit comporter au moins 8 caractères (BR05)."
        )

    if existing_user and not getattr(existing_user, "is_verified", True):
        # Mettre à jour l'utilisateur non encore vérifié
        existing_user.nom = user_in.nom
        existing_user.motDePasseHash = get_password_hash(user_in.password)
        if user_in.hauteurCm:
            existing_user.hauteurCm = user_in.hauteurCm
        if user_in.poidsKg:
            existing_user.poidsKg = user_in.poidsKg
        if user_in.genre:
            existing_user.genre = user_in.genre
        db.commit()
        user = existing_user
    else:
        # Création du nouvel utilisateur en attente de validation OTP
        user = Utilisateur(
            nom=user_in.nom,
            email=clean_email,
            motDePasseHash=get_password_hash(user_in.password),
            ville="Tunis",
            hauteurCm=user_in.hauteurCm,
            poidsKg=user_in.poidsKg,
            genre=user_in.genre,
            is_verified=False
        )
        db.add(user)
        db.commit()
        db.refresh(user)

    # Invalider d'anciens OTP non utilisés pour cette adresse
    db.query(EmailOTP).filter(
        EmailOTP.email == clean_email,
        EmailOTP.purpose == "REGISTER",
        EmailOTP.is_used == False
    ).update({"is_used": True})

    # Générer le code OTP
    code = generate_otp()
    expires_at = datetime.utcnow() + timedelta(minutes=10)
    otp_record = EmailOTP(
        email=clean_email,
        code=code,
        purpose="REGISTER",
        expires_at=expires_at,
        is_used=False
    )
    db.add(otp_record)
    db.commit()

    # Envoyer l'email
    send_otp_email(clean_email, code, "REGISTER")

    return AuthStepResponse(
        otp_required=True,
        email=clean_email,
        purpose="REGISTER",
        message="Un code de vérification à 6 chiffres a été envoyé à votre adresse email.",
        dev_otp=code
    )

@router.post("/login", response_model=AuthStepResponse)
def login(login_in: LoginRequest, db: Session = Depends(get_db)):
    """
    Étape 1 Connexion (UC07) :
    1. Vérifie l'email et le mot de passe.
    2. Si valides, génère et envoie un code OTP de sécurité par email.
    """
    clean_email = login_in.email.lower().strip()
    user = db.query(Utilisateur).filter(Utilisateur.email == clean_email).first()

    if not user or not verify_password(login_in.password, user.motDePasseHash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Adresse email ou mot de passe incorrect.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Invalider les anciens codes OTP pour la connexion
    db.query(EmailOTP).filter(
        EmailOTP.email == clean_email,
        EmailOTP.purpose == "LOGIN",
        EmailOTP.is_used == False
    ).update({"is_used": True})

    # Générer le code OTP pour connexion
    code = generate_otp()
    expires_at = datetime.utcnow() + timedelta(minutes=10)
    otp_record = EmailOTP(
        email=clean_email,
        code=code,
        purpose="LOGIN",
        expires_at=expires_at,
        is_used=False
    )
    db.add(otp_record)
    db.commit()

    # Envoyer l'email
    send_otp_email(clean_email, code, "LOGIN")

    return AuthStepResponse(
        otp_required=True,
        email=clean_email,
        purpose="LOGIN",
        message="Un code de sécurité à 6 chiffres a été envoyé à votre adresse email.",
        dev_otp=code
    )

@router.post("/verify-otp", response_model=AuthTokenResponse)
def verify_otp(verify_in: VerifyOtpRequest, db: Session = Depends(get_db)):
    """
    Étape 2 Validation OTP (Inscription et Connexion) :
    1. Vérifie le code OTP (doit être non utilisé et valide < 10 min).
    2. Si inscription : valide définitivement le compte (is_verified = True).
    3. Émet le jeton JWT d'authentification pour accéder à l'application.
    """
    clean_email = verify_in.email.lower().strip()
    code = verify_in.code.strip()
    purpose = verify_in.purpose.upper().strip()

    otp = db.query(EmailOTP).filter(
        EmailOTP.email == clean_email,
        EmailOTP.code == code,
        EmailOTP.purpose == purpose,
        EmailOTP.is_used == False,
        EmailOTP.expires_at >= datetime.utcnow()
    ).order_by(EmailOTP.id.desc()).first()

    if not otp:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Code de vérification invalide ou expiré. Veuillez vérifier votre saisie ou redemander un code."
        )

    # Marquer l'OTP comme utilisé
    otp.is_used = True

    user = db.query(Utilisateur).filter(Utilisateur.email == clean_email).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Utilisateur introuvable."
        )

    # Activer le compte si c'est une inscription
    if purpose == "REGISTER":
        user.is_verified = True

    db.commit()

    # Génération du token JWT
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    token = create_access_token(
        subject=user.id,
        expires_delta=access_token_expires
    )

    is_completed = bool(user.hauteurCm and user.poidsKg)

    return AuthTokenResponse(
        access_token=token,
        token_type="bearer",
        user_id=user.id,
        nom=user.nom,
        email=user.email,
        is_verified=getattr(user, "is_verified", True),
        genre=user.genre.value if getattr(user, "genre", None) else None,
        hauteurCm=user.hauteurCm,
        poidsKg=user.poidsKg,
        is_profile_completed=is_completed
    )

@router.post("/resend-otp")
def resend_otp(resend_in: ResendOtpRequest, db: Session = Depends(get_db)):
    """
    Renvoie un nouveau code OTP si l'utilisateur ne l'a pas reçu ou s'il a expiré.
    """
    clean_email = resend_in.email.lower().strip()
    purpose = resend_in.purpose.upper().strip()

    user = db.query(Utilisateur).filter(Utilisateur.email == clean_email).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Aucun compte associé à cette adresse email."
        )

    # Invalider les anciens codes
    db.query(EmailOTP).filter(
        EmailOTP.email == clean_email,
        EmailOTP.purpose == purpose,
        EmailOTP.is_used == False
    ).update({"is_used": True})

    # Générer et enregistrer un nouveau code
    code = generate_otp()
    expires_at = datetime.utcnow() + timedelta(minutes=10)
    otp_record = EmailOTP(
        email=clean_email,
        code=code,
        purpose=purpose,
        expires_at=expires_at,
        is_used=False
    )
    db.add(otp_record)
    db.commit()

    # Envoyer l'email
    send_otp_email(clean_email, code, purpose)

    return {
        "message": "Un nouveau code de vérification a été envoyé à votre adresse email."
    }
