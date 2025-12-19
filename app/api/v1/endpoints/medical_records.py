from typing import Any, List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.api import deps
from app.db.session import get_db
from app.models.medical_record import MedicalRecord
from app.models.user import User, UserRole
from app.models.patient import Patient
from app.schemas import medical_record as medical_record_schema
from app.services import ai_service

router = APIRouter()

@router.get("/", response_model=List[medical_record_schema.MedicalRecord])
async def read_medical_records(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(deps.get_current_active_user),
) -> Any:
    if current_user.role == UserRole.PATIENT:
        res = await db.execute(select(Patient).where(Patient.user_id == current_user.id))
        patient = res.scalars().first()
        if not patient:
            return []
        result = await db.execute(select(MedicalRecord).where(MedicalRecord.patient_id == patient.id))
    else:
        result = await db.execute(select(MedicalRecord))
    
    records = result.scalars().all()
    return records

@router.post("/", response_model=medical_record_schema.MedicalRecord)
async def create_medical_record(
    *,
    db: AsyncSession = Depends(get_db),
    record_in: medical_record_schema.MedicalRecordCreate,
    current_user: User = Depends(deps.get_current_active_user),
) -> Any:
    if current_user.role not in [UserRole.DOCTOR, UserRole.ADMIN]:
        raise HTTPException(status_code=403, detail="Not enough permissions")
    
    # AI Insights
    ai_insights = {}
    if record_in.diagnosis or record_in.lab_results:
        data_for_ai = {
            "diagnosis": record_in.diagnosis,
            "vitals": record_in.vitals,
            "lab_results": record_in.lab_results
        }
        ai_insights = await ai_service.generate_insights(data_for_ai)

    record = MedicalRecord(
        **record_in.model_dump(),
        ai_insights=ai_insights
    )
    db.add(record)
    await db.commit()
    await db.refresh(record)
    return record
