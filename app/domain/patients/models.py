from sqlalchemy import Column, String, Date, Boolean, JSON, DateTime, ForeignKey, Float, Text, Integer, Enum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.infrastructure.database import Base
from app.infrastructure.encryption import encrypt_data, decrypt_data
import uuid
import enum


class Gender(str, enum.Enum):
    """Gender enumeration"""
    MALE = "MALE"
    FEMALE = "FEMALE"
    OTHER = "OTHER"
    PREFER_NOT_TO_SAY = "PREFER_NOT_TO_SAY"


class BloodType(str, enum.Enum):
    """Blood type enumeration"""
    A_POSITIVE = "A+"
    A_NEGATIVE = "A-"
    B_POSITIVE = "B+"
    B_NEGATIVE = "B-"
    AB_POSITIVE = "AB+"
    AB_NEGATIVE = "AB-"
    O_POSITIVE = "O+"
    O_NEGATIVE = "O-"
    UNKNOWN = "UNKNOWN"


class MaritalStatus(str, enum.Enum):
    """Marital status enumeration"""
    SINGLE = "SINGLE"
    MARRIED = "MARRIED"
    DIVORCED = "DIVORCED"
    WIDOWED = "WIDOWED"
    SEPARATED = "SEPARATED"
    DOMESTIC_PARTNER = "DOMESTIC_PARTNER"


class Patient(Base):
    """Patient model with PII encryption"""
    __tablename__ = "patients"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    patient_number = Column(String(50), unique=True, nullable=False, index=True)
    
    # Personal information (encrypted)
    first_name = Column(String(100), nullable=False)  # Will be encrypted
    last_name = Column(String(100), nullable=False)   # Will be encrypted
    middle_name = Column(String(100))                # Will be encrypted
    date_of_birth = Column(Date, nullable=False)     # Will be encrypted
    gender = Column(Enum(Gender), nullable=False)
    
    # Contact information (encrypted)
    phone_primary = Column(String(20), nullable=False)  # Will be encrypted
    phone_secondary = Column(String(20))               # Will be encrypted
    email = Column(String(255))                        # Will be encrypted
    address = Column(JSON)                            # Will be encrypted
    
    # Medical information
    blood_type = Column(Enum(BloodType))
    allergies = Column(JSON)  # List of allergies
    medical_conditions = Column(JSON)  # List of medical conditions
    medications = Column(JSON)  # List of current medications
    
    # Identification (encrypted)
    national_id = Column(String(50), unique=True)      # Will be encrypted
    passport_number = Column(String(50))              # Will be encrypted
    driver_license = Column(String(50))               # Will be encrypted
    
    # Demographics
    marital_status = Column(Enum(MaritalStatus))
    occupation = Column(String(100))
    employer = Column(String(200))
    education_level = Column(String(50))
    
    # Emergency contact
    emergency_contact_name = Column(String(200))      # Will be encrypted
    emergency_contact_phone = Column(String(20))      # Will be encrypted
    emergency_contact_relationship = Column(String(50))
    
    # Insurance information
    insurance_provider = Column(String(200))
    insurance_policy_number = Column(String(100))
    insurance_group_number = Column(String(100))
    
    # System fields
    is_active = Column(Boolean, default=True)
    registered_date = Column(DateTime, default=func.now())
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    created_by = Column(UUID(as_uuid=True), ForeignKey("users.id"))
    updated_by = Column(UUID(as_uuid=True), ForeignKey("users.id"))
    
    # Relationships
    creator = relationship("User", foreign_keys=[created_by])
    updater = relationship("User", foreign_keys=[updated_by])
    emergency_contacts = relationship("EmergencyContact", back_populates="patient", cascade="all, delete-orphan")
    insurance_records = relationship("Insurance", back_populates="patient", cascade="all, delete-orphan")
    visits = relationship("PatientVisit", back_populates="patient", cascade="all, delete-orphan")
    
    # Phase 2 relationships
    appointments = relationship("Appointment", back_populates="patient")
    encounters = relationship("Encounter", back_populates="patient")
    
    def encrypt_sensitive_data(self):
        """Encrypt sensitive PII fields"""
        sensitive_fields = [
            'first_name', 'last_name', 'middle_name', 'date_of_birth',
            'phone_primary', 'phone_secondary', 'email', 'address',
            'national_id', 'passport_number', 'driver_license',
            'emergency_contact_name', 'emergency_contact_phone'
        ]
        
        for field in sensitive_fields:
            value = getattr(self, field, None)
            if value:
                if isinstance(value, (dict, list)):
                    import json
                    value = json.dumps(value)
                setattr(self, field, encrypt_data(str(value)))
    
    def decrypt_sensitive_data(self):
        """Decrypt sensitive PII fields"""
        sensitive_fields = [
            'first_name', 'last_name', 'middle_name', 'date_of_birth',
            'phone_primary', 'phone_secondary', 'email', 'address',
            'national_id', 'passport_number', 'driver_license',
            'emergency_contact_name', 'emergency_contact_phone'
        ]
        
        for field in sensitive_fields:
            value = getattr(self, field, None)
            if value:
                decrypted_value = decrypt_data(str(value))
                try:
                    # Try to parse as JSON for complex fields
                    import json
                    setattr(self, field, json.loads(decrypted_value))
                except (json.JSONDecodeError, ValueError):
                    setattr(self, field, decrypted_value)
    
    def get_full_name(self) -> str:
        """Get patient's full name"""
        names = [self.first_name, self.middle_name, self.last_name]
        return " ".join(filter(None, names))
    
    def get_age(self) -> int:
        """Calculate patient's age"""
        from datetime import date
        if self.date_of_birth:
            today = date.today()
            return today.year - self.date_of_birth.year - (
                (today.month, today.day) < (self.date_of_birth.month, self.date_of_birth.day)
            )
        return None


