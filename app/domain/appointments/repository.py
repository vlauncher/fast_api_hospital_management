"""
Appointments Repository Layer

Provides data access operations for appointments, schedules, leaves, and queues.
"""

from typing import Optional, List, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete, and_, or_, func
from sqlalchemy.orm import joinedload
from datetime import datetime, date, time
import uuid

from app.domain.appointments.models import (
    Appointment, AppointmentStatus, AppointmentType,
    DoctorSchedule, DoctorLeave, LeaveStatus,
    Queue, QueueStatus, QueueType
)


class DoctorScheduleRepository:
    """Repository for doctor schedule data access operations"""
    
    def __init__(self, db):
        self.db = db
    
    def create(self, schedule_data: dict) -> DoctorSchedule:
        """Create a new doctor schedule"""
        schedule = DoctorSchedule(**schedule_data)
        self.db.add(schedule)
        self.db.commit()
        self.db.refresh(schedule)
        return schedule
    
    def get_by_id(self, schedule_id: uuid.UUID) -> Optional[DoctorSchedule]:
        """Get schedule by ID"""
        return self.db.query(DoctorSchedule).filter(
            DoctorSchedule.id == schedule_id
        ).first()
    
    def get_by_doctor_id(self, doctor_id: uuid.UUID, active_only: bool = True) -> List[DoctorSchedule]:
        """Get all schedules for a doctor"""
        query = self.db.query(DoctorSchedule).filter(
            DoctorSchedule.doctor_id == doctor_id
        )
        if active_only:
            query = query.filter(DoctorSchedule.is_active == True)
        return query.order_by(DoctorSchedule.day_of_week).all()
    
    def get_schedule_for_day(
        self, 
        doctor_id: uuid.UUID, 
        day_of_week: int, 
        target_date: date
    ) -> Optional[DoctorSchedule]:
        """Get active schedule for a specific day"""
        return self.db.query(DoctorSchedule).filter(
            and_(
                DoctorSchedule.doctor_id == doctor_id,
                DoctorSchedule.day_of_week == day_of_week,
                DoctorSchedule.is_active == True,
                DoctorSchedule.effective_from <= target_date,
                or_(
                    DoctorSchedule.effective_until.is_(None),
                    DoctorSchedule.effective_until >= target_date
                )
            )
        ).first()
    
    def update(self, schedule_id: uuid.UUID, update_data: dict) -> Optional[DoctorSchedule]:
        """Update schedule"""
        schedule = self.get_by_id(schedule_id)
        if schedule:
            for key, value in update_data.items():
                if hasattr(schedule, key) and value is not None:
                    setattr(schedule, key, value)
            self.db.commit()
            self.db.refresh(schedule)
        return schedule
    
    def deactivate(self, schedule_id: uuid.UUID) -> bool:
        """Deactivate a schedule"""
        result = self.db.query(DoctorSchedule).filter(
            DoctorSchedule.id == schedule_id
        ).update({"is_active": False})
        self.db.commit()
        return result > 0
    
    def delete(self, schedule_id: uuid.UUID) -> bool:
        """Delete a schedule"""
        result = self.db.query(DoctorSchedule).filter(
            DoctorSchedule.id == schedule_id
        ).delete()
        self.db.commit()
        return result > 0


