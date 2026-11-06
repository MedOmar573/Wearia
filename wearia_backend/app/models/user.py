from datetime import datetime, date
from sqlalchemy import (
    Column, Integer, String, Float, Boolean, Date, DateTime, 
    ForeignKey, Enum as SQLEnum, UniqueConstraint
)
from sqlalchemy.orm import relationship
from app.database.base import Base
from app.models.enums import Genre, Coupe, TypePreference

class Utilisateur(Base):
    __tablename__ = "utilisateurs"

    id = Column(Integer, primary_key=True, index=True)
    nom = Column(String(100), nullable=False)
    email = Column(String(255), unique=True, nullable=False, index=True)
    motDePasseHash = Column(String(255), nullable=False)
    genre = Column(SQLEnum(Genre), nullable=True)
    dateNaissance = Column(Date, nullable=True)
    ville = Column(String(100), default="Tunis", nullable=False)
    
    # Mensurations & Morphologie
    hauteurCm = Column(Integer, nullable=True)
    poidsKg = Column(Float, nullable=True)
    tourEpaules = Column(Float, nullable=True)
    tourPoitrine = Column(Float, nullable=True)
    tourTaille = Column(Float, nullable=True)
    tourHanches = Column(Float, nullable=True)
    tailleVestimentaire = Column(String(20), nullable=True) # Ex: M, L, 42
    coupePreferee = Column(SQLEnum(Coupe), default=Coupe.REGULIERE, nullable=True)
    
    consentementRGPD = Column(Boolean, default=True, nullable=False)
    dateCreation = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relations
    routines = relationship("RoutineHebdomadaire", back_populates="utilisateur", cascade="all, delete-orphan")
    evenements = relationship("Evenement", back_populates="utilisateur", cascade="all, delete-orphan")
    preferences_couleur = relationship("PreferenceCouleur", back_populates="utilisateur", cascade="all, delete-orphan")
    preferences_style = relationship("PreferenceStyle", back_populates="utilisateur", cascade="all, delete-orphan")
    vetements = relationship("Vetement", back_populates="utilisateur", cascade="all, delete-orphan")
    tenues = relationship("Tenue", back_populates="utilisateur", cascade="all, delete-orphan")
    demandes_achat = relationship("DemandeAchat", back_populates="utilisateur", cascade="all, delete-orphan")

class PreferenceCouleur(Base):
    __tablename__ = "preferences_couleur"

    id = Column(Integer, primary_key=True, index=True)
    utilisateur_id = Column(Integer, ForeignKey("utilisateurs.id", ondelete="CASCADE"), nullable=False)
    couleur_id = Column(Integer, ForeignKey("couleurs.id", ondelete="CASCADE"), nullable=False)
    typePreference = Column(SQLEnum(TypePreference), default=TypePreference.AIME, nullable=False)

    utilisateur = relationship("Utilisateur", back_populates="preferences_couleur")
    couleur = relationship("Couleur")

    __table_args__ = (
        UniqueConstraint("utilisateur_id", "couleur_id", "typePreference", name="uq_user_color_pref"),
    )

class PreferenceStyle(Base):
    __tablename__ = "preferences_style"

    id = Column(Integer, primary_key=True, index=True)
    utilisateur_id = Column(Integer, ForeignKey("utilisateurs.id", ondelete="CASCADE"), nullable=False)
    style_id = Column(Integer, ForeignKey("styles_vestimentaires.id", ondelete="CASCADE"), nullable=False)
    typePreference = Column(SQLEnum(TypePreference), default=TypePreference.AIME, nullable=False)

    utilisateur = relationship("Utilisateur", back_populates="preferences_style")
    style = relationship("StyleVestimentaire")

    __table_args__ = (
        UniqueConstraint("utilisateur_id", "style_id", "typePreference", name="uq_user_style_pref"),
    )

