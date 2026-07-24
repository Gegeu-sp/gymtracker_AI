from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Text, Boolean
from sqlalchemy.orm import relationship, Mapped, mapped_column
from datetime import datetime, timezone
from typing import Optional, List, cast
from .database import Base

class Workout(Base):
    __tablename__ = "workouts"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    date: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))
    source: Mapped[Optional[str]] = mapped_column(String, nullable=True)  # "image", "manual" ou "llm"
    image_path: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    professor_profile: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # Perfil do professor usado
    exercises: Mapped[List["Exercise"]] = relationship("Exercise", back_populates="workout", cascade="all, delete")

class Exercise(Base):
    __tablename__ = "exercises"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    workout_id: Mapped[int] = mapped_column(Integer, ForeignKey("workouts.id"))
    name: Mapped[str] = mapped_column(String)  # Nome do exercício
    nickname: Mapped[Optional[str]] = mapped_column(String, nullable=True)  # Apelido
    equipment: Mapped[Optional[str]] = mapped_column(String, nullable=True)  # Equipamentos
    accessory: Mapped[Optional[str]] = mapped_column(String, nullable=True)  # Acessórios
    method: Mapped[Optional[str]] = mapped_column(String, nullable=True)  # Método (drop-set, bi-set, etc)
    sets: Mapped[int] = mapped_column(Integer)
    reps: Mapped[int] = mapped_column(Integer)
    weight_kg: Mapped[float] = mapped_column(Float, default=0.0)
    
    # Execução real e edição pré-salvamento
    actual_weight_kg: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    actual_reps: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    actual_rpe: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    is_edited: Mapped[bool] = mapped_column(Boolean, default=False)

    workout: Mapped["Workout"] = relationship("Workout", back_populates="exercises")

    @property
    def volume(self) -> float:
        sets_val = cast(int, self.sets)
        reps_val = cast(int, self.reps)
        weight_val = cast(float, self.weight_kg) or 0.0
        return float(sets_val * reps_val * weight_val)

class WorkoutProgress(Base):
    __tablename__ = "workout_progress"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    exercise_name: Mapped[str] = mapped_column(String, index=True)
    date: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))
    actual_weight_kg: Mapped[float] = mapped_column(Float)
    actual_reps: Mapped[int] = mapped_column(Integer)
    actual_rpe: Mapped[float] = mapped_column(Float)
    suggested_weight_kg: Mapped[float] = mapped_column(Float)