class DoctorLeaveRepository:
    """Repository for doctor leave data access operations"""
    
    def __init__(self, db):
        self.db = db
    
    def create(self, leave_data: dict) -> DoctorLeave:
        """Create a new leave request"""
        leave = DoctorLeave(**leave_data)
        self.db.add(leave)
        self.db.commit()
        self.db.refresh(leave)
        return leave
    
    def get_by_id(self, leave_id: uuid.UUID) -> Optional[DoctorLeave]:
        """Get leave by ID"""
        return self.db.query(DoctorLeave).options(
            joinedload(DoctorLeave.doctor),
            joinedload(DoctorLeave.approver)
        ).filter(DoctorLeave.id == leave_id).first()
    
    def get_by_doctor_id(
        self, 
        doctor_id: uuid.UUID, 
        status: Optional[LeaveStatus] = None
    ) -> List[DoctorLeave]:
        """Get all leaves for a doctor"""
        query = self.db.query(DoctorLeave).filter(
            DoctorLeave.doctor_id == doctor_id
        )
        if status:
            query = query.filter(DoctorLeave.status == status)
        return query.order_by(DoctorLeave.start_date.desc()).all()
    
    def get_leaves_for_date_range(
        self, 
        doctor_id: uuid.UUID, 
        start_date: date, 
        end_date: date
    ) -> List[DoctorLeave]:
        """Get approved leaves within date range"""
        return self.db.query(DoctorLeave).filter(
            and_(
                DoctorLeave.doctor_id == doctor_id,
                DoctorLeave.status == LeaveStatus.APPROVED,
                DoctorLeave.start_date <= end_date,
                DoctorLeave.end_date >= start_date
            )
        ).all()
    
    def is_doctor_on_leave(self, doctor_id: uuid.UUID, check_date: date) -> bool:
        """Check if doctor is on leave for a specific date"""
        leave = self.db.query(DoctorLeave).filter(
            and_(
                DoctorLeave.doctor_id == doctor_id,
                DoctorLeave.status == LeaveStatus.APPROVED,
                DoctorLeave.start_date <= check_date,
                DoctorLeave.end_date >= check_date
            )
        ).first()
        return leave is not None
    
    def update(self, leave_id: uuid.UUID, update_data: dict) -> Optional[DoctorLeave]:
        """Update leave request"""
        leave = self.get_by_id(leave_id)
        if leave:
            for key, value in update_data.items():
                if hasattr(leave, key) and value is not None:
                    setattr(leave, key, value)
            self.db.commit()
            self.db.refresh(leave)
        return leave
    
    def approve(self, leave_id: uuid.UUID, approved_by: uuid.UUID) -> Optional[DoctorLeave]:
        """Approve a leave request"""
        leave = self.get_by_id(leave_id)
        if leave and leave.status == LeaveStatus.PENDING:
            leave.status = LeaveStatus.APPROVED
            leave.approved_by = approved_by
            leave.approved_at = datetime.utcnow()
            self.db.commit()
            self.db.refresh(leave)
        return leave
    
    def reject(self, leave_id: uuid.UUID, approved_by: uuid.UUID, reason: str) -> Optional[DoctorLeave]:
        """Reject a leave request"""
        leave = self.get_by_id(leave_id)
        if leave and leave.status == LeaveStatus.PENDING:
            leave.status = LeaveStatus.REJECTED
            leave.approved_by = approved_by
            leave.approved_at = datetime.utcnow()
            leave.rejection_reason = reason
            self.db.commit()
            self.db.refresh(leave)
        return leave


