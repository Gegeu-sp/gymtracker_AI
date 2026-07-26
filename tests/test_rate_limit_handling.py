import io
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.database import Base, engine
from app.services.llm_service import LLMRateLimitError, _build_rate_limit_message
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

def test_build_rate_limit_message_parses_minutes_and_seconds():
    err = Exception("... Please try again in 8m51.36s. Need more tokens?")
    message = _build_rate_limit_message(err)
    assert "8 min 51s" in message
    assert "Limite" in message

def test_build_rate_limit_message_falls_back_without_duration():
    err = Exception("rate_limit_exceeded, no duration info here")
    message = _build_rate_limit_message(err)
    assert "Limite" in message

def test_image_upload_returns_429_on_rate_limit(client, monkeypatch):
    monkeypatch.setattr(image_router, "extract_text_from_image", lambda path: "texto de treino extraído via OCR, com mais de dez caracteres")

    def fake_llm(raw_text):
        raise LLMRateLimitError("⏳ Limite diário de tokens da IA (Groq) atingido. Tente novamente em ~9 min.")

    monkeypatch.setattr(image_router, "parse_workout_from_text", fake_llm)

    res = client.post("/image/upload", files=_fake_file())
    assert res.status_code == 429
    assert "Limite" in res.json()["detail"]

def test_workouts_generate_returns_429_on_rate_limit(client, monkeypatch):
    def fake_llm(request_dict):
        raise LLMRateLimitError("⏳ Limite diário de tokens da IA (Groq) atingido.")

    monkeypatch.setattr(workout_router, "generate_workout", fake_llm)

    res = client.post("/workouts/generate", json={"goal": "hipertrofia", "days_per_week": 1})
    assert res.status_code == 429
    assert "Limite" in res.json()["detail"]

def test_extraction_ocr_preview_returns_429_on_rate_limit(client, monkeypatch):
    monkeypatch.setattr(extraction_router, "extract_text_from_image", lambda path: "texto de referência com mais de dez caracteres")

    def fake_structure(raw_text):
        raise LLMRateLimitError("⏳ Limite diário de tokens da IA (Groq) atingido.")

    monkeypatch.setattr(extraction_router, "structure_reference_table", fake_structure)

    res = client.post("/extraction/ocr-preview", files=_fake_file())
    assert res.status_code == 429
    assert "Limite" in res.json()["detail"]

def test_extraction_generate_returns_429_on_rate_limit(client, monkeypatch):
    def fake_llm(raw_text, request_data):
        raise LLMRateLimitError("⏳ Limite diário de tokens da IA (Groq) atingido. Tente novamente em ~9 min.")

    monkeypatch.setattr(extraction_router, "parse_reference_and_generate", fake_llm)

    res = client.post("/extraction/generate", data={
        "raw_text": "texto de referência válido com mais de dez caracteres",
        "days_per_week": "1",
    })
    assert res.status_code == 429
    assert "Limite" in res.json()["detail"]
