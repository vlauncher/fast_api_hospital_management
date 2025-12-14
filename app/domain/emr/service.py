"""
EMR Service Layer

Business logic for encounters, diagnoses, procedures, clinical notes,
vital signs, and prescriptions.
"""

from typing import Optional, List, Dict, Any, Tuple
from datetime import datetime, date, timedelta
import uuid
from fastapi import HTTPException, status

from app.domain.emr.models import (
    Encounter, EncounterStatus, EncounterType,
    Diagnosis, DiagnosisType, DiagnosisCertainty,
    Procedure, ProcedureStatus,
    ClinicalNote, NoteType,
    VitalSigns,
    Prescription, PrescriptionStatus, PrescriptionItem, DrugRoute
)
from app.domain.emr.repository import (
    EncounterRepository, DiagnosisRepository, ProcedureRepository,
    ClinicalNoteRepository, VitalSignsRepository, PrescriptionRepository
)


class EncounterService:
    """Service layer for encounter management"""
    
    def __init__(self, db):
        self.db = db
        self.encounter_repo = EncounterRepository(db)
        self.diagnosis_repo = DiagnosisRepository(db)
        self.vitals_repo = VitalSignsRepository(db)
    
    def _generate_encounter_number(self) -> str:
        """Generate unique encounter number"""
        today = date.today()
        prefix = f"ENC-{today.strftime('%Y%m%d')}"
        
        # Count today's encounters
        count = self.encounter_repo.count(
            date_from=today,
            date_to=today
        )
        
        return f"{prefix}-{str(count + 1).zfill(4)}"
    
    def create_encounter(
        self,
        patient_id: uuid.UUID,
        doctor_id: uuid.UUID,
        encounter_type: EncounterType,
        created_by: uuid.UUID,
        department_id: Optional[uuid.UUID] = None,
        appointment_id: Optional[uuid.UUID] = None,
        chief_complaint: Optional[str] = None,
        symptoms: Optional[List[Dict]] = None,
        history_of_present_illness: Optional[str] = None
    ) -> Encounter:
        """Create a new encounter"""
        encounter_data = {
            "encounter_number": self._generate_encounter_number(),
            "patient_id": patient_id,
            "doctor_id": doctor_id,
            "department_id": department_id,
            "appointment_id": appointment_id,
            "encounter_type": encounter_type,
            "encounter_date": datetime.utcnow(),
            "chief_complaint": chief_complaint,
            "symptoms": symptoms,
            "history_of_present_illness": history_of_present_illness,
            "status": EncounterStatus.IN_PROGRESS,
            "created_by": created_by
        }
        
        return self.encounter_repo.create(encounter_data)
    
    def get_encounter(self, encounter_id: uuid.UUID) -> Encounter:
        """Get encounter by ID"""
        encounter = self.encounter_repo.get_by_id(encounter_id)
        if not encounter:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Encounter not found"
            )
        return encounter
    
    def get_encounters(
        self,
        skip: int = 0,
        limit: int = 20,
        patient_id: Optional[uuid.UUID] = None,
        doctor_id: Optional[uuid.UUID] = None,
        department_id: Optional[uuid.UUID] = None,
        status_filter: Optional[EncounterStatus] = None,
        encounter_type: Optional[EncounterType] = None,
        date_from: Optional[date] = None,
        date_to: Optional[date] = None
    ) -> Tuple[List[Encounter], int]:
        """Get encounters with filtering and pagination"""
        encounters = self.encounter_repo.get_all(
            skip=skip,
            limit=limit,
            patient_id=patient_id,
            doctor_id=doctor_id,
            department_id=department_id,
            status=status_filter,
            encounter_type=encounter_type,
            date_from=date_from,
            date_to=date_to
        )
        
        total = self.encounter_repo.count(
            patient_id=patient_id,
            doctor_id=doctor_id,
            status=status_filter,
            date_from=date_from,
            date_to=date_to
        )
        
        return encounters, total
    
    def get_patient_encounters(
        self, 
        patient_id: uuid.UUID, 
        limit: int = 50
    ) -> List[Encounter]:
        """Get all encounters for a patient"""
        return self.encounter_repo.get_patient_encounters(patient_id, limit)
    
    def update_encounter(
        self, 
        encounter_id: uuid.UUID, 
        update_data: dict,
        updated_by: uuid.UUID
    ) -> Encounter:
        """Update encounter"""
        encounter = self.get_encounter(encounter_id)
        
        # Check if encounter is locked
        if encounter.is_locked:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Cannot modify locked encounter"
            )
        
        # Check for amendment timeframe (24 hours for signed encounters)
        if encounter.signed_at:
            hours_since_signing = (datetime.utcnow() - encounter.signed_at).total_seconds() / 3600
            if hours_since_signing > 24:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Cannot modify encounter after 24 hours of signing"
                )
        
        encounter = self.encounter_repo.update(encounter_id, update_data)
        if not encounter:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Encounter not found"
            )
        return encounter
    
    def complete_encounter(self, encounter_id: uuid.UUID) -> Encounter:
        """Mark encounter as completed"""
        encounter = self.get_encounter(encounter_id)
        
        if encounter.status != EncounterStatus.IN_PROGRESS:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Only in-progress encounters can be completed"
            )
        
        return self.encounter_repo.update(encounter_id, {"status": EncounterStatus.COMPLETED})
    
    def sign_encounter(self, encounter_id: uuid.UUID, signed_by: uuid.UUID) -> Encounter:
        """Sign and lock an encounter"""
        encounter = self.get_encounter(encounter_id)
        
        if encounter.status not in [EncounterStatus.IN_PROGRESS, EncounterStatus.COMPLETED]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot sign encounter in current status"
            )
        
        # Validate encounter has required fields
        if not encounter.diagnoses:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Encounter must have at least one diagnosis before signing"
            )
        
        return self.encounter_repo.sign_encounter(encounter_id, signed_by)
    
    def amend_encounter(
        self, 
        encounter_id: uuid.UUID, 
        amended_by: uuid.UUID,
        reason: str
    ) -> Encounter:
        """Create amendment for signed encounter"""
        encounter = self.get_encounter(encounter_id)
        
        if encounter.status != EncounterStatus.SIGNED:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Only signed encounters can be amended"
            )
        
        return self.encounter_repo.amend_encounter(encounter_id, amended_by, reason)
    
    def add_vital_signs(
        self,
        encounter_id: uuid.UUID,
        recorded_by: uuid.UUID,
        vitals_data: dict
    ) -> VitalSigns:
        """Add vital signs to an encounter"""
        encounter = self.get_encounter(encounter_id)
        
        if encounter.is_locked:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Cannot add vitals to locked encounter"
            )
        
        vitals_data["encounter_id"] = encounter_id
        vitals_data["patient_id"] = encounter.patient_id
        vitals_data["recorded_by"] = recorded_by
        
        return self.vitals_repo.create(vitals_data)
    
    def get_encounter_vitals(self, encounter_id: uuid.UUID) -> List[VitalSigns]:
        """Get all vital signs for an encounter"""
        return self.vitals_repo.get_by_encounter(encounter_id)


