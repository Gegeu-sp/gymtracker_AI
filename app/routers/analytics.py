from typing import Optional
from fastapi import APIRouter, Depends
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session
from ..database import get_db
from ..services.analytics import (
    get_performance_dashboard,
    get_volume_chart,
    get_exercise_distribution,
    get_muscle_group_chart,
)

router = APIRouter(prefix="/analytics", tags=["analytics"])


@router.get("/performance", response_class=HTMLResponse)
def performance_dashboard(student_name: Optional[str] = None, db: Session = Depends(get_db)):
    return get_performance_dashboard(db, student_name=student_name)


@router.get("/volume", response_class=HTMLResponse)
def volume_chart(db: Session = Depends(get_db)):
    return get_volume_chart(db)


@router.get("/exercises", response_class=HTMLResponse)
def exercise_chart(db: Session = Depends(get_db)):
    return get_exercise_distribution(db)


@router.get("/muscles", response_class=HTMLResponse)
def muscles_chart(db: Session = Depends(get_db)):
    return get_muscle_group_chart(db)