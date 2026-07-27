from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.database import Base, SessionLocal, engine
from app.models import Exercise, Workout
from app.services.analytics import (
    build_performance_metrics,
    get_performance_dashboard,
    _estimate_e1rm,
    _effective_rpe,
)

@pytest.fixture(scope="module")
def client():
    Base.metadata.create_all(bind=engine)
    with TestClient(app) as c:
        yield c

def test_build_performance_metrics_collects_kpis(client):
    """
    Usa um student_name único para isolar os dados deste teste dos outros arquivos que
    compartilham o mesmo gym.db (seguindo o padrão já usado no restante da suíte, que nunca
    dropa tabelas — só cria/reaproveita).
    """
    student = "Analytics Teste A"
    db = SessionLocal()
    try:
        base_date = datetime.now(timezone.utc) - timedelta(days=2)

        workout_1 = Workout(date=base_date, notes="Treino A", student_name=student)
        workout_1.exercises = [
            Exercise(name="Supino Reto", sets=3, reps=8, weight_kg=100.0, actual_weight_kg=100.0, actual_reps=8, actual_rpe=8.0),
            Exercise(name="Puxada Frontal", sets=3, reps=10, weight_kg=50.0, actual_weight_kg=50.0, actual_reps=10, actual_rpe=7.5),
            Exercise(name="Agachamento Livre", sets=4, reps=6, weight_kg=80.0, actual_weight_kg=80.0, actual_reps=6, actual_rpe=8.5),
            Exercise(name="Cadeira Flexora", sets=3, reps=12, weight_kg=40.0, actual_weight_kg=40.0, actual_reps=12, actual_rpe=8.0),
        ]

        workout_2 = Workout(date=base_date + timedelta(days=1), notes="Treino B", student_name=student)
        workout_2.exercises = [
            Exercise(name="Supino Reto", sets=3, reps=6, weight_kg=105.0, actual_weight_kg=105.0, actual_reps=6, actual_rpe=8.5),
            Exercise(name="Remada Curvada", sets=3, reps=8, weight_kg=60.0, actual_weight_kg=60.0, actual_reps=8, actual_rpe=8.0),
            Exercise(name="Levantamento Terra", sets=3, reps=5, weight_kg=120.0, actual_weight_kg=120.0, actual_reps=5, actual_rpe=8.5),
            Exercise(name="Agachamento Livre", sets=3, reps=8, weight_kg=85.0, actual_weight_kg=85.0, actual_reps=8, actual_rpe=8.5),
        ]

        db.add_all([workout_1, workout_2])
        db.commit()

        metrics = build_performance_metrics(db, student_name=student)

        assert metrics["weekly_volume"]["Peito"]["effective_sets"] == 6
        # Costas: Puxada Frontal (3) + Remada Curvada (3) + Levantamento Terra (3), já que o
        # catálogo classifica Levantamento Terra como "Costas" também.
        assert metrics["weekly_volume"]["Costas"]["effective_sets"] == 9
        assert metrics["session_tonnage"][0]["tonnage"] > 0
        assert metrics["balance"]["push_pull"]["ratio"] is not None
        assert metrics["balance"]["quadriceps_posterior"]["ratio"] is not None
        assert metrics["fatigue"]["status"] in {"green", "yellow", "red"}

        # Regressão: "Remada Curvada" é exercício de costas (puxar), não pode contaminar a
        # razão quadríceps/posterior de coxa — só "Cadeira Flexora" (3) e "Levantamento Terra" (3)
        # devem contar como posterior de coxa.
        assert metrics["balance"]["quadriceps_posterior"]["posterior_sets"] == 6
    finally:
        db.close()

def test_estimate_e1rm_lower_rpe_yields_higher_estimate():
    """
    Regressão do bug de inversão: RPE mais baixo (mais reps de reserva / RIR) deve estimar
    um e1RM MAIOR, não menor — o atleta poderia ter feito mais reps até a falha. Em RPE 10
    (falha real) o Epley puro já é a estimativa, sem desconto.
    """
    at_failure = Exercise(sets=1, reps=5, weight_kg=100.0, actual_weight_kg=100.0, actual_reps=5, actual_rpe=10.0)
    with_reserve = Exercise(sets=1, reps=5, weight_kg=100.0, actual_weight_kg=100.0, actual_reps=5, actual_rpe=7.0)
    no_rpe_logged = Exercise(sets=1, reps=5, weight_kg=100.0, actual_weight_kg=100.0, actual_reps=5, actual_rpe=None)

    e1rm_failure = _estimate_e1rm(at_failure)
    e1rm_reserve = _estimate_e1rm(with_reserve)
    e1rm_no_rpe = _estimate_e1rm(no_rpe_logged)

    assert e1rm_failure == pytest.approx(116.7, abs=0.1)  # Epley puro: 100*(1+5/30)
    assert e1rm_reserve == pytest.approx(126.7, abs=0.1)  # RIR=3 -> 100*(1+8/30)
    assert e1rm_reserve > e1rm_failure
    assert e1rm_no_rpe == e1rm_failure  # sem RPE registrado, não inventa reps de reserva

def test_effective_rpe_returns_none_when_not_logged():
    assert _effective_rpe(Exercise(actual_rpe=None)) is None
    assert _effective_rpe(Exercise(actual_rpe=0)) is None
    assert _effective_rpe(Exercise(actual_rpe=7.5)) == 7.5

def test_session_without_rpe_shows_as_no_data(client):
    student = "Analytics Teste SemRPE"
    db = SessionLocal()
    try:
        workout = Workout(date=datetime.now(timezone.utc), notes="Treino sem RPE", student_name=student)
        workout.exercises = [
            Exercise(name="Supino Reto", sets=3, reps=8, weight_kg=100.0)
        ]
        db.add(workout)
        db.commit()

        metrics = build_performance_metrics(db, student_name=student)
        assert metrics["session_rpe"] == []

        html = get_performance_dashboard(db, student_name=student)
        assert "Sem dados" in html
    finally:
        db.close()

def test_get_performance_dashboard_contains_visual_sections(client):
    student = "Analytics Teste Visual"
    db = SessionLocal()
    try:
        workout = Workout(date=datetime.now(timezone.utc), notes="Treino", student_name=student)
        workout.exercises = [
            Exercise(name="Supino Reto", sets=3, reps=8, weight_kg=100.0, actual_weight_kg=100.0, actual_reps=8, actual_rpe=8.0)
        ]
        db.add(workout)
        db.commit()

        html = get_performance_dashboard(db, student_name=student)
        assert "Painel de Performance" in html
        assert "e1RM" in html
        assert "Volume Semanal" in html
    finally:
        db.close()

def test_performance_endpoint_returns_html(client):
    res = client.get("/analytics/performance")
    assert res.status_code == 200
    assert "Painel de Performance" in res.text

def test_performance_endpoint_filters_by_student(client):
    student = "Analytics Teste HTTP"
    db = SessionLocal()
    try:
        workout = Workout(date=datetime.now(timezone.utc), notes="Treino HTTP", student_name=student)
        workout.exercises = [
            Exercise(name="Supino Reto", sets=3, reps=8, weight_kg=100.0, actual_weight_kg=100.0, actual_reps=8, actual_rpe=8.0)
        ]
        db.add(workout)
        db.commit()
    finally:
        db.close()

    res = client.get("/analytics/performance", params={"student_name": student})
    assert res.status_code == 200
    assert student in res.text
