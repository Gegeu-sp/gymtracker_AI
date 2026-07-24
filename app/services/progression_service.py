from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session
from ..models import Exercise, WorkoutProgress
from ..schemas import ExerciseProgressionOut

# Exercícios compostos / multiarticulares que admitem incrementos maiores de +5.0kg
COMPOUND_EXERCISES = {
    "supino", "agachamento", "levantamento terra", "remada", "leg press", 
    "desenvolvimento", "puxada", "terra", "squat", "bench press", "deadlift"
}

def calculate_exercise_progression(
    exercise_id: int,
    exercise_name: str,
    target_reps: int,
    base_weight_kg: float,
    last_actual_weight_kg: Optional[float],
    last_actual_reps: Optional[int],
    last_actual_rpe: Optional[float]
) -> ExerciseProgressionOut:
    """
    Calcula a sobrecarga progressiva para um exercício individual baseando-se no histórico
    de execução real (Carga Real, Repetições Reais e RPE Percebido).
    
    Regras:
    - RPE < 8.0 e reps concluídas: Incremento de +2.5kg (isolados) ou +5.0kg (compostos).
    - 8.0 <= RPE <= 9.0: Mantém a carga.
    - RPE > 9.0 ou reps incompletas: Mantém a carga ou sugere ajuste.
    - TRAVA DE SEGURANÇA DE 120%: A carga sugerida NUNCA pode exceder 1.20x a última carga real executada.
    """
    if last_actual_weight_kg is None or last_actual_weight_kg <= 0:
        # Sem histórico prévio de execução real: sugere a carga base da prescrição
        return ExerciseProgressionOut(
            exercise_id=exercise_id,
            exercise_name=exercise_name,
            last_weight_kg=None,
            last_reps=None,
            last_rpe=None,
            suggested_weight_kg=round(base_weight_kg, 1),
            progression_applied=0.0,
            safety_cap_applied=False,
            notes="Primeira sessão registrada: Mantendo carga recomendada inicial."
        )

    # Identifica o tipo de exercício para definir o passo do incremento
    name_lower = exercise_name.lower()
    is_compound = any(comp in name_lower for comp in COMPOUND_EXERCISES)
    increment_step = 5.0 if is_compound else 2.5

    actual_rpe = last_actual_rpe if last_actual_rpe is not None else 8.0
    actual_reps = last_actual_reps if last_actual_reps is not None else target_reps

    notes = ""
    safety_cap_applied = False

    if actual_rpe < 8.0 and actual_reps >= target_reps:
        raw_suggested = last_actual_weight_kg + increment_step
        delta = increment_step
        notes = f"Sobrecarga progressiva recomendada (+{increment_step}kg) pois RPE foi {actual_rpe:.1f} (< 8.0)."
    elif 8.0 <= actual_rpe <= 9.0:
        raw_suggested = last_actual_weight_kg
        delta = 0.0
        notes = f"Mantendo carga atual de {last_actual_weight_kg}kg pois RPE está na zona ideal ({actual_rpe:.1f})."
    else:
        # RPE > 9.0 ou repetições não atingiram a meta
        raw_suggested = last_actual_weight_kg
        delta = 0.0
        if actual_reps < target_reps:
            notes = f"Mantendo carga de {last_actual_weight_kg}kg para consolidar repetições alvo ({actual_reps}/{target_reps} concluídas)."
        else:
            notes = f"Mantendo carga de {last_actual_weight_kg}kg pois o esforço percebido foi elevado (RPE {actual_rpe:.1f})."

    # TRAVA DE SEGURANÇA DE 120%: Carga sugerida não pode exceder 120% da última carga real
    max_safety_limit = round(last_actual_weight_kg * 1.20, 1)
    if raw_suggested > max_safety_limit:
        suggested_weight_kg = max_safety_limit
        safety_cap_applied = True
        notes += f" ⚠️ Trava de segurança de 120% aplicada (máximo {max_safety_limit}kg)."
    else:
        suggested_weight_kg = round(raw_suggested, 1)

    return ExerciseProgressionOut(
        exercise_id=exercise_id,
        exercise_name=exercise_name,
        last_weight_kg=last_actual_weight_kg,
        last_reps=last_actual_reps,
        last_rpe=last_actual_rpe,
        suggested_weight_kg=suggested_weight_kg,
        progression_applied=delta,
        safety_cap_applied=safety_cap_applied,
        notes=notes
    )

def get_workout_progression_suggestions(db: Session, workout_id: int) -> List[ExerciseProgressionOut]:
    """
    Busca os exercícios do treino informado e calcula as sugestões de progressão de carga
    com base no histórico em `workout_progress` ou execuções anteriores no banco.
    """
    exercises = db.query(Exercise).filter(Exercise.workout_id == workout_id).all()
    results = []

    for ex in exercises:
        # Procura o último registro de evolução para o mesmo nome de exercício
        last_progress = (
            db.query(WorkoutProgress)
            .filter(WorkoutProgress.exercise_name.ilike(ex.name))
            .order_by(WorkoutProgress.date.desc())
            .first()
        )

        last_weight = last_progress.actual_weight_kg if last_progress else ex.actual_weight_kg
        last_reps = last_progress.actual_reps if last_progress else ex.actual_reps
        last_rpe = last_progress.actual_rpe if last_progress else ex.actual_rpe

        prog = calculate_exercise_progression(
            exercise_id=ex.id,
            exercise_name=ex.name,
            target_reps=ex.reps,
            base_weight_kg=ex.weight_kg,
            last_actual_weight_kg=last_weight,
            last_actual_reps=last_reps,
            last_actual_rpe=last_rpe
        )
        results.append(prog)

    return results
