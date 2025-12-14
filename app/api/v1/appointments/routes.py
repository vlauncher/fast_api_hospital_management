"""
Appointments API Routes

API endpoints for appointment scheduling, doctor schedules, and queue management.
"""

from fastapi import APIRouter, Depends, HTTPException, status, Query, Request
from typing import List, Optional
from datetime import date, time
import uuid
import math

from app.infrastructure.database import get_db
from app.core.permissions import require_permissions, Permissions
from app.domain.appointments.service import (
    AppointmentService, DoctorScheduleService, 
    DoctorLeaveService, QueueService
)
from app.domain.appointments.models import (
    AppointmentStatus, AppointmentType,
    LeaveStatus, QueueStatus
)
from app.api.v1.appointments.schemas import (
    # Schedule schemas
    DoctorScheduleCreate, DoctorScheduleUpdate, DoctorScheduleResponse,
    # Leave schemas
    DoctorLeaveCreate, DoctorLeaveUpdate, DoctorLeaveApproval, DoctorLeaveResponse,
    # Appointment schemas
    AppointmentCreate, AppointmentUpdate, AppointmentReschedule,
    AppointmentCancel, AppointmentResponse, AppointmentListResponse,
    AvailableSlotsResponse, AvailableSlot,
    # Queue schemas
    QueueCreate, QueueResponse, QueueListResponse
)

router = APIRouter()


# ==================== Doctor Schedule Endpoints ====================

@router.post("/schedules", response_model=DoctorScheduleResponse, status_code=status.HTTP_201_CREATED)
def create_doctor_schedule(
    schedule_data: DoctorScheduleCreate,
    request: Request,
    db = Depends(get_db),
    current_user = Depends(require_permissions([Permissions.SYSTEM_ADMIN, "schedules:create"]))
):
    """Create a new doctor schedule"""
    service = DoctorScheduleService(db)
    schedule = service.create_schedule(
        doctor_id=schedule_data.doctor_id,
        day_of_week=schedule_data.day_of_week,
        start_time=schedule_data.start_time,
        end_time=schedule_data.end_time,
        effective_from=schedule_data.effective_from,
        slot_duration_minutes=schedule_data.slot_duration_minutes,
        max_patients_per_slot=schedule_data.max_patients_per_slot,
        break_start=schedule_data.break_start,
        break_end=schedule_data.break_end,
        effective_until=schedule_data.effective_until
    )
    return schedule


@router.get("/schedules/doctor/{doctor_id}", response_model=List[DoctorScheduleResponse])
def get_doctor_schedules(
    doctor_id: uuid.UUID,
    active_only: bool = Query(True),
    db = Depends(get_db),
    current_user = Depends(require_permissions([Permissions.PATIENTS_READ, "schedules:read"]))
):
    """Get all schedules for a doctor"""
    service = DoctorScheduleService(db)
    return service.get_doctor_schedules(doctor_id, active_only)


@router.patch("/schedules/{schedule_id}", response_model=DoctorScheduleResponse)
def update_doctor_schedule(
    schedule_id: uuid.UUID,
    update_data: DoctorScheduleUpdate,
    db = Depends(get_db),
    current_user = Depends(require_permissions([Permissions.SYSTEM_ADMIN, "schedules:update"]))
):
    """Update doctor schedule"""
    service = DoctorScheduleService(db)
    schedule = service.update_schedule(schedule_id, update_data.model_dump(exclude_unset=True))
    if not schedule:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Schedule not found"
        )
    return schedule


@router.delete("/schedules/{schedule_id}", status_code=status.HTTP_204_NO_CONTENT)
def deactivate_schedule(
    schedule_id: uuid.UUID,
    db = Depends(get_db),
    current_user = Depends(require_permissions([Permissions.SYSTEM_ADMIN, "schedules:delete"]))
):
    """Deactivate a doctor schedule"""
    service = DoctorScheduleService(db)
    if not service.deactivate_schedule(schedule_id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Schedule not found"
        )


