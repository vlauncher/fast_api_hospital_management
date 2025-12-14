"""
EMR API Schemas

Pydantic models for EMR-related API requests and responses.
"""

from pydantic import BaseModel, Field, validator
from typing import Optional, List, Dict, Any
from datetime import datetime, date, time
import uuid
from app.domain.emr.models import (
    EncounterType, EncounterStatus,
    DiagnosisType, DiagnosisCertainty,
    ProcedureStatus,
    NoteType,
    PrescriptionStatus, DrugRoute
)


# ==================== Encounter Schemas ====================

class EncounterBase(BaseModel):
    """Base schema for encounter"""
    encounter_type: EncounterType
    chief_complaint: Optional[str] = Field(None, max_length=2000)
    symptoms: Optional[List[Dict]] = None
    history_of_present_illness: Optional[str] = None


class EncounterCreate(EncounterBase):
    """Schema for creating encounter"""
    patient_id: uuid.UUID
    doctor_id: uuid.UUID
    department_id: Optional[uuid.UUID] = None
    appointment_id: Optional[uuid.UUID] = None


class EncounterUpdate(BaseModel):
    """Schema for updating encounter"""
    chief_complaint: Optional[str] = None
    symptoms: Optional[List[Dict]] = None
    history_of_present_illness: Optional[str] = None
    follow_up_required: Optional[bool] = None
    follow_up_date: Optional[date] = None
    follow_up_notes: Optional[str] = None


class EncounterAmend(BaseModel):
    """Schema for amending encounter"""
    reason: str = Field(..., min_length=10, max_length=1000)


class EncounterResponse(EncounterBase):
    """Schema for encounter response"""
    id: uuid.UUID
    encounter_number: str
    patient_id: uuid.UUID
    doctor_id: uuid.UUID
    department_id: Optional[uuid.UUID] = None
    appointment_id: Optional[uuid.UUID] = None
    encounter_date: datetime
    status: EncounterStatus
    is_locked: bool
    signed_at: Optional[datetime] = None
    signed_by: Optional[uuid.UUID] = None
    amended_at: Optional[datetime] = None
    amended_by: Optional[uuid.UUID] = None
    amendment_reason: Optional[str] = None
    follow_up_required: bool
    follow_up_date: Optional[date] = None
    follow_up_notes: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class EncounterListResponse(BaseModel):
    """Schema for paginated encounter list"""
    items: List[EncounterResponse]
    total: int
    page: int
    limit: int
    pages: int


# ==================== Diagnosis Schemas ====================

class DiagnosisBase(BaseModel):
    """Base schema for diagnosis"""
    icd_10_code: str = Field(..., min_length=3, max_length=20)
    description: str = Field(..., min_length=1, max_length=500)
    diagnosis_type: DiagnosisType = DiagnosisType.PRIMARY
    certainty: DiagnosisCertainty = DiagnosisCertainty.CONFIRMED
    onset_date: Optional[date] = None
    is_chronic: bool = False
    is_principal: bool = False
    notes: Optional[str] = None


class DiagnosisCreate(DiagnosisBase):
    """Schema for creating diagnosis"""
    pass


class DiagnosisUpdate(BaseModel):
    """Schema for updating diagnosis"""
    icd_10_code: Optional[str] = None
    description: Optional[str] = None
    diagnosis_type: Optional[DiagnosisType] = None
    certainty: Optional[DiagnosisCertainty] = None
    onset_date: Optional[date] = None
    resolution_date: Optional[date] = None
    is_chronic: Optional[bool] = None
    is_principal: Optional[bool] = None
    notes: Optional[str] = None


class DiagnosisResponse(DiagnosisBase):
    """Schema for diagnosis response"""
    id: uuid.UUID
    encounter_id: uuid.UUID
    resolution_date: Optional[date] = None
    diagnosed_by: uuid.UUID
    diagnosed_at: datetime
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


# ==================== Procedure Schemas ====================

class ProcedureBase(BaseModel):
    """Base schema for procedure"""
    cpt_code: str = Field(..., min_length=3, max_length=20)
    description: str = Field(..., min_length=1, max_length=500)
    scheduled_date: Optional[datetime] = None
    duration_minutes: Optional[int] = Field(None, ge=1)
    location: Optional[str] = None
    pre_procedure_diagnosis: Optional[str] = None
    notes: Optional[str] = None


class ProcedureCreate(ProcedureBase):
    """Schema for creating procedure"""
    performed_by: Optional[uuid.UUID] = None


