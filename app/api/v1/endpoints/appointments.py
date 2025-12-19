from typing import Any, List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.api import deps
from app.db.session import get_db
from app.models.appointment import Appointment, AppointmentStatus
from app.models.patient import Patient
from app.models.doctor import Doctor
from app.models.user import User, UserRole
from app.schemas import appointment as appointment_schema
from app.services import ai_service

router = APIRouter()

@router.post("/", response_model=appointment_schema.Appointment)
async def create_appointment(
    *,
    db: AsyncSession = Depends(get_db),
    appointment_in: appointment_schema.AppointmentCreate,
    current_user: User = Depends(deps.get_current_active_user),
) -> Any:
    """
    Create new appointment.
    """
    # Get patient profile for current user
    result = await db.execute(select(Patient).where(Patient.user_id == current_user.id))
    patient = result.scalars().first()
    if not patient:
        raise HTTPException(status_code=400, detail="Patient profile required to book appointment")
    
    # Check if doctor exists
    result = await db.execute(select(Doctor).where(Doctor.id == appointment_in.doctor_id))
    doctor = result.scalars().first()
    if not doctor:
        raise HTTPException(status_code=404, detail="Doctor not found")
    
    # AI Analysis
    ai_analysis = {}
    if appointment_in.symptoms:
        ai_analysis = await ai_service.analyze_symptoms(appointment_in.symptoms)

    appointment = Appointment(
        **appointment_in.model_dump(),
        patient_id=patient.id,
        status=AppointmentStatus.SCHEDULED,
        ai_preliminary_analysis=ai_analysis
    )
    
    # Simple check for virtual meeting link if is_virtual is true
    if appointment.is_virtual:
        appointment.meeting_link = f"https://telemedicine.hospital.com/{appointment.id}"
    
    db.add(appointment)
    await db.commit()
    await db.refresh(appointment)
    return appointment

@router.get("/my-appointments", response_model=List[appointment_schema.Appointment])
async def read_my_appointments(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(deps.get_current_active_user),
) -> Any:
    """
    Get all appointments for the current user (as patient or doctor).
    """
    if current_user.role == UserRole.PATIENT:
        result = await db.execute(select(Patient).where(Patient.user_id == current_user.id))
        patient = result.scalars().first()
        if not patient:
            return []
        result = await db.execute(select(Appointment).where(Appointment.patient_id == patient.id))
    elif current_user.role == UserRole.DOCTOR:
        result = await db.execute(select(Doctor).where(Doctor.user_id == current_user.id))
        doctor = result.scalars().first()
        if not doctor:
            return []
        result = await db.execute(select(Appointment).where(Appointment.doctor_id == doctor.id))
    else:
        # Admin or other staff?
        result = await db.execute(select(Appointment))
        
    appointments = result.scalars().all()
    return appointments

@router.put("/{appointment_id}", response_model=appointment_schema.Appointment)
async def update_appointment(
    appointment_id: str,
    *,
    db: AsyncSession = Depends(get_db),
    appointment_in: appointment_schema.AppointmentUpdate,
    current_user: User = Depends(deps.get_current_active_user),
) -> Any:
    """
    Update appointment status or notes.
    """
    result = await db.execute(select(Appointment).where(Appointment.id == appointment_id))
    appointment = result.scalars().first()
    if not appointment:
        raise HTTPException(status_code=404, detail="Appointment not found")
    
    # Permission check: patient can only cancel, doctor/admin can update all
    # For now, simple update
    update_data = appointment_in.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(appointment, field, value)
    
    db.add(appointment)
    await db.commit()
    await db.refresh(appointment)
    return appointment
