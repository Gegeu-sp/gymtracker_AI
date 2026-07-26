import os
from typing import List, Optional
from fastapi import APIRouter, UploadFile, File, Form, Depends, HTTPException
from sqlalchemy.orm import Session

from ..database import get_db
from ..schemas import WorkoutOut, OcrPreviewOut, WorkoutGenerationRequest
from ..services.ocr_service import extract_text_from_image
from ..services.llm_service import parse_reference_and_generate
from ..services.workout_service import save_generated_workouts

router = APIRouter(prefix="/extraction", tags=["extraction"])

@router.post("/ocr-preview", response_model=OcrPreviewOut)
async def preview_reference_ocr(file: UploadFile = File(...)):
    """
    Faz OCR da imagem de referência (ex: ficha de outro app/planilha de treino) e devolve
    o texto bruto para o usuário revisar/corrigir antes de gerar os treinos — EasyOCR pode
    errar em tabelas densas, então essa etapa evita propagar erros de leitura direto pro LLM.
    """
    os.makedirs("uploads", exist_ok=True)
    file_path = f"uploads/{file.filename}"
    with open(file_path, "wb") as f:
        content = await file.read()
        f.write(content)

    raw_text = extract_text_from_image(file_path)
    if not raw_text or len(raw_text.strip()) < 10:
        raise HTTPException(status_code=400, detail="Imagem sem texto legível")

    return {"raw_text": raw_text, "filename": file.filename}

@router.post("/generate", response_model=List[WorkoutOut])
def generate_from_reference(
    raw_text: str = Form(...),
    filename: Optional[str] = Form(None),
    professor_name: Optional[str] = Form(None),
    goal: str = Form("hipertrofia"),
    level: str = Form("intermediario"),
    days_per_week: int = Form(1, ge=1, le=6),
    specialization: Optional[str] = Form(None),
    training_philosophy: Optional[str] = Form(None),
    preferred_methods: Optional[str] = Form(None),
    rest_time: Optional[str] = Form(None),
    custom_instructions: Optional[str] = Form(None),
    db: Session = Depends(get_db),
):
    """
    Gera de 1 a `days_per_week` treinos usando a tabela de referência (texto de OCR já
    revisado pelo usuário) como base/estilo, combinada com o perfil do professor/objetivo,
    seguindo a metodologia de 3 blocos. Retorna List[WorkoutOut] — mesmo schema de
    /workouts/generate, 100% compatível com edição/execução/PDF/live-session já existentes.
    """
    if not raw_text or len(raw_text.strip()) < 10:
        raise HTTPException(status_code=400, detail="Texto de referência vazio ou inválido.")

    req = WorkoutGenerationRequest(
        professor_name=professor_name, goal=goal, level=level,
        days_per_week=days_per_week, specialization=specialization,
        training_philosophy=training_philosophy, preferred_methods=preferred_methods,
        rest_time=rest_time, custom_instructions=custom_instructions,
    )

    parsed = parse_reference_and_generate(raw_text, req.model_dump())

    prof_name = req.professor_name or "N/A"
    source_suffix = f" | Fonte: {filename}" if filename else ""

    def build_notes(day_data: dict) -> str:
        base = (f"🖼️ Extração de Referência | Prof. {prof_name} | "
                f"Objetivo: {req.goal.capitalize()} | Nível: {req.level.capitalize()}{source_suffix}")
        day_notes = day_data.get("notes")
        return f"{base}\n{day_notes}" if day_notes else base

    try:
        return save_generated_workouts(db, parsed, build_notes, source="image_reference")
    except ValueError:
        raise HTTPException(status_code=500, detail="Falha ao gerar treinos a partir da referência.")
