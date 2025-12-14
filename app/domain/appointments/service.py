"""
Appointments Service Layer

Business logic for appointment scheduling, doctor schedules, and queue management.
"""

from typing import Optional, List, Dict, Any, Tuple
from datetime import datetime, date, time, timedelta
import uuid
from fastapi import HTTPException, status

from app.domain.appointments.models import (
    Appointment, AppointmentStatus, AppointmentType,
    DoctorSchedule, DoctorLeave, LeaveStatus, LeaveType,
    Queue, QueueStatus, QueueType
)
from app.domain.appointments.repository import (
    AppointmentRepository, DoctorScheduleRepository,
    DoctorLeaveRepository, QueueRepository
)


class DoctorScheduleService:
    """Service layer for doctor schedule management"""
    
    def __init__(self, db):
        self.db = db
        self.schedule_repo = DoctorScheduleRepository(db)
        self.leave_repo = DoctorLeaveRepository(db)
    
    def create_schedule(
        self,
        doctor_id: uuid.UUID,
        day_of_week: int,
        start_time: time,
        end_time: time,
        effective_from: date,
        slot_duration_minutes: int = 30,
        max_patients_per_slot: int = 1,
        break_start: Optional[time] = None,
        break_end: Optional[time] = None,
        effective_until: Optional[date] = None
    ) -> DoctorSchedule:
        """Create a new doctor schedule"""
        # Validate day of week
        if day_of_week < 0 or day_of_week > 6:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Day of week must be between 0 (Monday) and 6 (Sunday)"
            )
        
        # Validate times
        if start_time >= end_time:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Start time must be before end time"
            )
        
        # Check for overlapping schedules
        existing = self.schedule_repo.get_schedule_for_day(
            doctor_id, day_of_week, effective_from
        )
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Schedule already exists for this day"
            )
        
        schedule_data = {
            "doctor_id": doctor_id,
            "day_of_week": day_of_week,
            "start_time": start_time,
            "end_time": end_time,
            "slot_duration_minutes": slot_duration_minutes,
            "max_patients_per_slot": max_patients_per_slot,
            "break_start": break_start,
            "break_end": break_end,
            "effective_from": effective_from,
            "effective_until": effective_until,
            "is_active": True
        }
        
        return self.schedule_repo.create(schedule_data)
    
    def get_doctor_schedules(
        self, 
        doctor_id: uuid.UUID, 
        active_only: bool = True
    ) -> List[DoctorSchedule]:
        """Get all schedules for a doctor"""
        return self.schedule_repo.get_by_doctor_id(doctor_id, active_only)
    
    def get_available_slots(
        self,
        doctor_id: uuid.UUID,
        target_date: date,
        appointment_repo: 'AppointmentRepository'
    ) -> List[Dict[str, Any]]:
        """Get available time slots for a doctor on a specific date"""
        if target_date < date.today():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot get slots for past dates"
            )
        
        # Check if doctor is on leave
        if self.leave_repo.is_doctor_on_leave(doctor_id, target_date):
            return []
        
        # Get schedule for the day
        day_of_week = target_date.weekday()
        schedule = self.schedule_repo.get_schedule_for_day(
            doctor_id, day_of_week, target_date
        )
        
        if not schedule:
            return []
        
        # Generate all possible slots
        slots = []
        current_time = datetime.combine(target_date, schedule.start_time)
        end_time = datetime.combine(target_date, schedule.end_time)
        slot_duration = timedelta(minutes=schedule.slot_duration_minutes)
        
        while current_time + slot_duration <= end_time:
            slot_time = current_time.time()
            
            # Skip break time
            if schedule.break_start and schedule.break_end:
                if schedule.break_start <= slot_time < schedule.break_end:
                    current_time += slot_duration
                    continue
            
            # Check if slot is in the past (for today)
            if target_date == date.today():
                now = datetime.now()
                if current_time <= now:
                    current_time += slot_duration
                    continue
            
            # Check existing appointments for this slot
            existing = appointment_repo.get_appointments_for_slot(
                doctor_id, target_date, slot_time
            )
            
            available_count = schedule.max_patients_per_slot - len(existing)
            
            if available_count > 0:
                slots.append({
                    "time": slot_time.isoformat(),
                    "available_slots": available_count,
                    "duration_minutes": schedule.slot_duration_minutes
                })
            
            current_time += slot_duration
        
        return slots
    
    def update_schedule(
        self, 
        schedule_id: uuid.UUID, 
        update_data: dict
    ) -> Optional[DoctorSchedule]:
        """Update doctor schedule"""
        return self.schedule_repo.update(schedule_id, update_data)
    
    def deactivate_schedule(self, schedule_id: uuid.UUID) -> bool:
        """Deactivate a schedule"""
        return self.schedule_repo.deactivate(schedule_id)


