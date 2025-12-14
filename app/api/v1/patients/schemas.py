from pydantic import BaseModel, Field, validator
from typing import Optional, List, Dict, Any
from datetime import datetime, date
import uuid
from app.domain.patients.models import Gender, BloodType, MaritalStatus


class BasePatientSchema(BaseModel):
    """Base schema for patient data"""
    first_name: str = Field(..., min_length=1, max_length=100)
    last_name: str = Field(..., min_length=1, max_length=100)
    middle_name: Optional[str] = Field(None, max_length=100)
    date_of_birth: date
    gender: Gender
    phone_primary: str = Field(..., min_length=5, max_length=20)
    phone_secondary: Optional[str] = Field(None, max_length=20)
    email: Optional[str] = Field(None, max_length=255)
    address: Optional[Dict[str, Any]] = None
    
    @validator('email')
    def validate_email(cls, v):
        if v and '@' not in v:
            raise ValueError('Invalid email format')
        return v
    
    @validator('phone_primary', 'phone_secondary')
    def validate_phone(cls, v):
        if v and not v.replace('+', '').replace('-', '').replace(' ', '').isdigit():
            raise ValueError('Phone number must contain only digits, +, -, and spaces')
        return v


class PatientCreate(BasePatientSchema):
    """Schema for creating a new patient"""
    blood_type: Optional[BloodType] = None
    allergies: Optional[List[str]] = []
    medical_conditions: Optional[List[str]] = []
    medications: Optional[List[str]] = []
    national_id: Optional[str] = Field(None, max_length=50)
    passport_number: Optional[str] = Field(None, max_length=50)
    driver_license: Optional[str] = Field(None, max_length=50)
    marital_status: Optional[MaritalStatus] = None
    occupation: Optional[str] = Field(None, max_length=100)
    employer: Optional[str] = Field(None, max_length=200)
    education_level: Optional[str] = Field(None, max_length=50)
    emergency_contact_name: Optional[str] = Field(None, max_length=200)
    emergency_contact_phone: Optional[str] = Field(None, max_length=20)
    emergency_contact_relationship: Optional[str] = Field(None, max_length=50)
    insurance_provider: Optional[str] = Field(None, max_length=200)
    insurance_policy_number: Optional[str] = Field(None, max_length=100)
    insurance_group_number: Optional[str] = Field(None, max_length=100)


class PatientUpdate(BaseModel):
    """Schema for updating patient information"""
    first_name: Optional[str] = Field(None, min_length=1, max_length=100)
    last_name: Optional[str] = Field(None, min_length=1, max_length=100)
    middle_name: Optional[str] = Field(None, max_length=100)
    date_of_birth: Optional[date] = None
    gender: Optional[Gender] = None
    phone_primary: Optional[str] = Field(None, min_length=5, max_length=20)
    phone_secondary: Optional[str] = Field(None, max_length=20)
    email: Optional[str] = Field(None, max_length=255)
    address: Optional[Dict[str, Any]] = None
    blood_type: Optional[BloodType] = None
    allergies: Optional[List[str]] = None
    medical_conditions: Optional[List[str]] = None
    medications: Optional[List[str]] = None
    national_id: Optional[str] = Field(None, max_length=50)
    passport_number: Optional[str] = Field(None, max_length=50)
    driver_license: Optional[str] = Field(None, max_length=50)
    marital_status: Optional[MaritalStatus] = None
    occupation: Optional[str] = Field(None, max_length=100)
    employer: Optional[str] = Field(None, max_length=200)
    education_level: Optional[str] = Field(None, max_length=50)
    emergency_contact_name: Optional[str] = Field(None, max_length=200)
    emergency_contact_phone: Optional[str] = Field(None, max_length=20)
    emergency_contact_relationship: Optional[str] = Field(None, max_length=50)
    insurance_provider: Optional[str] = Field(None, max_length=200)
    insurance_policy_number: Optional[str] = Field(None, max_length=100)
    insurance_group_number: Optional[str] = Field(None, max_length=100)
    is_active: Optional[bool] = None


