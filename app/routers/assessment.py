from html import escape as escape_html
from typing import List, Optional

from fastapi import APIRouter, Depends
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import PhysicalAssessment
from ..schemas import PhysicalAssessmentCreate, PhysicalAssessmentOut
from ..services.assessment_service import save_assessment, get_assessment_report_html

router = APIRouter(prefix="/assessments", tags=["assessments"])


@router.post("/", response_model=PhysicalAssessmentOut)
def create_assessment(data: PhysicalAssessmentCreate, db: Session = Depends(get_db)):
    return save_assessment(db, data)


@router.get("/", response_model=List[PhysicalAssessmentOut])
def list_assessments(student_name: Optional[str] = None, db: Session = Depends(get_db)):
    query = db.query(PhysicalAssessment)
    if student_name:
        query = query.filter(PhysicalAssessment.student_name.ilike(student_name))
    return query.order_by(PhysicalAssessment.date.desc()).all()


@router.get("/students", response_model=List[str])
def list_assessment_students(db: Session = Depends(get_db)):
    return [
        r[0] for r in db.query(PhysicalAssessment.student_name)
        .filter(PhysicalAssessment.student_name.isnot(None), PhysicalAssessment.student_name != "")
        .distinct().order_by(PhysicalAssessment.student_name).all()
    ]


@router.get("/report", response_class=HTMLResponse)
def assessment_report(student_name: str, db: Session = Depends(get_db)):
    return get_assessment_report_html(db, student_name)


