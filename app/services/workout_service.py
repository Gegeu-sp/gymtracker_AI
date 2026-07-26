import re
from typing import Callable, List
from sqlalchemy.orm import Session
from ..models import Exercise, Workout, WorkoutProgress
from .progression_service import calculate_exercise_progression

def safe_int(value, default=3):
    """Converte valor para int de forma segura, extraindo o primeiro número se for texto."""
    try:
        return int(value)
    except (ValueError, TypeError):
        if isinstance(value, str):
            match = re.search(r'\d+', value)
            if match:
                return int(match.group())
        return default

def safe_float(value, default=0.0):
    """Converte valor para float de forma segura."""
    try:
        return float(value)
    except (ValueError, TypeError):
        if isinstance(value, str):
            match = re.search(r'\d+\.?\d*', value)
            if match:
                return float(match.group())
        return default

def save_generated_workouts(
    db: Session,
    parsed: dict,
    build_notes: Callable[[dict], str],
    source: str = "llm",
) -> List[Workout]:
    """
    Persiste o dict {"workouts": [{"exercises": [...]}]} retornado pelo LLM,
    criando 1 Workout + N Exercise por dia. Compartilhado entre /workouts/generate
    e /extraction/generate. Levanta ValueError se o LLM não retornou treinos —
    o router chamador decide como converter isso em HTTPException.
    """
    if "workouts" not in parsed or not parsed["workouts"]:
        raise ValueError("LLM não retornou treinos válidos.")

    saved_workouts = []
    for day_data in parsed["workouts"]:
        workout = Workout(source=source, notes=build_notes(day_data))
        db.add(workout)
        db.commit()
        db.refresh(workout)

        for ex_data in day_data.get("exercises", []):
            db.add(Exercise(
                workout_id=workout.id,
                name=ex_data.get("name", "Exercício"),
                nickname=ex_data.get("nickname"),
                equipment=ex_data.get("equipment"),
                accessory=ex_data.get("accessory"),
                method=ex_data.get("method"),
                sets=safe_int(ex_data.get("sets"), 3),
                reps=safe_int(ex_data.get("reps"), 10),
                weight_kg=safe_float(ex_data.get("weight_kg"), 0.0),
                is_edited=False
            ))
        db.commit()
        saved_workouts.append(db.query(Workout).filter(Workout.id == workout.id).first())

    return saved_workouts

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