class EmergencyContact(Base):
    """Emergency contact information for patients"""
    __tablename__ = "emergency_contacts"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    patient_id = Column(UUID(as_uuid=True), ForeignKey("patients.id", ondelete="CASCADE"), nullable=False)
    
    # Contact information (encrypted)
    name = Column(String(200), nullable=False)  # Will be encrypted
    phone = Column(String(20), nullable=False)  # Will be encrypted
    phone_secondary = Column(String(20))        # Will be encrypted
    email = Column(String(255))                  # Will be encrypted
    address = Column(Text)                       # Will be encrypted
    
    # Relationship details
    relationship_type = Column(String(50), nullable=False)
    is_primary = Column(Boolean, default=False)
    is_authorized_for_medical_decisions = Column(Boolean, default=False)
    
    # Timestamps
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    
    # Relationships
    patient = relationship("Patient", back_populates="emergency_contacts")
    
    def encrypt_sensitive_data(self):
        """Encrypt sensitive fields"""
        sensitive_fields = ['name', 'phone', 'phone_secondary', 'email', 'address']
        
        for field in sensitive_fields:
            value = getattr(self, field, None)
            if value:
                setattr(self, field, encrypt_data(str(value)))
    
    def decrypt_sensitive_data(self):
        """Decrypt sensitive fields"""
        sensitive_fields = ['name', 'phone', 'phone_secondary', 'email', 'address']
        
        for field in sensitive_fields:
            value = getattr(self, field, None)
            if value:
                decrypted_value = decrypt_data(str(value))
                setattr(self, field, decrypted_value)


