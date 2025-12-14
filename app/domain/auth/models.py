from sqlalchemy import Column, String, Boolean, DateTime, ForeignKey, JSON, Enum, Integer
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.infrastructure.database import Base
from app.infrastructure.encryption import encrypt_data, decrypt_data
import uuid
import enum


class UserRole(str, enum.Enum):
    """User roles in the hospital management system"""
    SUPER_ADMIN = "super_admin"
    ADMIN = "admin"
    DOCTOR = "doctor"
    NURSE = "nurse"
    RECEPTIONIST = "receptionist"
    LAB_TECHNICIAN = "lab_technician"
    PHARMACIST = "pharmacist"
    BILLING_STAFF = "billing_staff"
    MEDICAL_RECORDS_STAFF = "medical_records_staff"


class UserStatus(str, enum.Enum):
    """User account status"""
    ACTIVE = "active"
    INACTIVE = "inactive"
    SUSPENDED = "suspended"
    PENDING_VERIFICATION = "pending_verification"


class User(Base):
    """User model for authentication and authorization"""
    __tablename__ = "users"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    
    # Profile information (encrypted)
    first_name = Column(String(100), nullable=False)  # Will be encrypted
    last_name = Column(String(100), nullable=False)   # Will be encrypted
    phone = Column(String(20))                       # Will be encrypted
    
    # Role and permissions
    role = Column(Enum(UserRole), nullable=False, default=UserRole.RECEPTIONIST)
    permissions = Column(JSON, default=list)
    
    # Department association
    department_id = Column(UUID(as_uuid=True), ForeignKey("departments.id"))
    department = relationship("Department", back_populates="users")
    
    # Status and metadata
    is_active = Column(Boolean, default=True)
    status = Column(Enum(UserStatus), default=UserStatus.ACTIVE)
    is_verified = Column(Boolean, default=False)
    
    # Timestamps
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    last_login_at = Column(DateTime)
    password_changed_at = Column(DateTime, default=func.now())
    
    # Session management
    failed_login_attempts = Column(Integer, default=0)
    locked_until = Column(DateTime)
    
    def set_password(self, password: str):
        """Set password hash"""
        from app.core.security import get_password_hash
        self.password_hash = get_password_hash(password)
        self.password_changed_at = func.now()
    
    def verify_password(self, password: str) -> bool:
        """Verify password"""
        from app.core.security import verify_password
        return verify_password(password, self.password_hash)
    
    def get_permissions(self) -> list:
        """Get user permissions based on role and custom permissions"""
        role_permissions = self._get_role_permissions()
        custom_permissions = self.permissions or []
        return list(set(role_permissions + custom_permissions))
    
    def _get_role_permissions(self) -> list:
        """Get default permissions for user role"""
        from app.core.permissions import Permissions
        
        permission_map = {
            UserRole.SUPER_ADMIN: [
                Permissions.SYSTEM_ADMIN,
                Permissions.USERS_CREATE, Permissions.USERS_READ, Permissions.USERS_UPDATE, Permissions.USERS_DELETE,
                Permissions.PATIENTS_CREATE, Permissions.PATIENTS_READ, Permissions.PATIENTS_UPDATE, Permissions.PATIENTS_DELETE,
                Permissions.APPOINTMENTS_CREATE, Permissions.APPOINTMENTS_READ, Permissions.APPOINTMENTS_UPDATE, Permissions.APPOINTMENTS_DELETE,
                Permissions.EMR_CREATE, Permissions.EMR_READ, Permissions.EMR_UPDATE, Permissions.EMR_SIGN,
                Permissions.PRESCRIPTIONS_CREATE, Permissions.PRESCRIPTIONS_READ, Permissions.PRESCRIPTIONS_UPDATE, Permissions.PRESCRIPTIONS_VERIFY,
                Permissions.SCHEDULES_CREATE, Permissions.SCHEDULES_READ, Permissions.SCHEDULES_UPDATE, Permissions.SCHEDULES_DELETE,
                Permissions.LEAVES_CREATE, Permissions.LEAVES_READ, Permissions.LEAVES_APPROVE,
                Permissions.QUEUE_MANAGE, Permissions.QUEUE_READ,
                Permissions.AUDIT_READ
            ],
            UserRole.ADMIN: [
                Permissions.USERS_CREATE, Permissions.USERS_READ, Permissions.USERS_UPDATE,
                Permissions.PATIENTS_CREATE, Permissions.PATIENTS_READ, Permissions.PATIENTS_UPDATE, Permissions.PATIENTS_DELETE,
                Permissions.APPOINTMENTS_CREATE, Permissions.APPOINTMENTS_READ, Permissions.APPOINTMENTS_UPDATE,
                Permissions.EMR_READ,
                Permissions.PRESCRIPTIONS_READ,
                Permissions.SCHEDULES_CREATE, Permissions.SCHEDULES_READ, Permissions.SCHEDULES_UPDATE,
                Permissions.LEAVES_READ, Permissions.LEAVES_APPROVE,
                Permissions.QUEUE_READ,
                Permissions.AUDIT_READ
            ],
            UserRole.DOCTOR: [
                Permissions.PATIENTS_READ, Permissions.PATIENTS_READ_DEPARTMENT,
                Permissions.PATIENTS_UPDATE,
                Permissions.APPOINTMENTS_READ_OWN, Permissions.APPOINTMENTS_UPDATE,
                Permissions.EMR_CREATE, Permissions.EMR_READ, Permissions.EMR_UPDATE, Permissions.EMR_SIGN,
                Permissions.DIAGNOSES_CREATE, Permissions.DIAGNOSES_READ, Permissions.DIAGNOSES_UPDATE,
                Permissions.PROCEDURES_CREATE, Permissions.PROCEDURES_READ, Permissions.PROCEDURES_UPDATE,
                Permissions.CLINICAL_NOTES_CREATE, Permissions.CLINICAL_NOTES_READ, Permissions.CLINICAL_NOTES_UPDATE, Permissions.CLINICAL_NOTES_SIGN,
                Permissions.PRESCRIPTIONS_CREATE, Permissions.PRESCRIPTIONS_READ, Permissions.PRESCRIPTIONS_UPDATE,
                Permissions.LEAVES_CREATE, Permissions.LEAVES_READ,
                Permissions.QUEUE_MANAGE, Permissions.QUEUE_READ
            ],
            UserRole.NURSE: [
                Permissions.PATIENTS_READ, Permissions.PATIENTS_READ_DEPARTMENT,
                Permissions.PATIENTS_UPDATE,
                Permissions.APPOINTMENTS_READ, Permissions.APPOINTMENTS_UPDATE,
                Permissions.EMR_READ, Permissions.EMR_UPDATE_VITALS,
                Permissions.PRESCRIPTIONS_READ,
                Permissions.CLINICAL_NOTES_READ,
                Permissions.QUEUE_MANAGE, Permissions.QUEUE_READ
            ],
            UserRole.RECEPTIONIST: [
                Permissions.PATIENTS_CREATE, Permissions.PATIENTS_READ,
                Permissions.APPOINTMENTS_CREATE, Permissions.APPOINTMENTS_READ, Permissions.APPOINTMENTS_UPDATE,
                Permissions.SCHEDULES_READ,
                Permissions.QUEUE_MANAGE, Permissions.QUEUE_READ
            ],
            UserRole.LAB_TECHNICIAN: [
                Permissions.PATIENTS_READ, Permissions.PATIENTS_READ_DEPARTMENT,
                Permissions.EMR_READ,
                Permissions.PRESCRIPTIONS_READ
            ],
            UserRole.PHARMACIST: [
                Permissions.PATIENTS_READ, Permissions.PATIENTS_READ_DEPARTMENT,
                Permissions.PRESCRIPTIONS_READ, Permissions.PRESCRIPTIONS_VERIFY,
                Permissions.EMR_READ
            ],
            UserRole.BILLING_STAFF: [
                Permissions.PATIENTS_READ, Permissions.PATIENTS_READ_DEPARTMENT,
                Permissions.APPOINTMENTS_READ,
                Permissions.EMR_READ,
                Permissions.PRESCRIPTIONS_READ
            ],
            UserRole.MEDICAL_RECORDS_STAFF: [
                Permissions.PATIENTS_READ, Permissions.PATIENTS_UPDATE,
                Permissions.EMR_READ,
                Permissions.PRESCRIPTIONS_READ,
                Permissions.CLINICAL_NOTES_READ
            ]
        }
        
        return permission_map.get(self.role, [])
    
    def encrypt_sensitive_data(self):
        """Encrypt sensitive fields"""
        if self.first_name:
            self.first_name = encrypt_data(self.first_name)
        if self.last_name:
            self.last_name = encrypt_data(self.last_name)
        if self.phone:
            self.phone = encrypt_data(self.phone)
    
    def decrypt_sensitive_data(self):
        """Decrypt sensitive fields"""
        if self.first_name:
            self.first_name = decrypt_data(self.first_name)
        if self.last_name:
            self.last_name = decrypt_data(self.last_name)
        if self.phone:
            self.phone = decrypt_data(self.phone)


class UserSession(Base):
    """User session model for tracking active sessions"""
    __tablename__ = "user_sessions"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    user = relationship("User", back_populates="sessions")
    
    session_token = Column(String(255), unique=True, nullable=False, index=True)
    refresh_token = Column(String(255), unique=True, nullable=False, index=True)
    
    ip_address = Column(String(45))
    user_agent = Column(String(500))
    
    is_active = Column(Boolean, default=True)
    expires_at = Column(DateTime, nullable=False)
    created_at = Column(DateTime, default=func.now())
    last_accessed_at = Column(DateTime, default=func.now())
    
    def is_expired(self) -> bool:
        """Check if session is expired"""
        from datetime import datetime
        return datetime.utcnow() > self.expires_at
    
    def revoke(self):
        """Revoke the session"""
        self.is_active = False


class Department(Base):
    """Department model for hospital organization"""
    __tablename__ = "departments"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(200), nullable=False, unique=True)
    code = Column(String(20), unique=True, nullable=False)
    description = Column(String(500))
    
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    
    users = relationship("User", back_populates="department")


# Add relationship to User model
User.sessions = relationship("UserSession", back_populates="user", cascade="all, delete-orphan")
