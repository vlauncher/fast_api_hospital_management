"""
EMR Repository Layer

Provides data access operations for encounters, diagnoses, procedures, 
clinical notes, vital signs, and prescriptions.
"""

from typing import Optional, List
from sqlalchemy import select, update, delete, and_, or_, func
from sqlalchemy.orm import joinedload
from datetime import datetime, date
import uuid

from app.domain.emr.models import (
    Encounter, EncounterStatus, EncounterType,
    Diagnosis, DiagnosisType, DiagnosisCertainty,
    Procedure, ProcedureStatus,
    ClinicalNote, NoteType,
    VitalSigns,
    Prescription, PrescriptionStatus, PrescriptionItem
)


class EncounterRepository:
    """Repository for encounter data access operations"""
    
    def __init__(self, db):
        self.db = db
    
    def create(self, encounter_data: dict) -> Encounter:
        """Create a new encounter"""
        encounter = Encounter(**encounter_data)
        self.db.add(encounter)
        self.db.commit()
        self.db.refresh(encounter)
        return encounter
    
    def get_by_id(self, encounter_id: uuid.UUID) -> Optional[Encounter]:
        """Get encounter by ID with relationships"""
        return self.db.query(Encounter).options(
            joinedload(Encounter.patient),
            joinedload(Encounter.doctor),
            joinedload(Encounter.department),
            joinedload(Encounter.diagnoses),
            joinedload(Encounter.prescriptions)
        ).filter(Encounter.id == encounter_id).first()
    
    def get_by_encounter_number(self, encounter_number: str) -> Optional[Encounter]:
        """Get encounter by encounter number"""
        return self.db.query(Encounter).filter(
            Encounter.encounter_number == encounter_number
        ).first()
    
    def get_all(
        self,
        skip: int = 0,
        limit: int = 20,
        patient_id: Optional[uuid.UUID] = None,
        doctor_id: Optional[uuid.UUID] = None,
        department_id: Optional[uuid.UUID] = None,
        status: Optional[EncounterStatus] = None,
        encounter_type: Optional[EncounterType] = None,
        date_from: Optional[date] = None,
        date_to: Optional[date] = None
    ) -> List[Encounter]:
        """Get encounters with filtering"""
        query = self.db.query(Encounter).options(
            joinedload(Encounter.patient),
            joinedload(Encounter.doctor)
        )
        
        if patient_id:
            query = query.filter(Encounter.patient_id == patient_id)
        if doctor_id:
            query = query.filter(Encounter.doctor_id == doctor_id)
        if department_id:
            query = query.filter(Encounter.department_id == department_id)
        if status:
            query = query.filter(Encounter.status == status)
        if encounter_type:
            query = query.filter(Encounter.encounter_type == encounter_type)
        if date_from:
            query = query.filter(func.date(Encounter.encounter_date) >= date_from)
        if date_to:
            query = query.filter(func.date(Encounter.encounter_date) <= date_to)
        
        return query.order_by(Encounter.encounter_date.desc()).offset(skip).limit(limit).all()
    
    def get_patient_encounters(self, patient_id: uuid.UUID, limit: int = 50) -> List[Encounter]:
        """Get all encounters for a patient"""
        return self.db.query(Encounter).options(
            joinedload(Encounter.doctor),
            joinedload(Encounter.diagnoses)
        ).filter(
            Encounter.patient_id == patient_id
        ).order_by(Encounter.encounter_date.desc()).limit(limit).all()
    
    def count(
        self,
        patient_id: Optional[uuid.UUID] = None,
        doctor_id: Optional[uuid.UUID] = None,
        status: Optional[EncounterStatus] = None,
        date_from: Optional[date] = None,
        date_to: Optional[date] = None
    ) -> int:
        """Count encounters with filters"""
        query = self.db.query(func.count(Encounter.id))
        
        if patient_id:
            query = query.filter(Encounter.patient_id == patient_id)
        if doctor_id:
            query = query.filter(Encounter.doctor_id == doctor_id)
        if status:
            query = query.filter(Encounter.status == status)
        if date_from:
            query = query.filter(func.date(Encounter.encounter_date) >= date_from)
        if date_to:
            query = query.filter(func.date(Encounter.encounter_date) <= date_to)
        
        return query.scalar()
    
    def update(self, encounter_id: uuid.UUID, update_data: dict) -> Optional[Encounter]:
        """Update encounter"""
        encounter = self.db.query(Encounter).filter(
            Encounter.id == encounter_id
        ).first()
        if encounter:
            for key, value in update_data.items():
                if hasattr(encounter, key) and value is not None:
                    setattr(encounter, key, value)
            self.db.commit()
            self.db.refresh(encounter)
        return encounter
    
    def sign_encounter(self, encounter_id: uuid.UUID, signed_by: uuid.UUID) -> Optional[Encounter]:
        """Sign and lock an encounter"""
        encounter = self.get_by_id(encounter_id)
        if encounter and encounter.status in [EncounterStatus.IN_PROGRESS, EncounterStatus.COMPLETED]:
            encounter.status = EncounterStatus.SIGNED
            encounter.signed_at = datetime.utcnow()
            encounter.signed_by = signed_by
            encounter.is_locked = True
            encounter.lock_reason = "Signed by provider"
            self.db.commit()
            self.db.refresh(encounter)
        return encounter
    
    def amend_encounter(
        self, 
        encounter_id: uuid.UUID, 
        amended_by: uuid.UUID, 
        reason: str
    ) -> Optional[Encounter]:
        """Create amendment for signed encounter"""
        encounter = self.get_by_id(encounter_id)
        if encounter and encounter.status == EncounterStatus.SIGNED:
            encounter.status = EncounterStatus.AMENDED
            encounter.amended_at = datetime.utcnow()
            encounter.amended_by = amended_by
            encounter.amendment_reason = reason
            encounter.is_locked = False  # Temporarily unlock for amendment
            self.db.commit()
            self.db.refresh(encounter)
        return encounter