class AppointmentRepository:
    """Repository for appointment data access operations"""
    
    def __init__(self, db):
        self.db = db
    
    def create(self, appointment_data: dict) -> Appointment:
        """Create a new appointment"""
        appointment = Appointment(**appointment_data)
        self.db.add(appointment)
        self.db.commit()
        self.db.refresh(appointment)
        return appointment
    
    def get_by_id(self, appointment_id: uuid.UUID) -> Optional[Appointment]:
        """Get appointment by ID with relationships"""
        return self.db.query(Appointment).options(
            joinedload(Appointment.patient),
            joinedload(Appointment.doctor),
            joinedload(Appointment.department)
        ).filter(Appointment.id == appointment_id).first()
    
    def get_by_appointment_number(self, appointment_number: str) -> Optional[Appointment]:
        """Get appointment by appointment number"""
        return self.db.query(Appointment).filter(
            Appointment.appointment_number == appointment_number
        ).first()
    
    def get_all(
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
    ) -> List[Appointment]:
        """Get appointments with filtering"""
        query = self.db.query(Appointment).options(
            joinedload(Appointment.patient),
            joinedload(Appointment.doctor)
        )
        
        if patient_id:
            query = query.filter(Appointment.patient_id == patient_id)
        if doctor_id:
            query = query.filter(Appointment.doctor_id == doctor_id)
        if department_id:
            query = query.filter(Appointment.department_id == department_id)
        if status:
            query = query.filter(Appointment.status == status)
        if appointment_type:
            query = query.filter(Appointment.appointment_type == appointment_type)
        if date_from:
            query = query.filter(Appointment.appointment_date >= date_from)
        if date_to:
            query = query.filter(Appointment.appointment_date <= date_to)
        if is_emergency is not None:
            query = query.filter(Appointment.is_emergency == is_emergency)
        
        return query.order_by(
            Appointment.appointment_date.desc(),
            Appointment.appointment_time.desc()
        ).offset(skip).limit(limit).all()
    
    def get_today_appointments(
        self, 
        doctor_id: Optional[uuid.UUID] = None,
        department_id: Optional[uuid.UUID] = None
    ) -> List[Appointment]:
        """Get today's appointments"""
        today = date.today()
        query = self.db.query(Appointment).options(
            joinedload(Appointment.patient),
            joinedload(Appointment.doctor)
        ).filter(Appointment.appointment_date == today)
        
        if doctor_id:
            query = query.filter(Appointment.doctor_id == doctor_id)
        if department_id:
            query = query.filter(Appointment.department_id == department_id)
        
        return query.order_by(Appointment.appointment_time).all()
    
    def get_appointments_for_slot(
        self,
        doctor_id: uuid.UUID,
        appointment_date: date,
        appointment_time: time
    ) -> List[Appointment]:
        """Get appointments for a specific slot (to check availability)"""
        return self.db.query(Appointment).filter(
            and_(
                Appointment.doctor_id == doctor_id,
                Appointment.appointment_date == appointment_date,
                Appointment.appointment_time == appointment_time,
                Appointment.status.notin_([
                    AppointmentStatus.CANCELLED,
                    AppointmentStatus.RESCHEDULED
                ])
            )
        ).all()
    
    def count(
        self,
        patient_id: Optional[uuid.UUID] = None,
        doctor_id: Optional[uuid.UUID] = None,
        status: Optional[AppointmentStatus] = None,
        date_from: Optional[date] = None,
        date_to: Optional[date] = None
    ) -> int:
        """Count appointments with filters"""
        query = self.db.query(func.count(Appointment.id))
        
        if patient_id:
            query = query.filter(Appointment.patient_id == patient_id)
        if doctor_id:
            query = query.filter(Appointment.doctor_id == doctor_id)
        if status:
            query = query.filter(Appointment.status == status)
        if date_from:
            query = query.filter(Appointment.appointment_date >= date_from)
        if date_to:
            query = query.filter(Appointment.appointment_date <= date_to)
        
        return query.scalar()
    
    def update(self, appointment_id: uuid.UUID, update_data: dict) -> Optional[Appointment]:
        """Update appointment"""
        appointment = self.db.query(Appointment).filter(
            Appointment.id == appointment_id
        ).first()
        if appointment:
            for key, value in update_data.items():
                if hasattr(appointment, key) and value is not None:
                    setattr(appointment, key, value)
            self.db.commit()
            self.db.refresh(appointment)
        return appointment
    
    def cancel(
        self, 
        appointment_id: uuid.UUID, 
        cancelled_by: uuid.UUID, 
        reason: str
    ) -> Optional[Appointment]:
        """Cancel an appointment"""
        appointment = self.get_by_id(appointment_id)
        if appointment and appointment.status not in [
            AppointmentStatus.CANCELLED, 
            AppointmentStatus.COMPLETED
        ]:
            appointment.status = AppointmentStatus.CANCELLED
            appointment.cancelled_at = datetime.utcnow()
            appointment.cancelled_by = cancelled_by
            appointment.cancelled_reason = reason
            self.db.commit()
            self.db.refresh(appointment)
        return appointment
    
    def check_in(
        self, 
        appointment_id: uuid.UUID, 
        checked_in_by: uuid.UUID
    ) -> Optional[Appointment]:
        """Check in a patient for appointment"""
        appointment = self.get_by_id(appointment_id)
        if appointment and appointment.status in [
            AppointmentStatus.SCHEDULED,
            AppointmentStatus.CONFIRMED
        ]:
            appointment.status = AppointmentStatus.CHECKED_IN
            appointment.checked_in_at = datetime.utcnow()
            appointment.checked_in_by = checked_in_by
            self.db.commit()
            self.db.refresh(appointment)
        return appointment
    
    def confirm(self, appointment_id: uuid.UUID) -> Optional[Appointment]:
        """Confirm an appointment"""
        appointment = self.get_by_id(appointment_id)
        if appointment and appointment.status == AppointmentStatus.SCHEDULED:
            appointment.status = AppointmentStatus.CONFIRMED
            appointment.confirmation_sent = True
            self.db.commit()
            self.db.refresh(appointment)
        return appointment
    
    def get_no_show_count(self, patient_id: uuid.UUID, days: int = 90) -> int:
        """Get count of no-shows in last N days"""
        from datetime import timedelta
        cutoff_date = date.today() - timedelta(days=days)
        return self.db.query(func.count(Appointment.id)).filter(
            and_(
                Appointment.patient_id == patient_id,
                Appointment.status == AppointmentStatus.NO_SHOW,
                Appointment.appointment_date >= cutoff_date
            )
        ).scalar()


