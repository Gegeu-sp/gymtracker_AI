from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from datetime import datetime, timezone
from ..database import get_db
from ..models import Workout, Exercise, WorkoutSet
from ..schemas import (
    LiveSetLogRequest, WorkoutSetOut, LiveSessionStateOut, LiveExerciseStateOut, WorkoutOut
)
from ..services.workout_service import apply_execution_result

router = APIRouter(prefix="/live-session", tags=["live-session"])

def _get_workout_or_404(workout_id: int, db: Session) -> Workout:
    workout = db.query(Workout).filter(Workout.id == workout_id).first()
    if not workout:
        raise HTTPException(status_code=404, detail="Treino não encontrado.")
    return workout

def _build_session_state(workout: Workout) -> LiveSessionStateOut:
    exercises_state = [
        LiveExerciseStateOut(
            exercise_id=ex.id,
            exercise_name=ex.name,
            prescribed_sets=ex.sets,
            prescribed_reps=ex.reps,
            prescribed_weight_kg=ex.weight_kg,
            rest_seconds_target=ex.rest_seconds_target,
            completed_sets=ex.logged_sets
        )
        for ex in sorted(workout.exercises, key=lambda x: x.id)
    ]
    return LiveSessionStateOut(
        workout_id=workout.id,
        started_at=workout.live_session_started_at,
        finished_at=workout.live_session_finished_at,
        exercises=exercises_state
    )

@router.post("/{workout_id}/start", response_model=LiveSessionStateOut)
def start_live_session(workout_id: int, db: Session = Depends(get_db)):
    """Inicia (ou retoma, se já iniciada) a sessão de treino ao vivo."""
    workout = _get_workout_or_404(workout_id, db)
    if workout.live_session_started_at is None:
        workout.live_session_started_at = datetime.now(timezone.utc)
        workout.live_session_finished_at = None
        db.commit()
        db.refresh(workout)
    return _build_session_state(workout)

@router.get("/{workout_id}", response_model=LiveSessionStateOut)
def get_live_session_state(workout_id: int, db: Session = Depends(get_db)):
    """Retorna o estado atual da sessão (séries já registradas por exercício)."""
    workout = _get_workout_or_404(workout_id, db)
    return _build_session_state(workout)

@router.post("/{workout_id}/sets", response_model=WorkoutSetOut)
def log_live_set(workout_id: int, data: LiveSetLogRequest, db: Session = Depends(get_db)):
    """Registra uma série individual concluída durante o treino ao vivo."""
    workout = _get_workout_or_404(workout_id, db)
    exercise = db.query(Exercise).filter(
        Exercise.id == data.exercise_id,
        Exercise.workout_id == workout_id
    ).first()
    if not exercise:
        raise HTTPException(status_code=404, detail="Exercício não encontrado neste treino.")

    if workout.live_session_started_at is None:
        workout.live_session_started_at = datetime.now(timezone.utc)

    next_set_number = db.query(WorkoutSet).filter(WorkoutSet.exercise_id == exercise.id).count() + 1

    workout_set = WorkoutSet(
        exercise_id=exercise.id,
        set_number=next_set_number,
        weight_kg=data.weight_kg,
        reps=data.reps,
        rpe=data.rpe,
        rest_seconds_actual=data.rest_seconds_actual
    )
    db.add(workout_set)
    db.commit()
    db.refresh(workout_set)
    return workout_set

@router.delete("/{workout_id}/sets/{set_id}", status_code=204)
def delete_live_set(workout_id: int, set_id: int, db: Session = Depends(get_db)):
    """Remove uma série registrada por engano, permitindo corrigir durante a sessão."""
    workout_set = (
        db.query(WorkoutSet)
        .join(Exercise, WorkoutSet.exercise_id == Exercise.id)
        .filter(WorkoutSet.id == set_id, Exercise.workout_id == workout_id)
        .first()
    )
    if not workout_set:
        raise HTTPException(status_code=404, detail="Série não encontrada neste treino.")
    db.delete(workout_set)
    db.commit()

@router.post("/{workout_id}/finish", response_model=WorkoutOut)
def finish_live_session(workout_id: int, db: Session = Depends(get_db)):
    """
    Finaliza a sessão ao vivo: agrega a última série de cada exercício em
    `Exercise.actual_*` e `workout_progress`, alimentando a sobrecarga progressiva
    exatamente como o registro agregado (`/workouts/{id}/log`) já faz.
    """
    workout = _get_workout_or_404(workout_id, db)

    for exercise in workout.exercises:
        last_set = (
            db.query(WorkoutSet)
            .filter(WorkoutSet.exercise_id == exercise.id)
            .order_by(WorkoutSet.set_number.desc())
            .first()
        )
        if last_set is None:
            continue
        apply_execution_result(
            db, exercise,
            actual_weight_kg=last_set.weight_kg,
            actual_reps=last_set.reps,
            actual_rpe=last_set.rpe if last_set.rpe is not None else 8.0
        )

    workout.live_session_finished_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(workout)
    return workout
