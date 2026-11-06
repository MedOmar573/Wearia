from datetime import datetime, date
from sqlalchemy import Column, Integer, String, Float, Boolean, Date, DateTime, ForeignKey, Enum as SQLEnum
from sqlalchemy.orm import relationship
from app.database.base import Base
from app.models.enums import Occasion, Appreciation
from app.models.clothing import tenue_vetements

class Tenue(Base):
    __tablename__ = "tenues"

    id = Column(Integer, primary_key=True, index=True)
    dateCreation = Column(DateTime, default=datetime.utcnow, nullable=False)
    datePrevue = Column(Date, default=date.today, nullable=False, index=True)
    datePortee = Column(DateTime, nullable=True) # Renseigné si l'utilisateur l'a portée
    occasion = Column(SQLEnum(Occasion), default=Occasion.QUOTIDIEN, nullable=False)
    
    # Données météo associées
    temperatureCelsius = Column(Float, nullable=True)
    precipitations = Column(Boolean, default=False, nullable=False)
    descriptionMeteo = Column(String(100), nullable=True)
    
    explication = Column(String(500), nullable=True)
    scoreCompatibilite = Column(Integer, default=100, nullable=False) # Sur 100
    estGeneree = Column(Boolean, default=True, nullable=False)
    estFavorite = Column(Boolean, default=False, nullable=False)

    # Clés étrangères
    utilisateur_id = Column(Integer, ForeignKey("utilisateurs.id", ondelete="CASCADE"), nullable=False)
    evenement_id = Column(Integer, ForeignKey("evenements.id", ondelete="SET NULL"), nullable=True)
    style_id = Column(Integer, ForeignKey("styles_vestimentaires.id", ondelete="SET NULL"), nullable=True)

    # Relations
    utilisateur = relationship("Utilisateur", back_populates="tenues")
    evenement = relationship("Evenement", back_populates="tenues")
    style_vestimentaire = relationship("StyleVestimentaire", back_populates="tenues")
    vetements = relationship("Vetement", secondary=tenue_vetements, back_populates="tenues")
    feedback = relationship("Feedback", uselist=False, back_populates="tenue", cascade="all, delete-orphan")

class Feedback(Base):
    __tablename__ = "feedbacks"

    id = Column(Integer, primary_key=True, index=True)
    tenue_id = Column(Integer, ForeignKey("tenues.id", ondelete="CASCADE"), unique=True, nullable=False)
    appreciation = Column(SQLEnum(Appreciation), nullable=False)
    motifRejet = Column(String(255), nullable=True)
    dateFeedback = Column(DateTime, default=datetime.utcnow, nullable=False)

    tenue = relationship("Tenue", back_populates="feedback")

