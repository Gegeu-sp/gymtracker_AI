from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session
from typing import List
from ..database import get_db
from ..models import Workout, Exercise
from ..schemas import (
    WorkoutCreate, WorkoutOut, WorkoutGenerationRequest,
    WorkoutEditRequest, WorkoutExecutionRequest, ExerciseProgressionOut
)
from ..services.llm_service import generate_workout
from ..services.progression_service import get_workout_progression_suggestions
from ..services.workout_service import apply_execution_result

router = APIRouter(prefix="/workouts", tags=["workouts"])

@router.post("/", response_model=WorkoutOut)
def create_manual_workout(data: WorkoutCreate, db: Session = Depends(get_db)):
    w = Workout(source="manual", notes=data.notes)
    db.add(w)
    db.commit()
    db.refresh(w)
    for ex in data.exercises:
        db.add(Exercise(workout_id=w.id, **ex.model_dump()))
    db.commit()
    
    # Garante a ordem correta ao retornar
    return db.query(Workout).filter(Workout.id == w.id).first()

@router.post("/generate", response_model=list[WorkoutOut])
def generate_workout_endpoint(req: WorkoutGenerationRequest, db: Session = Depends(get_db)):
    request_dict = req.model_dump()
    parsed = generate_workout(request_dict)
    
    if "workouts" not in parsed or not parsed["workouts"]:
        raise HTTPException(status_code=500, detail="Falha ao gerar treinos com LLM.")
    
    saved_workouts = []
    
    for day_data in parsed["workouts"]:
        prof_name = req.professor_name or "N/A"
        notes = f"🤖 Prof. {prof_name} | Objetivo: {req.goal.capitalize()} | Nível: {req.level.capitalize()}"
            
        workout = Workout(source="llm", notes=notes)
        db.add(workout)
        db.commit()
        db.refresh(workout)
        
        for ex_data in day_data.get("exercises", []):
            db.add(Exercise(
                workout_id=workout.id,
                name=ex_data.get("name", "Exercício"),
                nickname=ex_data.get("nickname"),
                equipment=ex_data.get("equipment"),
                accessory=ex_data.get("accessory"),
                method=ex_data.get("method"),
                sets=int(ex_data.get("sets", 3)),
                reps=int(ex_data.get("reps", 10)),
                weight_kg=float(ex_data.get("weight_kg", 0) or 0),
                is_edited=False
            ))
        db.commit()
        
        saved_workout = db.query(Workout).filter(Workout.id == workout.id).first()
        saved_workouts.append(saved_workout)
        
    return saved_workouts

@router.put("/{workout_id}/edit", response_model=WorkoutOut)
def edit_workout_prescription(
    workout_id: int, 
    data: WorkoutEditRequest, 
    db: Session = Depends(get_db)
):
    """
    Edição manual pré-salvamento: permite ajustar séries, repetições, carga e método
    dos exercícios gerados antes de confirmar a sessão.
    """
    workout = db.query(Workout).filter(Workout.id == workout_id).first()
    if not workout:
        raise HTTPException(status_code=404, detail="Treino não encontrado.")

    if data.notes is not None:
        workout.notes = data.notes

    for edit_item in data.exercises:
        ex = db.query(Exercise).filter(
            Exercise.id == edit_item.exercise_id, 
            Exercise.workout_id == workout_id
        ).first()
        if ex:
            if edit_item.sets is not None:
                ex.sets = edit_item.sets
            if edit_item.reps is not None:
                ex.reps = edit_item.reps
            if edit_item.weight_kg is not None:
                ex.weight_kg = edit_item.weight_kg
            if edit_item.method is not None:
                ex.method = edit_item.method
            ex.is_edited = True

    db.commit()
    db.refresh(workout)
    return workout

