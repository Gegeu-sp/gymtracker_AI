import pytest
from app.services.progression_service import calculate_exercise_progression

def test_progression_low_rpe_compound():
    """Testa se exercício composto com RPE < 8.0 recebe incremento de +5.0kg"""
    result = calculate_exercise_progression(
        exercise_id=1,
        exercise_name="Supino Reto com Barra",
        target_reps=10,
        base_weight_kg=50.0,
        last_actual_weight_kg=50.0,
        last_actual_reps=10,
        last_actual_rpe=7.0
    )
    assert result.suggested_weight_kg == 55.0
    assert result.progression_applied == 5.0
    assert result.safety_cap_applied is False

def test_progression_low_rpe_isolation():
    """Testa se exercício isolado com RPE < 8.0 recebe incremento de +2.5kg"""
    result = calculate_exercise_progression(
        exercise_id=2,
        exercise_name="Rosca Direta com Halteres",
        target_reps=12,
        base_weight_kg=15.0,
        last_actual_weight_kg=15.0,
        last_actual_reps=12,
        last_actual_rpe=6.5
    )
    assert result.suggested_weight_kg == 17.5
    assert result.progression_applied == 2.5
    assert result.safety_cap_applied is False

def test_progression_medium_rpe_maintains_weight():
    """Testa se RPE entre 8.0 e 9.0 mantém a carga atual sem incremento"""
    result = calculate_exercise_progression(
        exercise_id=3,
        exercise_name="Agachamento Livre",
        target_reps=8,
        base_weight_kg=80.0,
        last_actual_weight_kg=80.0,
        last_actual_reps=8,
        last_actual_rpe=8.5
    )
    assert result.suggested_weight_kg == 80.0
    assert result.progression_applied == 0.0
    assert result.safety_cap_applied is False

def test_progression_high_rpe_or_missed_reps():
    """Testa se RPE elevado (>9.0) ou repetições incompletas mantêm a carga"""
    result = calculate_exercise_progression(
        exercise_id=4,
        exercise_name="Desenvolvimento com Halteres",
        target_reps=10,
        base_weight_kg=24.0,
        last_actual_weight_kg=24.0,
        last_actual_reps=8,  # Meta era 10
        last_actual_rpe=9.5
    )
    assert result.suggested_weight_kg == 24.0
    assert result.progression_applied == 0.0

def test_safety_cap_120_percent_limit():
    """Testa se a trava de segurança limita a carga sugerida a no máximo 120% da última carga real"""
    # Se a última carga foi 20kg, 120% é 24kg
    # Se uma tentativa teórica tentasse sugerir 30kg, a trava deve limitar a 24kg
    result = calculate_exercise_progression(
        exercise_id=5,
        exercise_name="Supino Inclinado com Barra",
        target_reps=10,
        base_weight_kg=20.0,
        last_actual_weight_kg=20.0,
        last_actual_reps=10,
        last_actual_rpe=5.0
    )
    # 20 + 5 = 25. Mas 120% de 20 é 24.0kg. Logo deve limitar em 24.0kg.
    assert result.suggested_weight_kg == 24.0
    assert result.safety_cap_applied is True
