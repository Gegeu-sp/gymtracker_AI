import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.database import Base, engine

@pytest.fixture(scope="module")
def client():
    Base.metadata.create_all(bind=engine)
    with TestClient(app) as c:
        yield c

def _create_workout(client, exercises):
    res = client.post("/workouts/", json={"notes": "Treino Ao Vivo", "exercises": exercises})
    assert res.status_code == 200
    return res.json()

def test_start_live_session_is_idempotent(client):
    """POST /start marca o início da sessão e não sobrescreve em chamadas repetidas."""
    workout = _create_workout(client, [
        {"name": "Supino Reto", "sets": 3, "reps": 10, "weight_kg": 40.0}
    ])
    workout_id = workout["id"]

    res_first = client.post(f"/live-session/{workout_id}/start")
    assert res_first.status_code == 200
    started_at = res_first.json()["started_at"]
    assert started_at is not None

    res_second = client.post(f"/live-session/{workout_id}/start")
    assert res_second.status_code == 200
    assert res_second.json()["started_at"] == started_at

def test_log_individual_sets_accumulates(client):
    """Cada série registrada soma ao estado da sessão com set_number incremental."""
    workout = _create_workout(client, [
        {"name": "Agachamento Livre", "sets": 3, "reps": 10, "weight_kg": 60.0}
    ])
    workout_id = workout["id"]
    exercise_id = workout["exercises"][0]["id"]

    for i, (weight, reps) in enumerate([(60.0, 10), (62.5, 8), (62.5, 7)], start=1):
        res = client.post(f"/live-session/{workout_id}/sets", json={
            "exercise_id": exercise_id, "weight_kg": weight, "reps": reps, "rpe": 8.0
        })
        assert res.status_code == 200
        assert res.json()["set_number"] == i

    res_state = client.get(f"/live-session/{workout_id}")
    assert res_state.status_code == 200
    state = res_state.json()
    completed = state["exercises"][0]["completed_sets"]
    assert len(completed) == 3
    assert [s["set_number"] for s in completed] == [1, 2, 3]

def test_set_rpe_validation(client):
    """RPE fora de 1.0-10.0 deve ser rejeitado com 422, igual ao registro agregado."""
    workout = _create_workout(client, [
        {"name": "Remada Curvada", "sets": 3, "reps": 10, "weight_kg": 50.0}
    ])
    workout_id = workout["id"]
    exercise_id = workout["exercises"][0]["id"]

    res_invalid = client.post(f"/live-session/{workout_id}/sets", json={
        "exercise_id": exercise_id, "weight_kg": 50.0, "reps": 10, "rpe": 11.0
    })
    assert res_invalid.status_code == 422

def test_finish_session_aggregates_to_exercise_and_progress(client):
    """Finalizar a sessão grava a última série em Exercise.actual_* e alimenta a progressão."""
    workout = _create_workout(client, [
        {"name": "Leg Press 45", "sets": 2, "reps": 10, "weight_kg": 100.0}
    ])
    workout_id = workout["id"]
    exercise_id = workout["exercises"][0]["id"]

    client.post(f"/live-session/{workout_id}/sets", json={
        "exercise_id": exercise_id, "weight_kg": 100.0, "reps": 10, "rpe": 8.5
    })
    res_last_set = client.post(f"/live-session/{workout_id}/sets", json={
        "exercise_id": exercise_id, "weight_kg": 100.0, "reps": 10, "rpe": 6.5
    })
    assert res_last_set.status_code == 200

    res_finish = client.post(f"/live-session/{workout_id}/finish")
    assert res_finish.status_code == 200
    finished_workout = res_finish.json()
    ex_out = finished_workout["exercises"][0]
    assert ex_out["actual_weight_kg"] == 100.0
    assert ex_out["actual_reps"] == 10
    assert ex_out["actual_rpe"] == 6.5

    res_prog = client.get(f"/workouts/{workout_id}/progression")
    assert res_prog.status_code == 200
    prog_item = res_prog.json()[0]
    assert prog_item["suggested_weight_kg"] == 105.0  # +5kg, RPE 6.5 < 8.0, exercício composto

def test_delete_set_allows_correction(client):
    """Uma série registrada por engano pode ser removida antes de finalizar a sessão."""
    workout = _create_workout(client, [
        {"name": "Rosca Direta", "sets": 3, "reps": 12, "weight_kg": 20.0}
    ])
    workout_id = workout["id"]
    exercise_id = workout["exercises"][0]["id"]

    res_wrong = client.post(f"/live-session/{workout_id}/sets", json={
        "exercise_id": exercise_id, "weight_kg": 999.0, "reps": 1, "rpe": 10.0
    })
    wrong_set_id = res_wrong.json()["id"]

    res_delete = client.delete(f"/live-session/{workout_id}/sets/{wrong_set_id}")
    assert res_delete.status_code == 204

    res_state = client.get(f"/live-session/{workout_id}")
    assert res_state.json()["exercises"][0]["completed_sets"] == []