class DiagnosisRepository:
    """Repository for diagnosis data access operations"""
    
    def __init__(self, db):
        self.db = db
    
    def create(self, diagnosis_data: dict) -> Diagnosis:
        """Create a new diagnosis"""
        diagnosis = Diagnosis(**diagnosis_data)
        self.db.add(diagnosis)
        self.db.commit()
        self.db.refresh(diagnosis)
        return diagnosis
    
    def get_by_id(self, diagnosis_id: uuid.UUID) -> Optional[Diagnosis]:
        """Get diagnosis by ID"""
        return self.db.query(Diagnosis).options(
            joinedload(Diagnosis.encounter),
            joinedload(Diagnosis.diagnoser)
        ).filter(Diagnosis.id == diagnosis_id).first()
    
    def get_by_encounter(self, encounter_id: uuid.UUID) -> List[Diagnosis]:
        """Get all diagnoses for an encounter"""
        return self.db.query(Diagnosis).filter(
            Diagnosis.encounter_id == encounter_id
        ).order_by(Diagnosis.diagnosis_type, Diagnosis.created_at).all()
    
    def get_patient_diagnoses(
        self, 
        patient_id: uuid.UUID,
        active_only: bool = True
    ) -> List[Diagnosis]:
        """Get all diagnoses for a patient (across encounters)"""
        query = self.db.query(Diagnosis).join(
            Encounter, Diagnosis.encounter_id == Encounter.id
        ).filter(Encounter.patient_id == patient_id)
        
        if active_only:
            query = query.filter(Diagnosis.resolution_date.is_(None))
        
        return query.order_by(Diagnosis.diagnosed_at.desc()).all()
    
    def update(self, diagnosis_id: uuid.UUID, update_data: dict) -> Optional[Diagnosis]:
        """Update diagnosis"""
        diagnosis = self.db.query(Diagnosis).filter(
            Diagnosis.id == diagnosis_id
        ).first()
        if diagnosis:
            for key, value in update_data.items():
                if hasattr(diagnosis, key) and value is not None:
                    setattr(diagnosis, key, value)
            self.db.commit()
            self.db.refresh(diagnosis)
        return diagnosis
    
    def delete(self, diagnosis_id: uuid.UUID) -> bool:
        """Delete diagnosis"""
        result = self.db.query(Diagnosis).filter(
            Diagnosis.id == diagnosis_id
        ).delete()
        self.db.commit()
        return result > 0
    
    def search_by_icd_code(self, icd_code: str, limit: int = 20) -> List[Diagnosis]:
        """Search diagnoses by ICD-10 code"""
        return self.db.query(Diagnosis).filter(
            Diagnosis.icd_10_code.ilike(f"{icd_code}%")
        ).limit(limit).all()


