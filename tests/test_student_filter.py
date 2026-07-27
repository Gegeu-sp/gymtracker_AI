import io
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.database import Base, engine
import app.routers.image as image_router
import app.routers.workout as workout_router
import app.routers.extraction as extraction_router

@pytest.fixture(scope="module")
def client():
    Base.metadata.create_all(bind=engine)
    with TestClient(app) as c:
        yield c

def _fake_file(name="referencia.jpg"):
    return {"file": (name, io.BytesIO(b"fake-image-bytes"), "image/jpeg")}

def test_manual_create_stores_student_name(client):
    res = client.post("/workouts/", json={
        "student_name": "Ana Estudante",
        "notes": "Treino Teste",
        "exercises": [{"name": "Supino Reto", "sets": 3, "reps": 10, "weight_kg": 40.0}]
    })
    assert res.status_code == 200
    assert res.json()["student_name"] == "Ana Estudante"

def test_generate_endpoint_propagates_student_name(client, monkeypatch):
    monkeypatch.setattr(workout_router, "generate_workout", lambda request_dict: {
        "workouts": [{"name": "Treino A", "exercises": [
            {"name": "Agachamento Livre", "sets": 3, "reps": 10, "weight_kg": 60.0}
        ]}]
    })

    res = client.post("/workouts/generate", json={
        "student_name": "Bruno Estudante", "goal": "hipertrofia", "days_per_week": 1
    })
    assert res.status_code == 200
    assert res.json()[0]["student_name"] == "Bruno Estudante"

def test_image_upload_propagates_student_name(client, monkeypatch):
    monkeypatch.setattr(image_router, "extract_text_from_image", lambda path: "texto de treino extraído via OCR, com mais de dez caracteres")
    monkeypatch.setattr(image_router, "parse_workout_from_text", lambda raw_text: {
        "workouts": [{"exercises": [{"name": "Remada Curvada", "sets": 3, "reps": 10, "weight_kg": 50.0}]}]
    })

    res = client.post("/image/upload", files=_fake_file(), data={"student_name": "Carla Estudante"})
    assert res.status_code == 200
    assert res.json()["student_name"] == "Carla Estudante"

def test_extraction_generate_propagates_student_name(client, monkeypatch):
    monkeypatch.setattr(extraction_router, "parse_reference_and_generate", lambda raw_text, request_data: {
        "workouts": [{"name": "Treino A", "exercises": [
            {"name": "Supino Inclinado", "sets": 3, "reps": 10, "weight_kg": 40.0}
        ]}]
    })

    res = client.post("/extraction/generate", data={
        "raw_text": "texto de referência válido com mais de dez caracteres",
        "days_per_week": "1",
        "student_name": "Diego Estudante",
    })
    assert res.status_code == 200
    assert res.json()[0]["student_name"] == "Diego Estudante"

def test_list_students_returns_distinct_sorted_without_blanks(client):
    client.post("/workouts/", json={"student_name": "Zeca", "exercises": [{"name": "X", "sets": 1, "reps": 1, "weight_kg": 0.0}]})
    client.post("/workouts/", json={"student_name": "Zeca", "exercises": [{"name": "X", "sets": 1, "reps": 1, "weight_kg": 0.0}]})
    client.post("/workouts/", json={"student_name": "Amanda", "exercises": [{"name": "X", "sets": 1, "reps": 1, "weight_kg": 0.0}]})
    client.post("/workouts/", json={"exercises": [{"name": "X", "sets": 1, "reps": 1, "weight_kg": 0.0}]})  # sem student_name

    res = client.get("/workouts/students")
    assert res.status_code == 200
    students = res.json()
    assert students.count("Zeca") == 1
    assert "Amanda" in students
    assert "" not in students
    assert None not in students
    assert students.index("Amanda") < students.index("Zeca")

def test_list_workouts_filters_by_student_name_case_insensitive(client):
    client.post("/workouts/", json={"student_name": "Eduarda Filtro", "exercises": [{"name": "X", "sets": 1, "reps": 1, "weight_kg": 0.0}]})
    client.post("/workouts/", json={"student_name": "Outro Aluno", "exercises": [{"name": "X", "sets": 1, "reps": 1, "weight_kg": 0.0}]})

    res = client.get("/workouts/", params={"student_name": "eduarda filtro"})
    assert res.status_code == 200
    workouts = res.json()
    assert len(workouts) >= 1
    assert all(w["student_name"] == "Eduarda Filtro" for w in workouts)

def test_view_page_filters_by_student_name(client):
    client.post("/workouts/", json={"student_name": "Fabio Historico", "exercises": [{"name": "X", "sets": 1, "reps": 1, "weight_kg": 0.0}]})

    res = client.get("/workouts/view", params={"student_name": "Fabio Historico"})
    assert res.status_code == 200
    assert "Fabio Historico" in res.text
