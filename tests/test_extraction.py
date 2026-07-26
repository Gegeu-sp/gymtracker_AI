import io
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.database import Base, engine
import app.routers.extraction as extraction_router

@pytest.fixture(scope="module")
def client():
    Base.metadata.create_all(bind=engine)
    with TestClient(app) as c:
        yield c

def _fake_file():
    return {"file": ("referencia.jpg", io.BytesIO(b"fake-image-bytes"), "image/jpeg")}

def test_ocr_preview_returns_raw_text(client, monkeypatch):
    monkeypatch.setattr(extraction_router, "extract_text_from_image", lambda path: "SUPINO INCLINADO HALTER BANCO INCLINADO PIRÂMIDE 12-10-8")

    res = client.post("/extraction/ocr-preview", files=_fake_file())
    assert res.status_code == 200
    data = res.json()
    assert data["filename"] == "referencia.jpg"
    assert "SUPINO" in data["raw_text"]

def test_ocr_preview_returns_400_for_short_text(client, monkeypatch):
    monkeypatch.setattr(extraction_router, "extract_text_from_image", lambda path: "abc")

    res = client.post("/extraction/ocr-preview", files=_fake_file())
    assert res.status_code == 400
    assert res.json()["detail"] == "Imagem sem texto legível"

def _fake_parsed_workouts(n):
    return {
        "workouts": [
            {
                "name": f"Treino {i+1}",
                "notes": "⚠️ Alerta de teste",
                "exercises": [
                    {"name": "Supino Inclinado", "nickname": "RPE 8", "equipment": "Halter + Banco Inclinado",
                     "accessory": "90s", "method": "Pirâmide truncada (12-10-8)", "sets": 3, "reps": 10, "weight_kg": 40.0}
                ]
            }
            for i in range(n)
        ]
    }

def test_generate_creates_workouts_matching_days_per_week(client, monkeypatch):
    monkeypatch.setattr(extraction_router, "parse_reference_and_generate", lambda raw_text, request_data: _fake_parsed_workouts(3))

    res = client.post("/extraction/generate", data={
        "raw_text": "SUPINO INCLINADO HALTER BANCO INCLINADO PIRÂMIDE 12-10-8",
        "filename": "referencia.jpg",
        "goal": "hipertrofia",
        "level": "intermediario",
        "days_per_week": "3",
    })
    assert res.status_code == 200
    workouts = res.json()
    assert len(workouts) == 3
    for w in workouts:
        assert w["source"] == "image_reference"
        assert len(w["exercises"]) == 1
        assert w["exercises"][0]["name"] == "Supino Inclinado"
        assert "Extração de Referência" in w["notes"]
        assert "referencia.jpg" in w["notes"]

def test_generate_rejects_short_raw_text_without_calling_llm(client, monkeypatch):
    called = {"value": False}

    def fake_llm(raw_text, request_data):
        called["value"] = True
        return _fake_parsed_workouts(1)

    monkeypatch.setattr(extraction_router, "parse_reference_and_generate", fake_llm)

    res = client.post("/extraction/generate", data={"raw_text": "curto", "days_per_week": "1"})
    assert res.status_code == 400
    assert called["value"] is False

def test_generate_returns_500_when_llm_returns_no_workouts(client, monkeypatch):
    monkeypatch.setattr(extraction_router, "parse_reference_and_generate", lambda raw_text, request_data: {"workouts": []})

    res = client.post("/extraction/generate", data={
        "raw_text": "texto de referência válido com mais de dez caracteres",
        "days_per_week": "1",
    })
    assert res.status_code == 500
    assert res.json()["detail"] == "Falha ao gerar treinos a partir da referência."
