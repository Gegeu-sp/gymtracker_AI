from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session
from ..database import get_db
from ..models import Workout, Exercise
from ..schemas import WorkoutCreate, WorkoutOut, WorkoutGenerationRequest
from ..services.llm_service import generate_workout

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
        # CORREÇÃO 1: Notas limpas e objetivas (sem a filosofia gigante)
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
                weight_kg=float(ex_data.get("weight_kg", 0) or 0)
            ))
        db.commit()
        
        # CORREÇÃO 2: Buscar o treino garantindo a ordem de inserção (order_by(Exercise.id))
        saved_workout = db.query(Workout).filter(Workout.id == workout.id).first()
        saved_workouts.append(saved_workout)
        
    return saved_workouts

@router.get("/", response_model=list[WorkoutOut])
def list_workouts(db: Session = Depends(get_db)):
    return db.query(Workout).order_by(Workout.date.desc()).all()

@router.get("/view", response_class=HTMLResponse)
def view_workouts_table(db: Session = Depends(get_db)):
    # CORREÇÃO 3: Order_by(Workout.date.desc()) para os treinos mais recentes aparecerem primeiro
    workouts = db.query(Workout).order_by(Workout.date.desc()).all()
    
    html = """
    <!DOCTYPE html>
    <html lang="pt-BR">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Histórico de Treinos</title>
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
            .badge-image { background: #fff3e0; color: #e65100; }
            .links { text-align: center; margin-top: 30px; }
            .links a { margin: 0 15px; color: #006494; text-decoration: none; font-weight: 600; }
            .links a:hover { text-decoration: underline; }
            th:nth-child(1), td:nth-child(1) { width: 10%; }
            th:nth-child(2), td:nth-child(2) { width: 8%; }
            th:nth-child(3), td:nth-child(3) { width: 45%; }
            th:nth-child(4), td:nth-child(4) { width: 12%; text-align: right; }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>🏋️ Histórico de Treinos</h1>
            <table>
                <thead><tr><th>Data</th><th>Origem</th><th>Exercícios (Ordem Exata: Bloco 1 → Principal → Bloco 3)</th><th>Volume</th></tr></thead>
                <tbody>
    """
    for w in workouts:
        date_str = w.date.strftime("%d/%m/%Y<br><small style='color:#777'>%H:%M</small>")
        source_badge = f'<span class="badge badge-{w.source}">{w.source}</span>'
        ex_html = ""
        
        # CORREÇÃO 4: Ordenar exercícios pelo ID para manter a ordem exata de inserção (Bloco 1, 2, 3)
        ordered_exercises = sorted(w.exercises, key=lambda x: x.id)
        
        for ex in ordered_exercises:
            ex_html += f"""
                <div class="exercise-row">
                    <div class="ex-name">🏋️ {ex.name}</div>
                    {f"<div class='ex-detail'><strong>Intensidade:</strong> {ex.nickname}</div>" if ex.nickname else ""}
                    {f"<div class='ex-detail'><strong>Equipamentos:</strong> {ex.equipment}</div>" if ex.equipment else ""}
                    {f"<div class='ex-detail'><strong>Descanso:</strong> {ex.accessory}</div>" if ex.accessory else ""}
                    {f"<div class='ex-detail'><strong>Cadência/Método:</strong> {ex.method}</div>" if ex.method else ""}
                    <div class="ex-detail"><strong>Séries:</strong> {ex.sets}x | <strong>Reps:</strong> {ex.reps} | <strong>Peso:</strong> {ex.weight_kg}kg</div>
                </div>
            """
        total_vol = sum(ex.sets * ex.reps * (ex.weight_kg or 0) for ex in ordered_exercises)
        html += f"<tr><td class='date'>{date_str}</td><td>{source_badge}</td><td>{ex_html}</td><td class='volume'>{total_vol:,.0f} kg</td></tr>"
    
    html += """
                </tbody>
            </table>
            <div class="links">
                <a href="/">🏠 Dashboard</a>
                <a href="/docs">📚 API Docs</a>
                <a href="/analytics/volume">📊 Gráficos</a>
            </div>
        </div>
    </body>
    </html>
    """
    return HTMLResponse(content=html)