import plotly.express as px
import plotly.graph_objects as go
import plotly.io as pio
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List

from sqlalchemy.orm import Session

from ..models import Workout, Exercise
from .exercise_catalog import get_muscle_group


def _effective_weight(exercise: Exercise) -> float:
    actual_weight = getattr(exercise, "actual_weight_kg", None)
    if actual_weight is not None and actual_weight > 0:
        return float(actual_weight)
    weight_kg = getattr(exercise, "weight_kg", 0) or 0.0
    return float(weight_kg)


def _effective_reps(exercise: Exercise) -> int:
    actual_reps = getattr(exercise, "actual_reps", None)
    if actual_reps is not None and actual_reps > 0:
        return int(actual_reps)
    reps = getattr(exercise, "reps", 0) or 0
    return int(reps)


def _effective_rpe(exercise: Exercise) -> float:
    actual_rpe = getattr(exercise, "actual_rpe", None)
    if actual_rpe is not None and actual_rpe > 0:
        return float(actual_rpe)
    return 8.0


def _resolve_muscle_group(exercise: Exercise) -> str:
    muscle_group = getattr(exercise, "muscle_group", None)
    if muscle_group:
        return muscle_group
    return get_muscle_group(exercise.name)


def _estimate_e1rm(exercise: Exercise) -> float:
    weight = _effective_weight(exercise)
    reps = max(1, _effective_reps(exercise))
    rpe = _effective_rpe(exercise)
    if weight <= 0:
        return 0.0
    base_e1rm = weight * (1 + reps / 30.0)
    if rpe <= 7.0:
        return round(base_e1rm, 1)
    adjustment = 1.0 / (1.0 + max(0.0, rpe - 7.0) / 10.0)
    return round(base_e1rm * adjustment, 1)


def _classify_push_pull(exercise: Exercise) -> tuple[str, int]:
    name = (exercise.name or "").lower()
    if any(term in name for term in ["supino", "peitoral", "crucifixo", "desenvolvimento", "tríceps", "triceps", "flexao", "mergulho", "coice"]):
        return "push", int(exercise.sets or 0)
    if any(term in name for term in ["puxada", "remada", "terra", "barra fixa", "rosca", "pull", "lat", "barra"]):
        return "pull", int(exercise.sets or 0)
    return "", 0


def _classify_quads_posterior(exercise: Exercise) -> tuple[str, int]:
    name = (exercise.name or "").lower()
    if any(term in name for term in ["agachamento", "squat", "extensora", "leg press", "afundo", "cadeira extensora", "cadeira adutora"]):
        return "quadriceps", int(exercise.sets or 0)
    if any(term in name for term in ["flexora", "stiff", "terra", "remada", "hip thrust", "elevacao pelvica", "glute"]):
        return "posterior", int(exercise.sets or 0)
    return "", 0


