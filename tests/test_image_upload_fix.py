import io
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.database import Base, engine
import app.routers.image as image_router

@pytest.fixture(scope="module")
def client():
    Base.metadata.create_all(bind=engine)
    with TestClient(app) as c:
        yield c

def _fake_file():
    return {"file": ("treino.jpg", io.BytesIO(b"fake-image-bytes"), "image/jpeg")}

def test_upload_creates_workout_when_llm_returns_real_format(client, monkeypatch):
    """
    Regressão do bug: o LLM sempre responde no formato {"workouts": [{"exercises": [...]}]},
    nunca com "exercises" no nível raiz. Antes do fix, isso sempre disparava 400 mesmo com
    OCR/LLM funcionando perfeitamente.
    """
    monkeypatch.setattr(image_router, "extract_text_from_image", lambda path: "texto de treino extraído via OCR, com mais de dez caracteres")
    monkeypatch.setattr(image_router, "parse_workout_from_text", lambda raw_text: {
        "workouts": [
            {
                "name": "Treino A",
                "notes": "⚠️ Alerta de risco de teste",
                "exercises": [
                    {"name": "Supino Reto", "nickname": "RPE 8", "equipment": "Barra", "accessory": "90s", "method": "Tradicional", "sets": 3, "reps": 10, "weight_kg": 60.0},
                    {"name": "Agachamento Livre", "sets": 4, "reps": 8, "weight_kg": 80.0},
                    {"name": "Remada Curvada", "sets": 3, "reps": 10, "weight_kg": 50.0},
                ]
            }
        ]
    })

    res = client.post("/image/upload", files=_fake_file())
    assert res.status_code == 200
    data = res.json()
    assert data["total_exercises"] == 3
    assert data["exercises"][0]["name"] == "Supino Reto"
    assert "Extraído de: treino.jpg" in data["notes"]
    assert "Alerta de risco de teste" in data["notes"]

def test_upload_returns_400_when_llm_returns_no_workouts(client, monkeypatch):
    """Garante que o 400 ainda dispara quando de fato não há exercícios extraíveis."""
    monkeypatch.setattr(image_router, "extract_text_from_image", lambda path: "texto ilegível mas com mais de dez caracteres")
    monkeypatch.setattr(image_router, "parse_workout_from_text", lambda raw_text: {"workouts": []})

    res = client.post("/image/upload", files=_fake_file())
    assert res.status_code == 400
    assert res.json()["detail"] == "Nenhum exercício encontrado na imagem"

def test_upload_returns_400_when_ocr_text_too_short(client, monkeypatch):
    """Comportamento pré-existente preservado: texto de OCR muito curto continua 400."""
    monkeypatch.setattr(image_router, "extract_text_from_image", lambda path: "curto")

    res = client.post("/image/upload", files=_fake_file())
    assert res.status_code == 400
    assert res.json()["detail"] == "Imagem sem texto legível"
