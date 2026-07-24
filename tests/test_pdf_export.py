import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.database import Base, engine

@pytest.fixture(scope="module")
def client():
    Base.metadata.create_all(bind=engine)
    with TestClient(app) as c:
        yield c

def test_pdf_export_data_and_view_endpoint(client):
    """Testa se a rota /workouts/view e os dados de treino contêm estrutura necessária para PDF"""
    # 1. Cria um treino com os 3 blocos metodológicos e notas do treinador
    res_create = client.post("/workouts/", json={
        "notes": "⚠️ Alerta de Risco: Evitar peso excessivo no agachamento devido a desconforto prévio.",
        "exercises": [
            {
                "name": "Bloco 1: Mobilidade de Ombro e Quadril",
                "sets": 2,
                "reps": 15,
                "weight_kg": 0.0,
                "method": "Controle Articular"
            },
            {
                "name": "Supino Reto com Barra",
                "sets": 4,
                "reps": 10,
                "weight_kg": 60.0,
                "method": "Pirâmide"
            },
            {
                "name": "Bloco 3: Respiração Diafragmática e Alongamento",
                "sets": 1,
                "reps": 10,
                "weight_kg": 0.0,
                "method": "Parassimpático"
            }
        ]
    })
    assert res_create.status_code == 200
    workout_data = res_create.json()
    assert workout_data["id"] is not None
    assert "Alerta de Risco" in workout_data["notes"]
    assert len(workout_data["exercises"]) == 3

    # 2. Verifica se a rota HTML /workouts/view renderiza os botões e scripts de exportação para PDF
    res_view = client.get("/workouts/view")
    assert res_view.status_code == 200
    html_content = res_view.text
    assert "html2pdf.bundle.min.js" in html_content
    assert "downloadWorkoutPDF" in html_content
    assert "Baixar PDF" in html_content