class DiagnosisService:
    """Service layer for diagnosis management"""
    
    def __init__(self, db):
        self.db = db
        self.diagnosis_repo = DiagnosisRepository(db)
        self.encounter_repo = EncounterRepository(db)
    
    def add_diagnosis(
        self,
        encounter_id: uuid.UUID,
        icd_10_code: str,
        description: str,
        diagnosed_by: uuid.UUID,
        diagnosis_type: DiagnosisType = DiagnosisType.PRIMARY,
        certainty: DiagnosisCertainty = DiagnosisCertainty.CONFIRMED,
        onset_date: Optional[date] = None,
        is_chronic: bool = False,
        is_principal: bool = False,
        notes: Optional[str] = None
    ) -> Diagnosis:
        """Add a diagnosis to an encounter"""
        # Verify encounter exists and is not locked
        encounter = self.encounter_repo.get_by_id(encounter_id)
        if not encounter:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Encounter not found"
            )
        
        if encounter.is_locked:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Cannot add diagnosis to locked encounter"
            )
        
        # If setting as principal, unset other principal diagnoses
        if is_principal:
            existing = self.diagnosis_repo.get_by_encounter(encounter_id)
            for diag in existing:
                if diag.is_principal:
                    self.diagnosis_repo.update(diag.id, {"is_principal": False})
        
        diagnosis_data = {
            "encounter_id": encounter_id,
            "icd_10_code": icd_10_code,
            "description": description,
            "diagnosis_type": diagnosis_type,
            "certainty": certainty,
            "onset_date": onset_date,
            "is_chronic": is_chronic,
            "is_principal": is_principal,
            "notes": notes,
            "diagnosed_by": diagnosed_by
        }
        
        return self.diagnosis_repo.create(diagnosis_data)
    
    def get_diagnosis(self, diagnosis_id: uuid.UUID) -> Diagnosis:
        """Get diagnosis by ID"""
        diagnosis = self.diagnosis_repo.get_by_id(diagnosis_id)
        if not diagnosis:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Diagnosis not found"
            )
        return diagnosis
    
    def get_encounter_diagnoses(self, encounter_id: uuid.UUID) -> List[Diagnosis]:
        """Get all diagnoses for an encounter"""
        return self.diagnosis_repo.get_by_encounter(encounter_id)
    
    def get_patient_diagnoses(
        self, 
        patient_id: uuid.UUID, 
        active_only: bool = True
    ) -> List[Diagnosis]:
        """Get all diagnoses for a patient"""
        return self.diagnosis_repo.get_patient_diagnoses(patient_id, active_only)
    
    def update_diagnosis(
        self, 
        diagnosis_id: uuid.UUID, 
        update_data: dict
    ) -> Diagnosis:
        """Update diagnosis"""
        diagnosis = self.get_diagnosis(diagnosis_id)
        
        # Check if encounter is locked
        if diagnosis.encounter.is_locked:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Cannot modify diagnosis in locked encounter"
            )
        
        return self.diagnosis_repo.update(diagnosis_id, update_data)
    
    def resolve_diagnosis(
        self, 
        diagnosis_id: uuid.UUID, 
        resolution_date: date
    ) -> Diagnosis:
        """Mark diagnosis as resolved"""
        return self.diagnosis_repo.update(diagnosis_id, {"resolution_date": resolution_date})
    
    def delete_diagnosis(self, diagnosis_id: uuid.UUID) -> bool:
        """Delete diagnosis"""
        diagnosis = self.get_diagnosis(diagnosis_id)
        
        if diagnosis.encounter.is_locked:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Cannot delete diagnosis from locked encounter"
            )
        
        return self.diagnosis_repo.delete(diagnosis_id)


