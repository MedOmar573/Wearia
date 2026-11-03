from datetime import datetime
from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Enum as SQLEnum, Table
from sqlalchemy.orm import relationship
from app.database.base import Base
from app.models.enums import Coupe, Saison, StatutVetement

# Table d'association Tenue <-> Vetement (Many-to-Many)
tenue_vetements = Table(
    "tenue_vetements",
    Base.metadata,
    Column("tenue_id", Integer, ForeignKey("tenues.id", ondelete="CASCADE"), primary_key=True),
    Column("vetement_id", Integer, ForeignKey("vetements.id", ondelete="CASCADE"), primary_key=True)
)

class Vetement(Base):
    __tablename__ = "vetements"

    id = Column(Integer, primary_key=True, index=True)
    nom = Column(String(120), nullable=False)
    photoUrl = Column(String(500), nullable=False) # Exigé par BR07
    matiere = Column(String(100), nullable=True) # Saisie manuelle utilisateur
    coupe = Column(SQLEnum(Coupe), default=Coupe.REGULIERE, nullable=False)
    saison = Column(SQLEnum(Saison), default=Saison.TOUTE_SAISON, nullable=False)
    estThermique = Column(Boolean, default=False, nullable=False)
    estImpermeable = Column(Boolean, default=False, nullable=False)
    statut = Column(SQLEnum(StatutVetement), default=StatutVetement.DISPONIBLE, nullable=False)
    dateAjout = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Clés étrangères (BR07 : type et couleur obligatoires)
    utilisateur_id = Column(Integer, ForeignKey("utilisateurs.id", ondelete="CASCADE"), nullable=False)
    type_vetement_id = Column(Integer, ForeignKey("types_vetement.id"), nullable=False)
    couleur_id = Column(Integer, ForeignKey("couleurs.id"), nullable=False)
    style_id = Column(Integer, ForeignKey("styles_vestimentaires.id"), nullable=True)

    # Relations
    utilisateur = relationship("Utilisateur", back_populates="vetements")
    type_vetement = relationship("TypeVetement", back_populates="vetements")
    couleur = relationship("Couleur", back_populates="vetements")
    style_vestimentaire = relationship("StyleVestimentaire", back_populates="vetements")
    tenues = relationship("Tenue", secondary=tenue_vetements, back_populates="vetements")

