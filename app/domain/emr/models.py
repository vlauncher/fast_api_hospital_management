"""
Electronic Medical Records (EMR) Domain Models

Implements the database models for:
- Patient encounters
- Diagnoses (ICD-10 coded)
- Procedures (CPT coded)
- Clinical notes (SOAP format)
- Vital signs
- Prescriptions and prescription items
"""

from sqlalchemy import (
    Column, String, Date, Boolean, DateTime, ForeignKey, 
    Integer, Text, Float, Enum, JSON, CheckConstraint
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.infrastructure.database import Base
import uuid
import enum


class EncounterType(str, enum.Enum):
    """Type of medical encounter"""
    OUTPATIENT = "OUTPATIENT"
    INPATIENT = "INPATIENT"
    EMERGENCY = "EMERGENCY"
    TELEHEALTH = "TELEHEALTH"
    HOME_VISIT = "HOME_VISIT"
    DAY_SURGERY = "DAY_SURGERY"


class EncounterStatus(str, enum.Enum):
    """Status of encounter"""
    SCHEDULED = "SCHEDULED"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    SIGNED = "SIGNED"
    AMENDED = "AMENDED"
    CANCELLED = "CANCELLED"


class DiagnosisType(str, enum.Enum):
    """Type of diagnosis"""
    PRIMARY = "PRIMARY"
    SECONDARY = "SECONDARY"
    ADMITTING = "ADMITTING"
    DISCHARGE = "DISCHARGE"
    DIFFERENTIAL = "DIFFERENTIAL"
    WORKING = "WORKING"
    FINAL = "FINAL"


class DiagnosisCertainty(str, enum.Enum):
    """Certainty level of diagnosis"""
    CONFIRMED = "CONFIRMED"
    PROVISIONAL = "PROVISIONAL"
    DIFFERENTIAL = "DIFFERENTIAL"
    RULED_OUT = "RULED_OUT"
    SUSPECTED = "SUSPECTED"


class ProcedureStatus(str, enum.Enum):
    """Status of procedure"""
    SCHEDULED = "SCHEDULED"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"
    POSTPONED = "POSTPONED"


class NoteType(str, enum.Enum):
    """Type of clinical note"""
    SOAP = "SOAP"  # Subjective, Objective, Assessment, Plan
    PROGRESS = "PROGRESS"
    ADMISSION = "ADMISSION"
    DISCHARGE = "DISCHARGE"
    CONSULTATION = "CONSULTATION"
    PROCEDURE = "PROCEDURE"
    NURSING = "NURSING"
    OPERATIVE = "OPERATIVE"


class PrescriptionStatus(str, enum.Enum):
    """Status of prescription"""
    PENDING = "PENDING"
    VERIFIED = "VERIFIED"
    DISPENSED = "DISPENSED"
    PARTIALLY_DISPENSED = "PARTIALLY_DISPENSED"
    CANCELLED = "CANCELLED"
    EXPIRED = "EXPIRED"


class DrugRoute(str, enum.Enum):
    """Route of drug administration"""
    ORAL = "ORAL"
    INTRAVENOUS = "IV"
    INTRAMUSCULAR = "IM"
    SUBCUTANEOUS = "SC"
    TOPICAL = "TOPICAL"
    INHALATION = "INHALATION"
    SUBLINGUAL = "SUBLINGUAL"
    RECTAL = "RECTAL"
    OPHTHALMIC = "OPHTHALMIC"
    OTIC = "OTIC"
    NASAL = "NASAL"
    TRANSDERMAL = "TRANSDERMAL"


class Encounter(Base):
    """Encounter model - represents a patient visit/consultation"""
    __tablename__ = "encounters"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    encounter_number = Column(String(50), unique=True, nullable=False, index=True)
    
    # Patient and provider
    patient_id = Column(UUID(as_uuid=True), ForeignKey("patients.id"), nullable=False)
    doctor_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    department_id = Column(UUID(as_uuid=True), ForeignKey("departments.id"))
    
    # Related records
    appointment_id = Column(UUID(as_uuid=True), ForeignKey("appointments.id"))
    admission_id = Column(UUID(as_uuid=True))  # For inpatient encounters
    
    # Encounter details
    encounter_type = Column(Enum(EncounterType), nullable=False, default=EncounterType.OUTPATIENT)
    encounter_date = Column(DateTime, nullable=False, default=func.now())
    
    # Chief complaint and symptoms
    chief_complaint = Column(Text)
    symptoms = Column(JSON)  # List of symptoms with details
    history_of_present_illness = Column(Text)
    
    # Status and workflow
    status = Column(Enum(EncounterStatus), default=EncounterStatus.IN_PROGRESS)
    
    # Signing/locking
    signed_at = Column(DateTime)
    signed_by = Column(UUID(as_uuid=True), ForeignKey("users.id"))
    is_locked = Column(Boolean, default=False)
    lock_reason = Column(String(500))
    
    # Amendment tracking
    amended_at = Column(DateTime)
    amended_by = Column(UUID(as_uuid=True), ForeignKey("users.id"))
    amendment_reason = Column(Text)
    
    # Follow-up
    follow_up_required = Column(Boolean, default=False)
    follow_up_date = Column(Date)
    follow_up_notes = Column(Text)
    
    # Audit
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    created_by = Column(UUID(as_uuid=True), ForeignKey("users.id"))
    
    # Relationships
    patient = relationship("Patient", back_populates="encounters")
    doctor = relationship("User", foreign_keys=[doctor_id])
    department = relationship("Department", foreign_keys=[department_id])
    appointment = relationship("Appointment")
    signer = relationship("User", foreign_keys=[signed_by])
    amender = relationship("User", foreign_keys=[amended_by])
    creator = relationship("User", foreign_keys=[created_by])
    
    # Child relationships
    diagnoses = relationship("Diagnosis", back_populates="encounter", cascade="all, delete-orphan")
    procedures = relationship("Procedure", back_populates="encounter", cascade="all, delete-orphan")
    clinical_notes = relationship("ClinicalNote", back_populates="encounter", cascade="all, delete-orphan")
    vital_signs = relationship("VitalSigns", back_populates="encounter", cascade="all, delete-orphan")
    prescriptions = relationship("Prescription", back_populates="encounter", cascade="all, delete-orphan")


class Diagnosis(Base):
    """Diagnosis model with ICD-10 coding"""
    __tablename__ = "diagnoses"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    encounter_id = Column(UUID(as_uuid=True), ForeignKey("encounters.id", ondelete="CASCADE"), nullable=False)
    
    # ICD-10 Coding
    icd_10_code = Column(String(20), nullable=False, index=True)
    description = Column(Text, nullable=False)
    
    # Diagnosis classification
    diagnosis_type = Column(Enum(DiagnosisType), nullable=False, default=DiagnosisType.PRIMARY)
    certainty = Column(Enum(DiagnosisCertainty), nullable=False, default=DiagnosisCertainty.CONFIRMED)
    
    # Additional details
    onset_date = Column(Date)
    resolution_date = Column(Date)
    is_chronic = Column(Boolean, default=False)
    is_principal = Column(Boolean, default=False)  # Principal diagnosis for billing
    notes = Column(Text)
    
    # Provider
    diagnosed_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    diagnosed_at = Column(DateTime, default=func.now())
    
    # Audit
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    
    # Relationships
    encounter = relationship("Encounter", back_populates="diagnoses")
    diagnoser = relationship("User", foreign_keys=[diagnosed_by])


class Procedure(Base):
    """Procedure model with CPT coding"""
    __tablename__ = "procedures"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    encounter_id = Column(UUID(as_uuid=True), ForeignKey("encounters.id", ondelete="CASCADE"), nullable=False)
    
    # CPT Coding
    cpt_code = Column(String(20), nullable=False, index=True)
    description = Column(Text, nullable=False)
    
    # Scheduling
    scheduled_date = Column(DateTime)
    procedure_date = Column(DateTime)
    duration_minutes = Column(Integer)
    actual_duration_minutes = Column(Integer)
    
    # Status
    status = Column(Enum(ProcedureStatus), default=ProcedureStatus.SCHEDULED)
    
    # Location
    location = Column(String(200))  # Room/OR number
    
    # Clinical details
    pre_procedure_diagnosis = Column(Text)
    post_procedure_diagnosis = Column(Text)
    findings = Column(Text)
    technique = Column(Text)
    complications = Column(Text)
    specimens_collected = Column(JSON)  # List of specimens
    implants_used = Column(JSON)  # List of implants
    
    # Provider team
    performed_by = Column(UUID(as_uuid=True), ForeignKey("users.id"))
    assisted_by = Column(JSON)  # List of assistant UUIDs
    anesthesiologist_id = Column(UUID(as_uuid=True), ForeignKey("users.id"))
    
    # Anesthesia
    anesthesia_type = Column(String(50))
    anesthesia_start = Column(DateTime)
    anesthesia_end = Column(DateTime)
    
    notes = Column(Text)
    
    # Audit
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    created_by = Column(UUID(as_uuid=True), ForeignKey("users.id"))
    
    # Relationships
    encounter = relationship("Encounter", back_populates="procedures")
    performer = relationship("User", foreign_keys=[performed_by])
    anesthesiologist = relationship("User", foreign_keys=[anesthesiologist_id])
    creator = relationship("User", foreign_keys=[created_by])


class ClinicalNote(Base):
    """Clinical notes model with SOAP format support"""
    __tablename__ = "clinical_notes"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    encounter_id = Column(UUID(as_uuid=True), ForeignKey("encounters.id", ondelete="CASCADE"), nullable=False)
    
    # Note type and metadata
    note_type = Column(Enum(NoteType), nullable=False, default=NoteType.SOAP)
    title = Column(String(500))
    
    # SOAP Components
    subjective = Column(Text)  # Patient's symptoms, history
    objective = Column(Text)   # Physical exam, observations
    assessment = Column(Text)  # Diagnosis, interpretation
    plan = Column(Text)        # Treatment plan
    
    # General content (for non-SOAP notes)
    content = Column(Text)
    
    # Signing
    is_signed = Column(Boolean, default=False)
    signed_at = Column(DateTime)
    signed_by = Column(UUID(as_uuid=True), ForeignKey("users.id"))
    is_locked = Column(Boolean, default=False)
    
    # Addendum support
    is_addendum = Column(Boolean, default=False)
    parent_note_id = Column(UUID(as_uuid=True), ForeignKey("clinical_notes.id"))
    addendum_reason = Column(Text)
    
    # Auto-save support
    is_draft = Column(Boolean, default=True)
    last_auto_save = Column(DateTime)
    
    # Audit
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    created_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    
    # Relationships
    encounter = relationship("Encounter", back_populates="clinical_notes")
    author = relationship("User", foreign_keys=[created_by])
    signer = relationship("User", foreign_keys=[signed_by])
    parent_note = relationship("ClinicalNote", remote_side=[id])
    addendums = relationship("ClinicalNote", foreign_keys=[parent_note_id])


class VitalSigns(Base):
    """Vital signs recording model"""
    __tablename__ = "vital_signs"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    encounter_id = Column(UUID(as_uuid=True), ForeignKey("encounters.id", ondelete="CASCADE"), nullable=False)
    patient_id = Column(UUID(as_uuid=True), ForeignKey("patients.id"), nullable=False)
    
    # Blood Pressure
    systolic_bp = Column(Integer)  # mmHg
    diastolic_bp = Column(Integer)  # mmHg
    bp_position = Column(String(20))  # Sitting, Standing, Lying
    bp_arm = Column(String(10))  # Left, Right
    
    # Heart Rate
    heart_rate = Column(Integer)  # bpm
    heart_rhythm = Column(String(20))  # Regular, Irregular
    
    # Respiratory
    respiratory_rate = Column(Integer)  # breaths per minute
    oxygen_saturation = Column(Float)  # SpO2 percentage
    oxygen_therapy = Column(String(100))  # Room air, nasal cannula, etc.
    
    # Temperature
    temperature = Column(Float)  # Celsius
    temperature_method = Column(String(20))  # Oral, Axillary, Tympanic, Rectal
    
    # Anthropometrics
    weight = Column(Float)  # kg
    height = Column(Float)  # cm
    bmi = Column(Float)  # Calculated
    waist_circumference = Column(Float)  # cm
    
    # Pain
    pain_score = Column(Integer)  # 0-10 scale
    pain_location = Column(String(200))
    pain_character = Column(String(100))
    
    # Blood Glucose
    blood_glucose = Column(Float)  # mg/dL or mmol/L
    glucose_fasting = Column(Boolean)
    
    # Neurological
    gcs_score = Column(Integer)  # Glasgow Coma Scale (3-15)
    gcs_eye = Column(Integer)
    gcs_verbal = Column(Integer)
    gcs_motor = Column(Integer)
    pupil_left = Column(String(20))
    pupil_right = Column(String(20))
    
    # General
    level_of_consciousness = Column(String(50))
    notes = Column(Text)
    
    # Recording metadata
    recorded_at = Column(DateTime, default=func.now(), nullable=False)
    recorded_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    
    # Audit
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    
    # Relationships
    encounter = relationship("Encounter", back_populates="vital_signs")
    patient = relationship("Patient")
    recorder = relationship("User", foreign_keys=[recorded_by])
    
    def calculate_bmi(self):
        """Calculate BMI from weight and height"""
        if self.weight and self.height and self.height > 0:
            height_m = self.height / 100
            self.bmi = round(self.weight / (height_m ** 2), 1)
    
    def is_blood_pressure_abnormal(self) -> bool:
        """Check if blood pressure is abnormal"""
        if self.systolic_bp and self.diastolic_bp:
            if self.systolic_bp >= 140 or self.diastolic_bp >= 90:
                return True  # Hypertension
            if self.systolic_bp < 90 or self.diastolic_bp < 60:
                return True  # Hypotension
        return False


class Prescription(Base):
    """Prescription model for medication orders"""
    __tablename__ = "prescriptions"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    prescription_number = Column(String(50), unique=True, nullable=False, index=True)
    
    # References
    encounter_id = Column(UUID(as_uuid=True), ForeignKey("encounters.id"))
    patient_id = Column(UUID(as_uuid=True), ForeignKey("patients.id"), nullable=False)
    
    # Prescriber
    prescribed_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    prescription_date = Column(DateTime, default=func.now())
    
    # Status
    status = Column(Enum(PrescriptionStatus), default=PrescriptionStatus.PENDING)
    
    # Validity
    valid_from = Column(Date, default=func.current_date())
    valid_until = Column(Date)
    
    # Clinical notes
    diagnosis = Column(Text)
    clinical_notes = Column(Text)
    allergy_check_performed = Column(Boolean, default=False)
    interaction_check_performed = Column(Boolean, default=False)
    
    # Verification
    verified_by = Column(UUID(as_uuid=True), ForeignKey("users.id"))
    verified_at = Column(DateTime)
    verification_notes = Column(Text)
    
    # Dispensing
    dispensed_at = Column(DateTime)
    dispensed_by = Column(UUID(as_uuid=True), ForeignKey("users.id"))
    
    # Cancellation
    cancelled_at = Column(DateTime)
    cancelled_by = Column(UUID(as_uuid=True), ForeignKey("users.id"))
    cancellation_reason = Column(Text)
    
    # Audit
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    
    # Relationships
    encounter = relationship("Encounter", back_populates="prescriptions")
    patient = relationship("Patient")
    prescriber = relationship("User", foreign_keys=[prescribed_by])
    verifier = relationship("User", foreign_keys=[verified_by])
    dispenser = relationship("User", foreign_keys=[dispensed_by])
    canceller = relationship("User", foreign_keys=[cancelled_by])
    items = relationship("PrescriptionItem", back_populates="prescription", cascade="all, delete-orphan")


class PrescriptionItem(Base):
    """Individual medication item in a prescription"""
    __tablename__ = "prescription_items"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    prescription_id = Column(UUID(as_uuid=True), ForeignKey("prescriptions.id", ondelete="CASCADE"), nullable=False)
    
    # Drug reference (can be free text or linked to drug catalog)
    drug_id = Column(UUID(as_uuid=True))  # Optional FK to drugs table when available
    drug_name = Column(String(300), nullable=False)
    drug_code = Column(String(50))  # NDC, RxNorm, etc.
    generic_name = Column(String(300))
    
    # Dosage
    strength = Column(String(100))
    dosage = Column(String(100), nullable=False)  # e.g., "500mg"
    dosage_form = Column(String(50))  # Tablet, Capsule, Syrup, etc.
    
    # Frequency
    frequency = Column(String(100), nullable=False)  # e.g., "Three times daily"
    frequency_code = Column(String(20))  # TID, BID, QD, etc.
    
    # Duration
    duration_days = Column(Integer)
    duration_text = Column(String(100))  # "2 weeks", "As needed", etc.
    
    # Quantity
    quantity = Column(Integer, nullable=False)
    quantity_unit = Column(String(50))  # Tablets, mL, etc.
    
    # Route
    route = Column(Enum(DrugRoute), default=DrugRoute.ORAL)
    
    # Timing
    timing = Column(String(200))  # Before meals, At bedtime, etc.
    
    # Special instructions
    instructions = Column(Text)
    take_with_food = Column(Boolean)
    avoid_with_food = Column(Boolean)
    special_warnings = Column(Text)
    
    # Refills
    refills_allowed = Column(Integer, default=0)
    refills_remaining = Column(Integer, default=0)
    
    # Substitution
    allow_generic_substitution = Column(Boolean, default=True)
    substitution_reason = Column(Text)
    
    # Dispensing status
    is_dispensed = Column(Boolean, default=False)
    dispensed_quantity = Column(Integer, default=0)
    dispensed_at = Column(DateTime)
    dispensed_by = Column(UUID(as_uuid=True), ForeignKey("users.id"))
    
    # Audit
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    
    # Relationships
    prescription = relationship("Prescription", back_populates="items")
    dispenser = relationship("User", foreign_keys=[dispensed_by])