@router.post("/{workout_id}/log", response_model=WorkoutOut)
def log_workout_execution(
    workout_id: int, 
    data: WorkoutExecutionRequest, 
    db: Session = Depends(get_db)
):
    """
    Registro pós-treino: grava os dados reais executados (carga real, repetições reais e RPE percebido)
    e atualiza a tabela `workout_progress` para acompanhamento de evolução.
    """
    workout = db.query(Workout).filter(Workout.id == workout_id).first()
    if not workout:
        raise HTTPException(status_code=404, detail="Treino não encontrado.")

    for exec_item in data.executions:
        ex = db.query(Exercise).filter(
            Exercise.id == exec_item.exercise_id, 
            Exercise.workout_id == workout_id
        ).first()
        if not ex:
            continue

        apply_execution_result(
            db, ex,
            actual_weight_kg=exec_item.actual_weight_kg,
            actual_reps=exec_item.actual_reps,
            actual_rpe=exec_item.actual_rpe
        )

    db.commit()
    db.refresh(workout)
    return workout

@router.get("/{workout_id}/progression", response_model=List[ExerciseProgressionOut])
def get_workout_progression(workout_id: int, db: Session = Depends(get_db)):
    """
    Calcula e retorna a sugestão de sobrecarga progressiva para cada exercício do treino
    com base nas execuções passadas e aplicando a trava de segurança de 120%.
    """
    workout = db.query(Workout).filter(Workout.id == workout_id).first()
    if not workout:
        raise HTTPException(status_code=404, detail="Treino não encontrado.")

    return get_workout_progression_suggestions(db, workout_id)

@router.get("/", response_model=list[WorkoutOut])
def list_workouts(db: Session = Depends(get_db)):
    return db.query(Workout).order_by(Workout.date.desc()).all()

