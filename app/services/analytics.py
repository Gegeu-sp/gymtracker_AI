import plotly.express as px
import plotly.graph_objects as go
import plotly.io as pio
from datetime import datetime, timedelta, timezone
from html import escape as escape_html
from typing import Any, Dict, List, Optional

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


def _effective_rpe(exercise: Exercise) -> Optional[float]:
    """None quando o RPE nunca foi registrado — não deve ser confundido com um RPE real."""
    actual_rpe = getattr(exercise, "actual_rpe", None)
    if actual_rpe is not None and actual_rpe > 0:
        return float(actual_rpe)
    return None


def _resolve_muscle_group(exercise: Exercise) -> str:
    muscle_group = getattr(exercise, "muscle_group", None)
    if muscle_group:
        return muscle_group
    return get_muscle_group(exercise.name)


def _is_main_block_exercise(exercise: Exercise) -> bool:
    """
    "Séries efetivas" (FR-002/FR-003) são só do Bloco 2 (sessão principal), excluindo
    aquecimento/volta à calma — mesma heurística de nome usada em categorizeExercisesIntoBlocks
    no dashboard.html/extraction.html, portada para o backend.
    """
    name = (exercise.name or "").lower()
    warm_up_terms = ["bloco 1", "aquecimento", "mobilidade", "ativação", "ativacao", "warm-up", "warmup"]
    cool_down_terms = ["bloco 3", "volta à calma", "volta a calma", "cool-down", "cooldown", "recovery", "descompressão", "descompressao", "respiração", "respiracao"]
    if any(term in name for term in warm_up_terms):
        return False
    if any(term in name for term in cool_down_terms):
        return False
    return True


def _estimate_e1rm(exercise: Exercise) -> float:
    """
    Epley ajustado por RPE/RIR (Helms/Zourdos): RIR = 10 - RPE reps "escondidas" são somadas
    aos reps executados ANTES de aplicar Epley. RPE mais baixo (mais reps de reserva) resulta
    em e1RM estimado MAIOR, não menor — o atleta poderia ter feito mais reps até a falha.
    Sem RPE registrado, assume RIR=0 (equivalente a RPE 10, sem boost) — conservador, não
    inventa um "RPE típico".
    """
    weight = _effective_weight(exercise)
    reps = max(1, _effective_reps(exercise))
    if weight <= 0:
        return 0.0
    rpe = _effective_rpe(exercise)
    rir = max(0.0, 10.0 - rpe) if rpe is not None else 0.0
    return round(weight * (1 + (reps + rir) / 30.0), 1)


def _classify_push_pull(exercise: Exercise) -> tuple[str, int]:
    if not _is_main_block_exercise(exercise):
        return "", 0
    name = (exercise.name or "").lower()
    if any(term in name for term in ["supino", "peitoral", "crucifixo", "desenvolvimento", "tríceps", "triceps", "flexao", "mergulho", "coice"]):
        return "push", int(exercise.sets or 0)
    if any(term in name for term in ["puxada", "remada", "terra", "deadlift", "barra fixa", "rosca", "pull", "lat"]):
        return "pull", int(exercise.sets or 0)
    return "", 0


def _classify_quads_posterior(exercise: Exercise) -> tuple[str, int]:
    if not _is_main_block_exercise(exercise):
        return "", 0
    name = (exercise.name or "").lower()
    if any(term in name for term in ["agachamento", "squat", "extensora", "leg press", "afundo", "cadeira extensora", "cadeira adutora"]):
        return "quadriceps", int(exercise.sets or 0)
    if any(term in name for term in ["flexora", "stiff", "terra", "deadlift", "hip thrust", "elevacao pelvica", "glute"]):
        return "posterior", int(exercise.sets or 0)
    return "", 0


