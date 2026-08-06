from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import AdolescentAssessment
from ..schemas import AdolescentAssessmentCreate
from ..services.assessment_service import build_classification_report, save_assessment

router = APIRouter(prefix="/assessment", tags=["assessment"])


@router.post("/create")
def create_assessment(data: AdolescentAssessmentCreate, db: Session = Depends(get_db)):
    assessment = save_assessment(db, data)
    report = build_classification_report(db, data.student_name, assessment)
    return {"success": True, "report": report}


@router.get("/list")
def list_assessments(db: Session = Depends(get_db)):
    assessments = db.query(AdolescentAssessment).order_by(AdolescentAssessment.assessment_date.desc()).all()
    return [
        {
            "id": a.id,
            "student_name": a.student_name,
            "sex": a.sex,
            "age": a.age,
            "date": a.assessment_date,
            "pacer_laps": a.pacer_laps,
        }
        for a in assessments
    ]


@router.get("/{assessment_id}")
def get_assessment(assessment_id: int, db: Session = Depends(get_db)):
    assessment = db.query(AdolescentAssessment).filter(AdolescentAssessment.id == assessment_id).first()
    if not assessment:
        raise HTTPException(status_code=404, detail="Avaliação não encontrada.")
    return {
        "id": assessment.id,
        "student_name": assessment.student_name,
        "sex": assessment.sex,
        "age": assessment.age,
        "weight_kg": assessment.weight_kg,
        "height_m": assessment.height_m,
        "waist_circumference_cm": assessment.waist_circumference_cm,
        "pacer_laps": assessment.pacer_laps,
        "push_ups": assessment.push_ups,
        "curl_ups": assessment.curl_ups,
        "standing_long_jump_cm": assessment.standing_long_jump_cm,
        "flexibility_right_cm": assessment.flexibility_right_cm,
        "flexibility_left_cm": assessment.flexibility_left_cm,
        "sprint_30m_seconds": assessment.sprint_30m_seconds,
        "illinois_agility_seconds": assessment.illinois_agility_seconds,
        "notes": assessment.notes,
        "aerobic_classification": assessment.aerobic_classification,
        "strength_classification": assessment.strength_classification,
        "flexibility_classification": assessment.flexibility_classification,
        "speed_classification": assessment.speed_classification,
        "agility_classification": assessment.agility_classification,
    }