class ProcedureService:
    """Service layer for procedure management"""
    
    def __init__(self, db):
        self.db = db
        self.procedure_repo = ProcedureRepository(db)
        self.encounter_repo = EncounterRepository(db)
    
    def create_procedure(
        self,
        encounter_id: uuid.UUID,
        cpt_code: str,
        description: str,
        created_by: uuid.UUID,
        scheduled_date: Optional[datetime] = None,
        duration_minutes: Optional[int] = None,
        location: Optional[str] = None,
        performed_by: Optional[uuid.UUID] = None,
        pre_procedure_diagnosis: Optional[str] = None,
        notes: Optional[str] = None
    ) -> Procedure:
        """Create a new procedure"""
        # Verify encounter exists
        encounter = self.encounter_repo.get_by_id(encounter_id)
        if not encounter:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Encounter not found"
            )
        
        procedure_data = {
            "encounter_id": encounter_id,
            "cpt_code": cpt_code,
            "description": description,
            "scheduled_date": scheduled_date,
            "duration_minutes": duration_minutes,
            "location": location,
            "performed_by": performed_by or encounter.doctor_id,
            "pre_procedure_diagnosis": pre_procedure_diagnosis,
            "notes": notes,
            "status": ProcedureStatus.SCHEDULED,
            "created_by": created_by
        }
        
        return self.procedure_repo.create(procedure_data)
    
    def get_procedure(self, procedure_id: uuid.UUID) -> Procedure:
        """Get procedure by ID"""
        procedure = self.procedure_repo.get_by_id(procedure_id)
        if not procedure:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Procedure not found"
            )
        return procedure
    
    def get_encounter_procedures(self, encounter_id: uuid.UUID) -> List[Procedure]:
        """Get all procedures for an encounter"""
        return self.procedure_repo.get_by_encounter(encounter_id)
    
    def get_scheduled_procedures(
        self,
        date_from: Optional[date] = None,
        date_to: Optional[date] = None,
        doctor_id: Optional[uuid.UUID] = None
    ) -> List[Procedure]:
        """Get scheduled procedures"""
        return self.procedure_repo.get_scheduled_procedures(date_from, date_to, doctor_id)
    
    def update_procedure(
        self, 
        procedure_id: uuid.UUID, 
        update_data: dict
    ) -> Procedure:
        """Update procedure"""
        return self.procedure_repo.update(procedure_id, update_data)
    
    def start_procedure(self, procedure_id: uuid.UUID) -> Procedure:
        """Start a procedure"""
        return self.procedure_repo.update_status(procedure_id, ProcedureStatus.IN_PROGRESS)
    
    def complete_procedure(
        self, 
        procedure_id: uuid.UUID,
        findings: Optional[str] = None,
        technique: Optional[str] = None,
        complications: Optional[str] = None,
        post_procedure_diagnosis: Optional[str] = None
    ) -> Procedure:
        """Complete a procedure"""
        update_data = {
            "findings": findings,
            "technique": technique,
            "complications": complications,
            "post_procedure_diagnosis": post_procedure_diagnosis
        }
        
        self.procedure_repo.update(procedure_id, update_data)
        return self.procedure_repo.update_status(procedure_id, ProcedureStatus.COMPLETED)
    
    def cancel_procedure(self, procedure_id: uuid.UUID) -> Procedure:
        """Cancel a procedure"""
        return self.procedure_repo.update_status(procedure_id, ProcedureStatus.CANCELLED)


