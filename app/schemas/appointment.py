from typing import Optional
from pydantic import BaseModel
from datetime import date, time
from uuid import UUID
from app.models.appointment import AppointmentStatus

class AppointmentBase(BaseModel):
    doctor_id: UUID
    appointment_date: date
    appointment_time: time
    duration_minutes: Optional[int] = 30
    reason: Optional[str] = None
    symptoms: Optional[str] = None
    is_virtual: Optional[bool] = False

class AppointmentCreate(AppointmentBase):
    pass

class AppointmentUpdate(BaseModel):
    status: Optional[AppointmentStatus] = None
    notes: Optional[str] = None
    appointment_date: Optional[date] = None
    appointment_time: Optional[time] = None
    meeting_link: Optional[str] = None

class AppointmentInDBBase(AppointmentBase):
    id: UUID
    patient_id: UUID
    status: AppointmentStatus
    ai_preliminary_analysis: Optional[dict] = {}
    notes: Optional[str] = None
    meeting_link: Optional[str] = None

    class Config:
        from_attributes = True

class Appointment(AppointmentInDBBase):
    pass
