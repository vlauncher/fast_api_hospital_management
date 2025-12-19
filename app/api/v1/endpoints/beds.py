from typing import Any, List, Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.api import deps
from app.db.session import get_db
from app.models.bed import Bed, BedStatus
from app.models.user import User, UserRole
from app.schemas import bed as bed_schema

router = APIRouter()

@router.get("/", response_model=List[bed_schema.Bed])
async def read_beds(
    db: AsyncSession = Depends(get_db),
    status: Optional[BedStatus] = None,
    department_id: Optional[str] = None,
) -> Any:
    query = select(Bed)
    if status:
        query = query.where(Bed.status == status)
    if department_id:
        query = query.where(Bed.department_id == department_id)
    
    result = await db.execute(query)
    return result.scalars().all()

@router.post("/", response_model=bed_schema.Bed)
async def create_bed(
    *,
    db: AsyncSession = Depends(get_db),
    bed_in: bed_schema.BedCreate,
    current_user: User = Depends(deps.get_current_active_user),
) -> Any:
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Not enough permissions")
    
    bed = Bed(**bed_in.model_dump())
    db.add(bed)
    await db.commit()
    await db.refresh(bed)
    return bed

@router.put("/{bed_id}/assign", response_model=bed_schema.Bed)
async def assign_bed(
    bed_id: str,
    *,
    db: AsyncSession = Depends(get_db),
    bed_in: bed_schema.BedUpdate,
    current_user: User = Depends(deps.get_current_active_user),
) -> Any:
    if current_user.role not in [UserRole.ADMIN, UserRole.RECEPTIONIST]:
        raise HTTPException(status_code=403, detail="Not enough permissions")
    
    result = await db.execute(select(Bed).where(Bed.id == bed_id))
    bed = result.scalars().first()
    if not bed:
        raise HTTPException(status_code=404, detail="Bed not found")
    
    bed.patient_id = bed_in.patient_id
    bed.status = BedStatus.OCCUPIED
    bed.assigned_date = bed_in.assigned_date or datetime.utcnow()
    
    db.add(bed)
    await db.commit()
    await db.refresh(bed)
    return bed

from typing import Optional
from datetime import datetime