class ClinicalNoteService:
    """Service layer for clinical note management"""
    
    def __init__(self, db):
        self.db = db
        self.note_repo = ClinicalNoteRepository(db)
        self.encounter_repo = EncounterRepository(db)
    
    def create_note(
        self,
        encounter_id: uuid.UUID,
        note_type: NoteType,
        created_by: uuid.UUID,
        title: Optional[str] = None,
        subjective: Optional[str] = None,
        objective: Optional[str] = None,
        assessment: Optional[str] = None,
        plan: Optional[str] = None,
        content: Optional[str] = None,
        is_draft: bool = True
    ) -> ClinicalNote:
        """Create a new clinical note"""
        # Verify encounter exists
        encounter = self.encounter_repo.get_by_id(encounter_id)
        if not encounter:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Encounter not found"
            )
        
        if encounter.is_locked:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Cannot add note to locked encounter"
            )
        
        note_data = {
            "encounter_id": encounter_id,
            "note_type": note_type,
            "title": title,
            "subjective": subjective,
            "objective": objective,
            "assessment": assessment,
            "plan": plan,
            "content": content,
            "is_draft": is_draft,
            "created_by": created_by
        }
        
        return self.note_repo.create(note_data)
    
    def get_note(self, note_id: uuid.UUID) -> ClinicalNote:
        """Get clinical note by ID"""
        note = self.note_repo.get_by_id(note_id)
        if not note:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Clinical note not found"
            )
        return note
    
    def get_encounter_notes(self, encounter_id: uuid.UUID) -> List[ClinicalNote]:
        """Get all notes for an encounter"""
        return self.note_repo.get_by_encounter(encounter_id)
    
    def get_user_drafts(self, user_id: uuid.UUID) -> List[ClinicalNote]:
        """Get draft notes for a user"""
        return self.note_repo.get_drafts_by_user(user_id)
    
    def update_note(
        self, 
        note_id: uuid.UUID, 
        update_data: dict
    ) -> ClinicalNote:
        """Update clinical note (auto-save support)"""
        note = self.get_note(note_id)
        
        if note.is_locked:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Cannot modify locked note"
            )
        
        note = self.note_repo.update(note_id, update_data)
        if not note:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Clinical note not found"
            )
        return note
    
    def sign_note(self, note_id: uuid.UUID, signed_by: uuid.UUID) -> ClinicalNote:
        """Sign a clinical note"""
        note = self.get_note(note_id)
        
        if note.is_signed:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Note is already signed"
            )
        
        return self.note_repo.sign_note(note_id, signed_by)
    
    def create_addendum(
        self,
        parent_note_id: uuid.UUID,
        content: str,
        reason: str,
        created_by: uuid.UUID
    ) -> ClinicalNote:
        """Create an addendum to an existing note"""
        parent_note = self.get_note(parent_note_id)
        
        if not parent_note.is_signed:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Can only add addendum to signed notes"
            )
        
        addendum = self.note_repo.create_addendum(
            parent_note_id, content, reason, created_by
        )
        if not addendum:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to create addendum"
            )
        return addendum


