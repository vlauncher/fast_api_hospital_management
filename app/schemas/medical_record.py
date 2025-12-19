from typing import Optional
from pydantic import BaseModel
from datetime import datetime
from uuid import UUID

class MedicalRecordBase(BaseModel):
    patient_id: UUID
    doctor_id: UUID
    appointment_id: Optional[UUID] = None
    diagnosis: Optional[str] = None
    prescription: Optional[dict] = {}
    lab_results: Optional[dict] = {}
    vitals: Optional[dict] = {}
    ai_insights: Optional[dict] = {}
    follow_up_date: Optional[datetime] = None

class MedicalRecordCreate(MedicalRecordBase):
    pass

class MedicalRecord(MedicalRecordBase):
    id: UUID
    record_date: datetime
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