def build_performance_metrics(db: Session) -> Dict[str, Any]:
    workouts = db.query(Workout).order_by(Workout.date).all()
    workouts = [w for w in workouts if w.exercises]

    e1rm_rows: List[Dict[str, Any]] = []
    session_tonnage: List[Dict[str, Any]] = []
    session_rpe: List[Dict[str, Any]] = []
    weekly_sets_by_group: Dict[str, int] = {}

    if workouts:
        latest_date = max(w.date for w in workouts)
        weekly_cutoff = latest_date - timedelta(days=7)

        for workout in workouts:
            session_tonnage_value = 0.0
            session_rpe_values: List[float] = []
            for exercise in workout.exercises:
                effective_weight = _effective_weight(exercise)
                effective_reps = max(1, _effective_reps(exercise))
                effective_sets = max(1, int(getattr(exercise, "sets", 0) or 0))
                session_tonnage_value += effective_sets * effective_reps * effective_weight
                session_rpe_values.append(_effective_rpe(exercise))

                if workout.date >= weekly_cutoff:
                    muscle_group = _resolve_muscle_group(exercise)
                    weekly_sets_by_group[muscle_group] = weekly_sets_by_group.get(muscle_group, 0) + effective_sets

                if any(keyword in (exercise.name or "").lower() for keyword in ["supino", "agachamento", "terra", "deadlift", "squat", "bench"]):
                    e1rm_value = _estimate_e1rm(exercise)
                    if e1rm_value > 0:
                        e1rm_rows.append({
                            "date": workout.date,
                            "exercise": exercise.name,
                            "e1rm": round(e1rm_value, 1),
                            "load_kg": round(effective_weight, 1),
                            "rpe": round(_effective_rpe(exercise), 1),
                        })

            session_tonnage.append({
                "date": workout.date,
                "session": workout.notes or f"Treino {workout.id}",
                "tonnage": round(session_tonnage_value, 1),
            })

            if session_rpe_values:
                avg_rpe = round(sum(session_rpe_values) / len(session_rpe_values), 1)
                session_rpe.append({
                    "date": workout.date,
                    "session": workout.notes or f"Treino {workout.id}",
                    "average_rpe": avg_rpe,
                    "status": "ideal" if 7.0 <= avg_rpe <= 9.0 else "outside"
                })

    weekly_volume = {}
    for group, sets in sorted(weekly_sets_by_group.items()):
        if sets <= 0:
            continue
        if sets < 10:
            status = "sub-treinado"
            alert = "⚠️ Volume abaixo do ideal para hipertrofia"
        elif sets > 25:
            status = "overtraining"
            alert = "⚠️ Volume elevado, revisar recuperação"
        else:
            status = "ok"
            alert = "✅ Volume dentro da faixa de hipertrofia"
        weekly_volume[group] = {
            "effective_sets": sets,
            "status": status,
            "alert": alert,
        }

    push_sets = 0
    pull_sets = 0
    quad_sets = 0
    posterior_sets = 0
    for workout in workouts:
        for exercise in workout.exercises:
            classification_push_pull = _classify_push_pull(exercise)
            classification_quads = _classify_quads_posterior(exercise)
            if classification_push_pull[0] == "push":
                push_sets += classification_push_pull[1]
            elif classification_push_pull[0] == "pull":
                pull_sets += classification_push_pull[1]
            if classification_quads[0] == "quadriceps":
                quad_sets += classification_quads[1]
            elif classification_quads[0] == "posterior":
                posterior_sets += classification_quads[1]

    push_pull_ratio = round(push_sets / pull_sets, 2) if pull_sets else None
    quadriceps_posterior_ratio = round(quad_sets / posterior_sets, 2) if posterior_sets else None

    balance = {
        "push_pull": {
            "ratio": push_pull_ratio,
            "push_sets": push_sets,
            "pull_sets": pull_sets,
            "status": "ok" if push_pull_ratio is None or 0.8 <= push_pull_ratio <= 1.2 else "alert",
        },
        "quadriceps_posterior": {
            "ratio": quadriceps_posterior_ratio,
            "quadriceps_sets": quad_sets,
            "posterior_sets": posterior_sets,
            "status": "ok" if quadriceps_posterior_ratio is None or 0.8 <= quadriceps_posterior_ratio <= 1.2 else "alert",
        },
    }

    fatigue = {"status": "green", "message": "✅ Recuperação adequada. Mantém o plano atual."}
    if len(workouts) >= 2:
        last_two = [w for w in workouts if w.date >= latest_date - timedelta(days=14)]
        if len(last_two) >= 2:
            recent_rpe = [entry for entry in session_rpe if entry["date"] >= latest_date - timedelta(days=14)]
            if recent_rpe and recent_rpe[-1]["average_rpe"] >= 8.5 and recent_rpe[-1]["average_rpe"] > recent_rpe[0]["average_rpe"]:
                fatigue = {"status": "yellow", "message": "⚠️ RPE médio subindo sem redução de carga. Avalie deload."}

        for compound in ["Supino", "Agachamento", "Terra"]:
            history = [row for row in e1rm_rows if compound.lower() in (row["exercise"] or "").lower()]
            if len(history) >= 2:
                newest = history[-1]
                previous = history[-2]
                e1rm_delta = round(newest["e1rm"] - previous["e1rm"], 1)
                load_delta = round(newest["load_kg"] - previous["load_kg"], 1)
                rpe_delta = round(newest["rpe"] - previous["rpe"], 1)
                if abs(e1rm_delta) <= 1.0 and rpe_delta >= 0.5 and abs(load_delta) <= 2.5:
                    fatigue = {"status": "red", "message": f"🔴 {compound} estabilizou o e1RM com RPE crescente. Considere reduzir volume ou aplicar deload."}
                    break

    return {
        "e1rm_trend": e1rm_rows,
        "weekly_volume": weekly_volume,
        "session_tonnage": session_tonnage,
        "balance": balance,
        "session_rpe": session_rpe,
        "fatigue": fatigue,
    }


