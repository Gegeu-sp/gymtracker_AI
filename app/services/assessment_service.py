from typing import Any, Callable, Dict, Optional, Tuple

from sqlalchemy.orm import Session

from ..models import AdolescentAssessment
from ..schemas import AdolescentAssessmentCreate


def save_assessment(db: Session, data: AdolescentAssessmentCreate) -> AdolescentAssessment:
    payload = data.model_dump()
    weight_kg = payload.get("weight_kg")
    height_m = payload.get("height_m")
    bmi = round(weight_kg / (height_m ** 2), 1) if weight_kg and height_m and height_m > 0 else None

    assessment = AdolescentAssessment(**payload, bmi=bmi)
    db.add(assessment)
    db.commit()
    db.refresh(assessment)
    return assessment


def _avg_flexibility(a: AdolescentAssessment) -> Optional[float]:
    values = [v for v in (a.flexibility_right_cm, a.flexibility_left_cm) if v is not None]
    return sum(values) / len(values) if values else None


def _combined_strength(a: AdolescentAssessment) -> Optional[float]:
    if a.push_ups is None and a.curl_ups is None:
        return None
    return (a.push_ups or 0) + (a.curl_ups or 0)


# (chave, coluna de classificação no model, extrator do valor bruto, higher_is_better)
_CATEGORY_DEFINITIONS: list[Tuple[str, str, Callable[[AdolescentAssessment], Optional[float]], bool]] = [
    ("aerobic", "aerobic_classification", lambda a: a.pacer_laps, True),
    ("strength", "strength_classification", _combined_strength, True),
    ("flexibility", "flexibility_classification", _avg_flexibility, True),
    ("speed", "speed_classification", lambda a: a.sprint_30m_seconds, False),
    ("agility", "agility_classification", lambda a: a.illinois_agility_seconds, False),
]

_RECOMMENDATIONS = {
    "aerobic": "Considere aumentar o volume de trabalho aeróbico (ex: corrida contínua ou intervalado).",
    "strength": "Inclua mais exercícios de força/resistência muscular (flexões, abdominais) no treino.",
    "flexibility": "Adicione alongamentos e trabalho de mobilidade ao final dos treinos.",
    "speed": "Trabalhe sprints curtos e exercícios de potência para melhorar a velocidade.",
    "agility": "Inclua exercícios de mudança de direção e coordenação (escada de agilidade, cones).",
}


def _classify(current_value: Optional[float], previous_value: Optional[float], higher_is_better: bool) -> Tuple[str, str]:
    """
    Classificação por EVOLUÇÃO PRÓPRIA do aluno (mais recente vs. anterior) — não por norma
    populacional fixa (percentil por idade/sexo), pra não embutir uma tabela de referência que
    não temos 100% de certeza que está correta.
    """
    if current_value is None:
        return "— Sem dados", "sem_dados"
    if previous_value is None:
        return "🆕 Primeira Avaliação", "primeira_avaliacao"
    delta = current_value - previous_value
    if delta == 0:
        return "➡️ Manteve", "manteve"
    improved = (delta > 0) == higher_is_better
    return ("✅ Melhorou", "melhorou") if improved else ("⚠️ Piorou", "piorou")


def build_classification_report(db: Session, student_name: str, assessment: AdolescentAssessment) -> Dict[str, Any]:
    previous = (
        db.query(AdolescentAssessment)
        .filter(AdolescentAssessment.student_name.ilike(student_name))
        .filter(AdolescentAssessment.id != assessment.id)
        .filter(AdolescentAssessment.assessment_date <= assessment.assessment_date)
        .order_by(AdolescentAssessment.assessment_date.desc())
        .first()
    )

    classifications = {}
    recommendations = []
    for key, column_name, extractor, higher_is_better in _CATEGORY_DEFINITIONS:
        current_value = extractor(assessment)
        previous_value = extractor(previous) if previous else None
        label, direction = _classify(current_value, previous_value, higher_is_better)
        classifications[key] = label
        setattr(assessment, column_name, label)
        if direction == "piorou":
            recommendations.append(_RECOMMENDATIONS[key])

    db.commit()
    return {"classifications": classifications, "recommendations": recommendations}