class ProcedureUpdate(BaseModel):
    """Schema for updating procedure"""
    scheduled_date: Optional[datetime] = None
    duration_minutes: Optional[int] = None
    location: Optional[str] = None
    pre_procedure_diagnosis: Optional[str] = None
    notes: Optional[str] = None


class ProcedureComplete(BaseModel):
    """Schema for completing procedure"""
    findings: Optional[str] = None
    technique: Optional[str] = None
    complications: Optional[str] = None
    post_procedure_diagnosis: Optional[str] = None


class ProcedureResponse(ProcedureBase):
    """Schema for procedure response"""
    id: uuid.UUID
    encounter_id: uuid.UUID
    procedure_date: Optional[datetime] = None
    actual_duration_minutes: Optional[int] = None
    status: ProcedureStatus
    performed_by: Optional[uuid.UUID] = None
    findings: Optional[str] = None
    technique: Optional[str] = None
    complications: Optional[str] = None
    post_procedure_diagnosis: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


# ==================== Clinical Note Schemas ====================

class ClinicalNoteBase(BaseModel):
    """Base schema for clinical note"""
    note_type: NoteType
    title: Optional[str] = Field(None, max_length=500)


class ClinicalNoteCreate(ClinicalNoteBase):
    """Schema for creating clinical note (SOAP format)"""
    subjective: Optional[str] = None
    objective: Optional[str] = None
    assessment: Optional[str] = None
    plan: Optional[str] = None
    content: Optional[str] = None  # For non-SOAP notes
    is_draft: bool = True


class ClinicalNoteUpdate(BaseModel):
    """Schema for updating clinical note"""
    title: Optional[str] = None
    subjective: Optional[str] = None
    objective: Optional[str] = None
    assessment: Optional[str] = None
    plan: Optional[str] = None
    content: Optional[str] = None


class ClinicalNoteAddendum(BaseModel):
    """Schema for creating addendum"""
    content: str = Field(..., min_length=1)
    reason: str = Field(..., min_length=10, max_length=500)


class ClinicalNoteResponse(ClinicalNoteBase):
    """Schema for clinical note response"""
    id: uuid.UUID
    encounter_id: uuid.UUID
    subjective: Optional[str] = None
    objective: Optional[str] = None
    assessment: Optional[str] = None
    plan: Optional[str] = None
    content: Optional[str] = None
    is_signed: bool
    signed_at: Optional[datetime] = None
    signed_by: Optional[uuid.UUID] = None
    is_locked: bool
    is_addendum: bool
    parent_note_id: Optional[uuid.UUID] = None
    addendum_reason: Optional[str] = None
    is_draft: bool
    created_by: uuid.UUID
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


# ==================== Vital Signs Schemas ====================

class VitalSignsBase(BaseModel):
    """Base schema for vital signs"""
    systolic_bp: Optional[int] = Field(None, ge=50, le=300)
    diastolic_bp: Optional[int] = Field(None, ge=30, le=200)
    bp_position: Optional[str] = None
    bp_arm: Optional[str] = None
    heart_rate: Optional[int] = Field(None, ge=20, le=300)
    heart_rhythm: Optional[str] = None
    respiratory_rate: Optional[int] = Field(None, ge=5, le=60)
    oxygen_saturation: Optional[float] = Field(None, ge=50, le=100)
    oxygen_therapy: Optional[str] = None
    temperature: Optional[float] = Field(None, ge=30, le=45)
    temperature_method: Optional[str] = None
    weight: Optional[float] = Field(None, ge=0.5, le=500)
    height: Optional[float] = Field(None, ge=30, le=250)
    waist_circumference: Optional[float] = None
    pain_score: Optional[int] = Field(None, ge=0, le=10)
    pain_location: Optional[str] = None
    pain_character: Optional[str] = None
    blood_glucose: Optional[float] = Field(None, ge=20, le=600)
    glucose_fasting: Optional[bool] = None
    gcs_score: Optional[int] = Field(None, ge=3, le=15)
    gcs_eye: Optional[int] = Field(None, ge=1, le=4)
    gcs_verbal: Optional[int] = Field(None, ge=1, le=5)
    gcs_motor: Optional[int] = Field(None, ge=1, le=6)
    pupil_left: Optional[str] = None
    pupil_right: Optional[str] = None
    level_of_consciousness: Optional[str] = None
    notes: Optional[str] = None


class VitalSignsCreate(VitalSignsBase):
    """Schema for creating vital signs"""
    pass


class VitalSignsUpdate(VitalSignsBase):
    """Schema for updating vital signs"""
    pass


