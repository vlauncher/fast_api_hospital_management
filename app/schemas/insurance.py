from typing import Optional, List
from pydantic import BaseModel
from datetime import date
from uuid import UUID
from app.models.insurance import ClaimStatus

class InsuranceProviderBase(BaseModel):
    name: str
    contact_number: Optional[str] = None
    email: Optional[str] = None
    address: Optional[str] = None

class InsuranceProviderCreate(InsuranceProviderBase):
    pass

class InsuranceProvider(InsuranceProviderBase):
    id: UUID
    class Config:
        from_attributes = True

class PatientInsuranceBase(BaseModel):
    provider_id: UUID
    policy_number: str
    expiry_date: date
    coverage_details: Optional[dict] = {}

class PatientInsuranceCreate(PatientInsuranceBase):
    patient_id: UUID

class PatientInsurance(PatientInsuranceBase):
    id: UUID
    patient_id: UUID
    class Config:
        from_attributes = True

class InsuranceClaimBase(BaseModel):
    policy_id: UUID
    appointment_id: Optional[UUID] = None
    claim_amount: float
    diagnosis_code: Optional[str] = None
    documents_url: Optional[List[str]] = []

class InsuranceClaimCreate(InsuranceClaimBase):
    patient_id: UUID

class InsuranceClaimUpdate(BaseModel):
    status: Optional[ClaimStatus] = None
    approved_amount: Optional[float] = None

class InsuranceClaim(InsuranceClaimBase):
    id: UUID
    patient_id: UUID
    status: ClaimStatus
    approved_amount: float
    created_at: date
    updated_at: date
    class Config:
        from_attributes = True
