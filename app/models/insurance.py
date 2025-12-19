from sqlalchemy import Column, String, Integer, Float, ForeignKey, Date, Enum, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID
from app.db.base import Base
import enum
import uuid
from datetime import datetime

class ClaimStatus(str, enum.Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    PAID = "paid"

class InsuranceProvider(Base):
    __tablename__ = "insurance_providers"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    name = Column(String(255), nullable=False)
    contact_number = Column(String(50))
    email = Column(String(255))
    address = Column(String(500))
    created_at = Column(Date, default=datetime.utcnow)

class PatientInsurance(Base):
    __tablename__ = "patient_insurance"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    patient_id = Column(UUID(as_uuid=True), ForeignKey("patients.id"), nullable=False)
    provider_id = Column(UUID(as_uuid=True), ForeignKey("insurance_providers.id"), nullable=False)
    policy_number = Column(String(100), unique=True, nullable=False)
    expiry_date = Column(Date, nullable=False)
    coverage_details = Column(JSON, default={})
    
    patient = relationship("Patient", backref="insurance_policies")
    provider = relationship("InsuranceProvider", backref="policies")

class InsuranceClaim(Base):
    __tablename__ = "insurance_claims"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    patient_id = Column(UUID(as_uuid=True), ForeignKey("patients.id"), nullable=False)
    appointment_id = Column(UUID(as_uuid=True), ForeignKey("appointments.id"), nullable=True) # Optional link to appointment
    policy_id = Column(UUID(as_uuid=True), ForeignKey("patient_insurance.id"), nullable=False)
    
    claim_amount = Column(Float, nullable=False)
    approved_amount = Column(Float, default=0.0)
    status = Column(Enum(ClaimStatus), default=ClaimStatus.PENDING)
    
    diagnosis_code = Column(String(50)) # ICD-10 Code
    documents_url = Column(JSON, default=[]) # Cloudinary URLs
    
    created_at = Column(Date, default=datetime.utcnow)
    updated_at = Column(Date, default=datetime.utcnow, onupdate=datetime.utcnow)

    patient = relationship("Patient", backref="claims")
    policy = relationship("PatientInsurance", backref="claims")
    appointment = relationship("Appointment")