# ==================== Doctor Leave Endpoints ====================

@router.post("/leaves", response_model=DoctorLeaveResponse, status_code=status.HTTP_201_CREATED)
def request_doctor_leave(
    leave_data: DoctorLeaveCreate,
    request: Request,
    db = Depends(get_db),
    current_user = Depends(require_permissions([Permissions.PATIENTS_READ, "leaves:create"]))
):
    """Request doctor leave"""
    service = DoctorLeaveService(db)
    leave = service.request_leave(
        doctor_id=leave_data.doctor_id,
        leave_type=leave_data.leave_type,
        start_date=leave_data.start_date,
        end_date=leave_data.end_date,
        reason=leave_data.reason,
        start_time=leave_data.start_time,
        end_time=leave_data.end_time
    )
    return leave


@router.get("/leaves/doctor/{doctor_id}", response_model=List[DoctorLeaveResponse])
def get_doctor_leaves(
    doctor_id: uuid.UUID,
    status_filter: Optional[LeaveStatus] = None,
    db = Depends(get_db),
    current_user = Depends(require_permissions([Permissions.PATIENTS_READ, "leaves:read"]))
):
    """Get all leaves for a doctor"""
    service = DoctorLeaveService(db)
    return service.get_doctor_leaves(doctor_id, status_filter)


@router.post("/leaves/{leave_id}/approve", response_model=DoctorLeaveResponse)
def process_leave_approval(
    leave_id: uuid.UUID,
    approval: DoctorLeaveApproval,
    request: Request,
    db = Depends(get_db),
    current_user = Depends(require_permissions([Permissions.SYSTEM_ADMIN, "leaves:approve"]))
):
    """Approve or reject a leave request"""
    service = DoctorLeaveService(db)
    
    if approval.approved:
        return service.approve_leave(leave_id, uuid.UUID(current_user["sub"]))
    else:
        if not approval.rejection_reason:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Rejection reason is required"
            )
        return service.reject_leave(leave_id, uuid.UUID(current_user["sub"]), approval.rejection_reason)


@router.post("/leaves/{leave_id}/cancel", response_model=DoctorLeaveResponse)
def cancel_leave(
    leave_id: uuid.UUID,
    db = Depends(get_db),
    current_user = Depends(require_permissions([Permissions.PATIENTS_READ, "leaves:cancel"]))
):
    """Cancel a leave request"""
    service = DoctorLeaveService(db)
    return service.cancel_leave(leave_id)


# ==================== Appointment Endpoints ====================

@router.post("", response_model=AppointmentResponse, status_code=status.HTTP_201_CREATED)
def create_appointment(
    appointment_data: AppointmentCreate,
    request: Request,
    db = Depends(get_db),
    current_user = Depends(require_permissions([Permissions.PATIENTS_CREATE, "appointments:create"]))
):
    """Book a new appointment"""
    service = AppointmentService(db)
    appointment = service.create_appointment(
        patient_id=appointment_data.patient_id,
        doctor_id=appointment_data.doctor_id,
        appointment_date=appointment_data.appointment_date,
        appointment_time=appointment_data.appointment_time,
        appointment_type=appointment_data.appointment_type,
        created_by=uuid.UUID(current_user["sub"]),
        department_id=appointment_data.department_id,
        reason=appointment_data.reason,
        symptoms=appointment_data.symptoms,
        is_emergency=appointment_data.is_emergency,
        priority=appointment_data.priority
    )
    return appointment


