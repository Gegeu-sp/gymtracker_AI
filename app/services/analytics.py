import plotly.express as px
import plotly.io as pio
from sqlalchemy.orm import Session
from ..models import Workout, Exercise
from .exercise_catalog import get_muscle_group


def get_volume_chart(db: Session) -> str:
    """Gera gráfico de volume total ao longo do tempo."""
    workouts = db.query(Workout).order_by(Workout.date).all()
    data = []
    for w in workouts:
        vol = sum(e.sets * e.reps * e.weight_kg for e in w.exercises)
        data.append({
            "data": w.date.strftime("%Y-%m-%d %H:%M"),
            "volume_kg": vol
        })

    if not data:
        return "<p style='font-family:sans-serif;padding:20px;'>📊 Sem dados ainda. Registre seu primeiro treino!</p>"

    fig = px.line(
        data, x="data", y="volume_kg",
        title="📈 Volume Total por Treino (kg)",
        markers=True
    )
    fig.update_layout(template="plotly_white")
    return pio.to_html(fig, full_html=False)


def get_exercise_distribution(db: Session) -> str:
    """Distribuição dos exercícios mais feitos."""
    exercises = db.query(Exercise.name).all()
    counts = {}
    for ex in exercises:
        counts[ex.name] = counts.get(ex.name, 0) + 1

    sorted_counts = sorted(counts.items(), key=lambda x: x[1], reverse=True)[:10]
    data = [{"nome": nome, "quantidade": qtd} for nome, qtd in sorted_counts]

    if not data:
        return "<p style='font-family:sans-serif;padding:20px;'>📊 Sem dados ainda.</p>"

    fig = px.bar(
        data, x="quantidade", y="nome", orientation="h",
        title="🏋️ Top 10 Exercícios Mais Feitos"
    )
    fig.update_layout(template="plotly_white")
    return pio.to_html(fig, full_html=False)


def get_muscle_group_chart(db: Session) -> str:
    """Distribuição por grupo muscular, via app/services/exercise_catalog.py."""
    exercises = db.query(Exercise.name).all()
    if not exercises:
        return "<p style='font-family:sans-serif;padding:20px;'>📊 Sem dados ainda.</p>"

    groups = {}
    for ex in exercises:
        grupo = get_muscle_group(ex.name)
        groups[grupo] = groups.get(grupo, 0) + 1

    data = [{"grupo": k, "total": v} for k, v in groups.items()]
    fig = px.pie(data, names="grupo", values="total", title="💪 Distribuição por Grupo Muscular")
    fig.update_layout(template="plotly_white")
    return pio.to_html(fig, full_html=False)