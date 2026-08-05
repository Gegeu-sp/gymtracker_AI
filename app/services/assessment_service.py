import json
import re
from datetime import datetime
from html import escape as escape_html
from typing import Any, Dict, List, Optional, Tuple

import plotly.graph_objects as go
import plotly.io as pio
from sqlalchemy.orm import Session

from ..models import PhysicalAssessment
from ..schemas import PhysicalAssessmentCreate
from .analytics import _BACK_TO_DASHBOARD_HEADER

# (campo, rótulo, unidade, higher_is_better) — higher_is_better=None significa "sem julgamento
# de direção" (ex: peso/altura são só acompanhamento de crescimento, não "melhor/pior").
TEST_FIELDS: List[Tuple[str, str, str, Optional[bool]]] = [
    ("weight_kg", "Peso", "kg", None),
    ("height_cm", "Altura", "cm", None),
    ("bmi", "IMC", "kg/m²", None),
    ("flexibility_cm", "Flexibilidade (Sentar e Alcançar)", "cm", True),
    ("abdominal_reps", "Resistência Abdominal (1 min)", "reps", True),
    ("upper_body_power_m", "Força de Membros Superiores (Arremesso)", "m", True),
    ("agility_seconds", "Agilidade (Shuttle Run)", "s", False),
    ("aerobic_result", "Resistência Aeróbia (Vaivém/Corrida 9min)", "nível ou m", True),
]


def save_assessment(db: Session, data: PhysicalAssessmentCreate) -> PhysicalAssessment:
    assessment = PhysicalAssessment(**data.model_dump())
    db.add(assessment)
    db.commit()
    db.refresh(assessment)
    return assessment


def _bmi(weight_kg: Optional[float], height_cm: Optional[float]) -> Optional[float]:
    if not weight_kg or not height_cm:
        return None
    height_m = height_cm / 100.0
    if height_m <= 0:
        return None
    return round(weight_kg / (height_m ** 2), 1)


def build_assessment_report(db: Session, student_name: str) -> Dict[str, Any]:
    assessments = (
        db.query(PhysicalAssessment)
        .filter(PhysicalAssessment.student_name.ilike(student_name))
        .order_by(PhysicalAssessment.date)
        .all()
    )

    tests: Dict[str, Dict[str, Any]] = {}
    for field, label, unit, higher_is_better in TEST_FIELDS:
        history: List[Tuple[datetime, float]] = []
        for assessment in assessments:
            if field == "bmi":
                value = _bmi(assessment.weight_kg, assessment.height_cm)
            else:
                value = getattr(assessment, field, None)
            if value is not None:
                history.append((assessment.date, value))

        if not history:
            direction = "sem_dados"
            latest_value = previous_value = delta = delta_pct = None
        elif len(history) == 1:
            direction = "primeira_avaliacao"
            latest_value = history[-1][1]
            previous_value = delta = delta_pct = None
        else:
            latest_value = history[-1][1]
            previous_value = history[-2][1]
            delta = round(latest_value - previous_value, 2)
            delta_pct = round((delta / previous_value) * 100, 1) if previous_value else None
            if higher_is_better is None:
                direction = "neutro"
            elif delta == 0:
                direction = "manteve"
            elif (delta > 0) == higher_is_better:
                direction = "melhorou"
            else:
                direction = "piorou"

        tests[field] = {
            "label": label,
            "unit": unit,
            "higher_is_better": higher_is_better,
            "history": history,
            "latest_value": latest_value,
            "previous_value": previous_value,
            "delta": delta,
            "delta_pct": delta_pct,
            "direction": direction,
        }

    return {
        "student_name": student_name,
        "assessments_count": len(assessments),
        "latest_date": assessments[-1].date if assessments else None,
        "latest_age_years": assessments[-1].age_years if assessments else None,
        "tests": tests,
    }


_DIRECTION_BADGE = {
    "melhorou": "✅ Melhorou",
    "manteve": "➡️ Manteve",
    "piorou": "⚠️ Piorou",
    "neutro": "📊 Acompanhamento",
    "primeira_avaliacao": "🆕 Primeira avaliação",
    "sem_dados": "— Sem dados",
}