class VitalSignsResponse(VitalSignsBase):
    """Schema for vital signs response"""
    id: uuid.UUID
    encounter_id: uuid.UUID
    patient_id: uuid.UUID
    bmi: Optional[float] = None
    recorded_at: datetime
    recorded_by: uuid.UUID
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class VitalSignsTrends(BaseModel):
    """Schema for vital signs trends"""
    dates: List[Optional[str]]
    systolic_bp: List[Optional[int]]
    diastolic_bp: List[Optional[int]]
    heart_rate: List[Optional[int]]
    temperature: List[Optional[float]]
    weight: List[Optional[float]]
    bmi: List[Optional[float]]


# ==================== Prescription Schemas ====================

class PrescriptionItemBase(BaseModel):
    """Base schema for prescription item"""
    drug_name: str = Field(..., min_length=1, max_length=300)
    drug_code: Optional[str] = None
    generic_name: Optional[str] = None
    strength: Optional[str] = None
    dosage: str = Field(..., min_length=1, max_length=100)
    dosage_form: Optional[str] = None
    frequency: str = Field(..., min_length=1, max_length=100)
    frequency_code: Optional[str] = None
    duration_days: Optional[int] = Field(None, ge=1)
    duration_text: Optional[str] = None
    quantity: int = Field(..., ge=1)
    quantity_unit: str = Field("units", max_length=50)
    route: str = "ORAL"
    timing: Optional[str] = None
    instructions: Optional[str] = None
    take_with_food: Optional[bool] = None
    special_warnings: Optional[str] = None
    refills_allowed: int = Field(0, ge=0, le=10)
    allow_generic_substitution: bool = True


class PrescriptionItemCreate(PrescriptionItemBase):
    """Schema for creating prescription item"""
    pass


class PrescriptionItemUpdate(BaseModel):
    """Schema for updating prescription item"""
    dosage: Optional[str] = None
    frequency: Optional[str] = None
    duration_days: Optional[int] = None
    quantity: Optional[int] = None
    instructions: Optional[str] = None


class PrescriptionItemResponse(PrescriptionItemBase):
    """Schema for prescription item response"""
    id: uuid.UUID
    prescription_id: uuid.UUID
    is_dispensed: bool
    dispensed_quantity: int
    dispensed_at: Optional[datetime] = None
    dispensed_by: Optional[uuid.UUID] = None
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class PrescriptionBase(BaseModel):
    """Base schema for prescription"""
    diagnosis: Optional[str] = None
    clinical_notes: Optional[str] = None
    valid_until: Optional[date] = None


class PrescriptionCreate(PrescriptionBase):
    """Schema for creating prescription"""
    patient_id: uuid.UUID
    encounter_id: Optional[uuid.UUID] = None
    items: List[PrescriptionItemCreate]
    
    @validator('items')
    def validate_items(cls, v):
        if not v or len(v) == 0:
            raise ValueError('Prescription must have at least one item')
        return v


class PrescriptionUpdate(BaseModel):
    """Schema for updating prescription"""
    diagnosis: Optional[str] = None
    clinical_notes: Optional[str] = None
    valid_until: Optional[date] = None


class PrescriptionVerify(BaseModel):
    """Schema for verifying prescription"""
    notes: Optional[str] = None


class PrescriptionCancel(BaseModel):
    """Schema for cancelling prescription"""
    reason: str = Field(..., min_length=1, max_length=500)


class PrescriptionResponse(PrescriptionBase):
    """Schema for prescription response"""
    id: uuid.UUID
    prescription_number: str
    patient_id: uuid.UUID
    encounter_id: Optional[uuid.UUID] = None
    prescribed_by: uuid.UUID
    prescription_date: datetime
    status: PrescriptionStatus
    valid_from: Optional[date] = None
    verified_by: Optional[uuid.UUID] = None
    verified_at: Optional[datetime] = None
    verification_notes: Optional[str] = None
    dispensed_at: Optional[datetime] = None
    dispensed_by: Optional[uuid.UUID] = None
    cancelled_at: Optional[datetime] = None
    cancelled_by: Optional[uuid.UUID] = None
    cancellation_reason: Optional[str] = None
    items: List[PrescriptionItemResponse] = []
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class PrescriptionListResponse(BaseModel):
    """Schema for paginated prescription list"""
    items: List[PrescriptionResponse]
    total: int
    page: int
    limit: int
    pages: int


class PrintablePrescription(BaseModel):
    """Schema for printable prescription"""
    prescription_number: str
    prescription_date: Optional[str]
    valid_until: Optional[str]
    patient: Dict[str, str]
    prescriber: Dict[str, str]
    diagnosis: Optional[str]
    items: List[Dict[str, Any]]
    clinical_notes: Optional[str]
