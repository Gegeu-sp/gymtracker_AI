from pydantic import BaseModel, model_validator, field_validator
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
    
    # Execução real e estado de edição
    actual_weight_kg: Optional[float] = None
    actual_reps: Optional[int] = None
    actual_rpe: Optional[float] = None
    is_edited: bool = False

class ExerciseCreate(ExerciseBase):
    pass

class ExerciseOut(ExerciseBase):
    id: int
    workout_id: int

    @property
    def volume(self) -> float:
        return self.sets * self.reps * (self.weight_kg or 0.0)

    class Config:
        from_attributes = True

class ExerciseEditRequest(BaseModel):
    exercise_id: int
    sets: Optional[int] = None
    reps: Optional[int] = None
    weight_kg: Optional[float] = None
    method: Optional[str] = None

class WorkoutEditRequest(BaseModel):
    exercises: List[ExerciseEditRequest]
    notes: Optional[str] = None

class ExerciseExecutionItem(BaseModel):
    exercise_id: int
    actual_weight_kg: float
    actual_reps: int
    actual_rpe: float

    @field_validator('actual_rpe')
    @classmethod
    def validate_rpe(cls, v: float) -> float:
        if not (1.0 <= v <= 10.0):
            raise ValueError('O RPE percebido deve estar entre 1.0 e 10.0')
        return v

    @field_validator('actual_weight_kg', 'actual_reps')
    @classmethod
    def validate_non_negative(cls, v: float) -> float:
        if v < 0:
            raise ValueError('Valores de carga e repetições não podem ser negativos')
        return v

class WorkoutExecutionRequest(BaseModel):
    executions: List[ExerciseExecutionItem]

class ExerciseProgressionOut(BaseModel):
    exercise_id: int
    exercise_name: str
    last_weight_kg: Optional[float] = None
    last_reps: Optional[int] = None
    last_rpe: Optional[float] = None
    suggested_weight_kg: float
    progression_applied: float  # Delta em kg (+2.5, +5.0, 0.0, etc.)
    safety_cap_applied: bool = False
    notes: str

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

class ReferenceRow(BaseModel):
    exercise: str = ""
    nickname: str = ""
    equipment: str = ""
    accessory: str = ""
    method: str = ""

class OcrPreviewOut(BaseModel):
    raw_text: str
    filename: str
    rows: List[ReferenceRow] = []

class WorkoutSetOut(BaseModel):
    id: int
    exercise_id: int
    set_number: int
    weight_kg: float
    reps: int
    rpe: Optional[float] = None
    completed_at: datetime
    rest_seconds_actual: Optional[int] = None

    class Config:
        from_attributes = True

class LiveSetLogRequest(BaseModel):
    exercise_id: int
    weight_kg: float
    reps: int
    rpe: Optional[float] = None
    rest_seconds_actual: Optional[int] = None

    @field_validator('rpe')
    @classmethod
    def validate_rpe(cls, v: Optional[float]) -> Optional[float]:
        if v is not None and not (1.0 <= v <= 10.0):
            raise ValueError('O RPE percebido deve estar entre 1.0 e 10.0')
        return v

    @field_validator('weight_kg', 'reps')
    @classmethod
    def validate_non_negative(cls, v: float) -> float:
        if v < 0:
            raise ValueError('Valores de carga e repetições não podem ser negativos')
        return v

class LiveExerciseStateOut(BaseModel):
    exercise_id: int
    exercise_name: str
    prescribed_sets: int
    prescribed_reps: int
    prescribed_weight_kg: float
    rest_seconds_target: Optional[int] = None
    completed_sets: List[WorkoutSetOut] = []

    class Config:
        from_attributes = True

class LiveSessionStateOut(BaseModel):
    workout_id: int
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None
    exercises: List[LiveExerciseStateOut]

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