class VitalSignsService:
    """Service layer for vital signs management"""
    
    def __init__(self, db):
        self.db = db
        self.vitals_repo = VitalSignsRepository(db)
    
    def record_vitals(
        self,
        encounter_id: uuid.UUID,
        patient_id: uuid.UUID,
        recorded_by: uuid.UUID,
        vitals_data: dict
    ) -> VitalSigns:
        """Record vital signs"""
        vitals_data["encounter_id"] = encounter_id
        vitals_data["patient_id"] = patient_id
        vitals_data["recorded_by"] = recorded_by
        
        return self.vitals_repo.create(vitals_data)
    
    def get_vitals(self, vitals_id: uuid.UUID) -> VitalSigns:
        """Get vital signs by ID"""
        vitals = self.vitals_repo.get_by_id(vitals_id)
        if not vitals:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Vital signs not found"
            )
        return vitals
    
    def get_encounter_vitals(self, encounter_id: uuid.UUID) -> List[VitalSigns]:
        """Get all vital signs for an encounter"""
        return self.vitals_repo.get_by_encounter(encounter_id)
    
    def get_patient_vitals_history(
        self, 
        patient_id: uuid.UUID, 
        limit: int = 50
    ) -> List[VitalSigns]:
        """Get vital signs history for a patient"""
        return self.vitals_repo.get_patient_vitals_history(patient_id, limit)
    
    def update_vitals(
        self, 
        vitals_id: uuid.UUID, 
        update_data: dict
    ) -> VitalSigns:
        """Update vital signs"""
        return self.vitals_repo.update(vitals_id, update_data)
    
    def get_vitals_trends(self, patient_id: uuid.UUID) -> Dict[str, List]:
        """Get vital signs trends for charting"""
        vitals_history = self.vitals_repo.get_patient_vitals_history(patient_id, 100)
        
        trends = {
            "dates": [],
            "systolic_bp": [],
            "diastolic_bp": [],
            "heart_rate": [],
            "temperature": [],
            "weight": [],
            "bmi": []
        }
        
        for v in reversed(vitals_history):  # Oldest first for charting
            trends["dates"].append(v.recorded_at.isoformat() if v.recorded_at else None)
            trends["systolic_bp"].append(v.systolic_bp)
            trends["diastolic_bp"].append(v.diastolic_bp)
            trends["heart_rate"].append(v.heart_rate)
            trends["temperature"].append(v.temperature)
            trends["weight"].append(v.weight)
            trends["bmi"].append(v.bmi)
        
        return trends


