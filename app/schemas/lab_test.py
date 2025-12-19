from typing import Optional
from pydantic import BaseModel
from datetime import date
from uuid import UUID
from app.models.lab_test import LabTestStatus

class LabTestBase(BaseModel):
    patient_id: UUID
    doctor_id: UUID
    test_name: str
    test_type: Optional[str] = None
    test_date: Optional[date] = None

class LabTestCreate(LabTestBase):
    pass

class LabTestUpdate(BaseModel):
    results: Optional[dict] = None
    ai_interpretation: Optional[str] = None
    status: Optional[LabTestStatus] = None
    file_url: Optional[str] = None

class LabTest(LabTestBase):
    id: UUID
    results: Optional[dict] = {}
    ai_interpretation: Optional[str] = None
    status: LabTestStatus
    file_url: Optional[str] = None

    class Config:
        from_attributes = True
