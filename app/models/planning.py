from sqlalchemy import Column, Integer, String, Boolean, Date, ForeignKey, Enum as SQLEnum, UniqueConstraint
from sqlalchemy.orm import relationship
from app.database.base import Base
from app.models.enums import JourSemaine, Occasion

class RoutineHebdomadaire(Base):
    __tablename__ = "routines_hebdomadaires"

    id = Column(Integer, primary_key=True, index=True)
    utilisateur_id = Column(Integer, ForeignKey("utilisateurs.id", ondelete="CASCADE"), nullable=False)
    jourSemaine = Column(SQLEnum(JourSemaine), nullable=False)
    occasion = Column(SQLEnum(Occasion), nullable=False)
    estActive = Column(Boolean, default=True, nullable=False)

    utilisateur = relationship("Utilisateur", back_populates="routines")

    __table_args__ = (
        UniqueConstraint("utilisateur_id", "jourSemaine", name="uq_user_jour_routine"),
    )

class Evenement(Base):
    __tablename__ = "evenements"

    id = Column(Integer, primary_key=True, index=True)
    utilisateur_id = Column(Integer, ForeignKey("utilisateurs.id", ondelete="CASCADE"), nullable=False)
    titre = Column(String(150), nullable=False)
    date = Column(Date, nullable=False, index=True)
    occasion = Column(SQLEnum(Occasion), nullable=False)

    utilisateur = relationship("Utilisateur", back_populates="evenements")
    tenues = relationship("Tenue", back_populates="evenement")