@router.get("/view", response_class=HTMLResponse)
def view_workouts_table(db: Session = Depends(get_db)):
    workouts = db.query(Workout).order_by(Workout.date.desc()).all()
    
    html = """
    <!DOCTYPE html>
    <html lang="pt-BR">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Histórico de Treinos</title>
        <script src="https://cdnjs.cloudflare.com/ajax/libs/html2pdf.js/0.10.1/html2pdf.bundle.min.js"></script>
        <style>
            * { margin: 0; padding: 0; box-sizing: border-box; }
            body { font-family: 'Segoe UI', system-ui, sans-serif; background: linear-gradient(135deg, #006494 0%, #247BA0 100%); min-height: 100vh; padding: 40px 20px; }
            .container { max-width: 1600px; margin: 0 auto; background: #E8F1F2; padding: 40px; border-radius: 16px; box-shadow: 0 10px 40px rgba(0,0,0,0.2); }
            h1 { text-align: center; color: #006494; margin-bottom: 40px; font-size: 2.5rem; }
            table { width: 100%; border-collapse: separate; border-spacing: 0; background: white; border-radius: 12px; overflow: hidden; }
            th { background: linear-gradient(135deg, #006494 0%, #1B98E0 100%); color: white; padding: 18px 12px; text-align: left; font-weight: 600; text-transform: uppercase; font-size: 0.85rem; }
            td { padding: 16px 12px; border-bottom: 1px solid #ddd; font-size: 0.95rem; vertical-align: top; }
            tr:hover td { background: #f0f8ff; }
            .exercise-row { margin: 8px 0; padding: 10px; background: #f8f9fa; border-left: 4px solid #1B98E0; border-radius: 6px; }
            .ex-name { font-weight: 700; color: #006494; font-size: 1rem; margin-bottom: 6px; }
            .ex-detail { font-size: 0.85rem; color: #555; margin: 3px 0; }
            .ex-detail strong { color: #247BA0; }
            .volume { font-weight: 800; color: #006494; font-size: 1.1rem; white-space: nowrap; }
            .date { color: #555; font-size: 0.9rem; white-space: nowrap; }
            .badge { display: inline-block; padding: 4px 10px; border-radius: 20px; font-size: 0.75rem; font-weight: 700; text-transform: uppercase; }
            .badge-manual { background: #e3f2fd; color: #1565c0; }
            .badge-llm { background: #f3e5f5; color: #7b1fa2; }
            .badge-edited { background: #fff8e1; color: #f57f17; }
            .btn-pdf { display: inline-block; margin-top: 8px; padding: 6px 12px; background: #0288d1; color: white; border: none; border-radius: 6px; cursor: pointer; font-size: 0.8rem; font-weight: 600; text-decoration: none; transition: background 0.2s; }
            .btn-pdf:hover { background: #01579b; }
            .links { text-align: center; margin-top: 30px; }
            .links a { margin: 0 15px; color: #006494; text-decoration: none; font-weight: 600; }
            .links a:hover { text-decoration: underline; }
            th:nth-child(1), td:nth-child(1) { width: 10%; }
            th:nth-child(2), td:nth-child(2) { width: 15%; }
            th:nth-child(3), td:nth-child(3) { width: 63%; }
            th:nth-child(4), td:nth-child(4) { width: 12%; text-align: right; }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>🏋️ Histórico de Treinos</h1>
            <table>
                <thead><tr><th>Data</th><th>Origem & Ações</th><th>Exercícios (Ordem Exata: Bloco 1 → Principal → Bloco 3)</th><th>Volume Prescrito</th></tr></thead>
                <tbody>
    """
    for w in workouts:
        date_str = w.date.strftime("%d/%m/%Y<br><small style='color:#777'>%H:%M</small>")
        has_edited = any(getattr(ex, 'is_edited', False) for ex in w.exercises)
        edited_badge = ' <span class="badge badge-edited">Editado</span>' if has_edited else ''
        source_badge = f'<span class="badge badge-{w.source}">{w.source}</span>{edited_badge}'
        pdf_btn = f'<br><button class="btn-pdf" onclick="downloadWorkoutPDF({w.id})">📄 Baixar PDF</button>'
        ex_html = ""
        
        ordered_exercises = sorted(w.exercises, key=lambda x: x.id)
        
        for ex in ordered_exercises:
            exec_str = ""
            if ex.actual_weight_kg is not None:
                exec_str = f"<div class='ex-detail' style='color:#2e7d32;'><strong>Execução Real:</strong> {ex.actual_weight_kg}kg | {ex.actual_reps} reps | RPE {ex.actual_rpe}</div>"
                
            ex_html += f"""
                <div class="exercise-row">
                    <div class="ex-name">🏋️ {ex.name}</div>
                    {f"<div class='ex-detail'><strong>Cadência/Método:</strong> {ex.method}</div>" if ex.method else ""}
                    <div class="ex-detail"><strong>Prescrito:</strong> {ex.sets}x {ex.reps} reps @ {ex.weight_kg}kg</div>
                    {exec_str}
                </div>
            """
        total_vol = sum(ex.sets * ex.reps * (ex.weight_kg or 0) for ex in ordered_exercises)
        html += f"<tr><td class='date'>{date_str}</td><td>{source_badge}{pdf_btn}</td><td>{ex_html}</td><td class='volume'>{total_vol:,.0f} kg</td></tr>"
    
    html += """
                </tbody>
            </table>
            <div class="links">
                <a href="/">🏠 Dashboard</a>
                <a href="/docs">📚 API Docs</a>
                <a href="/analytics/volume">📊 Gráficos</a>
            </div>
        </div>

        <script>
            async function downloadWorkoutPDF(workoutId) {
                try {
                    const response = await fetch('/workouts/');
                    if (!response.ok) throw new Error('Erro ao buscar dados do treino.');
                    const workouts = await response.json();
                    const workout = workouts.find(w => w.id === workoutId);
                    if (!workout) { alert('Treino não encontrado.'); return; }

                    const dateStr = workout.date ? new Date(workout.date).toLocaleDateString('pt-BR') : new Date().toLocaleDateString('pt-BR');
                    
                    const block1 = []; const block2 = []; const block3 = [];
                    (workout.exercises || []).forEach(ex => {
                        const nameLower = (ex.name || '').toLowerCase();
                        if (nameLower.includes('bloco 1') || nameLower.includes('aquecimento') || nameLower.includes('mobilidade') || nameLower.includes('ativação') || nameLower.includes('warm-up')) {
                            block1.push(ex);
                        } else if (nameLower.includes('bloco 3') || nameLower.includes('volta à calma') || nameLower.includes('cool-down') || nameLower.includes('recovery') || nameLower.includes('respiração')) {
                            block3.push(ex);
                        } else {
                            block2.push(ex);
                        }
                    });

                    const tempContainer = document.createElement('div');
                    tempContainer.style.position = 'absolute';
                    tempContainer.style.left = '-9999px';
                    tempContainer.style.top = '-9999px';

                    const notesHtml = workout.notes ? `
                        <div style="background: #fff8e1; border: 2px solid #ffe0b2; border-left: 6px solid #f57f17; padding: 12px 16px; border-radius: 6px; margin-bottom: 20px;">
                            <strong style="color: #e65100; font-size: 0.95rem; display: block; margin-bottom: 4px;">⚠️ OBSERVAÇÕES & ALERTAS DE RISCO DO TREINADOR:</strong>
                            <span style="color: #424242; font-size: 0.9rem; font-weight: 500;">${workout.notes}</span>
                        </div>
                    ` : '';

                    const renderBlockTable = (title, exercises, headerBg, headerTextColor) => {
                        if (!exercises || exercises.length === 0) return '';
                        let rows = '';
                        exercises.forEach((ex, idx) => {
                            const name = ex.name || 'Exercício';
                            const equip = ex.equipment ? ` <small style="color: #666;">(${ex.equipment})</small>` : '';
                            const setsReps = `${ex.sets}x ${ex.reps}`;
                            const weight = ex.weight_kg ? `${ex.weight_kg} kg` : '0.0 kg';
                            const method = ex.method || 'Tradicional';
                            const execInfo = (ex.actual_weight_kg !== null && ex.actual_weight_kg !== undefined) 
                                ? `${ex.actual_weight_kg}kg | ${ex.actual_reps}r | RPE ${ex.actual_rpe}`
                                : '[ ___ kg | ___ reps | RPE ___ ]';

                            rows += `
                                <tr style="border-bottom: 1px solid #e0e0e0;">
                                    <td style="padding: 8px 10px; font-weight: 600; color: #222; font-size: 0.88rem;">${idx + 1}. ${name}${equip}</td>
                                    <td style="padding: 8px 10px; text-align: center; font-weight: 700; color: #006494; font-size: 0.88rem;">${setsReps}</td>
                                    <td style="padding: 8px 10px; text-align: center; font-weight: 700; color: #2e7d32; font-size: 0.88rem;">${weight}</td>
                                    <td style="padding: 8px 10px; font-size: 0.82rem; color: #555;">${method}</td>
                                    <td style="padding: 8px 10px; text-align: center; font-size: 0.82rem; font-family: monospace; color: #444; background: #fafafa; border-left: 1px dashed #ccc;">${execInfo}</td>
                                </tr>
                            `;
                        });
                        return `
                            <div style="margin-bottom: 20px; page-break-inside: avoid;">
                                <div style="background: ${headerBg}; color: ${headerTextColor}; padding: 8px 12px; font-weight: 700; font-size: 0.9rem; border-radius: 4px 4px 0 0; border: 1px solid #ddd; border-bottom: none;">
                                    ${title}
                                </div>
                                <table style="width: 100%; border-collapse: collapse; background: #fff; border: 1px solid #ddd; font-size: 0.85rem;">
                                    <thead>
                                        <tr style="background: #f5f5f5; border-bottom: 2px solid #ddd; color: #333; font-size: 0.8rem; text-transform: uppercase;">
                                            <th style="padding: 8px 10px; text-align: left;">Exercício</th>
                                            <th style="padding: 8px 10px; text-align: center; width: 14%;">Séries x Reps</th>
                                            <th style="padding: 8px 10px; text-align: center; width: 14%;">Carga Prescrita</th>
                                            <th style="padding: 8px 10px; text-align: left; width: 22%;">Método / Cadência</th>
                                            <th style="padding: 8px 10px; text-align: center; width: 24%;">Execução Real (Anotação)</th>
                                        </tr>
                                    </thead>
                                    <tbody>${rows}</tbody>
                                </table>
                            </div>
                        `;
                    };

                    tempContainer.innerHTML = `
                        <div id="pdf-content-${workoutId}" style="padding: 25px; font-family: 'Segoe UI', Arial, sans-serif; background: #ffffff; color: #111111; max-width: 800px; margin: 0 auto; line-height: 1.4;">
                            <div style="border-bottom: 3px solid #006494; padding-bottom: 12px; margin-bottom: 18px; display: flex; justify-content: space-between; align-items: flex-end;">
                                <div>
                                    <h1 style="color: #006494; font-size: 1.8rem; margin: 0; font-weight: 800;">🏋️ Gym Tracker AI</h1>
                                    <p style="color: #555555; font-size: 0.95rem; margin: 4px 0 0 0; font-weight: 600;">Ficha de Prescrição & Acompanhamento de Treino</p>
                                </div>
                                <div style="text-align: right; font-size: 0.85rem; color: #444444;">
                                    <div><strong>Treino ID:</strong> #${workout.id}</div>
                                    <div><strong>Data:</strong> ${dateStr}</div>
                                    <div><strong>Origem:</strong> ${(workout.source || 'MANUAL').toUpperCase()}</div>
                                </div>
                            </div>

                            ${notesHtml}
                            ${renderBlockTable("🔥 BLOCO 1: PREPARAÇÃO E ATIVAÇÃO (WARM-UP / MOBILIDADE)", block1, "#e3f2fd", "#0d47a1")}
                            ${renderBlockTable("💪 BLOCO 2: SESSÃO PRINCIPAL (MAIN SESSION)", block2, "#e8f5e9", "#1b5e20")}
                            ${renderBlockTable("🧘 BLOCO 3: RETORNO À HOMEOSTASE (COOL-DOWN / RECOVERY)", block3, "#f3e5f5", "#4a148c")}

                            <div style="margin-top: 25px; border-top: 1px dashed #ccc; padding-top: 10px; font-size: 0.75rem; color: #777; text-align: center;">
                                Gym Tracker AI • Ficha Oficial de Treino • Gerado em ${new Date().toLocaleDateString('pt-BR')} ${new Date().toLocaleTimeString('pt-BR', {hour:'2-digit', minute:'2-digit'})}
                            </div>
                        </div>
                    `;

                    document.body.appendChild(tempContainer);
                    const element = document.getElementById(`pdf-content-${workoutId}`);

                    if (window.html2pdf) {
                        const opt = {
                            margin: [10, 10, 10, 10],
                            filename: `Treino_${workout.id}_${dateStr.split('/').join('-')}.pdf`,
                            image: { type: 'jpeg', quality: 0.98 },
                            html2canvas: { scale: 2, useCORS: true },
                            jsPDF: { unit: 'mm', format: 'a4', orientation: 'portrait' }
                        };
                        await html2pdf().set(opt).from(element).save();
                    } else {
                        const printWin = window.open('', '_blank');
                        printWin.document.write(`<html><head><title>Treino ${workout.id}</title></head><body>${element.innerHTML}</body></html>`);
                        printWin.document.close();
                        printWin.focus();
                        printWin.print();
                        printWin.close();
                    }

                    document.body.removeChild(tempContainer);
                } catch (err) {
                    alert(`Erro ao gerar PDF: ${err.message}`);
                }
            }
        </script>
    </body>
    </html>
    """
    return HTMLResponse(content=html)