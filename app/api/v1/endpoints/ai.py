from typing import Any
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from app.services import ai_service
from app.api import deps
from app.models.user import User

router = APIRouter()

class SymptomAnalysisRequest(BaseModel):
    symptoms: list[str]
    duration_days: int
    severity: str
    patient_history: dict

class DrugInteractionRequest(BaseModel):
    medications: list[dict]
    patient_conditions: list[str]

@router.post("/symptom-analysis")
async def symptom_analysis(
    request: SymptomAnalysisRequest,
    current_user: User = Depends(deps.get_current_active_user),
) -> Any:
    """
    Standalone AI symptom analysis.
    """
    symptoms_str = ", ".join(request.symptoms)
    analysis = await ai_service.analyze_symptoms(symptoms_str)
    return {"analysis": analysis}

@router.post("/drug-interaction-check")
async def drug_interaction_check(
    request: DrugInteractionRequest,
    current_user: User = Depends(deps.get_current_active_user),
) -> Any:
    """
    Standalone AI drug interaction check.
    """
    med_names = [m.get("name") for m in request.medications]
    result = await ai_service.check_drug_interactions(med_names)
    return result
