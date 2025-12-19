from typing import Any, List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.api import deps
from app.db.session import get_db
from app.models.insurance import InsuranceProvider, PatientInsurance, InsuranceClaim, ClaimStatus
from app.models.user import User, UserRole
from app.schemas import insurance as insurance_schema

router = APIRouter()

@router.post("/providers", response_model=insurance_schema.InsuranceProvider)
async def create_provider(
    *,
    db: AsyncSession = Depends(get_db),
    provider_in: insurance_schema.InsuranceProviderCreate,
    current_user: User = Depends(deps.get_current_active_user),
) -> Any:
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Not enough permissions")
    provider = InsuranceProvider(**provider_in.model_dump())
    db.add(provider)
    await db.commit()
    await db.refresh(provider)
    return provider

@router.post("/policies", response_model=insurance_schema.PatientInsurance)
async def create_policy(
    *,
    db: AsyncSession = Depends(get_db),
    policy_in: insurance_schema.PatientInsuranceCreate,
    current_user: User = Depends(deps.get_current_active_user),
) -> Any:
    # Logic to ensure only patient or admin can add policy
    policy = PatientInsurance(**policy_in.model_dump())
    db.add(policy)
    await db.commit()
    await db.refresh(policy)
    return policy

@router.post("/claims", response_model=insurance_schema.InsuranceClaim)
async def create_claim(
    *,
    db: AsyncSession = Depends(get_db),
    claim_in: insurance_schema.InsuranceClaimCreate,
    current_user: User = Depends(deps.get_current_active_user),
) -> Any:
    claim = InsuranceClaim(
        **claim_in.model_dump(),
        status=ClaimStatus.PENDING
    )
    db.add(claim)
    await db.commit()
    await db.refresh(claim)
    return claim

@router.get("/claims", response_model=List[insurance_schema.InsuranceClaim])
async def read_claims(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(deps.get_current_active_user),
) -> Any:
    if current_user.role == UserRole.ADMIN:
        result = await db.execute(select(InsuranceClaim))
    else:
        # Filter by patient if current user is patient
        from app.models.patient import Patient
        res = await db.execute(select(Patient).where(Patient.user_id == current_user.id))
        patient = res.scalars().first()
        if not patient:
            return []
        result = await db.execute(select(InsuranceClaim).where(InsuranceClaim.patient_id == patient.id))
    
    claims = result.scalars().all()
    return claims
