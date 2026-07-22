from pydantic import BaseModel, model_validator
from typing import Optional, List
from datetime import datetime

class ExerciseBase(BaseModel):
    name: str
    nickname: Optional[str] = None
    equipment: Optional[str] = None
    accessory: Optional[str] = None
    method: Optional[str] = None
    sets: int
    reps: int
    weight_kg: float = 0.0

class ExerciseCreate(ExerciseBase):
    pass

class ExerciseOut(ExerciseBase):
    id: int
    workout_id: int

    @property
    def volume(self) -> float:
        return float(self.sets * self.reps * (self.weight_kg or 0.0))

    class Config:
        from_attributes = True

class WorkoutCreate(BaseModel):
    exercises: List[ExerciseCreate]
    notes: Optional[str] = None

# Schema unificado para geração (Perfil do Professor + Aluno)
class WorkoutGenerationRequest(BaseModel):
    professor_name: Optional[str] = None
    goal: str = "hipertrofia"
    level: str = "intermediario"
    days_per_week: int = 1  # 1 a 6 treinos
    specialization: Optional[str] = None
    training_philosophy: Optional[str] = None
    preferred_methods: Optional[str] = None
    rest_time: Optional[str] = None
    custom_instructions: Optional[str] = None

class WorkoutOut(BaseModel):
    id: int
    date: datetime
    source: str
    notes: Optional[str] = None
    exercises: List[ExerciseOut]
    
    total_volume: float = 0.0
    total_exercises: int = 0
    total_sets: int = 0
    total_reps: int = 0

    @model_validator(mode='after')
    def calculate_totals(self) -> 'WorkoutOut':
        if self.exercises:
            self.total_exercises = len(self.exercises)
            self.total_sets = sum(ex.sets for ex in self.exercises)
            self.total_reps = sum(ex.sets * ex.reps for ex in self.exercises)
            self.total_volume = sum(ex.sets * ex.reps * (ex.weight_kg or 0.0) for ex in self.exercises)
        return self

    class Config:
        from_attributes = True