from typing import Any, List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.api import deps
from app.db.session import get_db
from app.models.lab_test import LabTest, LabTestStatus
from app.models.user import User, UserRole
from app.models.patient import Patient
from app.schemas import lab_test as lab_test_schema

router = APIRouter()

@router.get("/", response_model=List[lab_test_schema.LabTest])
async def read_lab_tests(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(deps.get_current_active_user),
) -> Any:
    if current_user.role == UserRole.PATIENT:
        res = await db.execute(select(Patient).where(Patient.user_id == current_user.id))
        patient = res.scalars().first()
        if not patient:
            return []
        result = await db.execute(select(LabTest).where(LabTest.patient_id == patient.id))
    else:
        result = await db.execute(select(LabTest))
    
    tests = result.scalars().all()
    return tests

@router.post("/", response_model=lab_test_schema.LabTest)
async def create_lab_test(
    *,
    db: AsyncSession = Depends(get_db),
    test_in: lab_test_schema.LabTestCreate,
    current_user: User = Depends(deps.get_current_active_user),
) -> Any:
    if current_user.role not in [UserRole.DOCTOR, UserRole.ADMIN]:
        raise HTTPException(status_code=403, detail="Not enough permissions")
    
    test = LabTest(**test_in.model_dump(), status=LabTestStatus.PENDING)
    db.add(test)
    await db.commit()
    await db.refresh(test)
    return test

@router.put("/{test_id}", response_model=lab_test_schema.LabTest)
async def update_lab_test(
    test_id: str,
    *,
    db: AsyncSession = Depends(get_db),
    test_in: lab_test_schema.LabTestUpdate,
    current_user: User = Depends(deps.get_current_active_user),
) -> Any:
    # Logic for doctor or lab technician (if added)
    result = await db.execute(select(LabTest).where(LabTest.id == test_id))
    test = result.scalars().first()
    if not test:
        raise HTTPException(status_code=404, detail="Lab test not found")
    
    update_data = test_in.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(test, field, value)
    
    db.add(test)
    await db.commit()
    await db.refresh(test)
    return test