class Insurance(Base):
    """Insurance information for patients"""
    __tablename__ = "insurance"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    patient_id = Column(UUID(as_uuid=True), ForeignKey("patients.id", ondelete="CASCADE"), nullable=False)
    
    # Insurance details
    provider_name = Column(String(200), nullable=False)
    policy_number = Column(String(100), unique=True, nullable=False)
    group_number = Column(String(100))
    
    # Policy holder information (encrypted)
    policy_holder_name = Column(String(200))  # Will be encrypted
    policy_holder_relationship = Column(String(50))
    policy_holder_dob = Column(Date)         # Will be encrypted
    policy_holder_ssn = Column(String(50))   # Will be encrypted
    
    # Coverage details
    coverage_start_date = Column(Date, nullable=False)
    coverage_end_date = Column(Date)
    copay_amount = Column(Float)
    deductible_amount = Column(Float)
    coverage_percentage = Column(Float)
    max_coverage = Column(Float)
    
    # Contact information (encrypted)
    insurance_phone = Column(String(20))     # Will be encrypted
    insurance_address = Column(Text)          # Will be encrypted
    
    # Status
    is_active = Column(Boolean, default=True)
    is_primary = Column(Boolean, default=False)
    verification_status = Column(String(20), default="PENDING")
    verified_date = Column(DateTime)
    verified_by = Column(UUID(as_uuid=True), ForeignKey("users.id"))
    
    # Timestamps
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    
    # Relationships
    patient = relationship("Patient", back_populates="insurance_records")
    verifier = relationship("User", foreign_keys=[verified_by])
    
    def encrypt_sensitive_data(self):
        """Encrypt sensitive fields"""
        sensitive_fields = [
            'policy_holder_name', 'policy_holder_dob', 'policy_holder_ssn',
            'insurance_phone', 'insurance_address'
        ]
        
        for field in sensitive_fields:
            value = getattr(self, field, None)
            if value:
                if isinstance(value, (dict, list)):
                    import json
                    value = json.dumps(value)
                elif isinstance(value, datetime.date):
                    value = value.isoformat()
                setattr(self, field, encrypt_data(str(value)))
    
    def decrypt_sensitive_data(self):
        """Decrypt sensitive fields"""
        sensitive_fields = [
            'policy_holder_name', 'policy_holder_dob', 'policy_holder_ssn',
            'insurance_phone', 'insurance_address'
        ]
        
        for field in sensitive_fields:
            value = getattr(self, field, None)
            if value:
                decrypted_value = decrypt_data(str(value))
                try:
                    # Try to parse as JSON for complex fields
                    import json
                    from datetime import datetime
                    
                    if field == 'policy_holder_dob':
                        # Parse date from string
                        setattr(self, field, datetime.strptime(decrypted_value, '%Y-%m-%d').date())
                    else:
                        setattr(self, field, json.loads(decrypted_value))
                except (json.JSONDecodeError, ValueError):
                    setattr(self, field, decrypted_value)


class PatientVisit(Base):
    """Patient visit records for tracking appointments and encounters"""
    __tablename__ = "patient_visits"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    patient_id = Column(UUID(as_uuid=True), ForeignKey("patients.id", ondelete="CASCADE"), nullable=False)
    
    # Visit details
    visit_type = Column(String(50), nullable=False)  # e.g., "CONSULTATION", "EMERGENCY", "FOLLOW_UP"
    visit_date = Column(DateTime, nullable=False)
    check_in_time = Column(DateTime)
    check_out_time = Column(DateTime)
    
    # Clinical information
    chief_complaint = Column(Text)
    diagnosis = Column(JSON)  # List of diagnosis codes
    treatment = Column(JSON)  # List of treatments provided
    medications_prescribed = Column(JSON)
    notes = Column(Text)
    
    # Staff involved
    attending_physician_id = Column(UUID(as_uuid=True), ForeignKey("users.id"))
    nurse_id = Column(UUID(as_uuid=True), ForeignKey("users.id"))
    
    # Financial
    visit_cost = Column(Float)
    insurance_charged = Column(Float)
    patient_responsible = Column(Float)
    payment_status = Column(String(20), default="PENDING")
    
    # Status
    status = Column(String(20), default="SCHEDULED")  # SCHEDULED, CHECKED_IN, IN_PROGRESS, COMPLETED, CANCELLED
    
    # Timestamps
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    
    # Relationships
    patient = relationship("Patient", back_populates="visits")
    attending_physician = relationship("User", foreign_keys=[attending_physician_id])
    nurse = relationship("User", foreign_keys=[nurse_id])
