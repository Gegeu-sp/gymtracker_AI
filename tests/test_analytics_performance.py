from datetime import datetime, timedelta, timezone

import pytest

from app.database import Base, SessionLocal, engine
from app.models import Exercise, Workout
from app.services.analytics import build_performance_metrics, get_performance_dashboard


@pytest.fixture
def db_session():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)


def test_build_performance_metrics_collects_kpis(db_session):
    base_date = datetime.now(timezone.utc) - timedelta(days=2)

    workout_1 = Workout(date=base_date, notes="Treino A")
    workout_1.exercises = [
        Exercise(name="Supino Reto", sets=3, reps=8, weight_kg=100.0, actual_weight_kg=100.0, actual_reps=8, actual_rpe=8.0),
        Exercise(name="Puxada Frontal", sets=3, reps=10, weight_kg=50.0, actual_weight_kg=50.0, actual_reps=10, actual_rpe=7.5),
        Exercise(name="Agachamento Livre", sets=4, reps=6, weight_kg=80.0, actual_weight_kg=80.0, actual_reps=6, actual_rpe=8.5),
        Exercise(name="Cadeira Flexora", sets=3, reps=12, weight_kg=40.0, actual_weight_kg=40.0, actual_reps=12, actual_rpe=8.0),
    ]

    workout_2 = Workout(date=base_date + timedelta(days=1), notes="Treino B")
    workout_2.exercises = [
        Exercise(name="Supino Reto", sets=3, reps=6, weight_kg=105.0, actual_weight_kg=105.0, actual_reps=6, actual_rpe=8.5),
        Exercise(name="Remada Curvada", sets=3, reps=8, weight_kg=60.0, actual_weight_kg=60.0, actual_reps=8, actual_rpe=8.0),
        Exercise(name="Levantamento Terra", sets=3, reps=5, weight_kg=120.0, actual_weight_kg=120.0, actual_reps=5, actual_rpe=8.5),
        Exercise(name="Agachamento Livre", sets=3, reps=8, weight_kg=85.0, actual_weight_kg=85.0, actual_reps=8, actual_rpe=8.5),
    ]

    db_session.add_all([workout_1, workout_2])
    db_session.commit()

    metrics = build_performance_metrics(db_session)

    assert metrics["weekly_volume"]["Peito"]["effective_sets"] >= 3
    assert metrics["weekly_volume"]["Costas"]["effective_sets"] >= 3
    assert metrics["session_tonnage"][0]["tonnage"] > 0
    assert metrics["balance"]["push_pull"]["ratio"] > 0
    assert metrics["balance"]["quadriceps_posterior"]["ratio"] > 0
    assert metrics["fatigue"]["status"] in {"green", "yellow", "red"}


def test_get_performance_dashboard_contains_visual_sections(db_session):
    workout = Workout(date=datetime.now(timezone.utc), notes="Treino")
    workout.exercises = [
        Exercise(name="Supino Reto", sets=3, reps=8, weight_kg=100.0, actual_weight_kg=100.0, actual_reps=8, actual_rpe=8.0)
    ]
    db_session.add(workout)
    db_session.commit()

    html = get_performance_dashboard(db_session)
    assert "Painel de Performance" in html
    assert "e1RM" in html
    assert "Volume Semanal" in html
