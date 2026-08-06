import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.database import Base, engine


@pytest.fixture(scope="module")
def client():
    Base.metadata.create_all(bind=engine)
    with TestClient(app) as c:
        yield c


def _payload(student_name="Aluno Teste Assessment", **overrides):
    base = {
        "student_name": student_name,
        "sex": "M",
        "age": 15,
        "weight_kg": 60.0,
        "height_m": 1.70,
        "pacer_laps": 40,
        "push_ups": 20,
        "curl_ups": 25,
        "sprint_30m_seconds": 5.5,
        "illinois_agility_seconds": 18.0,
        "flexibility_right_cm": 30.0,
        "flexibility_left_cm": 28.0,
    }
    base.update(overrides)
    return base


def test_create_assessment_returns_success_and_report_with_five_categories(client):
    res = client.post("/assessment/create", json=_payload())
    assert res.status_code == 200
    body = res.json()
    assert body["success"] is True
    assert set(body["report"]["classifications"].keys()) == {"aerobic", "strength", "flexibility", "speed", "agility"}


def test_first_assessment_shows_primeira_avaliacao_in_all_categories(client):
    res = client.post("/assessment/create", json=_payload(student_name="Aluno Teste Primeira"))
    classifications = res.json()["report"]["classifications"]
    for value in classifications.values():
        assert "Primeira Avaliação" in value


def test_invalid_sex_rejected(client):
    res = client.post("/assessment/create", json=_payload(sex="X"))
    assert res.status_code == 422


def test_age_out_of_range_rejected(client):
    res = client.post("/assessment/create", json=_payload(age=25))
    assert res.status_code == 422


def test_second_assessment_calculates_correct_direction_per_category(client):
    """
    Regressão: velocidade e agilidade são "menor é melhor" (tempo mais baixo), diferente das
    demais categorias (aeróbio, força, flexibilidade), onde "maior é melhor".
    """
    student = "Aluno Teste Evolucao"
    client.post("/assessment/create", json=_payload(
        student_name=student, pacer_laps=30, push_ups=15, curl_ups=15,
        sprint_30m_seconds=6.0, illinois_agility_seconds=20.0,
        flexibility_right_cm=25.0, flexibility_left_cm=25.0,
    ))

    res = client.post("/assessment/create", json=_payload(
        student_name=student, pacer_laps=40, push_ups=20, curl_ups=20,
        sprint_30m_seconds=5.2, illinois_agility_seconds=17.0,
        flexibility_right_cm=30.0, flexibility_left_cm=30.0,
    ))
    classifications = res.json()["report"]["classifications"]

    # Aeróbio/força/flexibilidade subiram -> melhorou.
    assert "Melhorou" in classifications["aerobic"]
    assert "Melhorou" in classifications["strength"]
    assert "Melhorou" in classifications["flexibility"]
    # Velocidade e agilidade: tempo CAIU (6.0->5.2s, 20.0->17.0s) -> melhorou, mesmo com delta negativo.
    assert "Melhorou" in classifications["speed"]
    assert "Melhorou" in classifications["agility"]


def test_second_assessment_detects_worse_performance_and_recommends(client):
    student = "Aluno Teste Piora"
    client.post("/assessment/create", json=_payload(student, pacer_laps=40))
    res = client.post("/assessment/create", json=_payload(student, pacer_laps=25))

    report = res.json()["report"]
    assert "Piorou" in report["classifications"]["aerobic"]
    assert any("aeróbico" in rec for rec in report["recommendations"])


def test_missing_metric_shows_sem_dados(client):
    res = client.post("/assessment/create", json=_payload(
        student_name="Aluno Teste Sem Dados", pacer_laps=None,
    ))
    assert res.json()["report"]["classifications"]["aerobic"] == "— Sem dados"


def test_list_assessments_returns_expected_fields(client):
    student = "Aluno Teste Lista"
    client.post("/assessment/create", json=_payload(student_name=student, pacer_laps=33))

    res = client.get("/assessment/list")
    assert res.status_code == 200
    entries = [a for a in res.json() if a["student_name"] == student]
    assert len(entries) == 1
    entry = entries[0]
    assert entry["sex"] == "M"
    assert entry["age"] == 15
    assert entry["pacer_laps"] == 33
    assert "date" in entry
    assert "id" in entry


def test_get_assessment_by_id_returns_full_fields(client):
    create_res = client.post("/assessment/create", json=_payload(student_name="Aluno Teste GetById"))
    list_res = client.get("/assessment/list")
    entry = next(a for a in list_res.json() if a["student_name"] == "Aluno Teste GetById")

    res = client.get(f"/assessment/{entry['id']}")
    assert res.status_code == 200
    body = res.json()
    assert body["student_name"] == "Aluno Teste GetById"
    assert body["weight_kg"] == 60.0
    assert body["height_m"] == 1.70
    assert body["aerobic_classification"] is not None
    assert "notes" in body


def test_get_assessment_not_found_returns_404(client):
    res = client.get("/assessment/999999")
    assert res.status_code == 404


def test_assessment_page_returns_html(client):
    res = client.get("/assessment")
    assert res.status_code == 200
    assert "Avaliação" in res.text