@router.get("", response_model=AppointmentListResponse)
def list_appointments(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    patient_id: Optional[uuid.UUID] = None,
    doctor_id: Optional[uuid.UUID] = None,
    department_id: Optional[uuid.UUID] = None,
    status_filter: Optional[AppointmentStatus] = Query(None, alias="status"),
    appointment_type: Optional[AppointmentType] = None,
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
    is_emergency: Optional[bool] = None,
    db = Depends(get_db),
    current_user = Depends(require_permissions([Permissions.PATIENTS_READ, "appointments:read"]))
):
    """List appointments with filtering and pagination"""
    service = AppointmentService(db)
    skip = (page - 1) * limit
    
    appointments, total = service.get_appointments(
        skip=skip,
        limit=limit,
        patient_id=patient_id,
        doctor_id=doctor_id,
        department_id=department_id,
        status=status_filter,
        appointment_type=appointment_type,
        date_from=date_from,
        date_to=date_to,
        is_emergency=is_emergency
    )
    
    return AppointmentListResponse(
        items=appointments,
        total=total,
        page=page,
        limit=limit,
        pages=math.ceil(total / limit) if total > 0 else 1
    )


@router.get("/today", response_model=List[AppointmentResponse])
def get_today_appointments(
    doctor_id: Optional[uuid.UUID] = None,
    department_id: Optional[uuid.UUID] = None,
    db = Depends(get_db),
    current_user = Depends(require_permissions([Permissions.PATIENTS_READ, "appointments:read"]))
):
    """Get today's appointments"""
    service = AppointmentService(db)
    return service.get_today_appointments(doctor_id, department_id)


@router.get("/available-slots", response_model=AvailableSlotsResponse)
def get_available_slots(
    doctor_id: uuid.UUID,
    target_date: date,
    db = Depends(get_db)
):
    """Get available time slots for a doctor on a specific date (public endpoint)"""
    service = AppointmentService(db)
    slots = service.get_available_slots(doctor_id, target_date)
    
    return AvailableSlotsResponse(
        doctor_id=doctor_id,
        date=target_date,
        slots=[AvailableSlot(**slot) for slot in slots]
    )


@router.get("/{appointment_id}", response_model=AppointmentResponse)
def get_appointment(
    appointment_id: uuid.UUID,
    db = Depends(get_db),
    current_user = Depends(require_permissions([Permissions.PATIENTS_READ, "appointments:read"]))
):
    """Get appointment by ID"""
    service = AppointmentService(db)
    return service.get_appointment(appointment_id)


@router.patch("/{appointment_id}", response_model=AppointmentResponse)
def update_appointment(
    appointment_id: uuid.UUID,
    update_data: AppointmentUpdate,
    db = Depends(get_db),
    current_user = Depends(require_permissions([Permissions.PATIENTS_UPDATE, "appointments:update"]))
):
    """Update appointment"""
    service = AppointmentService(db)
    return service.update_appointment(appointment_id, update_data.model_dump(exclude_unset=True))


@router.post("/{appointment_id}/confirm", response_model=AppointmentResponse)
def confirm_appointment(
    appointment_id: uuid.UUID,
    db = Depends(get_db),
    current_user = Depends(require_permissions([Permissions.PATIENTS_UPDATE, "appointments:update"]))
):
    """Confirm an appointment"""
    service = AppointmentService(db)
    return service.confirm_appointment(appointment_id)


@router.post("/{appointment_id}/check-in", response_model=dict)
def check_in_patient(
    appointment_id: uuid.UUID,
    request: Request,
    db = Depends(get_db),
    current_user = Depends(require_permissions([Permissions.PATIENTS_UPDATE, "appointments:update"]))
):
    """Check in patient for appointment"""
    service = AppointmentService(db)
    appointment, queue = service.check_in_patient(
        appointment_id, 
        uuid.UUID(current_user["sub"])
    )
    
    return {
        "appointment": AppointmentResponse.model_validate(appointment),
        "queue": QueueResponse.model_validate(queue)
    }


@router.post("/{appointment_id}/cancel", response_model=AppointmentResponse)
def cancel_appointment(
    appointment_id: uuid.UUID,
    cancel_data: AppointmentCancel,
    request: Request,
    db = Depends(get_db),
    current_user = Depends(require_permissions([Permissions.PATIENTS_UPDATE, "appointments:delete"]))
):
    """Cancel an appointment"""
    service = AppointmentService(db)
    return service.cancel_appointment(
        appointment_id,
        uuid.UUID(current_user["sub"]),
        cancel_data.reason
    )


