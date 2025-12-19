from typing import Any, List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.api import deps
from app.db.session import get_db
from app.models.medical_record import Prescription
from app.models.user import User, UserRole
from app.schemas import prescription as prescription_schema
from app.services import ai_service

router = APIRouter()

@router.post("/", response_model=prescription_schema.Prescription)
async def create_prescription(
    *,
    db: AsyncSession = Depends(get_db),
    prescription_in: prescription_schema.PrescriptionCreate,
    current_user: User = Depends(deps.get_current_active_user),
) -> Any:
    if current_user.role not in [UserRole.DOCTOR, UserRole.ADMIN]:
        raise HTTPException(status_code=403, detail="Not enough permissions")
    
    # AI Interaction Check
    ai_check = {}
    if prescription_in.medications:
        med_names = [m.get("name") for m in prescription_in.medications]
        ai_check = await ai_service.check_drug_interactions(med_names)

    prescription = Prescription(
        **prescription_in.model_dump(),
        ai_drug_interaction_check=ai_check
    )
    db.add(prescription)
    await db.commit()
    await db.refresh(prescription)
    return prescription

@router.get("/{prescription_id}", response_model=prescription_schema.Prescription)
async def read_prescription(
    prescription_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(deps.get_current_active_user),
) -> Any:
    result = await db.execute(select(Prescription).where(Prescription.id == prescription_id))
    prescription = result.scalars().first()
    if not prescription:
        raise HTTPException(status_code=404, detail="Prescription not found")
    return prescription
