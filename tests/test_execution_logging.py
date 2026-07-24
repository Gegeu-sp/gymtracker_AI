import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.database import Base, engine, get_db
from app.models import Workout, Exercise, WorkoutProgress
from sqlalchemy.orm import sessionmaker

# Configuração de banco em memória para os testes
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

@pytest.fixture(scope="module")
def client():
    Base.metadata.create_all(bind=engine)
    with TestClient(app) as c:
        yield c

def test_pre_save_editing_endpoint(client):
    """Testa a edição pré-salvamento via PUT /workouts/{id}/edit"""
    # 1. Cria um treino manualmente para testar
    res_create = client.post("/workouts/", json={
        "notes": "Treino Inicial",
        "exercises": [
            {
                "name": "Supino Reto",
                "sets": 3,
                "reps": 10,
                "weight_kg": 40.0,
                "method": "Tradicional"
            }
        ]
    })
    assert res_create.status_code == 200
    workout_data = res_create.json()
    workout_id = workout_data["id"]
    exercise_id = workout_data["exercises"][0]["id"]

    # 2. Edita a prescrição antes de salvar
    res_edit = client.put(f"/workouts/{workout_id}/edit", json={
        "exercises": [
            {
                "exercise_id": exercise_id,
                "sets": 4,
                "reps": 12,
                "weight_kg": 45.0,
                "method": "Drop-set"
            }
        ]
    })
    assert res_edit.status_code == 200
    updated_data = res_edit.json()
    ex_updated = updated_data["exercises"][0]

    assert ex_updated["sets"] == 4
    assert ex_updated["reps"] == 12
    assert ex_updated["weight_kg"] == 45.0
    assert ex_updated["method"] == "Drop-set"
    assert ex_updated["is_edited"] is True

def test_log_execution_and_rpe_validation(client):
    """Testa o registro de execução real pós-treino e a validação estrita de RPE (1-10)"""
    res_create = client.post("/workouts/", json={
        "notes": "Treino Execução",
        "exercises": [
            {
                "name": "Agachamento Livre",
                "sets": 3,
                "reps": 10,
                "weight_kg": 60.0
            }
        ]
    })
    workout_id = res_create.json()["id"]
    exercise_id = res_create.json()["exercises"][0]["id"]

    # 1. Teste de falha com RPE inválido (RPE 12.0)
    res_invalid = client.post(f"/workouts/{workout_id}/log", json={
        "executions": [
            {
                "exercise_id": exercise_id,
                "actual_weight_kg": 60.0,
                "actual_reps": 10,
                "actual_rpe": 12.0  # Inválido!
            }
        ]
    })
    assert res_invalid.status_code == 422  # Validation Error

    # 2. Teste de sucesso com RPE válido (RPE 7.5)
    res_valid = client.post(f"/workouts/{workout_id}/log", json={
        "executions": [
            {
                "exercise_id": exercise_id,
                "actual_weight_kg": 60.0,
                "actual_reps": 10,
                "actual_rpe": 7.5
            }
        ]
    })
    assert res_valid.status_code == 200
    ex_logged = res_valid.json()["exercises"][0]
    assert ex_logged["actual_weight_kg"] == 60.0
    assert ex_logged["actual_reps"] == 10
    assert ex_logged["actual_rpe"] == 7.5

def test_get_workout_progression_endpoint(client):
    """Testa o endpoint GET /workouts/{id}/progression"""
    res_create = client.post("/workouts/", json={
        "notes": "Treino Progressão Teste",
        "exercises": [
            {
                "name": "Leg Press 45",
                "sets": 3,
                "reps": 10,
                "weight_kg": 100.0
            }
        ]
    })
    workout_id = res_create.json()["id"]
    exercise_id = res_create.json()["exercises"][0]["id"]

    # Loga uma execução com RPE baixo (6.5)
    client.post(f"/workouts/{workout_id}/log", json={
        "executions": [
            {
                "exercise_id": exercise_id,
                "actual_weight_kg": 100.0,
                "actual_reps": 10,
                "actual_rpe": 6.5
            }
        ]
    })

    # Consulta a progressão recomendada
    res_prog = client.get(f"/workouts/{workout_id}/progression")
    assert res_prog.status_code == 200
    progs = res_prog.json()
    assert len(progs) == 1
    prog_item = progs[0]
    assert prog_item["exercise_name"] == "Leg Press 45"
    assert prog_item["suggested_weight_kg"] == 105.0  # +5kg por ser exercício composto
    assert prog_item["progression_applied"] == 5.0
