"""
Appointments API Schemas

Pydantic models for appointment-related API requests and responses.
"""

from pydantic import BaseModel, Field, validator
from typing import Optional, List, Dict, Any
from datetime import datetime, date, time
import uuid
from app.domain.appointments.models import (
    AppointmentStatus, AppointmentType,
    LeaveType, LeaveStatus,
    QueueType, QueueStatus
)


# ==================== Doctor Schedule Schemas ====================

class DoctorScheduleBase(BaseModel):
    """Base schema for doctor schedule"""
    day_of_week: int = Field(..., ge=0, le=6, description="Day of week (0=Monday, 6=Sunday)")
    start_time: time
    end_time: time
    slot_duration_minutes: int = Field(30, ge=10, le=120)
    max_patients_per_slot: int = Field(1, ge=1, le=10)
    break_start: Optional[time] = None
    break_end: Optional[time] = None


class DoctorScheduleCreate(DoctorScheduleBase):
    """Schema for creating doctor schedule"""
    doctor_id: uuid.UUID
    effective_from: date
    effective_until: Optional[date] = None
    
    @validator('end_time')
    def validate_time_order(cls, v, values):
        if 'start_time' in values and v <= values['start_time']:
            raise ValueError('End time must be after start time')
        return v


class DoctorScheduleUpdate(BaseModel):
    """Schema for updating doctor schedule"""
    start_time: Optional[time] = None
    end_time: Optional[time] = None
    slot_duration_minutes: Optional[int] = Field(None, ge=10, le=120)
    max_patients_per_slot: Optional[int] = Field(None, ge=1, le=10)
    break_start: Optional[time] = None
    break_end: Optional[time] = None
    effective_until: Optional[date] = None
    is_active: Optional[bool] = None


class DoctorScheduleResponse(DoctorScheduleBase):
    """Schema for doctor schedule response"""
    id: uuid.UUID
    doctor_id: uuid.UUID
    effective_from: date
    effective_until: Optional[date] = None
    is_active: bool
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


# ==================== Doctor Leave Schemas ====================

class DoctorLeaveBase(BaseModel):
    """Base schema for doctor leave"""
    leave_type: LeaveType
    start_date: date
    end_date: date
    start_time: Optional[time] = None
    end_time: Optional[time] = None
    reason: Optional[str] = Field(None, max_length=1000)


class DoctorLeaveCreate(DoctorLeaveBase):
    """Schema for creating leave request"""
    doctor_id: uuid.UUID
    
    @validator('end_date')
    def validate_dates(cls, v, values):
        if 'start_date' in values and v < values['start_date']:
            raise ValueError('End date must be on or after start date')
        return v


class DoctorLeaveUpdate(BaseModel):
    """Schema for updating leave request"""
    leave_type: Optional[LeaveType] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    reason: Optional[str] = None


class DoctorLeaveApproval(BaseModel):
    """Schema for leave approval"""
    approved: bool
    rejection_reason: Optional[str] = None


class DoctorLeaveResponse(DoctorLeaveBase):
    """Schema for leave response"""
    id: uuid.UUID
    doctor_id: uuid.UUID
    status: LeaveStatus
    approved_by: Optional[uuid.UUID] = None
    approved_at: Optional[datetime] = None
    rejection_reason: Optional[str] = None
    created_at: datetime
    
    class Config:
        from_attributes = True


# ==================== Appointment Schemas ====================

class AppointmentBase(BaseModel):
    """Base schema for appointment"""
    appointment_type: AppointmentType
    reason: Optional[str] = Field(None, max_length=1000)
    symptoms: Optional[str] = Field(None, max_length=2000)
    notes: Optional[str] = None
    is_emergency: bool = False
    priority: int = Field(3, ge=1, le=5)


class AppointmentCreate(AppointmentBase):
    """Schema for creating appointment"""
    patient_id: uuid.UUID
    doctor_id: uuid.UUID
    department_id: Optional[uuid.UUID] = None
    appointment_date: date
    appointment_time: time
    
    @validator('appointment_date')
    def validate_date(cls, v):
        if v < date.today():
            raise ValueError('Appointment date cannot be in the past')
        return v


class AppointmentUpdate(BaseModel):
    """Schema for updating appointment"""
    appointment_type: Optional[AppointmentType] = None
    reason: Optional[str] = None
    symptoms: Optional[str] = None
    notes: Optional[str] = None
    is_emergency: Optional[bool] = None
    priority: Optional[int] = Field(None, ge=1, le=5)


class AppointmentReschedule(BaseModel):
    """Schema for rescheduling appointment"""
    new_date: date
    new_time: time
    
    @validator('new_date')
    def validate_date(cls, v):
        if v < date.today():
            raise ValueError('New appointment date cannot be in the past')
        return v


class AppointmentCancel(BaseModel):
    """Schema for cancelling appointment"""
    reason: str = Field(..., min_length=1, max_length=500)


class AppointmentResponse(AppointmentBase):
    """Schema for appointment response"""
    id: uuid.UUID
    appointment_number: str
    patient_id: uuid.UUID
    doctor_id: uuid.UUID
    department_id: Optional[uuid.UUID] = None
    appointment_date: date
    appointment_time: time
    slot_duration: int
    status: AppointmentStatus
    checked_in_at: Optional[datetime] = None
    cancelled_at: Optional[datetime] = None
    cancelled_reason: Optional[str] = None
    reminder_sent: bool
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class AppointmentListResponse(BaseModel):
    """Schema for paginated appointment list"""
    items: List[AppointmentResponse]
    total: int
    page: int
    limit: int
    pages: int


class AvailableSlot(BaseModel):
    """Schema for available time slot"""
    time: str
    available_slots: int
    duration_minutes: int


class AvailableSlotsResponse(BaseModel):
    """Schema for available slots response"""
    doctor_id: uuid.UUID
    date: date
    slots: List[AvailableSlot]


# ==================== Queue Schemas ====================

class QueueCreate(BaseModel):
    """Schema for creating queue entry (walk-in)"""
    patient_id: uuid.UUID
    doctor_id: uuid.UUID
    department_id: Optional[uuid.UUID] = None
    is_emergency: bool = False
    notes: Optional[str] = None


class QueueResponse(BaseModel):
    """Schema for queue response"""
    id: uuid.UUID
    appointment_id: Optional[uuid.UUID] = None
    patient_id: uuid.UUID
    doctor_id: uuid.UUID
    department_id: Optional[uuid.UUID] = None
    queue_number: int
    queue_date: date
    queue_type: QueueType
    status: QueueStatus
    priority: int
    is_emergency: bool
    checked_in_at: datetime
    called_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    estimated_wait_time: Optional[int] = None
    actual_wait_time: Optional[int] = None
    notes: Optional[str] = None
    
    class Config:
        from_attributes = True


class QueueListResponse(BaseModel):
    """Schema for queue list response"""
    doctor_id: uuid.UUID
    queue_date: date
    waiting_count: int
    items: List[QueueResponse]
