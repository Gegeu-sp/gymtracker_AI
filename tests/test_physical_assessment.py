import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.database import Base, SessionLocal, engine
from app.models import PhysicalAssessment
from app.services.assessment_service import build_assessment_report, get_assessment_report_html


@pytest.fixture(scope="module")
def client():
    Base.metadata.create_all(bind=engine)
    with TestClient(app) as c:
        yield c


def test_create_assessment_via_endpoint(client):
    payload = {
        "student_name": "Avaliacao Teste A",
        "age_years": 15,
        "weight_kg": 55.0,
        "height_cm": 165.0,
        "flexibility_cm": 28.0,
        "abdominal_reps": 30,
        "upper_body_power_m": 4.5,
        "agility_seconds": 12.0,
        "aerobic_test_type": "vaivem",
        "aerobic_result": 6.0,
    }
    res = client.post("/assessments/", json=payload)
    assert res.status_code == 200
    body = res.json()
    assert body["student_name"] == "Avaliacao Teste A"
    assert body["weight_kg"] == 55.0


def test_invalid_aerobic_test_type_rejected(client):
    res = client.post("/assessments/", json={"student_name": "Avaliacao Teste B", "aerobic_test_type": "esteira"})
    assert res.status_code == 422


def test_list_assessments_filters_by_student(client):
    student = "Avaliacao Teste Filtro"
    client.post("/assessments/", json={"student_name": student, "weight_kg": 50.0})

    res = client.get("/assessments/", params={"student_name": student})
    assert res.status_code == 200
    body = res.json()
    assert len(body) == 1
    assert body[0]["student_name"] == student


def test_report_with_single_assessment_has_no_comparison():
    student = "Avaliacao Teste Unica"
    db = SessionLocal()
    try:
        db.add(PhysicalAssessment(student_name=student, weight_kg=60.0, flexibility_cm=25.0))
        db.commit()

        report = build_assessment_report(db, student)
        assert report["assessments_count"] == 1
        assert report["tests"]["flexibility_cm"]["direction"] == "primeira_avaliacao"
        assert report["tests"]["flexibility_cm"]["delta"] is None
        # Teste nunca aplicado nessa avaliação -> sem dados, não deve quebrar.
        assert report["tests"]["agility_seconds"]["direction"] == "sem_dados"
    finally:
        db.close()


def test_report_compares_latest_vs_previous_with_correct_direction():
    """
    Regressão: agilidade é "menor é melhor" (tempo mais baixo = mais ágil), diferente dos
    demais testes onde "maior é melhor" (flexibilidade, abdominais, arremesso, aeróbio).
    """
    student = "Avaliacao Teste Evolucao"
    db = SessionLocal()
    try:
        db.add(PhysicalAssessment(student_name=student, flexibility_cm=20.0, agility_seconds=15.0))
        db.commit()
        db.add(PhysicalAssessment(student_name=student, flexibility_cm=25.0, agility_seconds=13.0))
        db.commit()

        report = build_assessment_report(db, student)

        # Flexibilidade subiu (20 -> 25): maior é melhor -> "melhorou".
        assert report["tests"]["flexibility_cm"]["direction"] == "melhorou"
        assert report["tests"]["flexibility_cm"]["delta"] == 5.0

        # Agilidade caiu (15s -> 13s): menor é melhor -> "melhorou", mesmo com delta negativo.
        assert report["tests"]["agility_seconds"]["direction"] == "melhorou"
        assert report["tests"]["agility_seconds"]["delta"] == -2.0
    finally:
        db.close()


def test_report_computes_bmi_from_weight_and_height():
    student = "Avaliacao Teste IMC"
    db = SessionLocal()
    try:
        db.add(PhysicalAssessment(student_name=student, weight_kg=70.0, height_cm=175.0))
        db.commit()

        report = build_assessment_report(db, student)
        # IMC = 70 / 1.75^2 = 22.9
        assert report["tests"]["bmi"]["latest_value"] == pytest.approx(22.9, abs=0.1)
        # IMC não tem julgamento de direção (não é "melhor/pior").
        assert report["tests"]["bmi"]["higher_is_better"] is None
    finally:
        db.close()


def test_report_html_shows_trend_chart_with_multiple_assessments():
    student = "Avaliacao Teste HTML"
    db = SessionLocal()
    try:
        db.add(PhysicalAssessment(student_name=student, flexibility_cm=20.0))
        db.commit()
        db.add(PhysicalAssessment(student_name=student, flexibility_cm=24.0))
        db.commit()

        html = get_assessment_report_html(db, student)
        assert "Relatório de Avaliação Física" in html
        assert "Flexibilidade" in html
        assert "Baixar PDF" in html
        assert 'href="/"' in html
    finally:
        db.close()


def test_report_html_with_no_assessments_shows_empty_state():
    db = SessionLocal()
    try:
        html = get_assessment_report_html(db, "Aluno Sem Avaliacao Nenhuma")
        assert "Nenhuma avaliação física registrada" in html
    finally:
        db.close()


def test_assessments_view_endpoint_returns_html(client):
    res = client.get("/assessments/view")
    assert res.status_code == 200
    assert "Avaliação Física" in res.text


def test_assessments_report_endpoint_returns_html(client):
    student = "Avaliacao Teste Endpoint Relatorio"
    client.post("/assessments/", json={"student_name": student, "weight_kg": 55.0})

    res = client.get("/assessments/report", params={"student_name": student})
    assert res.status_code == 200
    assert student in res.text
