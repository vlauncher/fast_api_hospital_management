from sqlalchemy import Column, String, DateTime, ForeignKey, JSON, Text, Enum, Integer, Boolean
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.infrastructure.database import Base
from app.infrastructure.encryption import encrypt_data, decrypt_data
import uuid
import enum


class AuditAction(str, enum.Enum):
    """Audit action types"""
    CREATE = "CREATE"
    READ = "READ"
    UPDATE = "UPDATE"
    DELETE = "DELETE"
    LOGIN = "LOGIN"
    LOGOUT = "LOGOUT"
    ACCESS_DENIED = "ACCESS_DENIED"
    PASSWORD_CHANGE = "PASSWORD_CHANGE"
    EXPORT = "EXPORT"
    IMPORT = "IMPORT"
    SYSTEM = "SYSTEM"


class AuditResource(str, enum.Enum):
    """Audit resource types"""
    USER = "USER"
    PATIENT = "PATIENT"
    EMERGENCY_CONTACT = "EMERGENCY_CONTACT"
    INSURANCE = "INSURANCE"
    PATIENT_VISIT = "PATIENT_VISIT"
    DEPARTMENT = "DEPARTMENT"
    AUDIT_LOG = "AUDIT_LOG"
    SYSTEM = "SYSTEM"


class AuditSeverity(str, enum.Enum):
    """Audit severity levels"""
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class AuditLog(Base):
    """Comprehensive audit log model"""
    __tablename__ = "audit_logs"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Event details
    action = Column(Enum(AuditAction), nullable=False, index=True)
    resource_type = Column(Enum(AuditResource), nullable=False, index=True)
    resource_id = Column(UUID(as_uuid=True), nullable=True, index=True)
    
    # User information
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True, index=True)
    user = relationship("User", foreign_keys=[user_id])
    username = Column(String(50), nullable=True, index=True)  # Redundant but useful for performance
    
    # Request details
    ip_address = Column(String(45), nullable=True, index=True)
    user_agent = Column(Text, nullable=True)
    endpoint = Column(String(255), nullable=True, index=True)
    method = Column(String(10), nullable=True)
    
    # Data changes
    old_values = Column(JSON, nullable=True)  # Previous state (sensitive fields encrypted)
    new_values = Column(JSON, nullable=True)  # New state (sensitive fields encrypted)
    changes_summary = Column(Text, nullable=True)  # Human-readable summary of changes
    
    # Status and outcome
    status_code = Column(String(10), nullable=True)  # HTTP status code
    success = Column(String(10), nullable=False, default="SUCCESS", index=True)  # SUCCESS, FAILURE, ERROR
    error_message = Column(Text, nullable=True)
    
    # Classification
    severity = Column(Enum(AuditSeverity), nullable=False, default=AuditSeverity.LOW, index=True)
    category = Column(String(50), nullable=True, index=True)  # e.g., "SECURITY", "DATA", "SYSTEM"
    
    # Timestamps
    timestamp = Column(DateTime, default=func.now(), nullable=False, index=True)
    session_id = Column(String(255), nullable=True, index=True)
    
    # Compliance fields
    retention_days = Column(Integer, default=2555)  # Default 7 years retention
    compliance_tag = Column(String(50), nullable=True)  # e.g., "HIPAA", "GDPR"
    
    def encrypt_sensitive_data(self):
        """Encrypt sensitive data in old_values and new_values"""
        sensitive_fields = [
            'first_name', 'last_name', 'middle_name', 'date_of_birth',
            'phone_primary', 'phone_secondary', 'email', 'address',
            'national_id', 'ssn', 'passport_number', 'driver_license',
            'medical_record_number', 'policy_holder_name', 'policy_holder_ssn'
        ]
        
        def encrypt_dict(data):
            if not data or not isinstance(data, dict):
                return data
            
            encrypted_data = {}
            for key, value in data.items():
                if key in sensitive_fields:
                    if isinstance(value, (dict, list)):
                        import json
                        value = json.dumps(value)
                    encrypted_data[key] = encrypt_data(str(value))
                else:
                    encrypted_data[key] = value
            return encrypted_data
        
        if self.old_values:
            self.old_values = encrypt_dict(self.old_values)
        
        if self.new_values:
            self.new_values = encrypt_dict(self.new_values)
    
    def decrypt_sensitive_data(self):
        """Decrypt sensitive data in old_values and new_values"""
        def decrypt_dict(data):
            if not data or not isinstance(data, dict):
                return data
            
            decrypted_data = {}
            for key, value in data.items():
                try:
                    decrypted_value = decrypt_data(str(value))
                    # Try to parse as JSON for complex objects
                    import json
                    decrypted_data[key] = json.loads(decrypted_value)
                except (json.JSONDecodeError, ValueError):
                    decrypted_data[key] = decrypted_value
            return decrypted_data
        
        if self.old_values:
            try:
                self.old_values = decrypt_dict(self.old_values)
            except Exception:
                pass  # Keep original if decryption fails
        
        if self.new_values:
            try:
                self.new_values = decrypt_dict(self.new_values)
            except Exception:
                pass  # Keep original if decryption fails