def get_assessment_report_html(db: Session, student_name: str) -> str:
    report = build_assessment_report(db, student_name)
    tests = report["tests"]

    if report["assessments_count"] == 0:
        return (
            _BACK_TO_DASHBOARD_HEADER
            + f"<p style='font-family:sans-serif;padding:20px;'>📊 Nenhuma avaliação física registrada ainda para {escape_html(student_name)}.</p>"
        )

    summary_cards = []
    for field, _, _, _ in TEST_FIELDS:
        data = tests[field]
        if data["latest_value"] is None:
            continue
        value_str = f"{data['latest_value']:.1f} {data['unit']}"
        delta_str = ""
        if data["delta"] is not None:
            sign = "+" if data["delta"] > 0 else ""
            delta_str = f"<small>{sign}{data['delta']:.1f} {data['unit']} desde a avaliação anterior</small>"
        summary_cards.append(
            f"<div class='metric-card'><h3>{escape_html(data['label'])}</h3>"
            f"<div class='value'>{value_str}</div>"
            f"<p>{_DIRECTION_BADGE.get(data['direction'], '')}</p>"
            f"{delta_str}</div>"
        )

    charts_html = []
    for field, label, unit, _ in TEST_FIELDS:
        data = tests[field]
        history = data["history"]
        if len(history) < 2:
            chart = f"<p style='color:#5A7A8C;'>Precisa de pelo menos 2 avaliações com {escape_html(label)} registrado para mostrar a evolução.</p>"
        else:
            fig = go.Figure()
            fig.add_trace(go.Scatter(
                x=[d.strftime("%d/%m/%Y") for d, _ in history],
                y=[v for _, v in history],
                mode="lines+markers",
                line=dict(color="#006494", width=3),
                marker=dict(color="#1B98E0", size=9),
            ))
            fig.update_layout(title=f"{label} ({unit})", xaxis_title="Data", yaxis_title=unit, template="plotly_white")
            chart = pio.to_html(fig, full_html=False, include_plotlyjs="cdn")
        charts_html.append(f"<div class='card'><h2>{escape_html(label)}</h2><div class='chart-card'>{chart}</div></div>")

    latest_date_str = report["latest_date"].strftime("%d/%m/%Y") if report["latest_date"] else ""
    age_str = f" · {report['latest_age_years']} anos" if report["latest_age_years"] else ""
    student_slug = re.sub(r"[^\w\-]+", "_", report["student_name"])
    safe_filename = json.dumps(f"Avaliacao_{student_slug}.pdf")

    return f"""
    <!DOCTYPE html>
    <html lang="pt-BR">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Relatório de Avaliação Física | Gym Tracker AI</title>
        <script src="https://cdnjs.cloudflare.com/ajax/libs/html2pdf.js/0.10.1/html2pdf.bundle.min.js"></script>
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
            .btn-pdf {{ padding: 10px 18px; background: #0288d1; color: white; border: none; border-radius: 8px; cursor: pointer; font-size: 0.95rem; font-weight: 700; }}
            .btn-pdf:hover {{ background: #01579b; }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <div>
                    <h1>🧪 Relatório de Avaliação Física</h1>
                    <p>{escape_html(report["student_name"])}{age_str} · {report["assessments_count"]} avaliação(ões) · última em {latest_date_str}</p>
                </div>
                <div style="display: flex; align-items: center; gap: 16px;">
                    <button class="btn-pdf" onclick="baixarRelatorioPDF()">📄 Baixar PDF do Relatório</button>
                    <a href="/">⬅️ Dashboard</a>
                </div>
            </div>

            <div id="reportContent">
                <div class="card">
                    <div class="grid">
                        {''.join(summary_cards) if summary_cards else "<p style='color:#5A7A8C;'>Sem resultados registrados ainda.</p>"}
                    </div>
                </div>

                {''.join(charts_html)}
            </div>
        </div>

        <script>
            function baixarRelatorioPDF() {{
                const element = document.getElementById('reportContent');
                const opt = {{
                    margin: 10,
                    filename: {safe_filename},
                    image: {{ type: 'jpeg', quality: 0.98 }},
                    html2canvas: {{ scale: 2, useCORS: true }},
                    jsPDF: {{ unit: 'mm', format: 'a4', orientation: 'portrait' }}
                }};
                html2pdf().set(opt).from(element).save();
            }}
        </script>
    </body>
    </html>
    """