class PatientResponse(BasePatientSchema):
    """Schema for patient response data"""
    id: uuid.UUID
    patient_number: str
    blood_type: Optional[BloodType] = None
    allergies: Optional[List[str]] = []
    medical_conditions: Optional[List[str]] = []
    medications: Optional[List[str]] = []
    national_id: Optional[str] = None
    passport_number: Optional[str] = None
    driver_license: Optional[str] = None
    marital_status: Optional[MaritalStatus] = None
    occupation: Optional[str] = None
    employer: Optional[str] = None
    education_level: Optional[str] = None
    emergency_contact_name: Optional[str] = None
    emergency_contact_phone: Optional[str] = None
    emergency_contact_relationship: Optional[str] = None
    insurance_provider: Optional[str] = None
    insurance_policy_number: Optional[str] = None
    insurance_group_number: Optional[str] = None
    is_active: bool
    registered_date: datetime
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class PatientListResponse(BaseModel):
    """Schema for paginated patient list response"""
    items: List[PatientResponse]
    total: int
    page: int
    limit: int
    pages: int


class EmergencyContactCreate(BaseModel):
    """Schema for creating emergency contact"""
    name: str = Field(..., min_length=1, max_length=200)
    phone: str = Field(..., min_length=5, max_length=20)
    phone_secondary: Optional[str] = Field(None, max_length=20)
    email: Optional[str] = Field(None, max_length=255)
    address: Optional[str] = None
    relationship_type: str = Field(..., min_length=1, max_length=50)
    is_primary: bool = False
    is_authorized_for_medical_decisions: bool = False
    
    @validator('phone', 'phone_secondary')
    def validate_phone(cls, v):
        if v and not v.replace('+', '').replace('-', '').replace(' ', '').isdigit():
            raise ValueError('Phone number must contain only digits, +, -, and spaces')
        return v


class EmergencyContactUpdate(BaseModel):
    """Schema for updating emergency contact"""
    name: Optional[str] = Field(None, min_length=1, max_length=200)
    phone: Optional[str] = Field(None, min_length=5, max_length=20)
    phone_secondary: Optional[str] = Field(None, max_length=20)
    email: Optional[str] = Field(None, max_length=255)
    address: Optional[str] = None
    relationship_type: Optional[str] = Field(None, min_length=1, max_length=50)
    is_primary: Optional[bool] = None
    is_authorized_for_medical_decisions: Optional[bool] = None


class EmergencyContactResponse(BaseModel):
    """Schema for emergency contact response"""
    id: uuid.UUID
    patient_id: uuid.UUID
    name: str
    phone: str
    phone_secondary: Optional[str] = None
    email: Optional[str] = None
    address: Optional[str] = None
    relationship_type: str
    is_primary: bool
    is_authorized_for_medical_decisions: bool
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class InsuranceCreate(BaseModel):
    """Schema for creating insurance record"""
    provider_name: str = Field(..., min_length=1, max_length=200)
    policy_number: str = Field(..., min_length=1, max_length=100)
    group_number: Optional[str] = Field(None, max_length=100)
    policy_holder_name: Optional[str] = Field(None, max_length=200)
    policy_holder_relationship: Optional[str] = Field(None, max_length=50)
    policy_holder_dob: Optional[date] = None
    policy_holder_ssn: Optional[str] = Field(None, max_length=50)
    coverage_start_date: date
    coverage_end_date: Optional[date] = None
    copay_amount: Optional[float] = Field(None, ge=0)
    deductible_amount: Optional[float] = Field(None, ge=0)
    coverage_percentage: Optional[float] = Field(None, ge=0, le=100)
    max_coverage: Optional[float] = Field(None, ge=0)
    insurance_phone: Optional[str] = Field(None, max_length=20)
    insurance_address: Optional[str] = None
    is_primary: bool = False
    
    @validator('insurance_phone')
    def validate_phone(cls, v):
        if v and not v.replace('+', '').replace('-', '').replace(' ', '').isdigit():
            raise ValueError('Phone number must contain only digits, +, -, and spaces')
        return v


