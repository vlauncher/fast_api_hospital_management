from typing import Optional, List, Dict, Any
from pydantic import BaseModel
from datetime import datetime
from uuid import UUID

class PrescriptionBase(BaseModel):
    medical_record_id: UUID
    patient_id: UUID
    doctor_id: UUID
    medications: List[Dict[str, Any]] = [] # [{"name": "DrugA", "dosage": "10mg"}]
    dosage_instructions: Optional[str] = None
    duration_days: Optional[int] = None
    special_instructions: Optional[str] = None

class PrescriptionCreate(PrescriptionBase):
    pass

class Prescription(PrescriptionBase):
    id: UUID
    ai_drug_interaction_check: Optional[dict] = {}
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

from typing import Any
