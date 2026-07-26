from sqlalchemy.orm import Session
from ..models import Exercise, WorkoutProgress
from .progression_service import calculate_exercise_progression

def apply_execution_result(
    db: Session,
    exercise: Exercise,
    actual_weight_kg: float,
    actual_reps: int,
    actual_rpe: float
) -> None:
    """
    Grava a execução real de um exercício (carga, reps, RPE) e registra o histórico
    de evolução em `workout_progress`. Compartilhado entre o registro pós-treino agregado
    (`/workouts/{id}/log`) e o Modo Treino ao Vivo (`/live-session/{id}/finish`).
    """
    exercise.actual_weight_kg = actual_weight_kg
    exercise.actual_reps = actual_reps
    exercise.actual_rpe = actual_rpe

    prog = calculate_exercise_progression(
        exercise_id=exercise.id,
        exercise_name=exercise.name,
        target_reps=exercise.reps,
        base_weight_kg=exercise.weight_kg,
        last_actual_weight_kg=actual_weight_kg,
        last_actual_reps=actual_reps,
        last_actual_rpe=actual_rpe
    )

    db.add(WorkoutProgress(
        exercise_name=exercise.name,
        actual_weight_kg=actual_weight_kg,
        actual_reps=actual_reps,
        actual_rpe=actual_rpe,
        suggested_weight_kg=prog.suggested_weight_kg
    ))