def get_performance_dashboard(db: Session) -> str:
    metrics = build_performance_metrics(db)
    e1rm_rows = metrics["e1rm_trend"]
    weekly_volume = metrics["weekly_volume"]
    session_tonnage = metrics["session_tonnage"]
    balance = metrics["balance"]
    session_rpe = metrics["session_rpe"]
    fatigue = metrics["fatigue"]

    e1rm_chart = ""
    if e1rm_rows:
        grouped_rows: Dict[str, List[Dict[str, Any]]] = {}
        for row in e1rm_rows:
            grouped_rows.setdefault(row["exercise"], []).append(row)
        fig = go.Figure()
        for exercise_name, rows in grouped_rows.items():
            fig.add_trace(go.Scatter(x=[r["date"].strftime("%Y-%m-%d") for r in rows], y=[r["e1rm"] for r in rows], mode="lines+markers", name=exercise_name))
        fig.update_layout(title="📈 Tendência de e1RM estimado (Epley ajustado por RPE)", xaxis_title="Data", yaxis_title="e1RM (kg)", template="plotly_white")
        e1rm_chart = pio.to_html(fig, full_html=False, include_plotlyjs="cdn")
    else:
        e1rm_chart = "<p style='color:#5A7A8C;'>Sem dados de e1RM ainda.</p>"

    weekly_chart = ""
    if weekly_volume:
        fig = go.Figure(data=[go.Bar(x=list(weekly_volume.keys()), y=[item["effective_sets"] for item in weekly_volume.values()], marker_color=["#2ECC71" if item["status"] == "ok" else "#F39C12" if item["status"] == "sub-treinado" else "#FF6B6B" for item in weekly_volume.values()])])
        fig.update_layout(title="🧠 Volume semanal por grupo muscular", xaxis_title="Grupo muscular", yaxis_title="Séries efetivas", template="plotly_white")
        weekly_chart = pio.to_html(fig, full_html=False, include_plotlyjs="cdn")
    else:
        weekly_chart = "<p style='color:#5A7A8C;'>Sem dados suficientes para o volume semanal.</p>"

    tonnage_chart = ""
    if session_tonnage:
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=[item["date"].strftime("%Y-%m-%d") for item in session_tonnage], y=[item["tonnage"] for item in session_tonnage], mode="lines+markers", line=dict(color="#006494", width=3), marker=dict(color="#1B98E0")))
        fig.update_layout(title="🏋️ Tonelagem total por sessão", xaxis_title="Sessão", yaxis_title="Tonelagem (kg)", template="plotly_white")
        tonnage_chart = pio.to_html(fig, full_html=False, include_plotlyjs="cdn")
    else:
        tonnage_chart = "<p style='color:#5A7A8C;'>Sem dados de tonagem registrada.</p>"

    balance_cards = []
    for label, values in balance.items():
        ratio = values.get("ratio")
        ratio_str = "N/A" if ratio is None else f"{ratio:.2f}"
        status = values.get("status", "ok")
        badge = "✅ Equilibrado" if status == "ok" else "⚠️ Desequilíbrio"
        if label == "push_pull":
            balance_cards.append(f"<div class='metric-card'><h3>Push/Pull Ratio</h3><div class='value'>{ratio_str}</div><p>{badge}</p><small>Empurrar: {values.get('push_sets', 0)} séries · Puxar: {values.get('pull_sets', 0)} séries</small></div>")
        else:
            balance_cards.append(f"<div class='metric-card'><h3>Quadríceps/Posteriores</h3><div class='value'>{ratio_str}</div><p>{badge}</p><small>Quadríceps: {values.get('quadriceps_sets', 0)} séries · Posteriores: {values.get('posterior_sets', 0)} séries</small></div>")

    rpe_cards = []
    if session_rpe:
        last_entry = session_rpe[-1]
        rpe_cards.append(f"<div class='metric-card'><h3>RPE Médio da Última Sessão</h3><div class='value'>{last_entry['average_rpe']:.1f}</div><p>{'✅ Zona ideal' if last_entry['status'] == 'ideal' else '⚠️ Ajustar intensidade'}</p></div>")
    else:
        rpe_cards.append("<div class='metric-card'><h3>RPE Médio</h3><div class='value'>N/A</div><p>Sem dados</p></div>")

    fatigue_badge = f"<div class='metric-card'><h3>Semáforo de Fadiga</h3><div class='value'>{fatigue['status'].upper()}</div><p>{fatigue['message']}</p></div>"

    return f"""
    <!DOCTYPE html>
    <html lang="pt-BR">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Painel de Performance | Gym Tracker AI</title>
        <style>
            body {{ font-family: 'Segoe UI', Arial, sans-serif; margin: 0; background: linear-gradient(135deg, #006494 0%, #247BA0 100%); color: #006494; }}
            .container {{ max-width: 1400px; margin: 0 auto; padding: 32px 20px 60px; }}
            .card {{ background: white; border-radius: 16px; padding: 24px; margin-bottom: 20px; box-shadow: 0 12px 40px rgba(0,0,0,0.12); }} 
            .header {{ display: flex; justify-content: space-between; align-items: center; gap: 16px; margin-bottom: 24px; color: white; }}
            .header a {{ color: white; text-decoration: none; font-weight: 600; }}
            .grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(240px, 1fr)); gap: 16px; }}
            .metric-card {{ background: #F8FBFC; border: 1px solid #D1E3E8; border-radius: 12px; padding: 18px; }}
            .metric-card h3 {{ margin: 0 0 8px; font-size: 1rem; color: #006494; }}
            .metric-card .value {{ font-size: 1.8rem; font-weight: 800; color: #1B98E0; }}
            .metric-card p {{ margin: 6px 0 0; color: #5A7A8C; }}
            .metric-card small {{ color: #5A7A8C; }}
            .chart-card {{ margin-top: 18px; }}
            .pill {{ display: inline-block; padding: 6px 10px; border-radius: 999px; font-size: 0.85rem; font-weight: 700; background: #E8F6FD; color: #006494; }}
            .legend {{ margin-top: 12px; color: #5A7A8C; font-size: 0.9rem; }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <div>
                    <h1>🏋️ Painel de Performance</h1>
                    <p>KPIs automáticos para musculação, hipertrofia e prevenção de lesões.</p>
                </div>
                <div>
                    <a href="/">⬅️ Dashboard</a>
                </div>
            </div>

            <div class="card">
                <div class="grid">
                    {''.join(balance_cards)}
                    {''.join(rpe_cards)}
                    {fatigue_badge}
                </div>
            </div>

            <div class="card">
                <h2>📈 Tendência do e1RM estimado</h2>
                <div class="chart-card">{e1rm_chart}</div>
            </div>

            <div class="card">
                <h2>🧠 Volume Semanal por Grupo Muscular</h2>
                <div class="chart-card">{weekly_chart}</div>
                <div class="legend">
                    {''.join(f"<div><span class='pill'>{group}</span> · {data['effective_sets']} séries · {data['alert']}</div>" for group, data in weekly_volume.items())}
                </div>
            </div>

            <div class="card">
                <h2>⚖️ Tonelagem Total por Sessão</h2>
                <div class="chart-card">{tonnage_chart}</div>
            </div>
        </div>
    </body>
    </html>
    """


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