class DoctorLeaveService:
    """Service layer for doctor leave management"""
    
    def __init__(self, db):
        self.db = db
        self.leave_repo = DoctorLeaveRepository(db)
    
    def request_leave(
        self,
        doctor_id: uuid.UUID,
        leave_type: LeaveType,
        start_date: date,
        end_date: date,
        reason: Optional[str] = None,
        start_time: Optional[time] = None,
        end_time: Optional[time] = None
    ) -> DoctorLeave:
        """Request a new leave"""
        if start_date > end_date:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Start date must be before or equal to end date"
            )
        
        if start_date < date.today():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot request leave for past dates"
            )
        
        # Check for overlapping leaves
        existing = self.leave_repo.get_leaves_for_date_range(
            doctor_id, start_date, end_date
        )
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Leave already exists for this period"
            )
        
        leave_data = {
            "doctor_id": doctor_id,
            "leave_type": leave_type,
            "start_date": start_date,
            "end_date": end_date,
            "start_time": start_time,
            "end_time": end_time,
            "reason": reason,
            "status": LeaveStatus.PENDING
        }
        
        return self.leave_repo.create(leave_data)
    
    def get_doctor_leaves(
        self, 
        doctor_id: uuid.UUID, 
        status: Optional[LeaveStatus] = None
    ) -> List[DoctorLeave]:
        """Get all leaves for a doctor"""
        return self.leave_repo.get_by_doctor_id(doctor_id, status)
    
    def approve_leave(
        self, 
        leave_id: uuid.UUID, 
        approved_by: uuid.UUID
    ) -> DoctorLeave:
        """Approve a leave request"""
        leave = self.leave_repo.approve(leave_id, approved_by)
        if not leave:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Leave request not found or already processed"
            )
        return leave
    
    def reject_leave(
        self, 
        leave_id: uuid.UUID, 
        approved_by: uuid.UUID, 
        reason: str
    ) -> DoctorLeave:
        """Reject a leave request"""
        leave = self.leave_repo.reject(leave_id, approved_by, reason)
        if not leave:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Leave request not found or already processed"
            )
        return leave
    
    def cancel_leave(self, leave_id: uuid.UUID) -> DoctorLeave:
        """Cancel a leave request"""
        leave = self.leave_repo.get_by_id(leave_id)
        if not leave:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Leave request not found"
            )
        
        if leave.status not in [LeaveStatus.PENDING, LeaveStatus.APPROVED]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot cancel this leave request"
            )
        
        return self.leave_repo.update(leave_id, {"status": LeaveStatus.CANCELLED})


