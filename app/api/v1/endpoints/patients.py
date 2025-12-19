from typing import Any, List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.api import deps
from app.db.session import get_db
from app.models.patient import Patient
from app.models.user import User
from app.schemas import patient as patient_schema

router = APIRouter()

@router.post("/", response_model=patient_schema.Patient)
async def create_patient(
    *,
    db: AsyncSession = Depends(get_db),
    patient_in: patient_schema.PatientCreate,
    current_user: User = Depends(deps.get_current_active_user),
) -> Any:
    """
    Create new patient profile for current user.
    """
    result = await db.execute(select(Patient).where(Patient.user_id == current_user.id))
    if result.scalars().first():
        raise HTTPException(
            status_code=400,
            detail="Patient profile already exists for this user.",
        )
    
    patient = Patient(
        **patient_in.model_dump(),
        user_id=current_user.id
    )
    db.add(patient)
    await db.commit()
    await db.refresh(patient)
    return patient

@router.get("/me", response_model=patient_schema.Patient)
async def read_patient_me(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(deps.get_current_active_user),
) -> Any:
    """
    Get current user's patient profile.
    """
    result = await db.execute(select(Patient).where(Patient.user_id == current_user.id))
    patient = result.scalars().first()
    if not patient:
        raise HTTPException(status_code=404, detail="Patient profile not found")
    return patient

@router.put("/me", response_model=patient_schema.Patient)
async def update_patient_me(
    *,
    db: AsyncSession = Depends(get_db),
    patient_in: patient_schema.PatientUpdate,
    current_user: User = Depends(deps.get_current_active_user),
) -> Any:
    """
    Update current user's patient profile.
    """
    result = await db.execute(select(Patient).where(Patient.user_id == current_user.id))
    patient = result.scalars().first()
    if not patient:
        raise HTTPException(status_code=404, detail="Patient profile not found")
    
    update_data = patient_in.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(patient, field, value)
    
    db.add(patient)
    await db.commit()
    await db.refresh(patient)
    return patient