class SystemEvent(Base):
    """System events and alerts"""
    __tablename__ = "system_events"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Event details
    event_type = Column(String(50), nullable=False, index=True)
    event_category = Column(String(50), nullable=False, index=True)  # SECURITY, PERFORMANCE, ERROR, INFO
    severity = Column(Enum(AuditSeverity), nullable=False, default=AuditSeverity.MEDIUM, index=True)
    
    # Event data
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    details = Column(JSON, nullable=True)
    
    # Source information
    source_service = Column(String(50), nullable=False, index=True)  # auth, patients, api, etc.
    source_host = Column(String(255), nullable=True)
    
    # Status
    status = Column(String(20), default="ACTIVE", index=True)  # ACTIVE, RESOLVED, SUPPRESSED
    resolution = Column(Text, nullable=True)
    resolved_at = Column(DateTime, nullable=True)
    resolved_by = Column(UUID(as_uuid=True), ForeignKey("users.id"))
    
    # Timestamps
    occurred_at = Column(DateTime, default=func.now(), nullable=False, index=True)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    
    # Relationships
    resolver = relationship("User", foreign_keys=[resolved_by])


class ComplianceReport(Base):
    """Compliance and regulatory reports"""
    __tablename__ = "compliance_reports"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Report details
    report_type = Column(String(50), nullable=False, index=True)  # HIPAA, GDPR, SOX, etc.
    report_name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    
    # Report period
    period_start = Column(DateTime, nullable=False)
    period_end = Column(DateTime, nullable=False)
    
    # Report content
    summary = Column(Text, nullable=True)
    findings = Column(JSON, nullable=True)
    recommendations = Column(JSON, nullable=True)
    metrics = Column(JSON, nullable=True)
    
    # Status
    status = Column(String(20), default="DRAFT", index=True)  # DRAFT, REVIEW, APPROVED, PUBLISHED
    version = Column(String(20), default="1.0")
    
    # Generation details
    generated_by = Column(UUID(as_uuid=True), ForeignKey("users.id"))
    generated_at = Column(DateTime, default=func.now())
    approved_by = Column(UUID(as_uuid=True), ForeignKey("users.id"))
    approved_at = Column(DateTime, nullable=True)
    
    # File information
    file_path = Column(String(500), nullable=True)
    file_format = Column(String(20), nullable=True)  # PDF, CSV, JSON
    file_size = Column(Integer, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    
    # Relationships
    generator = relationship("User", foreign_keys=[generated_by])
    approver = relationship("User", foreign_keys=[approved_by])


class DataAccessLog(Base):
    """Detailed data access logging for PII and sensitive data"""
    __tablename__ = "data_access_logs"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Access details
    resource_type = Column(Enum(AuditResource), nullable=False, index=True)
    resource_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    field_name = Column(String(100), nullable=False, index=True)  # Which specific field was accessed
    field_value_hash = Column(String(64), nullable=True)  # Hash of the value for integrity
    
    # User information
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True, index=True)
    user = relationship("User", foreign_keys=[user_id])
    username = Column(String(50), nullable=True, index=True)
    
    # Request details
    ip_address = Column(String(45), nullable=True, index=True)
    user_agent = Column(Text, nullable=True)
    endpoint = Column(String(255), nullable=True, index=True)
    
    # Access classification
    access_purpose = Column(String(100), nullable=True)  # Treatment, billing, operations, etc.
    legal_basis = Column(String(100), nullable=True)  # Consent, legal obligation, etc.
    data_sensitivity = Column(String(20), default="MEDIUM", index=True)  # LOW, MEDIUM, HIGH, CRITICAL
    
    # Timestamps
    accessed_at = Column(DateTime, default=func.now(), nullable=False, index=True)
    session_id = Column(String(255), nullable=True, index=True)
    
    # Retention
    retention_days = Column(Integer, default=2555)  # Default 7 years retention


class SecurityEvent(Base):
    """Security-specific events and incidents"""
    __tablename__ = "security_events"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Event details
    event_type = Column(String(50), nullable=False, index=True)  # LOGIN_FAILED, BRUTE_FORCE, etc.
    threat_level = Column(String(20), nullable=False, index=True)  # LOW, MEDIUM, HIGH, CRITICAL
    category = Column(String(50), nullable=False, index=True)  # AUTHENTICATION, AUTHORIZATION, DATA_BREACH, etc.
    
    # Event description
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    technical_details = Column(JSON, nullable=True)
    
    # Source/target information
    source_ip = Column(String(45), nullable=True, index=True)
    target_user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True, index=True)
    target_resource = Column(String(255), nullable=True)
    
    # Response and mitigation
    response_taken = Column(JSON, nullable=True)  # Actions taken to mitigate
    blocked = Column(Boolean, default=False, index=True)
    investigation_status = Column(String(20), default="OPEN", index=True)  # OPEN, INVESTIGATING, RESOLVED, CLOSED
    
    # Impact assessment
    impact_assessment = Column(Text, nullable=True)
    affected_users = Column(Integer, default=0)
    affected_resources = Column(Integer, default=0)
    
    # Investigation details
    investigated_by = Column(UUID(as_uuid=True), ForeignKey("users.id"))
    investigation_notes = Column(Text, nullable=True)
    resolution_details = Column(Text, nullable=True)
    
    # Timestamps
    occurred_at = Column(DateTime, default=func.now(), nullable=False, index=True)
    detected_at = Column(DateTime, default=func.now())
    resolved_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    
    # Relationships
    target_user = relationship("User", foreign_keys=[target_user_id])
    investigator = relationship("User", foreign_keys=[investigated_by])