@router.post("/{appointment_id}/reschedule", response_model=AppointmentResponse)
def reschedule_appointment(
    appointment_id: uuid.UUID,
    reschedule_data: AppointmentReschedule,
    request: Request,
    db = Depends(get_db),
    current_user = Depends(require_permissions([Permissions.PATIENTS_UPDATE, "appointments:update"]))
):
    """Reschedule an appointment"""
    service = AppointmentService(db)
    return service.reschedule_appointment(
        appointment_id,
        reschedule_data.new_date,
        reschedule_data.new_time,
        uuid.UUID(current_user["sub"])
    )


# ==================== Queue Endpoints ====================

@router.post("/queue/walk-in", response_model=QueueResponse, status_code=status.HTTP_201_CREATED)
def add_walk_in_patient(
    queue_data: QueueCreate,
    db = Depends(get_db),
    current_user = Depends(require_permissions([Permissions.PATIENTS_CREATE, "queue:manage"]))
):
    """Add a walk-in patient to the queue"""
    service = QueueService(db)
    return service.add_walk_in_patient(
        patient_id=queue_data.patient_id,
        doctor_id=queue_data.doctor_id,
        department_id=queue_data.department_id,
        is_emergency=queue_data.is_emergency,
        notes=queue_data.notes
    )


@router.get("/queue/doctor/{doctor_id}", response_model=QueueListResponse)
def get_doctor_queue(
    doctor_id: uuid.UUID,
    queue_date: Optional[date] = None,
    status_filter: Optional[QueueStatus] = Query(None, alias="status"),
    db = Depends(get_db),
    current_user = Depends(require_permissions([Permissions.PATIENTS_READ, "queue:read"]))
):
    """Get queue for a doctor"""
    service = QueueService(db)
    queue = service.get_doctor_queue(doctor_id, queue_date, status_filter)
    waiting_count = service.get_waiting_count(doctor_id, queue_date)
    
    return QueueListResponse(
        doctor_id=doctor_id,
        queue_date=queue_date or date.today(),
        waiting_count=waiting_count,
        items=queue
    )


@router.post("/queue/doctor/{doctor_id}/call-next", response_model=Optional[QueueResponse])
def call_next_patient(
    doctor_id: uuid.UUID,
    db = Depends(get_db),
    current_user = Depends(require_permissions([Permissions.PATIENTS_READ, "queue:manage"]))
):
    """Call next patient in queue"""
    service = QueueService(db)
    queue = service.call_next_patient(doctor_id)
    if not queue:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No patients waiting in queue"
        )
    return queue


@router.post("/queue/{queue_id}/start", response_model=QueueResponse)
def start_consultation(
    queue_id: uuid.UUID,
    db = Depends(get_db),
    current_user = Depends(require_permissions([Permissions.PATIENTS_UPDATE, "queue:manage"]))
):
    """Start consultation for a patient"""
    service = QueueService(db)
    return service.start_consultation(queue_id)


@router.post("/queue/{queue_id}/complete", response_model=QueueResponse)
def complete_consultation(
    queue_id: uuid.UUID,
    db = Depends(get_db),
    current_user = Depends(require_permissions([Permissions.PATIENTS_UPDATE, "queue:manage"]))
):
    """Complete consultation for a patient"""
    service = QueueService(db)
    return service.complete_consultation(queue_id)


@router.post("/queue/{queue_id}/skip", response_model=QueueResponse)
def skip_patient(
    queue_id: uuid.UUID,
    db = Depends(get_db),
    current_user = Depends(require_permissions([Permissions.PATIENTS_UPDATE, "queue:manage"]))
):
    """Skip a patient in queue"""
    service = QueueService(db)
    return service.skip_patient(queue_id)