class ProcedureRepository:
    """Repository for procedure data access operations"""
    
    def __init__(self, db):
        self.db = db
    
    def create(self, procedure_data: dict) -> Procedure:
        """Create a new procedure"""
        procedure = Procedure(**procedure_data)
        self.db.add(procedure)
        self.db.commit()
        self.db.refresh(procedure)
        return procedure
    
    def get_by_id(self, procedure_id: uuid.UUID) -> Optional[Procedure]:
        """Get procedure by ID"""
        return self.db.query(Procedure).options(
            joinedload(Procedure.encounter),
            joinedload(Procedure.performer)
        ).filter(Procedure.id == procedure_id).first()
    
    def get_by_encounter(self, encounter_id: uuid.UUID) -> List[Procedure]:
        """Get all procedures for an encounter"""
        return self.db.query(Procedure).filter(
            Procedure.encounter_id == encounter_id
        ).order_by(Procedure.procedure_date).all()
    
    def get_scheduled_procedures(
        self, 
        date_from: Optional[date] = None, 
        date_to: Optional[date] = None,
        doctor_id: Optional[uuid.UUID] = None
    ) -> List[Procedure]:
        """Get scheduled procedures"""
        query = self.db.query(Procedure).filter(
            Procedure.status == ProcedureStatus.SCHEDULED
        )
        
        if date_from:
            query = query.filter(func.date(Procedure.scheduled_date) >= date_from)
        if date_to:
            query = query.filter(func.date(Procedure.scheduled_date) <= date_to)
        if doctor_id:
            query = query.filter(Procedure.performed_by == doctor_id)
        
        return query.order_by(Procedure.scheduled_date).all()
    
    def update(self, procedure_id: uuid.UUID, update_data: dict) -> Optional[Procedure]:
        """Update procedure"""
        procedure = self.db.query(Procedure).filter(
            Procedure.id == procedure_id
        ).first()
        if procedure:
            for key, value in update_data.items():
                if hasattr(procedure, key) and value is not None:
                    setattr(procedure, key, value)
            self.db.commit()
            self.db.refresh(procedure)
        return procedure
    
    def update_status(
        self, 
        procedure_id: uuid.UUID, 
        status: ProcedureStatus
    ) -> Optional[Procedure]:
        """Update procedure status"""
        procedure = self.get_by_id(procedure_id)
        if procedure:
            procedure.status = status
            if status == ProcedureStatus.IN_PROGRESS:
                procedure.procedure_date = datetime.utcnow()
            elif status == ProcedureStatus.COMPLETED:
                if procedure.procedure_date:
                    procedure.actual_duration_minutes = int(
                        (datetime.utcnow() - procedure.procedure_date).total_seconds() / 60
                    )
            self.db.commit()
            self.db.refresh(procedure)
        return procedure


class ClinicalNoteRepository:
    """Repository for clinical note data access operations"""
    
    def __init__(self, db):
        self.db = db
    
    def create(self, note_data: dict) -> ClinicalNote:
        """Create a new clinical note"""
        note = ClinicalNote(**note_data)
        self.db.add(note)
        self.db.commit()
        self.db.refresh(note)
        return note
    
    def get_by_id(self, note_id: uuid.UUID) -> Optional[ClinicalNote]:
        """Get clinical note by ID"""
        return self.db.query(ClinicalNote).options(
            joinedload(ClinicalNote.encounter),
            joinedload(ClinicalNote.author),
            joinedload(ClinicalNote.addendums)
        ).filter(ClinicalNote.id == note_id).first()
    
    def get_by_encounter(self, encounter_id: uuid.UUID) -> List[ClinicalNote]:
        """Get all notes for an encounter"""
        return self.db.query(ClinicalNote).filter(
            and_(
                ClinicalNote.encounter_id == encounter_id,
                ClinicalNote.is_addendum == False
            )
        ).order_by(ClinicalNote.created_at).all()
    
    def get_drafts_by_user(self, user_id: uuid.UUID) -> List[ClinicalNote]:
        """Get draft notes for a user"""
        return self.db.query(ClinicalNote).filter(
            and_(
                ClinicalNote.created_by == user_id,
                ClinicalNote.is_draft == True
            )
        ).order_by(ClinicalNote.updated_at.desc()).all()
    
    def update(self, note_id: uuid.UUID, update_data: dict) -> Optional[ClinicalNote]:
        """Update clinical note"""
        note = self.db.query(ClinicalNote).filter(
            ClinicalNote.id == note_id
        ).first()
        if note and not note.is_locked:
            for key, value in update_data.items():
                if hasattr(note, key) and value is not None:
                    setattr(note, key, value)
            note.last_auto_save = datetime.utcnow()
            self.db.commit()
            self.db.refresh(note)
        return note
    
    def sign_note(self, note_id: uuid.UUID, signed_by: uuid.UUID) -> Optional[ClinicalNote]:
        """Sign a clinical note"""
        note = self.get_by_id(note_id)
        if note and not note.is_signed:
            note.is_signed = True
            note.signed_at = datetime.utcnow()
            note.signed_by = signed_by
            note.is_draft = False
            note.is_locked = True
            self.db.commit()
            self.db.refresh(note)
        return note
    
    def create_addendum(
        self, 
        parent_note_id: uuid.UUID, 
        content: str, 
        reason: str,
        created_by: uuid.UUID
    ) -> ClinicalNote:
        """Create an addendum to an existing note"""
        parent_note = self.get_by_id(parent_note_id)
        if not parent_note:
            return None
        
        addendum_data = {
            "encounter_id": parent_note.encounter_id,
            "note_type": parent_note.note_type,
            "title": f"Addendum to {parent_note.title or 'Note'}",
            "content": content,
            "is_addendum": True,
            "parent_note_id": parent_note_id,
            "addendum_reason": reason,
            "created_by": created_by,
            "is_draft": True
        }
        
        return self.create(addendum_data)