def build_performance_metrics(db: Session, student_name: Optional[str] = None) -> Dict[str, Any]:
    query = db.query(Workout)
    if student_name:
        query = query.filter(Workout.student_name.ilike(student_name))
    workouts = query.order_by(Workout.date).all()
    workouts = [w for w in workouts if w.exercises]

    e1rm_rows: List[Dict[str, Any]] = []
    session_tonnage: List[Dict[str, Any]] = []
    session_rpe: List[Dict[str, Any]] = []
    weekly_sets_by_group: Dict[str, int] = {}
    weekly_reps_by_group: Dict[str, int] = {}
    weekly_load_by_group: Dict[str, float] = {}

    # Janela semanal a partir de AGORA (FR-002), não da data do último treino registrado —
    # senão a "semana" desliza pra trás junto com o histórico e pode mascarar sub-treino real.
    weekly_cutoff = datetime.now(timezone.utc) - timedelta(days=7)

    for workout in workouts:
        workout_date = workout.date if workout.date.tzinfo else workout.date.replace(tzinfo=timezone.utc)
        session_tonnage_value = 0.0
        session_rpe_values: List[float] = []
        for exercise in workout.exercises:
            effective_weight = _effective_weight(exercise)
            effective_reps = max(1, _effective_reps(exercise))
            effective_sets = max(1, int(getattr(exercise, "sets", 0) or 0))
            is_main_block = _is_main_block_exercise(exercise)

            # Tonelagem da sessão (FR-003) é só do Bloco 2 (sessão principal) — aquecimento e
            # volta à calma não têm carga de trabalho real e inflavam o número artificialmente.
            if is_main_block:
                session_tonnage_value += effective_sets * effective_reps * effective_weight

            rpe = _effective_rpe(exercise)
            if rpe is not None:
                session_rpe_values.append(rpe)

            if is_main_block and workout_date >= weekly_cutoff:
                muscle_group = _resolve_muscle_group(exercise)
                weekly_sets_by_group[muscle_group] = weekly_sets_by_group.get(muscle_group, 0) + effective_sets
                weekly_reps_by_group[muscle_group] = weekly_reps_by_group.get(muscle_group, 0) + (effective_sets * effective_reps)
                weekly_load_by_group[muscle_group] = weekly_load_by_group.get(muscle_group, 0.0) + (effective_sets * effective_reps * effective_weight)

            if any(keyword in (exercise.name or "").lower() for keyword in ["supino", "agachamento", "terra", "deadlift", "squat", "bench"]):
                e1rm_value = _estimate_e1rm(exercise)
                if e1rm_value > 0:
                    e1rm_rows.append({
                        "date": workout_date,
                        "exercise": exercise.name,
                        "e1rm": e1rm_value,
                        "load_kg": round(effective_weight, 1),
                        "rpe": rpe,
                    })

        session_tonnage.append({
            "date": workout_date,
            "session": workout.notes or f"Treino {workout.id}",
            "tonnage": round(session_tonnage_value, 1),
        })

        if session_rpe_values:
            avg_rpe = round(sum(session_rpe_values) / len(session_rpe_values), 1)
            session_rpe.append({
                "date": workout_date,
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
            "effective_reps": weekly_reps_by_group.get(group, 0),
            "load_kg": round(weekly_load_by_group.get(group, 0.0), 1),
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

    # Faixa "saudável" 0.5-1.1: puxar até o dobro do que empurra é bom (protege ombro),
    # só alerta quando o empurrar domina claramente (ex: 1:0.5 = ratio 2.0).
    balance = {
        "push_pull": {
            "ratio": push_pull_ratio,
            "push_sets": push_sets,
            "pull_sets": pull_sets,
            "status": "ok" if push_pull_ratio is None or 0.5 <= push_pull_ratio <= 1.1 else "alert",
        },
        "quadriceps_posterior": {
            "ratio": quadriceps_posterior_ratio,
            "quadriceps_sets": quad_sets,
            "posterior_sets": posterior_sets,
            "status": "ok" if quadriceps_posterior_ratio is None or 0.5 <= quadriceps_posterior_ratio <= 1.5 else "alert",
        },
    }

    fatigue = {"status": "green", "message": "✅ Recuperação adequada. Mantém o plano atual."}
    if len(session_rpe) >= 2:
        recent_rpe = session_rpe[-3:]
        if len(recent_rpe) >= 2 and recent_rpe[-1]["average_rpe"] >= 8.5 and recent_rpe[-1]["average_rpe"] > recent_rpe[0]["average_rpe"]:
            fatigue = {"status": "yellow", "message": "⚠️ RPE médio subindo sem redução de carga. Avalie deload."}

    for compound in ["Supino", "Agachamento", "Terra"]:
        history = [row for row in e1rm_rows if compound.lower() in (row["exercise"] or "").lower()]
        if len(history) >= 3:
            recent = history[-3:]
            e1rm_values = [r["e1rm"] for r in recent]
            load_values = [r["load_kg"] for r in recent]
            rpe_values = [r["rpe"] for r in recent if r["rpe"] is not None]
            e1rm_stagnant = (max(e1rm_values) - min(e1rm_values)) <= 1.5
            load_stable = (max(load_values) - min(load_values)) <= 2.5
            rpe_rising = len(rpe_values) >= 2 and rpe_values[-1] > rpe_values[0]
            if e1rm_stagnant and load_stable and rpe_rising:
                fatigue = {"status": "red", "message": f"🔴 {compound} estabilizou o e1RM com RPE crescente nas últimas 3 sessões. Considere reduzir volume ou aplicar deload."}
                break

    return {
        "e1rm_trend": e1rm_rows,
        "weekly_volume": weekly_volume,
        "session_tonnage": session_tonnage,
        "balance": balance,
        "session_rpe": session_rpe,
        "fatigue": fatigue,
    }


def get_performance_dashboard(db: Session, student_name: Optional[str] = None) -> str:
    metrics = build_performance_metrics(db, student_name=student_name)
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

    weekly_breakdown_chart = ""
    if weekly_volume:
        groups = list(weekly_volume.keys())
        fig = go.Figure()
        fig.add_trace(go.Bar(name="Séries", x=groups, y=[item["effective_sets"] for item in weekly_volume.values()], marker_color="#1B98E0"))
        fig.add_trace(go.Bar(name="Repetições", x=groups, y=[item["effective_reps"] for item in weekly_volume.values()], marker_color="#247BA0"))
        fig.add_trace(go.Bar(name="Carga (kg)", x=groups, y=[item["load_kg"] for item in weekly_volume.values()], marker_color="#006494"))
        fig.update_layout(title="📊 Volume semanal — Séries / Repetições / Carga por grupo muscular", xaxis_title="Grupo muscular", barmode="group", template="plotly_white")
        weekly_breakdown_chart = pio.to_html(fig, full_html=False, include_plotlyjs="cdn")
    else:
        weekly_breakdown_chart = "<p style='color:#5A7A8C;'>Sem dados suficientes para o detalhamento semanal.</p>"

    tonnage_chart = ""
    if session_tonnage:
        fig = go.Figure()
        fig.add_trace(go.Bar(
            x=[f"{item['date'].strftime('%d/%m')} · {item['session']}" for item in session_tonnage],
            y=[item["tonnage"] for item in session_tonnage],
            marker_color="#1B98E0",
        ))
        fig.update_layout(title="🏋️ Tonelagem total por sessão", xaxis_title="Sessão", yaxis_title="Tonelagem (kg)", template="plotly_white")
        tonnage_chart = pio.to_html(fig, full_html=False, include_plotlyjs="cdn")
    else:
        tonnage_chart = "<p style='color:#5A7A8C;'>Sem dados de tonagem registrada.</p>"

    rpe_chart = ""
    if session_rpe:
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=[item["date"].strftime("%Y-%m-%d") for item in session_rpe],
            y=[item["average_rpe"] for item in session_rpe],
            mode="lines+markers",
            line=dict(color="#006494", width=3),
            marker=dict(color=["#2ECC71" if item["status"] == "ideal" else "#F39C12" for item in session_rpe], size=9),
        ))
        fig.update_layout(title="🔥 Tendência do RPE médio por sessão", xaxis_title="Data", yaxis_title="RPE médio", template="plotly_white", yaxis=dict(range=[0, 10]))
        rpe_chart = pio.to_html(fig, full_html=False, include_plotlyjs="cdn")
    else:
        rpe_chart = "<p style='color:#5A7A8C;'>Sem dados de RPE ainda — registre a execução real (Histórico → Registrar Execução, ou Modo ao Vivo) para começar a ver a tendência.</p>"

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
        rpe_cards.append("<div class='metric-card'><h3>RPE Médio</h3><div class='value'>—</div><p>Sem dados — registre a execução real (Histórico → Registrar Execução, ou Modo ao Vivo) para ver o RPE médio.</p></div>")

    fatigue_badge = f"<div class='metric-card'><h3>Semáforo de Fadiga</h3><div class='value'>{fatigue['status'].upper()}</div><p>{fatigue['message']}</p></div>"

    all_students = [
        r[0] for r in db.query(Workout.student_name)
        .filter(Workout.student_name.isnot(None), Workout.student_name != "")
        .distinct().order_by(Workout.student_name).all()
    ]
    student_options = "".join(
        f'<option value="{escape_html(s)}"{" selected" if s == student_name else ""}>{escape_html(s)}</option>'
        for s in all_students
    )
    student_selector = f"""
        <select onchange="location.href='/analytics/performance' + (this.value ? '?student_name=' + encodeURIComponent(this.value) : '')" style="padding: 10px 16px; border-radius: 8px; border: none; font-size: 1rem;">
            <option value="">👥 Todos os Alunos</option>
            {student_options}
        </select>
    """

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
            .pill-ok {{ background: #E4F9EE; color: #1E8449; }}
            .pill-sub-treinado {{ background: #FEF3E2; color: #B9770E; }}
            .pill-overtraining {{ background: #FDECEA; color: #C0392B; }}
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
                <div style="display: flex; align-items: center; gap: 16px;">
                    {student_selector}
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
                <h2>🔥 Tendência do RPE Médio</h2>
                <div class="chart-card">{rpe_chart}</div>
            </div>

            <div class="card">
                <h2>🧠 Volume Semanal por Grupo Muscular</h2>
                <div class="chart-card">{weekly_chart}</div>
                <div class="legend">
                    {''.join(f"<div><span class='pill pill-{data['status']}'>{group}</span> · {data['effective_sets']} séries · {data['alert']}</div>" for group, data in weekly_volume.items())}
                </div>
            </div>

            <div class="card">
                <h2>📊 Volume Semanal — Séries / Repetições / Carga</h2>
                <div class="chart-card">{weekly_breakdown_chart}</div>
            </div>

            <div class="card">
                <h2>⚖️ Tonelagem Total por Sessão</h2>
                <div class="chart-card">{tonnage_chart}</div>
            </div>
        </div>
    </body>
    </html>
    """


# Cabeçalho mínimo de navegação para os fragmentos de gráfico abaixo, que não têm um
# <html>/<head> próprio — antes eram becos sem saída (só dava pra sair pelo botão voltar
# do navegador), sem nenhum link de volta ao Dashboard.
_BACK_TO_DASHBOARD_HEADER = """
<div style="font-family:'Segoe UI',Arial,sans-serif; background:linear-gradient(135deg,#006494 0%,#247BA0 100%); padding:14px 20px;">
    <a href="/" style="color:white; text-decoration:none; font-weight:600;">⬅️ Dashboard</a>
</div>
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
        return _BACK_TO_DASHBOARD_HEADER + "<p style='font-family:sans-serif;padding:20px;'>📊 Sem dados ainda. Registre seu primeiro treino!</p>"

    fig = px.line(
        data, x="data", y="volume_kg",
        title="📈 Volume Total por Treino (kg)",
        markers=True
    )
    fig.update_layout(template="plotly_white")
    return _BACK_TO_DASHBOARD_HEADER + pio.to_html(fig, full_html=False)


def get_exercise_distribution(db: Session) -> str:
    """Distribuição dos exercícios mais feitos."""
    exercises = db.query(Exercise.name).all()
    counts = {}
    for ex in exercises:
        counts[ex.name] = counts.get(ex.name, 0) + 1

    sorted_counts = sorted(counts.items(), key=lambda x: x[1], reverse=True)[:10]
    data = [{"nome": nome, "quantidade": qtd} for nome, qtd in sorted_counts]

    if not data:
        return _BACK_TO_DASHBOARD_HEADER + "<p style='font-family:sans-serif;padding:20px;'>📊 Sem dados ainda.</p>"

    fig = px.bar(
        data, x="quantidade", y="nome", orientation="h",
        title="🏋️ Top 10 Exercícios Mais Feitos"
    )
    fig.update_layout(template="plotly_white")
    return _BACK_TO_DASHBOARD_HEADER + pio.to_html(fig, full_html=False)


def get_muscle_group_chart(db: Session) -> str:
    """Distribuição por grupo muscular, via app/services/exercise_catalog.py."""
    exercises = db.query(Exercise.name).all()
    if not exercises:
        return _BACK_TO_DASHBOARD_HEADER + "<p style='font-family:sans-serif;padding:20px;'>📊 Sem dados ainda.</p>"

    groups = {}
    for ex in exercises:
        grupo = get_muscle_group(ex.name)
        groups[grupo] = groups.get(grupo, 0) + 1

    data = [{"grupo": k, "total": v} for k, v in groups.items()]
    fig = px.pie(data, names="grupo", values="total", title="💪 Distribuição por Grupo Muscular")
    fig.update_layout(template="plotly_white")
    return _BACK_TO_DASHBOARD_HEADER + pio.to_html(fig, full_html=False)