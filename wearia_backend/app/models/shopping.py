from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Enum as SQLEnum
from sqlalchemy.orm import relationship
from app.database.base import Base
from app.models.enums import Occasion

class ArticleCatalogue(Base):
    __tablename__ = "articles_catalogue"

    id = Column(Integer, primary_key=True, index=True)
    nom = Column(String(150), nullable=False)
    imageUrl = Column(String(500), nullable=False)
    lienAchat = Column(String(500), nullable=True)
    prix = Column(Float, nullable=False)
    vendeur = Column(String(100), default="Boutique Démo", nullable=False)
    taillesDisponibles = Column(String(100), default="S, M, L, XL", nullable=False)

    type_vetement_id = Column(Integer, ForeignKey("types_vetement.id"), nullable=False)
    couleur_id = Column(Integer, ForeignKey("couleurs.id"), nullable=False)

    type_vetement = relationship("TypeVetement")
    couleur = relationship("Couleur")

class DemandeAchat(Base):
    __tablename__ = "demandes_achat"

    id = Column(Integer, primary_key=True, index=True)
    utilisateur_id = Column(Integer, ForeignKey("utilisateurs.id", ondelete="CASCADE"), nullable=False)
    besoin = Column(String(255), nullable=False)
    occasion = Column(SQLEnum(Occasion), default=Occasion.QUOTIDIEN, nullable=False)
    dateDemande = Column(DateTime, default=datetime.utcnow, nullable=False)
    style_id = Column(Integer, ForeignKey("styles_vestimentaires.id", ondelete="SET NULL"), nullable=True)

    utilisateur = relationship("Utilisateur", back_populates="demandes_achat")
    style_recherche = relationship("StyleVestimentaire")
    suggestions = relationship("SuggestionAchat", back_populates="demande_achat", cascade="all, delete-orphan")

class SuggestionAchat(Base):
    __tablename__ = "suggestions_achat"

    id = Column(Integer, primary_key=True, index=True)
    demande_achat_id = Column(Integer, ForeignKey("demandes_achat.id", ondelete="CASCADE"), nullable=False)
    article_id = Column(Integer, ForeignKey("articles_catalogue.id", ondelete="CASCADE"), nullable=False)
    motifSuggestion = Column(String(300), nullable=False)

    demande_achat = relationship("DemandeAchat", back_populates="suggestions")
    article = relationship("ArticleCatalogue")

