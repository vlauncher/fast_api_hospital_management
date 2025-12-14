"""
Appointments Domain Models

Implements the database models for:
- Appointment scheduling
- Doctor schedules and availability
- Doctor leaves/unavailability
- Patient queue management
"""

from sqlalchemy import (
    Column, String, Date, Boolean, DateTime, ForeignKey, 
    Integer, Time, Text, Enum, CheckConstraint, UniqueConstraint
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.infrastructure.database import Base
import uuid
import enum


class AppointmentStatus(str, enum.Enum):
    """Appointment status enumeration"""
    SCHEDULED = "SCHEDULED"
    CONFIRMED = "CONFIRMED"
    CHECKED_IN = "CHECKED_IN"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"
    NO_SHOW = "NO_SHOW"
    RESCHEDULED = "RESCHEDULED"


class AppointmentType(str, enum.Enum):
    """Type of appointment"""
    NEW_CONSULTATION = "NEW_CONSULTATION"
    FOLLOW_UP = "FOLLOW_UP"
    EMERGENCY = "EMERGENCY"
    ROUTINE_CHECKUP = "ROUTINE_CHECKUP"
    SPECIALIST_REFERRAL = "SPECIALIST_REFERRAL"
    LAB_VISIT = "LAB_VISIT"
    PROCEDURE = "PROCEDURE"
    VACCINATION = "VACCINATION"
    TELEHEALTH = "TELEHEALTH"


class LeaveType(str, enum.Enum):
    """Type of doctor leave"""
    ANNUAL = "ANNUAL"
    SICK = "SICK"
    EMERGENCY = "EMERGENCY"
    CONFERENCE = "CONFERENCE"
    TRAINING = "TRAINING"
    PERSONAL = "PERSONAL"
    OTHER = "OTHER"


class LeaveStatus(str, enum.Enum):
    """Status of leave request"""
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    CANCELLED = "CANCELLED"


class QueueType(str, enum.Enum):
    """Type of queue"""
    WALK_IN = "WALK_IN"
    SCHEDULED = "SCHEDULED"
    EMERGENCY = "EMERGENCY"


class QueueStatus(str, enum.Enum):
    """Queue status"""
    WAITING = "WAITING"
    CALLED = "CALLED"
    IN_CONSULTATION = "IN_CONSULTATION"
    COMPLETED = "COMPLETED"
    LEFT = "LEFT"
    SKIPPED = "SKIPPED"


class DoctorSchedule(Base):
    """Doctor schedule model for managing doctor availability"""
    __tablename__ = "doctor_schedules"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    doctor_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    
    # Day of week (0=Monday, 6=Sunday)
    day_of_week = Column(Integer, nullable=False)
    start_time = Column(Time, nullable=False)
    end_time = Column(Time, nullable=False)
    
    # Slot configuration
    slot_duration_minutes = Column(Integer, default=30)
    max_patients_per_slot = Column(Integer, default=1)
    
    # Break times (stored as JSON-like intervals)
    break_start = Column(Time)
    break_end = Column(Time)
    
    # Validity period
    effective_from = Column(Date, nullable=False)
    effective_until = Column(Date)
    
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    
    # Relationships
    doctor = relationship("User", foreign_keys=[doctor_id])
    
    __table_args__ = (
        CheckConstraint('day_of_week >= 0 AND day_of_week <= 6', name='check_day_of_week'),
        CheckConstraint('start_time < end_time', name='check_time_order'),
    )


class DoctorLeave(Base):
    """Doctor leave/unavailability model"""
    __tablename__ = "doctor_leaves"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    doctor_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    
    leave_type = Column(Enum(LeaveType), nullable=False, default=LeaveType.ANNUAL)
    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=False)
    start_time = Column(Time)  # Optional: for partial day leaves
    end_time = Column(Time)    # Optional: for partial day leaves
    
    reason = Column(Text)
    status = Column(Enum(LeaveStatus), default=LeaveStatus.PENDING)
    
    approved_by = Column(UUID(as_uuid=True), ForeignKey("users.id"))
    approved_at = Column(DateTime)
    rejection_reason = Column(Text)
    
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    
    # Relationships
    doctor = relationship("User", foreign_keys=[doctor_id])
    approver = relationship("User", foreign_keys=[approved_by])
    
    __table_args__ = (
        CheckConstraint('start_date <= end_date', name='check_leave_dates'),
    )


