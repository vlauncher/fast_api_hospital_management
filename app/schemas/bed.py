from typing import Optional
from pydantic import BaseModel
from datetime import datetime
from uuid import UUID
from app.models.bed import BedType, BedStatus

class BedBase(BaseModel):
    bed_number: str
    department_id: UUID
    bed_type: Optional[BedType] = BedType.GENERAL
    status: Optional[BedStatus] = BedStatus.AVAILABLE

class BedCreate(BedBase):
    pass

class BedUpdate(BaseModel):
    status: Optional[BedStatus] = None
    patient_id: Optional[UUID] = None
    assigned_date: Optional[datetime] = None

class Bed(BedBase):
    id: UUID
    patient_id: Optional[UUID] = None
    assigned_date: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
