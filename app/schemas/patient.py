from typing import Optional, List
from pydantic import BaseModel
from datetime import date, datetime
from uuid import UUID
from app.models.patient import Gender

class PatientBase(BaseModel):
    date_of_birth: date
    gender: Gender
    blood_group: Optional[str] = None
    address: Optional[str] = None
    emergency_contact_name: Optional[str] = None
    emergency_contact_phone: Optional[str] = None
    medical_history: Optional[dict] = {}
    allergies: Optional[List[str]] = []

class PatientCreate(PatientBase):
    pass

class PatientUpdate(PatientBase):
    date_of_birth: Optional[date] = None
    gender: Optional[Gender] = None

class PatientInDBBase(PatientBase):
    id: UUID
    user_id: UUID
    created_at: date
    updated_at: date

    class Config:
        from_attributes = True

class Patient(PatientInDBBase):
    pass
