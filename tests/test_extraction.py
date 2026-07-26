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

def test_ocr_preview_returns_structured_rows(client, monkeypatch):
    monkeypatch.setattr(extraction_router, "extract_text_from_image", lambda path: "SUPIN0 INCLINADO HALTER BANCO INCLINADO PIRAMIDE 12-10-8")
    monkeypatch.setattr(extraction_router, "structure_reference_table", lambda raw_text: [
        {"exercise": "Supino", "nickname": "Inclinado", "equipment": "Halter", "accessory": "Banco Inclinado", "method": "Pirâmide truncada crescente 12-10-8"}
    ])

    res = client.post("/extraction/ocr-preview", files=_fake_file())
    assert res.status_code == 200
    data = res.json()
    assert data["filename"] == "referencia.jpg"
    assert "SUPIN0" in data["raw_text"]
    assert len(data["rows"]) == 1
    assert data["rows"][0]["exercise"] == "Supino"
    assert data["rows"][0]["nickname"] == "Inclinado"

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

def test_generate_passes_volume_adjustment_to_llm(client, monkeypatch):
    """O controle de volume da UI (manter/aumentar/diminuir) precisa chegar até o prompt do LLM."""
    captured = {}

    def fake_llm(raw_text, request_data):
        captured["volume_adjustment"] = request_data.get("volume_adjustment")
        return _fake_parsed_workouts(1)

    monkeypatch.setattr(extraction_router, "parse_reference_and_generate", fake_llm)

    res = client.post("/extraction/generate", data={
        "raw_text": "SUPINO INCLINADO HALTER BANCO INCLINADO PIRÂMIDE 12-10-8",
        "days_per_week": "1",
        "volume_adjustment": "aumentar",
    })
    assert res.status_code == 200
    assert captured["volume_adjustment"] == "aumentar"

def test_generate_defaults_volume_adjustment_to_manter(client, monkeypatch):
    captured = {}

    def fake_llm(raw_text, request_data):
        captured["volume_adjustment"] = request_data.get("volume_adjustment")
        return _fake_parsed_workouts(1)

    monkeypatch.setattr(extraction_router, "parse_reference_and_generate", fake_llm)

    res = client.post("/extraction/generate", data={
        "raw_text": "SUPINO INCLINADO HALTER BANCO INCLINADO PIRÂMIDE 12-10-8",
        "days_per_week": "1",
    })
    assert res.status_code == 200
    assert captured["volume_adjustment"] == "manter"

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
