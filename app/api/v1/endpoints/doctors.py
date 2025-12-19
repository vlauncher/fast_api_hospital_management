from typing import Any, List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.api import deps
from app.db.session import get_db
from app.models.doctor import Doctor
from app.models.user import User, UserRole
from app.schemas import doctor as doctor_schema

router = APIRouter()

@router.get("/", response_model=List[doctor_schema.Doctor])
async def read_doctors(
    db: AsyncSession = Depends(get_db),
    skip: int = 0,
    limit: int = 100,
) -> Any:
    """
    Retrieve doctors.
    """
    result = await db.execute(select(Doctor).offset(skip).limit(limit))
    doctors = result.scalars().all()
    return doctors

@router.get("/{doctor_id}", response_model=doctor_schema.Doctor)
async def read_doctor(
    doctor_id: str,
    db: AsyncSession = Depends(get_db),
) -> Any:
    """
    Get doctor by ID.
    """
    result = await db.execute(select(Doctor).where(Doctor.id == doctor_id))
    doctor = result.scalars().first()
    if not doctor:
        raise HTTPException(status_code=404, detail="Doctor not found")
    return doctor

@router.post("/", response_model=doctor_schema.Doctor)
async def create_doctor(
    *,
    db: AsyncSession = Depends(get_db),
    doctor_in: doctor_schema.DoctorCreate,
    current_user: User = Depends(deps.get_current_active_user),
) -> Any:
    """
    Create new doctor profile. (Admin only or based on role)
    """
    if current_user.role != UserRole.ADMIN:
         raise HTTPException(status_code=403, detail="Not enough permissions")
    
    # Check if user exists and is doctor
    result = await db.execute(select(User).where(User.id == doctor_in.user_id))
    user = result.scalars().first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    if user.role != UserRole.DOCTOR:
        raise HTTPException(status_code=400, detail="User is not a doctor")

    # Check if doctor profile already exists
    result = await db.execute(select(Doctor).where(Doctor.user_id == doctor_in.user_id))
    if result.scalars().first():
        raise HTTPException(status_code=400, detail="Doctor profile already exists")

    doctor = Doctor(**doctor_in.model_dump())
    db.add(doctor)
    await db.commit()
    await db.refresh(doctor)
    return doctor