class AppointmentService:
    """Service layer for appointment management"""
    
    def __init__(self, db):
        self.db = db
        self.appointment_repo = AppointmentRepository(db)
        self.schedule_service = DoctorScheduleService(db)
        self.leave_repo = DoctorLeaveRepository(db)
        self.queue_repo = QueueRepository(db)
    
    def _generate_appointment_number(self) -> str:
        """Generate unique appointment number"""
        today = date.today()
        prefix = f"APT-{today.strftime('%Y%m%d')}"
        
        # Count today's appointments
        count = self.appointment_repo.count(
            date_from=today,
            date_to=today
        )
        
        return f"{prefix}-{str(count + 1).zfill(4)}"
    
    def create_appointment(
        self,
        patient_id: uuid.UUID,
        doctor_id: uuid.UUID,
        appointment_date: date,
        appointment_time: time,
        appointment_type: AppointmentType,
        created_by: uuid.UUID,
        department_id: Optional[uuid.UUID] = None,
        reason: Optional[str] = None,
        symptoms: Optional[str] = None,
        is_emergency: bool = False,
        priority: int = 3
    ) -> Appointment:
        """Create a new appointment"""
        # Validate date is not in the past
        if appointment_date < date.today():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot book appointments for past dates"
            )
        
        # Check if doctor is on leave
        if self.leave_repo.is_doctor_on_leave(doctor_id, appointment_date):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Doctor is not available on this date"
            )
        
        # Check slot availability (unless emergency)
        if not is_emergency:
            existing = self.appointment_repo.get_appointments_for_slot(
                doctor_id, appointment_date, appointment_time
            )
            
            # Get schedule to check max patients
            day_of_week = appointment_date.weekday()
            schedule = self.schedule_service.schedule_repo.get_schedule_for_day(
                doctor_id, day_of_week, appointment_date
            )
            
            if schedule:
                max_patients = schedule.max_patients_per_slot
                if len(existing) >= max_patients:
                    raise HTTPException(
                        status_code=status.HTTP_409_CONFLICT,
                        detail="This time slot is fully booked"
                    )
        
        # Check patient's no-show history
        no_show_count = self.appointment_repo.get_no_show_count(patient_id)
        if no_show_count >= 3:
            # Flag but don't prevent booking
            pass  # Could add a warning or require deposit
        
        appointment_data = {
            "appointment_number": self._generate_appointment_number(),
            "patient_id": patient_id,
            "doctor_id": doctor_id,
            "department_id": department_id,
            "appointment_date": appointment_date,
            "appointment_time": appointment_time,
            "appointment_type": appointment_type,
            "status": AppointmentStatus.SCHEDULED,
            "is_emergency": is_emergency,
            "priority": 1 if is_emergency else priority,
            "reason": reason,
            "symptoms": symptoms,
            "created_by": created_by
        }
        
        return self.appointment_repo.create(appointment_data)
    
    def get_appointment(self, appointment_id: uuid.UUID) -> Appointment:
        """Get appointment by ID"""
        appointment = self.appointment_repo.get_by_id(appointment_id)
        if not appointment:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Appointment not found"
            )
        return appointment
    
    def get_appointments(
        self,
        skip: int = 0,
        limit: int = 20,
        patient_id: Optional[uuid.UUID] = None,
        doctor_id: Optional[uuid.UUID] = None,
        department_id: Optional[uuid.UUID] = None,
        status: Optional[AppointmentStatus] = None,
        appointment_type: Optional[AppointmentType] = None,
        date_from: Optional[date] = None,
        date_to: Optional[date] = None,
        is_emergency: Optional[bool] = None
    ) -> Tuple[List[Appointment], int]:
        """Get appointments with filtering and pagination"""
        appointments = self.appointment_repo.get_all(
            skip=skip,
            limit=limit,
            patient_id=patient_id,
            doctor_id=doctor_id,
            department_id=department_id,
            status=status,
            appointment_type=appointment_type,
            date_from=date_from,
            date_to=date_to,
            is_emergency=is_emergency
        )
        
        total = self.appointment_repo.count(
            patient_id=patient_id,
            doctor_id=doctor_id,
            status=status,
            date_from=date_from,
            date_to=date_to
        )
        
        return appointments, total
    
    def get_today_appointments(
        self,
        doctor_id: Optional[uuid.UUID] = None,
        department_id: Optional[uuid.UUID] = None
    ) -> List[Appointment]:
        """Get today's appointments"""
        return self.appointment_repo.get_today_appointments(doctor_id, department_id)
    
    def get_available_slots(
        self,
        doctor_id: uuid.UUID,
        target_date: date
    ) -> List[Dict[str, Any]]:
        """Get available time slots for a doctor"""
        return self.schedule_service.get_available_slots(
            doctor_id, target_date, self.appointment_repo
        )
    
    def update_appointment(
        self, 
        appointment_id: uuid.UUID, 
        update_data: dict
    ) -> Appointment:
        """Update appointment"""
        appointment = self.appointment_repo.update(appointment_id, update_data)
        if not appointment:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Appointment not found"
            )
        return appointment
    
    def confirm_appointment(self, appointment_id: uuid.UUID) -> Appointment:
        """Confirm an appointment"""
        appointment = self.appointment_repo.confirm(appointment_id)
        if not appointment:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Appointment not found or cannot be confirmed"
            )
        return appointment
    
    def check_in_patient(
        self, 
        appointment_id: uuid.UUID, 
        checked_in_by: uuid.UUID
    ) -> Tuple[Appointment, Queue]:
        """Check in patient and add to queue"""
        appointment = self.appointment_repo.check_in(appointment_id, checked_in_by)
        if not appointment:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Appointment not found or cannot check in"
            )
        
        # Add to queue
        queue_number = self.queue_repo.get_next_queue_number(
            appointment.doctor_id, 
            appointment.appointment_date
        )
        
        queue_data = {
            "appointment_id": appointment.id,
            "patient_id": appointment.patient_id,
            "doctor_id": appointment.doctor_id,
            "department_id": appointment.department_id,
            "queue_number": queue_number,
            "queue_date": appointment.appointment_date,
            "queue_type": QueueType.SCHEDULED,
            "status": QueueStatus.WAITING,
            "priority": appointment.priority,
            "is_emergency": appointment.is_emergency
        }
        
        queue = self.queue_repo.create(queue_data)
        
        return appointment, queue
    
    def cancel_appointment(
        self, 
        appointment_id: uuid.UUID, 
        cancelled_by: uuid.UUID, 
        reason: str
    ) -> Appointment:
        """Cancel an appointment"""
        appointment = self.appointment_repo.cancel(
            appointment_id, cancelled_by, reason
        )
        if not appointment:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Appointment not found or cannot be cancelled"
            )
        return appointment
    
    def reschedule_appointment(
        self,
        appointment_id: uuid.UUID,
        new_date: date,
        new_time: time,
        rescheduled_by: uuid.UUID
    ) -> Appointment:
        """Reschedule an appointment"""
        old_appointment = self.get_appointment(appointment_id)
        
        if old_appointment.status in [
            AppointmentStatus.CANCELLED,
            AppointmentStatus.COMPLETED,
            AppointmentStatus.RESCHEDULED
        ]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot reschedule this appointment"
            )
        
        # Create new appointment
        new_appointment = self.create_appointment(
            patient_id=old_appointment.patient_id,
            doctor_id=old_appointment.doctor_id,
            appointment_date=new_date,
            appointment_time=new_time,
            appointment_type=old_appointment.appointment_type,
            created_by=rescheduled_by,
            department_id=old_appointment.department_id,
            reason=old_appointment.reason,
            symptoms=old_appointment.symptoms,
            is_emergency=old_appointment.is_emergency,
            priority=old_appointment.priority
        )
        
        # Update old appointment
        self.appointment_repo.update(appointment_id, {
            "status": AppointmentStatus.RESCHEDULED,
            "rescheduled_to": new_appointment.id
        })
        
        # Link new appointment to old
        self.appointment_repo.update(new_appointment.id, {
            "rescheduled_from": old_appointment.id
        })
        
        return new_appointment


