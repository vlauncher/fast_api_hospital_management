import asyncio
import uuid
from datetime import date, time, datetime, timedelta
import os
import sys

# Add project root to python path
sys.path.append(os.getcwd())

from app.infrastructure.database import SessionLocal, init_db
from app.domain.auth.models import User, UserRole, Department
from app.domain.patients.models import Patient, Gender
from app.domain.appointments.service import DoctorScheduleService, AppointmentService, QueueService
from app.domain.appointments.models import AppointmentType
from app.domain.emr.service import EncounterService, DiagnosisService, VitalSignsService, PrescriptionService
from app.domain.emr.models import EncounterType, DiagnosisType, NoteType

async def run_workflow():
    print("Initializing database...")
    # Ensure tables exist (redundant if migration ran, but safe)
    # await init_db() 
    
    db = SessionLocal()
    
    try:
        print("\n--- 1. Setup Data ---")
        # Create Department
        dept_name = f"General Medicine {uuid.uuid4().hex[:4]}"
        dept = Department(
            id=uuid.uuid4(),
            name=dept_name,
            code=f"GM-{uuid.uuid4().hex[:4]}",
            is_active=True
        )
        db.add(dept)
        
        # Create Doctor
        doctor = User(
            id=uuid.uuid4(),
            email=f"doctor_{uuid.uuid4()}@hospital.com",
            username=f"dr_house_{uuid.uuid4().hex[:4]}",
            password_hash="hashed_secret",
            first_name="Gregory",
            last_name="House",
            role=UserRole.DOCTOR,
            department_id=dept.id,
            is_active=True
        )
        db.add(doctor)
        
        # Create Patient
        patient = Patient(
            id=uuid.uuid4(),
            patient_number=f"P{uuid.uuid4().hex[:8]}".upper(),
            first_name="John",
            last_name="Doe",
            date_of_birth=date(1980, 1, 1),
            gender=Gender.MALE,
            phone_primary="555-0123",
            email="john.doe@example.com",
            created_by=doctor.id
        )
        db.add(patient)
        
        db.commit()
        print(f"Created Doctor: {doctor.first_name} {doctor.last_name}")
        print(f"Created Patient: {patient.patient_number}")
        
        print("\n--- 2. Doctor Schedule ---")
        schedule_service = DoctorScheduleService(db)
        schedule = schedule_service.create_schedule(
            doctor_id=doctor.id,
            day_of_week=date.today().weekday(),
            start_time=time(9, 0),
            end_time=time(17, 0),
            effective_from=date.today()
        )
        print(f"Created schedule for Today: 09:00 - 17:00")
        
        print("\n--- 3. Book Appointment ---")
        appt_service = AppointmentService(db)
        appointment = appt_service.create_appointment(
            patient_id=patient.id,
            doctor_id=doctor.id,
            appointment_date=date.today(),
            appointment_time=time(10, 0),
            appointment_type=AppointmentType.NEW_CONSULTATION,
            created_by=doctor.id,
            department_id=dept.id,
            reason="Severe headache"
        )
        print(f"Booked Appointment: {appointment.appointment_number} at 10:00")
        
        print("\n--- 4. Patient Check-in ---")
        appointment, queue = appt_service.check_in_patient(
            appointment.id,
            checked_in_by=doctor.id
        )
        print(f"Patient checked in. Queue Number: {queue.queue_number}")
        
        print("\n--- 5. Start Consultation (Encounter) ---")
        encounter_service = EncounterService(db)
        
        # In a real API flow, we might call 'call_next_patient' from QueueService first
        queue_service = QueueService(db)
        queue_service.call_next_patient(doctor.id)
        
        encounter = encounter_service.create_encounter(
            patient_id=patient.id,
            doctor_id=doctor.id,
            encounter_type=EncounterType.OUTPATIENT,
            created_by=doctor.id,
            department_id=dept.id,
            appointment_id=appointment.id,
            chief_complaint="Persistent headache for 3 days",
            history_of_present_illness="Patient reports throbbing pain in frontal region."
        )
        print(f"Started Encounter: {encounter.encounter_number}")
        
        print("\n--- 6. Record Vitals ---")
        vitals = encounter_service.add_vital_signs(
            encounter.id,
            doctor.id,
            {
                "systolic_bp": 120,
                "diastolic_bp": 80,
                "heart_rate": 72,
                "temperature": 37.0,
                "weight": 70.0,
                "height": 175.0
            }
        )
        print(f"Recorded Vitals - BP: {vitals.systolic_bp}/{vitals.diastolic_bp}, BMI: {vitals.bmi:.2f}")
        
        print("\n--- 7. Add Diagnosis ---")
        diag_service = DiagnosisService(db)
        diagnosis = diag_service.add_diagnosis(
            encounter_id=encounter.id,
            icd_10_code="R51",
            description="Headache",
            diagnosed_by=doctor.id,
            diagnosis_type=DiagnosisType.PRIMARY
        )
        print(f"Added Diagnosis: {diagnosis.icd_10_code} - {diagnosis.description}")
        
        print("\n--- 8. Prescribe Medication ---")
        presc_service = PrescriptionService(db)
        prescription = presc_service.create_prescription(
            patient_id=patient.id,
            prescribed_by=doctor.id,
            encounter_id=encounter.id,
            items=[
                {
                    "drug_name": "Paracetamol",
                    "dosage": "500mg",
                    "frequency": "Every 6 hours",
                    "duration_days": 5,
                    "quantity": 20,
                    "instructions": "Take after food"
                }
            ]
        )
        print(f"Created Prescription: {prescription.prescription_number} with 1 item")
        
        # Simulate new request / clear cache to ensure relationships are re-loaded
        db.expire_all()
        
        print("\n--- 9. Sign Encounter ---")
        signed_encounter = encounter_service.sign_encounter(
            encounter.id,
            signed_by=doctor.id
        )
        print(f"Encounter Signed by {signed_encounter.signed_by}. Status: {signed_encounter.status.value}")
        print("Encounter is now locked/immutable.")

        print("\n✅ WORKFLOW COMPLETED SUCCESSFULLY!")
        
    except Exception as e:
        print(f"\n❌ WORKFLOW FAILED: {str(e)}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()

if __name__ == "__main__":
    asyncio.run(run_workflow())