class InsuranceUpdate(BaseModel):
    """Schema for updating insurance record"""
    provider_name: Optional[str] = Field(None, min_length=1, max_length=200)
    policy_number: Optional[str] = Field(None, min_length=1, max_length=100)
    group_number: Optional[str] = Field(None, max_length=100)
    policy_holder_name: Optional[str] = Field(None, max_length=200)
    policy_holder_relationship: Optional[str] = Field(None, max_length=50)
    policy_holder_dob: Optional[date] = None
    policy_holder_ssn: Optional[str] = Field(None, max_length=50)
    coverage_start_date: Optional[date] = None
    coverage_end_date: Optional[date] = None
    copay_amount: Optional[float] = Field(None, ge=0)
    deductible_amount: Optional[float] = Field(None, ge=0)
    coverage_percentage: Optional[float] = Field(None, ge=0, le=100)
    max_coverage: Optional[float] = Field(None, ge=0)
    insurance_phone: Optional[str] = Field(None, max_length=20)
    insurance_address: Optional[str] = None
    is_active: Optional[bool] = None
    is_primary: Optional[bool] = None


class InsuranceResponse(BaseModel):
    """Schema for insurance response"""
    id: uuid.UUID
    patient_id: uuid.UUID
    provider_name: str
    policy_number: str
    group_number: Optional[str] = None
    policy_holder_name: Optional[str] = None
    policy_holder_relationship: Optional[str] = None
    policy_holder_dob: Optional[date] = None
    policy_holder_ssn: Optional[str] = None
    coverage_start_date: date
    coverage_end_date: Optional[date] = None
    copay_amount: Optional[float] = None
    deductible_amount: Optional[float] = None
    coverage_percentage: Optional[float] = None
    max_coverage: Optional[float] = None
    insurance_phone: Optional[str] = None
    insurance_address: Optional[str] = None
    is_active: bool
    is_primary: bool
    verification_status: str
    verified_date: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class PatientVisitCreate(BaseModel):
    """Schema for creating patient visit"""
    visit_type: str = Field(..., min_length=1, max_length=50)
    visit_date: datetime
    chief_complaint: Optional[str] = None
    diagnosis: Optional[List[str]] = []
    treatment: Optional[List[str]] = []
    medications_prescribed: Optional[List[str]] = []
    notes: Optional[str] = None
    attending_physician_id: Optional[uuid.UUID] = None
    nurse_id: Optional[uuid.UUID] = None
    visit_cost: Optional[float] = Field(None, ge=0)
    insurance_charged: Optional[float] = Field(None, ge=0)
    patient_responsible: Optional[float] = Field(None, ge=0)
    status: str = "SCHEDULED"


class PatientVisitUpdate(BaseModel):
    """Schema for updating patient visit"""
    visit_type: Optional[str] = Field(None, min_length=1, max_length=50)
    visit_date: Optional[datetime] = None
    check_in_time: Optional[datetime] = None
    check_out_time: Optional[datetime] = None
    chief_complaint: Optional[str] = None
    diagnosis: Optional[List[str]] = None
    treatment: Optional[List[str]] = None
    medications_prescribed: Optional[List[str]] = None
    notes: Optional[str] = None
    attending_physician_id: Optional[uuid.UUID] = None
    nurse_id: Optional[uuid.UUID] = None
    visit_cost: Optional[float] = Field(None, ge=0)
    insurance_charged: Optional[float] = Field(None, ge=0)
    patient_responsible: Optional[float] = Field(None, ge=0)
    payment_status: Optional[str] = None
    status: Optional[str] = None


class PatientVisitResponse(BaseModel):
    """Schema for patient visit response"""
    id: uuid.UUID
    patient_id: uuid.UUID
    visit_type: str
    visit_date: datetime
    check_in_time: Optional[datetime] = None
    check_out_time: Optional[datetime] = None
    chief_complaint: Optional[str] = None
    diagnosis: Optional[List[str]] = []
    treatment: Optional[List[str]] = []
    medications_prescribed: Optional[List[str]] = []
    notes: Optional[str] = None
    attending_physician_id: Optional[uuid.UUID] = None
    nurse_id: Optional[uuid.UUID] = None
    visit_cost: Optional[float] = None
    insurance_charged: Optional[float] = None
    patient_responsible: Optional[float] = None
    payment_status: str
    status: str
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class PatientVisitListResponse(BaseModel):
    """Schema for patient visit list response"""
    items: List[PatientVisitResponse]
    total: int
    page: int
    limit: int
    pages: int


class ErrorResponse(BaseModel):
    """Schema for error responses"""
    error: str
    message: str
    details: Optional[dict] = None


class SuccessResponse(BaseModel):
    """Schema for success responses"""
    success: bool = True
    message: str
    data: Optional[dict] = None