class QueueService:
    """Service layer for queue management"""
    
    def __init__(self, db):
        self.db = db
        self.queue_repo = QueueRepository(db)
    
    def add_walk_in_patient(
        self,
        patient_id: uuid.UUID,
        doctor_id: uuid.UUID,
        department_id: Optional[uuid.UUID] = None,
        is_emergency: bool = False,
        notes: Optional[str] = None
    ) -> Queue:
        """Add a walk-in patient to the queue"""
        today = date.today()
        queue_number = self.queue_repo.get_next_queue_number(doctor_id, today)
        
        queue_data = {
            "patient_id": patient_id,
            "doctor_id": doctor_id,
            "department_id": department_id,
            "queue_number": queue_number,
            "queue_date": today,
            "queue_type": QueueType.EMERGENCY if is_emergency else QueueType.WALK_IN,
            "status": QueueStatus.WAITING,
            "priority": 1 if is_emergency else 3,
            "is_emergency": is_emergency,
            "notes": notes
        }
        
        return self.queue_repo.create(queue_data)
    
    def get_doctor_queue(
        self, 
        doctor_id: uuid.UUID, 
        queue_date: Optional[date] = None,
        status: Optional[QueueStatus] = None
    ) -> List[Queue]:
        """Get queue for a doctor"""
        return self.queue_repo.get_doctor_queue(doctor_id, queue_date, status)
    
    def get_waiting_count(
        self, 
        doctor_id: uuid.UUID, 
        queue_date: Optional[date] = None
    ) -> int:
        """Get count of waiting patients"""
        return self.queue_repo.get_waiting_count(doctor_id, queue_date)
    
    def call_next_patient(self, doctor_id: uuid.UUID) -> Optional[Queue]:
        """Call next patient in queue"""
        return self.queue_repo.call_next(doctor_id)
    
    def update_queue_status(
        self, 
        queue_id: uuid.UUID, 
        status: QueueStatus
    ) -> Queue:
        """Update queue status"""
        queue = self.queue_repo.update_status(queue_id, status)
        if not queue:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Queue entry not found"
            )
        return queue
    
    def skip_patient(self, queue_id: uuid.UUID) -> Queue:
        """Skip a patient in queue"""
        return self.update_queue_status(queue_id, QueueStatus.SKIPPED)
    
    def start_consultation(self, queue_id: uuid.UUID) -> Queue:
        """Start consultation for a patient"""
        return self.update_queue_status(queue_id, QueueStatus.IN_CONSULTATION)
    
    def complete_consultation(self, queue_id: uuid.UUID) -> Queue:
        """Complete consultation for a patient"""
        return self.update_queue_status(queue_id, QueueStatus.COMPLETED)
