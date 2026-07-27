import os
from fastapi import APIRouter, UploadFile, File, Depends, HTTPException
from sqlalchemy.orm import Session
from ..database import get_db
from ..models import Workout, Exercise
from ..schemas import WorkoutOut
from ..services.ocr_service import extract_text_from_image
from ..services.llm_service import parse_workout_from_text, LLMRateLimitError
from ..services.workout_service import safe_int, safe_float
from ..services.exercise_catalog import get_muscle_group
from datetime import datetime

router = APIRouter(prefix="/image", tags=["image"])

@router.post("/upload", response_model=WorkoutOut)
async def upload_workout_image(file: UploadFile = File(...), db: Session = Depends(get_db)):
    """Upload de imagem -> OCR -> LLM -> Banco."""
    try:
        # 1. Salvar imagem
        os.makedirs("uploads", exist_ok=True)
        file_path = f"uploads/{file.filename}"
        
        with open(file_path, "wb") as f:
            content = await file.read()
            f.write(content)
        
        # 2. Extrair texto com OCR
        raw_text = extract_text_from_image(file_path)
        
        if not raw_text or len(raw_text.strip()) < 10:
            raise HTTPException(status_code=400, detail="Imagem sem texto legível")
        
        # 3. Interpretar com LLM
        parsed = parse_workout_from_text(raw_text)

        # O LLM sempre responde no formato {"workouts": [{"exercises": [...]}]},
        # mesmo em parse_workout_from_text (mesmo SYSTEM_PROMPT usado por generate_workout).
        day_data = (parsed.get("workouts") or [{}])[0]
        exercises = day_data.get("exercises") or []

        if not exercises:
            raise HTTPException(status_code=400, detail="Nenhum exercício encontrado na imagem")

        # 4. Criar registro do treino
        day_notes = day_data.get("notes")
        notes = f"Extraído de: {file.filename}"
        if day_notes:
            notes += f"\n{day_notes}"

        workout = Workout(
            date=datetime.utcnow(),
            source="image",
            image_path=file_path,
            notes=notes,
            professor_profile=None
        )
        db.add(workout)
        db.commit()
        db.refresh(workout)

        # 5. Criar os exercícios vinculados (com conversão segura)
        for ex in exercises:
            ex_name = ex.get("name", "Exercício")
            exercise = Exercise(
                workout_id=workout.id,
                name=ex_name,
                nickname=ex.get("nickname"),
                equipment=ex.get("equipment"),
                accessory=ex.get("accessory"),
                method=ex.get("method"),
                sets=safe_int(ex.get("sets"), 3),
                reps=safe_int(ex.get("reps"), 10),
                weight_kg=safe_float(ex.get("weight_kg"), 0.0),
                muscle_group=get_muscle_group(ex_name)
            )
            db.add(exercise)
        
        db.commit()
        
        # 6. Calcular totais para a resposta
        exercises_list = db.query(Exercise).filter(Exercise.workout_id == workout.id).all()
        total_volume = sum(e.sets * e.reps * (e.weight_kg or 0) for e in exercises_list)
        
        return {
            "id": workout.id,
            "date": workout.date,
            "source": workout.source,
            "notes": workout.notes,
            "professor_profile": None,
            "exercises": exercises_list,
            "total_volume": total_volume,
            "total_exercises": len(exercises_list),
            "total_sets": sum(e.sets for e in exercises_list),
            "total_reps": sum(e.sets * e.reps for e in exercises_list)
        }
        
    except HTTPException:
        raise
    except LLMRateLimitError as e:
        raise HTTPException(status_code=429, detail=str(e))
    except Exception as e:
        print(f"❌ ERRO NO UPLOAD: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Erro interno: {str(e)}")