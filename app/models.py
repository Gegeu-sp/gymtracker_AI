from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from datetime import datetime
from .database import Base

class Workout(Base):
    __tablename__ = "workouts"
    id = Column(Integer, primary_key=True, index=True)
    date = Column(DateTime, default=datetime.utcnow)
    source = Column(String)  # "image", "manual" ou "llm"
    image_path = Column(String, nullable=True)
    notes = Column(Text, nullable=True)
    professor_profile = Column(Text, nullable=True)  # Perfil do professor usado
    exercises = relationship("Exercise", back_populates="workout", cascade="all, delete")

class Exercise(Base):
    __tablename__ = "exercises"
    id = Column(Integer, primary_key=True, index=True)
    workout_id = Column(Integer, ForeignKey("workouts.id"))
    name = Column(String)  # Nome do exercício
    nickname = Column(String, nullable=True)  # Apelido
    equipment = Column(String, nullable=True)  # Equipamentos
    accessory = Column(String, nullable=True)  # Acessórios
    method = Column(String, nullable=True)  # Método (drop-set, bi-set, etc)
    sets = Column(Integer)
    reps = Column(Integer)
    weight_kg = Column(Float, default=0.0)
    workout = relationship("Workout", back_populates="exercises")

    @property
    def volume(self) -> float:
        return float(self.sets * self.reps * (self.weight_kg or 0.0))