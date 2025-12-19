from typing import Optional, List, Dict
from pydantic import BaseModel
from datetime import date
from uuid import UUID

class DoctorBase(BaseModel):
    specialization: str
    license_number: str
    qualification: Optional[str] = None
    experience_years: Optional[int] = None
    consultation_fee: Optional[float] = None
    available_days: Optional[List[str]] = []
    available_time_slots: Optional[Dict[str, List[str]]] = {}

class DoctorCreate(DoctorBase):
    user_id: UUID

class DoctorUpdate(DoctorBase):
    specialization: Optional[str] = None
    license_number: Optional[str] = None

class DoctorInDBBase(DoctorBase):
    id: UUID
    user_id: UUID
    created_at: date
    updated_at: date

    class Config:
        from_attributes = True

class Doctor(DoctorInDBBase):
    pass