class QueueRepository:
    """Repository for queue data access operations"""
    
    def __init__(self, db):
        self.db = db
    
    def create(self, queue_data: dict) -> Queue:
        """Create a new queue entry"""
        queue = Queue(**queue_data)
        self.db.add(queue)
        self.db.commit()
        self.db.refresh(queue)
        return queue
    
    def get_by_id(self, queue_id: uuid.UUID) -> Optional[Queue]:
        """Get queue entry by ID"""
        return self.db.query(Queue).options(
            joinedload(Queue.patient),
            joinedload(Queue.doctor),
            joinedload(Queue.appointment)
        ).filter(Queue.id == queue_id).first()
    
    def get_next_queue_number(self, doctor_id: uuid.UUID, queue_date: date) -> int:
        """Get next queue number for doctor on a date"""
        max_number = self.db.query(func.max(Queue.queue_number)).filter(
            and_(
                Queue.doctor_id == doctor_id,
                Queue.queue_date == queue_date
            )
        ).scalar()
        return (max_number or 0) + 1
    
    def get_doctor_queue(
        self, 
        doctor_id: uuid.UUID, 
        queue_date: Optional[date] = None,
        status: Optional[QueueStatus] = None
    ) -> List[Queue]:
        """Get queue for a doctor"""
        if queue_date is None:
            queue_date = date.today()
        
        query = self.db.query(Queue).options(
            joinedload(Queue.patient),
            joinedload(Queue.appointment)
        ).filter(
            and_(
                Queue.doctor_id == doctor_id,
                Queue.queue_date == queue_date
            )
        )
        
        if status:
            query = query.filter(Queue.status == status)
        
        return query.order_by(
            Queue.is_emergency.desc(),
            Queue.priority,
            Queue.queue_number
        ).all()
    
    def get_waiting_count(self, doctor_id: uuid.UUID, queue_date: Optional[date] = None) -> int:
        """Get count of waiting patients"""
        if queue_date is None:
            queue_date = date.today()
        
        return self.db.query(func.count(Queue.id)).filter(
            and_(
                Queue.doctor_id == doctor_id,
                Queue.queue_date == queue_date,
                Queue.status == QueueStatus.WAITING
            )
        ).scalar()
    
    def update_status(
        self, 
        queue_id: uuid.UUID, 
        status: QueueStatus
    ) -> Optional[Queue]:
        """Update queue status"""
        queue = self.get_by_id(queue_id)
        if queue:
            queue.status = status
            if status == QueueStatus.CALLED:
                queue.called_at = datetime.utcnow()
            elif status == QueueStatus.COMPLETED:
                queue.completed_at = datetime.utcnow()
                if queue.checked_in_at:
                    queue.actual_wait_time = int(
                        (queue.completed_at - queue.checked_in_at).total_seconds() / 60
                    )
            self.db.commit()
            self.db.refresh(queue)
        return queue
    
    def call_next(self, doctor_id: uuid.UUID) -> Optional[Queue]:
        """Call next patient in queue"""
        today = date.today()
        next_patient = self.db.query(Queue).filter(
            and_(
                Queue.doctor_id == doctor_id,
                Queue.queue_date == today,
                Queue.status == QueueStatus.WAITING
            )
        ).order_by(
            Queue.is_emergency.desc(),
            Queue.priority,
            Queue.queue_number
        ).first()
        
        if next_patient:
            next_patient.status = QueueStatus.CALLED
            next_patient.called_at = datetime.utcnow()
            self.db.commit()
            self.db.refresh(next_patient)
        
        return next_patient