class VitalSignsRepository:
    """Repository for vital signs data access operations"""
    
    def __init__(self, db):
        self.db = db
    
    def create(self, vitals_data: dict) -> VitalSigns:
        """Create a new vital signs record"""
        vitals = VitalSigns(**vitals_data)
        vitals.calculate_bmi()
        self.db.add(vitals)
        self.db.commit()
        self.db.refresh(vitals)
        return vitals
    
    def get_by_id(self, vitals_id: uuid.UUID) -> Optional[VitalSigns]:
        """Get vital signs by ID"""
        return self.db.query(VitalSigns).options(
            joinedload(VitalSigns.encounter),
            joinedload(VitalSigns.recorder)
        ).filter(VitalSigns.id == vitals_id).first()
    
    def get_by_encounter(self, encounter_id: uuid.UUID) -> List[VitalSigns]:
        """Get all vital signs for an encounter"""
        return self.db.query(VitalSigns).filter(
            VitalSigns.encounter_id == encounter_id
        ).order_by(VitalSigns.recorded_at.desc()).all()
    
    def get_latest_for_encounter(self, encounter_id: uuid.UUID) -> Optional[VitalSigns]:
        """Get latest vital signs for an encounter"""
        return self.db.query(VitalSigns).filter(
            VitalSigns.encounter_id == encounter_id
        ).order_by(VitalSigns.recorded_at.desc()).first()
    
    def get_patient_vitals_history(
        self, 
        patient_id: uuid.UUID, 
        limit: int = 50
    ) -> List[VitalSigns]:
        """Get vital signs history for a patient"""
        return self.db.query(VitalSigns).filter(
            VitalSigns.patient_id == patient_id
        ).order_by(VitalSigns.recorded_at.desc()).limit(limit).all()
    
    def update(self, vitals_id: uuid.UUID, update_data: dict) -> Optional[VitalSigns]:
        """Update vital signs"""
        vitals = self.db.query(VitalSigns).filter(
            VitalSigns.id == vitals_id
        ).first()
        if vitals:
            for key, value in update_data.items():
                if hasattr(vitals, key) and value is not None:
                    setattr(vitals, key, value)
            vitals.calculate_bmi()
            self.db.commit()
            self.db.refresh(vitals)
        return vitals


