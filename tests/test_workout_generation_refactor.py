import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.database import Base, engine
import app.routers.workout as workout_router

@pytest.fixture(scope="module")
def client():
    Base.metadata.create_all(bind=engine)
    with TestClient(app) as c:
        yield c

def test_generate_endpoint_preserves_notes_format_after_refactor(client, monkeypatch):
    """O refactor para save_generated_workouts não pode mudar a notes/response observável."""
    monkeypatch.setattr(workout_router, "generate_workout", lambda request_dict: {
        "workouts": [
            {"name": "Treino A", "exercises": [
                {"name": "Supino Reto", "sets": 3, "reps": 10, "weight_kg": 40.0}
            ]},
            {"name": "Treino B", "exercises": [
                {"name": "Agachamento Livre", "sets": 4, "reps": 8, "weight_kg": 80.0}
            ]},
        ]
    })

    res = client.post("/workouts/generate", json={
        "professor_name": "Prof. Ana", "goal": "forca", "level": "avancado", "days_per_week": 2
    })
    assert res.status_code == 200
    workouts = res.json()
    assert len(workouts) == 2
    assert workouts[0]["notes"] == "🤖 Prof. Prof. Ana | Objetivo: Forca | Nível: Avancado"
    assert workouts[0]["source"] == "llm"

def test_generate_endpoint_tolerates_invalid_sets_via_safe_conversion(client, monkeypatch):
    """
    Antes do refactor, um "sets": "3-4" (formato que o prompt proíbe mas o LLM pode
    ocasionalmente violar) causava 500 não tratado via int("3-4"). Depois do refactor,
    safe_int extrai o primeiro número em vez de quebrar.
    """
    monkeypatch.setattr(workout_router, "generate_workout", lambda request_dict: {
        "workouts": [
            {"name": "Treino C", "exercises": [
                {"name": "Remada Curvada", "sets": "3-4", "reps": "8-12", "weight_kg": 50.0}
            ]}
        ]
    })

    res = client.post("/workouts/generate", json={"goal": "hipertrofia", "days_per_week": 1})
    assert res.status_code == 200
    ex = res.json()[0]["exercises"][0]
    assert ex["sets"] == 3
    assert ex["reps"] == 8

def test_generate_endpoint_returns_500_when_llm_fails(client, monkeypatch):
    monkeypatch.setattr(workout_router, "generate_workout", lambda request_dict: {"workouts": []})

    res = client.post("/workouts/generate", json={"goal": "hipertrofia", "days_per_week": 1})
    assert res.status_code == 500
    assert res.json()["detail"] == "Falha ao gerar treinos com LLM."