class Appointment(Base):
    """Appointment model for patient-doctor appointments"""
    __tablename__ = "appointments"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    appointment_number = Column(String(50), unique=True, nullable=False, index=True)
    
    # Patient and doctor
    patient_id = Column(UUID(as_uuid=True), ForeignKey("patients.id"), nullable=False)
    doctor_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    department_id = Column(UUID(as_uuid=True), ForeignKey("departments.id"))
    
    # Scheduling
    appointment_date = Column(Date, nullable=False, index=True)
    appointment_time = Column(Time, nullable=False)
    slot_duration = Column(Integer, default=30)
    
    # Type and status
    appointment_type = Column(Enum(AppointmentType), nullable=False, default=AppointmentType.NEW_CONSULTATION)
    status = Column(Enum(AppointmentStatus), default=AppointmentStatus.SCHEDULED)
    
    # Priority and flags
    is_emergency = Column(Boolean, default=False)
    priority = Column(Integer, default=3)  # 1=Highest, 5=Lowest
    
    # Visit details
    reason = Column(Text)
    symptoms = Column(Text)
    notes = Column(Text)
    
    # Check-in tracking
    checked_in_at = Column(DateTime)
    checked_in_by = Column(UUID(as_uuid=True), ForeignKey("users.id"))
    
    # Cancellation
    cancelled_at = Column(DateTime)
    cancelled_by = Column(UUID(as_uuid=True), ForeignKey("users.id"))
    cancelled_reason = Column(Text)
    
    # Rescheduling
    rescheduled_from = Column(UUID(as_uuid=True), ForeignKey("appointments.id"))
    rescheduled_to = Column(UUID(as_uuid=True))
    
    # Notifications
    reminder_sent = Column(Boolean, default=False)
    reminder_sent_at = Column(DateTime)
    confirmation_sent = Column(Boolean, default=False)
    
    # Audit
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    created_by = Column(UUID(as_uuid=True), ForeignKey("users.id"))
    
    # Relationships
    patient = relationship("Patient", back_populates="appointments")
    doctor = relationship("User", foreign_keys=[doctor_id])
    department = relationship("Department", foreign_keys=[department_id])
    checked_in_user = relationship("User", foreign_keys=[checked_in_by])
    cancelled_user = relationship("User", foreign_keys=[cancelled_by])
    creator = relationship("User", foreign_keys=[created_by])
    rescheduled_appointment = relationship("Appointment", foreign_keys=[rescheduled_from], remote_side=[id])
    queue_entries = relationship("Queue", back_populates="appointment")
    
    def get_datetime(self):
        """Get appointment datetime"""
        from datetime import datetime
        return datetime.combine(self.appointment_date, self.appointment_time)


class Queue(Base):
    """Queue model for patient queue management"""
    __tablename__ = "queues"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # References
    appointment_id = Column(UUID(as_uuid=True), ForeignKey("appointments.id"))
    patient_id = Column(UUID(as_uuid=True), ForeignKey("patients.id"), nullable=False)
    doctor_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    department_id = Column(UUID(as_uuid=True), ForeignKey("departments.id"))
    
    # Queue info
    queue_number = Column(Integer, nullable=False)
    queue_date = Column(Date, nullable=False, index=True)
    queue_type = Column(Enum(QueueType), nullable=False, default=QueueType.SCHEDULED)
    
    # Status tracking
    status = Column(Enum(QueueStatus), default=QueueStatus.WAITING)
    checked_in_at = Column(DateTime, default=func.now())
    called_at = Column(DateTime)
    completed_at = Column(DateTime)
    
    # Priority
    priority = Column(Integer, default=3)
    is_emergency = Column(Boolean, default=False)
    
    # Estimated wait time (in minutes)
    estimated_wait_time = Column(Integer)
    actual_wait_time = Column(Integer)
    
    notes = Column(Text)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    
    # Relationships
    appointment = relationship("Appointment", back_populates="queue_entries")
    patient = relationship("Patient")
    doctor = relationship("User", foreign_keys=[doctor_id])
    department = relationship("Department", foreign_keys=[department_id])
    
    __table_args__ = (
        UniqueConstraint('doctor_id', 'queue_date', 'queue_number', name='unique_queue_number_per_doctor_date'),
    )