class PrescriptionRepository:
    """Repository for prescription data access operations"""
    
    def __init__(self, db):
        self.db = db
    
    def create(self, prescription_data: dict, items: List[dict] = None) -> Prescription:
        """Create a new prescription with items"""
        prescription = Prescription(**prescription_data)
        self.db.add(prescription)
        self.db.flush()  # Get the ID
        
        if items:
            for item_data in items:
                item_data["prescription_id"] = prescription.id
                item = PrescriptionItem(**item_data)
                self.db.add(item)
        
        self.db.commit()
        self.db.refresh(prescription)
        return prescription
    
    def get_by_id(self, prescription_id: uuid.UUID) -> Optional[Prescription]:
        """Get prescription by ID with items"""
        return self.db.query(Prescription).options(
            joinedload(Prescription.patient),
            joinedload(Prescription.prescriber),
            joinedload(Prescription.encounter),
            joinedload(Prescription.items)
        ).filter(Prescription.id == prescription_id).first()
    
    def get_by_prescription_number(self, prescription_number: str) -> Optional[Prescription]:
        """Get prescription by prescription number"""
        return self.db.query(Prescription).filter(
            Prescription.prescription_number == prescription_number
        ).first()
    
    def get_all(
        self,
        skip: int = 0,
        limit: int = 20,
        patient_id: Optional[uuid.UUID] = None,
        doctor_id: Optional[uuid.UUID] = None,
        encounter_id: Optional[uuid.UUID] = None,
        status: Optional[PrescriptionStatus] = None,
        date_from: Optional[date] = None,
        date_to: Optional[date] = None
    ) -> List[Prescription]:
        """Get prescriptions with filtering"""
        query = self.db.query(Prescription).options(
            joinedload(Prescription.patient),
            joinedload(Prescription.prescriber),
            joinedload(Prescription.items)
        )
        
        if patient_id:
            query = query.filter(Prescription.patient_id == patient_id)
        if doctor_id:
            query = query.filter(Prescription.prescribed_by == doctor_id)
        if encounter_id:
            query = query.filter(Prescription.encounter_id == encounter_id)
        if status:
            query = query.filter(Prescription.status == status)
        if date_from:
            query = query.filter(func.date(Prescription.prescription_date) >= date_from)
        if date_to:
            query = query.filter(func.date(Prescription.prescription_date) <= date_to)
        
        return query.order_by(Prescription.prescription_date.desc()).offset(skip).limit(limit).all()
    
    def get_pending_prescriptions(self) -> List[Prescription]:
        """Get pending prescriptions (for pharmacy)"""
        return self.db.query(Prescription).options(
            joinedload(Prescription.patient),
            joinedload(Prescription.items)
        ).filter(
            Prescription.status == PrescriptionStatus.PENDING
        ).order_by(Prescription.prescription_date).all()
    
    def count(
        self,
        patient_id: Optional[uuid.UUID] = None,
        status: Optional[PrescriptionStatus] = None,
        date_from: Optional[date] = None,
        date_to: Optional[date] = None
    ) -> int:
        """Count prescriptions with filters"""
        query = self.db.query(func.count(Prescription.id))
        
        if patient_id:
            query = query.filter(Prescription.patient_id == patient_id)
        if status:
            query = query.filter(Prescription.status == status)
        if date_from:
            query = query.filter(func.date(Prescription.prescription_date) >= date_from)
        if date_to:
            query = query.filter(func.date(Prescription.prescription_date) <= date_to)
        
        return query.scalar()
    
    def update(self, prescription_id: uuid.UUID, update_data: dict) -> Optional[Prescription]:
        """Update prescription"""
        prescription = self.db.query(Prescription).filter(
            Prescription.id == prescription_id
        ).first()
        if prescription:
            for key, value in update_data.items():
                if hasattr(prescription, key) and value is not None:
                    setattr(prescription, key, value)
            self.db.commit()
            self.db.refresh(prescription)
        return prescription
    
    def verify(self, prescription_id: uuid.UUID, verified_by: uuid.UUID, notes: str = None) -> Optional[Prescription]:
        """Verify a prescription (pharmacist)"""
        prescription = self.get_by_id(prescription_id)
        if prescription and prescription.status == PrescriptionStatus.PENDING:
            prescription.status = PrescriptionStatus.VERIFIED
            prescription.verified_by = verified_by
            prescription.verified_at = datetime.utcnow()
            prescription.verification_notes = notes
            self.db.commit()
            self.db.refresh(prescription)
        return prescription
    
    def cancel(
        self, 
        prescription_id: uuid.UUID, 
        cancelled_by: uuid.UUID, 
        reason: str
    ) -> Optional[Prescription]:
        """Cancel a prescription"""
        prescription = self.get_by_id(prescription_id)
        if prescription and prescription.status not in [
            PrescriptionStatus.DISPENSED, 
            PrescriptionStatus.CANCELLED
        ]:
            prescription.status = PrescriptionStatus.CANCELLED
            prescription.cancelled_at = datetime.utcnow()
            prescription.cancelled_by = cancelled_by
            prescription.cancellation_reason = reason
            self.db.commit()
            self.db.refresh(prescription)
        return prescription
    
    def add_item(self, prescription_id: uuid.UUID, item_data: dict) -> PrescriptionItem:
        """Add item to prescription"""
        item_data["prescription_id"] = prescription_id
        item = PrescriptionItem(**item_data)
        self.db.add(item)
        self.db.commit()
        self.db.refresh(item)
        return item
    
    def update_item(self, item_id: uuid.UUID, update_data: dict) -> Optional[PrescriptionItem]:
        """Update prescription item"""
        item = self.db.query(PrescriptionItem).filter(
            PrescriptionItem.id == item_id
        ).first()
        if item:
            for key, value in update_data.items():
                if hasattr(item, key) and value is not None:
                    setattr(item, key, value)
            self.db.commit()
            self.db.refresh(item)
        return item
    
    def delete_item(self, item_id: uuid.UUID) -> bool:
        """Delete prescription item"""
        result = self.db.query(PrescriptionItem).filter(
            PrescriptionItem.id == item_id
        ).delete()
        self.db.commit()
        return result > 0
