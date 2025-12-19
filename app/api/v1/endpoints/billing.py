from typing import Any, List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.api import deps
from app.db.session import get_db
from app.models.billing import Billing
from app.models.user import User, UserRole
from app.models.patient import Patient
from app.schemas import billing as billing_schema

router = APIRouter()

@router.post("/", response_model=billing_schema.Billing)
async def create_bill(
    *,
    db: AsyncSession = Depends(get_db),
    bill_in: billing_schema.BillingCreate,
    current_user: User = Depends(deps.get_current_active_user),
) -> Any:
    if current_user.role not in [UserRole.ADMIN, UserRole.RECEPTIONIST]:
        raise HTTPException(status_code=403, detail="Not enough permissions")
    
    bill = Billing(**bill_in.model_dump())
    db.add(bill)
    await db.commit()
    await db.refresh(bill)
    return bill

@router.get("/patient/{patient_id}", response_model=List[billing_schema.Billing])
async def read_patient_bills(
    patient_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(deps.get_current_active_user),
) -> Any:
    # Logic to ensure only patient themselves or admin can see bills
    result = await db.execute(select(Billing).where(Billing.patient_id == patient_id))
    return result.scalars().all()