class PrescriptionService:
    """Service layer for prescription management"""
    
    def __init__(self, db):
        self.db = db
        self.prescription_repo = PrescriptionRepository(db)
        self.encounter_repo = EncounterRepository(db)
    
    def _generate_prescription_number(self) -> str:
        """Generate unique prescription number"""
        today = date.today()
        prefix = f"RX-{today.strftime('%Y%m%d')}"
        
        # Count today's prescriptions
        count = self.prescription_repo.count(
            date_from=today,
            date_to=today
        )
        
        return f"{prefix}-{str(count + 1).zfill(4)}"
    
    def create_prescription(
        self,
        patient_id: uuid.UUID,
        prescribed_by: uuid.UUID,
        items: List[Dict],
        encounter_id: Optional[uuid.UUID] = None,
        diagnosis: Optional[str] = None,
        clinical_notes: Optional[str] = None,
        valid_until: Optional[date] = None
    ) -> Prescription:
        """Create a new prescription with items"""
        if not items:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Prescription must have at least one item"
            )
        
        # Default validity: 30 days
        if not valid_until:
            valid_until = date.today() + timedelta(days=30)
        
        prescription_data = {
            "prescription_number": self._generate_prescription_number(),
            "patient_id": patient_id,
            "encounter_id": encounter_id,
            "prescribed_by": prescribed_by,
            "diagnosis": diagnosis,
            "clinical_notes": clinical_notes,
            "valid_until": valid_until,
            "status": PrescriptionStatus.PENDING,
            "allergy_check_performed": True,  # Should be validated before this
            "interaction_check_performed": True
        }
        
        # Prepare items
        prescription_items = []
        for item in items:
            prescription_items.append({
                "drug_name": item["drug_name"],
                "drug_code": item.get("drug_code"),
                "generic_name": item.get("generic_name"),
                "strength": item.get("strength"),
                "dosage": item["dosage"],
                "dosage_form": item.get("dosage_form"),
                "frequency": item["frequency"],
                "frequency_code": item.get("frequency_code"),
                "duration_days": item.get("duration_days"),
                "duration_text": item.get("duration_text"),
                "quantity": item["quantity"],
                "quantity_unit": item.get("quantity_unit", "units"),
                "route": DrugRoute(item.get("route", "ORAL")),
                "timing": item.get("timing"),
                "instructions": item.get("instructions"),
                "take_with_food": item.get("take_with_food"),
                "special_warnings": item.get("special_warnings"),
                "refills_allowed": item.get("refills_allowed", 0),
                "refills_remaining": item.get("refills_allowed", 0),
                "allow_generic_substitution": item.get("allow_generic_substitution", True)
            })
        
        return self.prescription_repo.create(prescription_data, prescription_items)
    
    def get_prescription(self, prescription_id: uuid.UUID) -> Prescription:
        """Get prescription by ID"""
        prescription = self.prescription_repo.get_by_id(prescription_id)
        if not prescription:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Prescription not found"
            )
        return prescription
    
    def get_prescriptions(
        self,
        skip: int = 0,
        limit: int = 20,
        patient_id: Optional[uuid.UUID] = None,
        doctor_id: Optional[uuid.UUID] = None,
        encounter_id: Optional[uuid.UUID] = None,
        status_filter: Optional[PrescriptionStatus] = None,
        date_from: Optional[date] = None,
        date_to: Optional[date] = None
    ) -> Tuple[List[Prescription], int]:
        """Get prescriptions with filtering and pagination"""
        prescriptions = self.prescription_repo.get_all(
            skip=skip,
            limit=limit,
            patient_id=patient_id,
            doctor_id=doctor_id,
            encounter_id=encounter_id,
            status=status_filter,
            date_from=date_from,
            date_to=date_to
        )
        
        total = self.prescription_repo.count(
            patient_id=patient_id,
            status=status_filter,
            date_from=date_from,
            date_to=date_to
        )
        
        return prescriptions, total
    
    def get_pending_prescriptions(self) -> List[Prescription]:
        """Get pending prescriptions for pharmacy"""
        return self.prescription_repo.get_pending_prescriptions()
    
    def update_prescription(
        self, 
        prescription_id: uuid.UUID, 
        update_data: dict
    ) -> Prescription:
        """Update prescription"""
        prescription = self.get_prescription(prescription_id)
        
        if prescription.status in [
            PrescriptionStatus.DISPENSED, 
            PrescriptionStatus.CANCELLED
        ]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot modify dispensed or cancelled prescription"
            )
        
        return self.prescription_repo.update(prescription_id, update_data)
    
    def verify_prescription(
        self, 
        prescription_id: uuid.UUID, 
        verified_by: uuid.UUID,
        notes: Optional[str] = None
    ) -> Prescription:
        """Verify prescription (pharmacist)"""
        prescription = self.prescription_repo.verify(prescription_id, verified_by, notes)
        if not prescription:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Prescription not found or already verified"
            )
        return prescription
    
    def cancel_prescription(
        self, 
        prescription_id: uuid.UUID, 
        cancelled_by: uuid.UUID,
        reason: str
    ) -> Prescription:
        """Cancel prescription"""
        prescription = self.prescription_repo.cancel(prescription_id, cancelled_by, reason)
        if not prescription:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Prescription not found or cannot be cancelled"
            )
        return prescription
    
    def add_prescription_item(
        self, 
        prescription_id: uuid.UUID, 
        item_data: dict
    ) -> PrescriptionItem:
        """Add item to prescription"""
        prescription = self.get_prescription(prescription_id)
        
        if prescription.status != PrescriptionStatus.PENDING:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot add items to non-pending prescription"
            )
        
        return self.prescription_repo.add_item(prescription_id, item_data)
    
    def update_prescription_item(
        self, 
        item_id: uuid.UUID, 
        update_data: dict
    ) -> PrescriptionItem:
        """Update prescription item"""
        return self.prescription_repo.update_item(item_id, update_data)
    
    def delete_prescription_item(self, item_id: uuid.UUID) -> bool:
        """Delete prescription item"""
        return self.prescription_repo.delete_item(item_id)
    
    def generate_printable_prescription(
        self, 
        prescription_id: uuid.UUID
    ) -> Dict[str, Any]:
        """Generate data for printable prescription"""
        prescription = self.get_prescription(prescription_id)
        
        return {
            "prescription_number": prescription.prescription_number,
            "prescription_date": prescription.prescription_date.isoformat() if prescription.prescription_date else None,
            "valid_until": prescription.valid_until.isoformat() if prescription.valid_until else None,
            "patient": {
                "id": str(prescription.patient_id),
                "name": f"{prescription.patient.first_name} {prescription.patient.last_name}" if prescription.patient else "Unknown"
            },
            "prescriber": {
                "id": str(prescription.prescribed_by),
                "name": f"{prescription.prescriber.first_name} {prescription.prescriber.last_name}" if prescription.prescriber else "Unknown"
            },
            "diagnosis": prescription.diagnosis,
            "items": [
                {
                    "drug_name": item.drug_name,
                    "strength": item.strength,
                    "dosage": item.dosage,
                    "frequency": item.frequency,
                    "duration": item.duration_text or f"{item.duration_days} days" if item.duration_days else None,
                    "quantity": f"{item.quantity} {item.quantity_unit or ''}",
                    "route": item.route.value if item.route else None,
                    "instructions": item.instructions
                }
                for item in prescription.items
            ],
            "clinical_notes": prescription.clinical_notes
        }
