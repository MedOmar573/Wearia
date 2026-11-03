from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, Enum as SQLEnum
from sqlalchemy.orm import relationship
from app.database.base import Base
from app.models.enums import GenreCible

class Categorie(Base):
    __tablename__ = "categories"

    id = Column(Integer, primary_key=True, index=True)
    nom = Column(String(100), unique=True, nullable=False, index=True)

    types_vetement = relationship("TypeVetement", back_populates="categorie", cascade="all, delete-orphan")

class TypeVetement(Base):
    __tablename__ = "types_vetement"

    id = Column(Integer, primary_key=True, index=True)
    nom = Column(String(100), unique=True, nullable=False, index=True)
    genreCible = Column(SQLEnum(GenreCible), default=GenreCible.MIXTE, nullable=False)
    estCoucheSuperieure = Column(Boolean, default=False, nullable=False) # Satisfait BR02 (manteau, veste, pull)

    categorie_id = Column(Integer, ForeignKey("categories.id", ondelete="CASCADE"), nullable=False)
    categorie = relationship("Categorie", back_populates="types_vetement")
    vetements = relationship("Vetement", back_populates="type_vetement")

class Couleur(Base):
    __tablename__ = "couleurs"

    id = Column(Integer, primary_key=True, index=True)
    nom = Column(String(50), unique=True, nullable=False)
    codeHex = Column(String(10), nullable=False)

    vetements = relationship("Vetement", back_populates="couleur")

class StyleVestimentaire(Base):
    __tablename__ = "styles_vestimentaires"

    id = Column(Integer, primary_key=True, index=True)
    libelle = Column(String(100), unique=True, nullable=False)

    vetements = relationship("Vetement", back_populates="style_vestimentaire")
    tenues = relationship("Tenue", back_populates="style_vestimentaire")