@router.get("/view", response_class=HTMLResponse)
def view_assessments(student_name: Optional[str] = None, db: Session = Depends(get_db)):
    query = db.query(PhysicalAssessment)
    if student_name:
        query = query.filter(PhysicalAssessment.student_name.ilike(student_name))
    assessments = query.order_by(PhysicalAssessment.date.desc()).all()

    all_students = [
        r[0] for r in db.query(PhysicalAssessment.student_name)
        .filter(PhysicalAssessment.student_name.isnot(None), PhysicalAssessment.student_name != "")
        .distinct().order_by(PhysicalAssessment.student_name).all()
    ]
    student_options = "".join(
        f'<option value="{escape_html(s)}"{" selected" if s == student_name else ""}>{escape_html(s)}</option>'
        for s in all_students
    )
    datalist_options = "".join(f'<option value="{escape_html(s)}">' for s in all_students)

    def fmt(value, suffix=""):
        return f"{value}{suffix}" if value is not None else "—"

    rows_html = "".join(f"""
        <tr>
            <td class="date">{a.date.strftime('%d/%m/%Y')}</td>
            <td>{escape_html(a.student_name)}</td>
            <td>{fmt(a.age_years, ' anos')}</td>
            <td>{fmt(a.weight_kg, ' kg')}</td>
            <td>{fmt(a.height_cm, ' cm')}</td>
            <td>{fmt(a.flexibility_cm, ' cm')}</td>
            <td>{fmt(a.abdominal_reps, ' reps')}</td>
            <td>{fmt(a.upper_body_power_m, ' m')}</td>
            <td>{fmt(a.agility_seconds, ' s')}</td>
            <td>{fmt(a.aerobic_result)}{f" ({a.aerobic_test_type})" if a.aerobic_test_type else ""}</td>
            <td>{escape_html(a.notes) if a.notes else ""}</td>
        </tr>
    """ for a in assessments)

    report_link = (
        f'<a href="/assessments/report?student_name={escape_html(student_name)}" target="_blank" class="btn-report">📊 Ver Relatório</a>'
        if student_name else ""
    )

    return f"""
    <!DOCTYPE html>
    <html lang="pt-BR">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Avaliação Física | Gym Tracker AI</title>
        <style>
            * {{ margin: 0; padding: 0; box-sizing: border-box; }}
            body {{ font-family: 'Segoe UI', system-ui, sans-serif; background: linear-gradient(135deg, #006494 0%, #247BA0 100%); min-height: 100vh; padding: 40px 20px; }}
            .container {{ max-width: 1600px; margin: 0 auto; background: #E8F1F2; padding: 40px; border-radius: 16px; box-shadow: 0 10px 40px rgba(0,0,0,0.2); }}
            h1 {{ text-align: center; color: #006494; margin-bottom: 30px; font-size: 2.2rem; }}
            .card {{ background: white; border-radius: 12px; padding: 24px; margin-bottom: 24px; box-shadow: 0 4px 16px rgba(0,0,0,0.08); }}
            .card h2 {{ color: #006494; margin-bottom: 16px; font-size: 1.3rem; }}
            form {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 14px; }}
            label {{ display: block; font-size: 0.85rem; color: #247BA0; font-weight: 600; margin-bottom: 4px; }}
            input, select {{ width: 100%; padding: 10px; border: 2px solid #D1E3E8; border-radius: 8px; font-size: 0.95rem; font-family: inherit; }}
            .form-actions {{ grid-column: 1 / -1; text-align: right; }}
            button[type="submit"] {{ padding: 12px 24px; background: #006494; color: white; border: none; border-radius: 8px; cursor: pointer; font-weight: 700; font-size: 1rem; }}
            button[type="submit"]:hover {{ background: #01476b; }}
            table {{ width: 100%; border-collapse: separate; border-spacing: 0; background: white; border-radius: 12px; overflow: hidden; font-size: 0.85rem; }}
            th {{ background: linear-gradient(135deg, #006494 0%, #1B98E0 100%); color: white; padding: 12px 8px; text-align: left; font-weight: 600; text-transform: uppercase; font-size: 0.75rem; }}
            td {{ padding: 10px 8px; border-bottom: 1px solid #ddd; }}
            tr:hover td {{ background: #f0f8ff; }}
            .student-filter {{ text-align: center; margin-bottom: 25px; display: flex; justify-content: center; align-items: center; gap: 16px; }}
            .student-filter select {{ padding: 10px 16px; border-radius: 8px; border: 2px solid #D1E3E8; font-size: 1rem; font-family: inherit; background: white; color: #006494; }}
            .btn-report {{ padding: 10px 18px; background: #0288d1; color: white; border-radius: 8px; text-decoration: none; font-weight: 700; }}
            .links {{ text-align: center; margin-top: 30px; }}
            .links a {{ margin: 0 15px; color: #006494; text-decoration: none; font-weight: 600; }}
            .links a:hover {{ text-decoration: underline; }}
        </style>
    </head>
    <body>
        <div class="container">
            <h1>🧪 Avaliação Física (Testes PROESP-BR)</h1>

            <div class="card">
                <h2>Nova Avaliação</h2>
                <form id="assessmentForm">
                    <div>
                        <label>Aluno *</label>
                        <input type="text" name="student_name" list="studentList" required value="{escape_html(student_name) if student_name else ''}">
                        <datalist id="studentList">{datalist_options}</datalist>
                    </div>
                    <div><label>Idade (anos)</label><input type="number" name="age_years" min="1" max="25"></div>
                    <div><label>Peso (kg)</label><input type="number" step="0.1" name="weight_kg"></div>
                    <div><label>Altura (cm)</label><input type="number" step="0.1" name="height_cm"></div>
                    <div><label>Flexibilidade — Sentar e Alcançar (cm)</label><input type="number" step="0.1" name="flexibility_cm"></div>
                    <div><label>Resistência Abdominal (reps/1min)</label><input type="number" name="abdominal_reps"></div>
                    <div><label>Arremesso de Medicine Ball (m)</label><input type="number" step="0.1" name="upper_body_power_m"></div>
                    <div><label>Agilidade — Shuttle Run (s)</label><input type="number" step="0.1" name="agility_seconds"></div>
                    <div>
                        <label>Teste Aeróbio</label>
                        <select name="aerobic_test_type">
                            <option value="">Não aplicado</option>
                            <option value="vaivem">Vaivém 20m (nível)</option>
                            <option value="corrida_9min">Corrida/Caminhada 9min (m)</option>
                        </select>
                    </div>
                    <div><label>Resultado Aeróbio (nível ou metros)</label><input type="number" step="0.1" name="aerobic_result"></div>
                    <div style="grid-column: 1 / -1;"><label>Observações</label><input type="text" name="notes"></div>
                    <div class="form-actions"><button type="submit">💾 Salvar Avaliação</button></div>
                </form>
            </div>

            <div class="student-filter">
                <select onchange="location.href='/assessments/view' + (this.value ? '?student_name=' + encodeURIComponent(this.value) : '')">
                    <option value="">👥 Todos os Alunos</option>
                    {student_options}
                </select>
                {report_link}
            </div>

            <table>
                <thead>
                    <tr>
                        <th>Data</th><th>Aluno</th><th>Idade</th><th>Peso</th><th>Altura</th>
                        <th>Flexibilidade</th><th>Abdominal</th><th>Arremesso</th><th>Agilidade</th><th>Aeróbio</th><th>Obs.</th>
                    </tr>
                </thead>
                <tbody>
                    {rows_html if rows_html else '<tr><td colspan="11" style="text-align:center; padding: 24px; color: #5A7A8C;">Nenhuma avaliação registrada ainda.</td></tr>'}
                </tbody>
            </table>

            <div class="links">
                <a href="/">🏠 Dashboard</a>
                <a href="/workouts/view">📋 Histórico de Treinos</a>
            </div>
        </div>

        <script>
            document.getElementById('assessmentForm').addEventListener('submit', async (e) => {{
                e.preventDefault();
                const form = e.target;
                const fd = new FormData(form);
                const payload = {{}};
                for (const [key, value] of fd.entries()) {{
                    if (value === '') continue;
                    if (['age_years', 'abdominal_reps'].includes(key)) {{
                        payload[key] = parseInt(value, 10);
                    }} else if (['weight_kg', 'height_cm', 'flexibility_cm', 'upper_body_power_m', 'agility_seconds', 'aerobic_result'].includes(key)) {{
                        payload[key] = parseFloat(value);
                    }} else {{
                        payload[key] = value;
                    }}
                }}
                try {{
                    const res = await fetch('/assessments/', {{
                        method: 'POST',
                        headers: {{ 'Content-Type': 'application/json' }},
                        body: JSON.stringify(payload)
                    }});
                    if (!res.ok) {{
                        const err = await res.json();
                        alert('Erro ao salvar: ' + JSON.stringify(err.detail));
                        return;
                    }}
                    location.href = '/assessments/view?student_name=' + encodeURIComponent(payload.student_name);
                }} catch (err) {{
                    alert('Erro ao salvar avaliação: ' + err.message);
                }}
            }});
        </script>
    </body>
    </html>
    """
