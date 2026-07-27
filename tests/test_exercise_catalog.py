import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.database import Base, engine
from app.services.exercise_catalog import get_muscle_group, get_canonical_name, resolve_catalog_entry

@pytest.fixture(scope="module")
def client():
    Base.metadata.create_all(bind=engine)
    with TestClient(app) as c:
        yield c

# --- Testes unitários do catálogo ---

@pytest.mark.parametrize("name,expected_group", [
    ("Supino Reto", "Peito"),
    ("Supino Reto com Barra", "Peito"),
    ("Agachamento Livre", "Pernas"),
    ("Rosca Direta", "Bíceps"),
    ("Tríceps Pulley", "Tríceps"),
    ("Remada Curvada", "Costas"),
    ("Elevação Lateral", "Ombros"),
    ("Panturrilha em Pé", "Panturrilha"),
    ("Prancha Abdominal", "Core"),
    ("Um Exercício Totalmente Inventado Xyz", "Outros"),
])
def test_get_muscle_group_recognizes_common_exercises(name, expected_group):
    assert get_muscle_group(name) == expected_group

def test_get_canonical_name_unifies_name_variants():
    """Variações de escrita do MESMO exercício devem resolver para o mesmo nome canônico."""
    assert get_canonical_name("Supino Reto") == get_canonical_name("Supino Reto com Barra")
    assert get_canonical_name("SUPINO RETO") == get_canonical_name("supino reto")
    assert get_canonical_name("Agachamento Livre") == get_canonical_name("Agachamento")

def test_get_canonical_name_keeps_different_exercises_separate():
    """Exercícios genuinamente diferentes (mesmo do mesmo grupo muscular) NÃO devem unir histórico."""
    assert get_canonical_name("Supino Reto") != get_canonical_name("Crucifixo")
    assert get_canonical_name("Supino Reto") != get_canonical_name("Supino Inclinado")

def test_resolve_catalog_entry_prefers_more_specific_alias():
    """'Supino Inclinado' não pode cair no bucket genérico de 'Supino Reto'."""
    entry = resolve_catalog_entry("Supino Inclinado com Halteres")
    assert entry is not None
    assert entry["canonical_name"] == "Supino Inclinado"

def test_get_canonical_name_falls_back_to_normalized_name_for_unknown_exercise():
    assert get_canonical_name("Exercício Bem Exótico 123") == get_canonical_name("exercício bem exótico 123")

# --- Testes de integração: muscle_group populado + progressão por identidade canônica ---

def _create_workout(client, exercise_name, weight_kg=60.0):
    res = client.post("/workouts/", json={
        "notes": "Teste catálogo",
        "exercises": [{"name": exercise_name, "sets": 3, "reps": 10, "weight_kg": weight_kg}]
    })
    assert res.status_code == 200
    return res.json()

def test_manual_workout_creation_populates_muscle_group(client):
    workout = _create_workout(client, "Rosca Direta")
    assert workout["exercises"][0]["name"] == "Rosca Direta"
    # muscle_group não está no schema de resposta (WorkoutOut/ExerciseOut) — validado via banco:
    from app.database import SessionLocal
    from app.models import Exercise
    db = SessionLocal()
    try:
        ex = db.query(Exercise).filter(Exercise.id == workout["exercises"][0]["id"]).first()
        assert ex.muscle_group == "Bíceps"
    finally:
        db.close()

def test_progression_carries_over_across_exercise_name_variants(client):
    """RPE baixo em 'Supino Reto' deve influenciar a progressão sugerida para 'Supino Reto com Barra'."""
    w1 = _create_workout(client, "Supino Reto", weight_kg=60.0)
    ex1_id = w1["exercises"][0]["id"]
    res_log = client.post(f"/workouts/{w1['id']}/log", json={
        "executions": [{"exercise_id": ex1_id, "actual_weight_kg": 60.0, "actual_reps": 10, "actual_rpe": 6.5}]
    })
    assert res_log.status_code == 200

    w2 = _create_workout(client, "Supino Reto com Barra", weight_kg=60.0)
    res_prog = client.get(f"/workouts/{w2['id']}/progression")
    assert res_prog.status_code == 200
    prog = res_prog.json()[0]
    assert prog["last_weight_kg"] == 60.0
    assert prog["suggested_weight_kg"] == 65.0  # +5kg, RPE 6.5 < 8.0, exercício composto

def test_progression_does_not_leak_between_different_exercises(client):
    """Histórico de 'Levantamento Terra' não pode contaminar a sugestão de 'Crucifixo' (exercício não relacionado)."""
    w1 = _create_workout(client, "Levantamento Terra", weight_kg=100.0)
    ex1_id = w1["exercises"][0]["id"]
    client.post(f"/workouts/{w1['id']}/log", json={
        "executions": [{"exercise_id": ex1_id, "actual_weight_kg": 100.0, "actual_reps": 10, "actual_rpe": 6.0}]
    })

    w2 = _create_workout(client, "Crucifixo", weight_kg=15.0)
    res_prog = client.get(f"/workouts/{w2['id']}/progression")
    assert res_prog.status_code == 200
    prog = res_prog.json()[0]
    assert prog["last_weight_kg"] is None
    assert prog["notes"] == "Primeira sessão registrada: Mantendo carga recomendada inicial."
