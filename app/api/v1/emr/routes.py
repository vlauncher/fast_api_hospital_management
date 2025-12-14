"""
EMR API Routes

API endpoints for Electronic Medical Records including encounters, diagnoses,
procedures, clinical notes, vital signs, and prescriptions.
"""

from fastapi import APIRouter, Depends, HTTPException, status, Query, Request
from typing import List, Optional
from datetime import date
import uuid
import math

from app.infrastructure.database import get_db
from app.core.permissions import require_permissions, Permissions
from app.domain.emr.service import (
    EncounterService, DiagnosisService, ProcedureService,
    ClinicalNoteService, VitalSignsService, PrescriptionService
)
from app.domain.emr.models import (
    EncounterStatus, EncounterType,
    DiagnosisType, DiagnosisCertainty,
    ProcedureStatus, NoteType, PrescriptionStatus
)
from app.api.v1.emr.schemas import (
    # Encounter schemas
    EncounterCreate, EncounterUpdate, EncounterAmend,
    EncounterResponse, EncounterListResponse,
    # Diagnosis schemas
    DiagnosisCreate, DiagnosisUpdate, DiagnosisResponse,
    # Procedure schemas
    ProcedureCreate, ProcedureUpdate, ProcedureComplete, ProcedureResponse,
    # Clinical note schemas
    ClinicalNoteCreate, ClinicalNoteUpdate, ClinicalNoteAddendum, ClinicalNoteResponse,
    # Vital signs schemas
    VitalSignsCreate, VitalSignsUpdate, VitalSignsResponse, VitalSignsTrends,
    # Prescription schemas
    PrescriptionCreate, PrescriptionUpdate, PrescriptionVerify, PrescriptionCancel,
    PrescriptionResponse, PrescriptionListResponse, PrintablePrescription,
    PrescriptionItemCreate, PrescriptionItemUpdate, PrescriptionItemResponse
)

router = APIRouter()


# ==================== Encounter Endpoints ====================

@router.post("/encounters", response_model=EncounterResponse, status_code=status.HTTP_201_CREATED)
def create_encounter(
    encounter_data: EncounterCreate,
    request: Request,
    db = Depends(get_db),
    current_user = Depends(require_permissions([Permissions.PATIENTS_UPDATE, "emr:create"]))
):
    """Create a new encounter"""
    service = EncounterService(db)
    encounter = service.create_encounter(
        patient_id=encounter_data.patient_id,
        doctor_id=encounter_data.doctor_id,
        encounter_type=encounter_data.encounter_type,
        created_by=uuid.UUID(current_user["sub"]),
        department_id=encounter_data.department_id,
        appointment_id=encounter_data.appointment_id,
        chief_complaint=encounter_data.chief_complaint,
        symptoms=encounter_data.symptoms,
        history_of_present_illness=encounter_data.history_of_present_illness
    )
    return encounter


@router.get("/encounters", response_model=EncounterListResponse)
def list_encounters(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    patient_id: Optional[uuid.UUID] = None,
    doctor_id: Optional[uuid.UUID] = None,
    department_id: Optional[uuid.UUID] = None,
    status_filter: Optional[EncounterStatus] = Query(None, alias="status"),
    encounter_type: Optional[EncounterType] = None,
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
    db = Depends(get_db),
    current_user = Depends(require_permissions([Permissions.PATIENTS_READ, "emr:read"]))
):
    """List encounters with filtering and pagination"""
    service = EncounterService(db)
    skip = (page - 1) * limit
    
    encounters, total = service.get_encounters(
        skip=skip,
        limit=limit,
        patient_id=patient_id,
        doctor_id=doctor_id,
        department_id=department_id,
        status_filter=status_filter,
        encounter_type=encounter_type,
        date_from=date_from,
        date_to=date_to
    )
    
    return EncounterListResponse(
        items=encounters,
        total=total,
        page=page,
        limit=limit,
        pages=math.ceil(total / limit) if total > 0 else 1
    )


@router.get("/encounters/patient/{patient_id}", response_model=List[EncounterResponse])
def get_patient_encounters(
    patient_id: uuid.UUID,
    limit: int = Query(50, ge=1, le=100),
    db = Depends(get_db),
    current_user = Depends(require_permissions([Permissions.PATIENTS_READ, "emr:read"]))
):
    """Get all encounters for a patient"""
    service = EncounterService(db)
    return service.get_patient_encounters(patient_id, limit)


@router.get("/encounters/{encounter_id}", response_model=EncounterResponse)
def get_encounter(
    encounter_id: uuid.UUID,
    db = Depends(get_db),
    current_user = Depends(require_permissions([Permissions.PATIENTS_READ, "emr:read"]))
):
    """Get encounter by ID"""
    service = EncounterService(db)
    return service.get_encounter(encounter_id)


@router.patch("/encounters/{encounter_id}", response_model=EncounterResponse)
def update_encounter(
    encounter_id: uuid.UUID,
    update_data: EncounterUpdate,
    request: Request,
    db = Depends(get_db),
    current_user = Depends(require_permissions([Permissions.PATIENTS_UPDATE, "emr:update"]))
):
    """Update encounter"""
    service = EncounterService(db)
    return service.update_encounter(
        encounter_id,
        update_data.model_dump(exclude_unset=True),
        uuid.UUID(current_user["sub"])
    )


@router.post("/encounters/{encounter_id}/complete", response_model=EncounterResponse)
def complete_encounter(
    encounter_id: uuid.UUID,
    db = Depends(get_db),
    current_user = Depends(require_permissions([Permissions.PATIENTS_UPDATE, "emr:update"]))
):
    """Mark encounter as completed"""
    service = EncounterService(db)
    return service.complete_encounter(encounter_id)


@router.post("/encounters/{encounter_id}/sign", response_model=EncounterResponse)
def sign_encounter(
    encounter_id: uuid.UUID,
    request: Request,
    db = Depends(get_db),
    current_user = Depends(require_permissions([Permissions.PATIENTS_UPDATE, "emr:sign"]))
):
    """Sign and lock an encounter"""
    service = EncounterService(db)
    return service.sign_encounter(encounter_id, uuid.UUID(current_user["sub"]))


@router.post("/encounters/{encounter_id}/amend", response_model=EncounterResponse)
def amend_encounter(
    encounter_id: uuid.UUID,
    amend_data: EncounterAmend,
    request: Request,
    db = Depends(get_db),
    current_user = Depends(require_permissions([Permissions.PATIENTS_UPDATE, "emr:sign"]))
):
    """Amend a signed encounter"""
    service = EncounterService(db)
    return service.amend_encounter(
        encounter_id,
        uuid.UUID(current_user["sub"]),
        amend_data.reason
    )


# ==================== Vital Signs Endpoints ====================

@router.post("/encounters/{encounter_id}/vitals", response_model=VitalSignsResponse, status_code=status.HTTP_201_CREATED)
def add_vital_signs(
    encounter_id: uuid.UUID,
    vitals_data: VitalSignsCreate,
    request: Request,
    db = Depends(get_db),
    current_user = Depends(require_permissions([Permissions.PATIENTS_UPDATE, "emr:update_vitals"]))
):
    """Add vital signs to an encounter"""
    service = EncounterService(db)
    return service.add_vital_signs(
        encounter_id,
        uuid.UUID(current_user["sub"]),
        vitals_data.model_dump(exclude_unset=True)
    )


@router.get("/encounters/{encounter_id}/vitals", response_model=List[VitalSignsResponse])
def get_encounter_vitals(
    encounter_id: uuid.UUID,
    db = Depends(get_db),
    current_user = Depends(require_permissions([Permissions.PATIENTS_READ, "emr:read"]))
):
    """Get all vital signs for an encounter"""
    service = EncounterService(db)
    return service.get_encounter_vitals(encounter_id)


@router.get("/vitals/patient/{patient_id}/trends", response_model=VitalSignsTrends)
def get_patient_vitals_trends(
    patient_id: uuid.UUID,
    db = Depends(get_db),
    current_user = Depends(require_permissions([Permissions.PATIENTS_READ, "emr:read"]))
):
    """Get vital signs trends for charting"""
    service = VitalSignsService(db)
    return service.get_vitals_trends(patient_id)


# ==================== Diagnosis Endpoints ====================

@router.post("/encounters/{encounter_id}/diagnoses", response_model=DiagnosisResponse, status_code=status.HTTP_201_CREATED)
def add_diagnosis(
    encounter_id: uuid.UUID,
    diagnosis_data: DiagnosisCreate,
    request: Request,
    db = Depends(get_db),
    current_user = Depends(require_permissions([Permissions.PATIENTS_UPDATE, "diagnoses:create"]))
):
    """Add diagnosis to an encounter"""
    service = DiagnosisService(db)
    return service.add_diagnosis(
        encounter_id=encounter_id,
        icd_10_code=diagnosis_data.icd_10_code,
        description=diagnosis_data.description,
        diagnosed_by=uuid.UUID(current_user["sub"]),
        diagnosis_type=diagnosis_data.diagnosis_type,
        certainty=diagnosis_data.certainty,
        onset_date=diagnosis_data.onset_date,
        is_chronic=diagnosis_data.is_chronic,
        is_principal=diagnosis_data.is_principal,
        notes=diagnosis_data.notes
    )


@router.get("/encounters/{encounter_id}/diagnoses", response_model=List[DiagnosisResponse])
def get_encounter_diagnoses(
    encounter_id: uuid.UUID,
    db = Depends(get_db),
    current_user = Depends(require_permissions([Permissions.PATIENTS_READ, "emr:read"]))
):
    """Get all diagnoses for an encounter"""
    service = DiagnosisService(db)
    return service.get_encounter_diagnoses(encounter_id)


@router.get("/diagnoses/patient/{patient_id}", response_model=List[DiagnosisResponse])
def get_patient_diagnoses(
    patient_id: uuid.UUID,
    active_only: bool = Query(True),
    db = Depends(get_db),
    current_user = Depends(require_permissions([Permissions.PATIENTS_READ, "emr:read"]))
):
    """Get all diagnoses for a patient"""
    service = DiagnosisService(db)
    return service.get_patient_diagnoses(patient_id, active_only)


@router.patch("/diagnoses/{diagnosis_id}", response_model=DiagnosisResponse)
def update_diagnosis(
    diagnosis_id: uuid.UUID,
    update_data: DiagnosisUpdate,
    db = Depends(get_db),
    current_user = Depends(require_permissions([Permissions.PATIENTS_UPDATE, "diagnoses:update"]))
):
    """Update diagnosis"""
    service = DiagnosisService(db)
    return service.update_diagnosis(diagnosis_id, update_data.model_dump(exclude_unset=True))


@router.delete("/diagnoses/{diagnosis_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_diagnosis(
    diagnosis_id: uuid.UUID,
    db = Depends(get_db),
    current_user = Depends(require_permissions([Permissions.PATIENTS_UPDATE, "diagnoses:delete"]))
):
    """Delete diagnosis"""
    service = DiagnosisService(db)
    if not service.delete_diagnosis(diagnosis_id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Diagnosis not found"
        )


# ==================== Procedure Endpoints ====================

@router.post("/encounters/{encounter_id}/procedures", response_model=ProcedureResponse, status_code=status.HTTP_201_CREATED)
def create_procedure(
    encounter_id: uuid.UUID,
    procedure_data: ProcedureCreate,
    request: Request,
    db = Depends(get_db),
    current_user = Depends(require_permissions([Permissions.PATIENTS_UPDATE, "procedures:create"]))
):
    """Create a new procedure"""
    service = ProcedureService(db)
    return service.create_procedure(
        encounter_id=encounter_id,
        cpt_code=procedure_data.cpt_code,
        description=procedure_data.description,
        created_by=uuid.UUID(current_user["sub"]),
        scheduled_date=procedure_data.scheduled_date,
        duration_minutes=procedure_data.duration_minutes,
        location=procedure_data.location,
        performed_by=procedure_data.performed_by,
        pre_procedure_diagnosis=procedure_data.pre_procedure_diagnosis,
        notes=procedure_data.notes
    )


@router.get("/encounters/{encounter_id}/procedures", response_model=List[ProcedureResponse])
def get_encounter_procedures(
    encounter_id: uuid.UUID,
    db = Depends(get_db),
    current_user = Depends(require_permissions([Permissions.PATIENTS_READ, "emr:read"]))
):
    """Get all procedures for an encounter"""
    service = ProcedureService(db)
    return service.get_encounter_procedures(encounter_id)


@router.get("/procedures/scheduled", response_model=List[ProcedureResponse])
def get_scheduled_procedures(
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
    doctor_id: Optional[uuid.UUID] = None,
    db = Depends(get_db),
    current_user = Depends(require_permissions([Permissions.PATIENTS_READ, "procedures:read"]))
):
    """Get scheduled procedures"""
    service = ProcedureService(db)
    return service.get_scheduled_procedures(date_from, date_to, doctor_id)


@router.post("/procedures/{procedure_id}/start", response_model=ProcedureResponse)
def start_procedure(
    procedure_id: uuid.UUID,
    db = Depends(get_db),
    current_user = Depends(require_permissions([Permissions.PATIENTS_UPDATE, "procedures:update"]))
):
    """Start a procedure"""
    service = ProcedureService(db)
    return service.start_procedure(procedure_id)


@router.post("/procedures/{procedure_id}/complete", response_model=ProcedureResponse)
def complete_procedure(
    procedure_id: uuid.UUID,
    complete_data: ProcedureComplete,
    db = Depends(get_db),
    current_user = Depends(require_permissions([Permissions.PATIENTS_UPDATE, "procedures:update"]))
):
    """Complete a procedure"""
    service = ProcedureService(db)
    return service.complete_procedure(
        procedure_id,
        findings=complete_data.findings,
        technique=complete_data.technique,
        complications=complete_data.complications,
        post_procedure_diagnosis=complete_data.post_procedure_diagnosis
    )


@router.post("/procedures/{procedure_id}/cancel", response_model=ProcedureResponse)
def cancel_procedure(
    procedure_id: uuid.UUID,
    db = Depends(get_db),
    current_user = Depends(require_permissions([Permissions.PATIENTS_UPDATE, "procedures:update"]))
):
    """Cancel a procedure"""
    service = ProcedureService(db)
    return service.cancel_procedure(procedure_id)


# ==================== Clinical Note Endpoints ====================

@router.post("/encounters/{encounter_id}/notes", response_model=ClinicalNoteResponse, status_code=status.HTTP_201_CREATED)
def create_clinical_note(
    encounter_id: uuid.UUID,
    note_data: ClinicalNoteCreate,
    request: Request,
    db = Depends(get_db),
    current_user = Depends(require_permissions([Permissions.PATIENTS_UPDATE, "clinical_notes:create"]))
):
    """Create a new clinical note"""
    service = ClinicalNoteService(db)
    return service.create_note(
        encounter_id=encounter_id,
        note_type=note_data.note_type,
        created_by=uuid.UUID(current_user["sub"]),
        title=note_data.title,
        subjective=note_data.subjective,
        objective=note_data.objective,
        assessment=note_data.assessment,
        plan=note_data.plan,
        content=note_data.content,
        is_draft=note_data.is_draft
    )


@router.get("/encounters/{encounter_id}/notes", response_model=List[ClinicalNoteResponse])
def get_encounter_notes(
    encounter_id: uuid.UUID,
    db = Depends(get_db),
    current_user = Depends(require_permissions([Permissions.PATIENTS_READ, "emr:read"]))
):
    """Get all clinical notes for an encounter"""
    service = ClinicalNoteService(db)
    return service.get_encounter_notes(encounter_id)


@router.get("/notes/drafts", response_model=List[ClinicalNoteResponse])
def get_my_draft_notes(
    request: Request,
    db = Depends(get_db),
    current_user = Depends(require_permissions([Permissions.PATIENTS_READ, "clinical_notes:read"]))
):
    """Get my draft notes"""
    service = ClinicalNoteService(db)
    return service.get_user_drafts(uuid.UUID(current_user["sub"]))


@router.patch("/notes/{note_id}", response_model=ClinicalNoteResponse)
def update_clinical_note(
    note_id: uuid.UUID,
    update_data: ClinicalNoteUpdate,
    db = Depends(get_db),
    current_user = Depends(require_permissions([Permissions.PATIENTS_UPDATE, "clinical_notes:update"]))
):
    """Update clinical note (supports auto-save)"""
    service = ClinicalNoteService(db)
    return service.update_note(note_id, update_data.model_dump(exclude_unset=True))


@router.post("/notes/{note_id}/sign", response_model=ClinicalNoteResponse)
def sign_clinical_note(
    note_id: uuid.UUID,
    request: Request,
    db = Depends(get_db),
    current_user = Depends(require_permissions([Permissions.PATIENTS_UPDATE, "clinical_notes:sign"]))
):
    """Sign a clinical note"""
    service = ClinicalNoteService(db)
    return service.sign_note(note_id, uuid.UUID(current_user["sub"]))


@router.post("/notes/{note_id}/addendum", response_model=ClinicalNoteResponse, status_code=status.HTTP_201_CREATED)
def create_addendum(
    note_id: uuid.UUID,
    addendum_data: ClinicalNoteAddendum,
    request: Request,
    db = Depends(get_db),
    current_user = Depends(require_permissions([Permissions.PATIENTS_UPDATE, "clinical_notes:update"]))
):
    """Create an addendum to a signed note"""
    service = ClinicalNoteService(db)
    return service.create_addendum(
        note_id,
        addendum_data.content,
        addendum_data.reason,
        uuid.UUID(current_user["sub"])
    )


# ==================== Prescription Endpoints ====================

@router.post("/prescriptions", response_model=PrescriptionResponse, status_code=status.HTTP_201_CREATED)
def create_prescription(
    prescription_data: PrescriptionCreate,
    request: Request,
    db = Depends(get_db),
    current_user = Depends(require_permissions([Permissions.PATIENTS_UPDATE, "prescriptions:create"]))
):
    """Create a new prescription"""
    service = PrescriptionService(db)
    
    # Convert items to dict format expected by service
    items = [item.model_dump() for item in prescription_data.items]
    
    return service.create_prescription(
        patient_id=prescription_data.patient_id,
        prescribed_by=uuid.UUID(current_user["sub"]),
        items=items,
        encounter_id=prescription_data.encounter_id,
        diagnosis=prescription_data.diagnosis,
        clinical_notes=prescription_data.clinical_notes,
        valid_until=prescription_data.valid_until
    )


@router.get("/prescriptions", response_model=PrescriptionListResponse)
def list_prescriptions(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    patient_id: Optional[uuid.UUID] = None,
    doctor_id: Optional[uuid.UUID] = None,
    encounter_id: Optional[uuid.UUID] = None,
    status_filter: Optional[PrescriptionStatus] = Query(None, alias="status"),
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
    db = Depends(get_db),
    current_user = Depends(require_permissions([Permissions.PATIENTS_READ, "prescriptions:read"]))
):
    """List prescriptions with filtering and pagination"""
    service = PrescriptionService(db)
    skip = (page - 1) * limit
    
    prescriptions, total = service.get_prescriptions(
        skip=skip,
        limit=limit,
        patient_id=patient_id,
        doctor_id=doctor_id,
        encounter_id=encounter_id,
        status_filter=status_filter,
        date_from=date_from,
        date_to=date_to
    )
    
    return PrescriptionListResponse(
        items=prescriptions,
        total=total,
        page=page,
        limit=limit,
        pages=math.ceil(total / limit) if total > 0 else 1
    )


@router.get("/prescriptions/pending", response_model=List[PrescriptionResponse])
def get_pending_prescriptions(
    db = Depends(get_db),
    current_user = Depends(require_permissions([Permissions.PATIENTS_READ, "prescriptions:read"]))
):
    """Get pending prescriptions for pharmacy"""
    service = PrescriptionService(db)
    return service.get_pending_prescriptions()


@router.get("/prescriptions/{prescription_id}", response_model=PrescriptionResponse)
def get_prescription(
    prescription_id: uuid.UUID,
    db = Depends(get_db),
    current_user = Depends(require_permissions([Permissions.PATIENTS_READ, "prescriptions:read"]))
):
    """Get prescription by ID"""
    service = PrescriptionService(db)
    return service.get_prescription(prescription_id)


@router.patch("/prescriptions/{prescription_id}", response_model=PrescriptionResponse)
def update_prescription(
    prescription_id: uuid.UUID,
    update_data: PrescriptionUpdate,
    db = Depends(get_db),
    current_user = Depends(require_permissions([Permissions.PATIENTS_UPDATE, "prescriptions:update"]))
):
    """Update prescription"""
    service = PrescriptionService(db)
    return service.update_prescription(prescription_id, update_data.model_dump(exclude_unset=True))


@router.post("/prescriptions/{prescription_id}/verify", response_model=PrescriptionResponse)
def verify_prescription(
    prescription_id: uuid.UUID,
    verify_data: PrescriptionVerify,
    request: Request,
    db = Depends(get_db),
    current_user = Depends(require_permissions([Permissions.PATIENTS_UPDATE, "prescriptions:verify"]))
):
    """Verify prescription (pharmacist)"""
    service = PrescriptionService(db)
    return service.verify_prescription(
        prescription_id,
        uuid.UUID(current_user["sub"]),
        verify_data.notes
    )


@router.post("/prescriptions/{prescription_id}/cancel", response_model=PrescriptionResponse)
def cancel_prescription(
    prescription_id: uuid.UUID,
    cancel_data: PrescriptionCancel,
    request: Request,
    db = Depends(get_db),
    current_user = Depends(require_permissions([Permissions.PATIENTS_UPDATE, "prescriptions:update"]))
):
    """Cancel prescription"""
    service = PrescriptionService(db)
    return service.cancel_prescription(
        prescription_id,
        uuid.UUID(current_user["sub"]),
        cancel_data.reason
    )


@router.get("/prescriptions/{prescription_id}/print", response_model=PrintablePrescription)
def get_printable_prescription(
    prescription_id: uuid.UUID,
    db = Depends(get_db),
    current_user = Depends(require_permissions([Permissions.PATIENTS_READ, "prescriptions:read"]))
):
    """Generate printable prescription"""
    service = PrescriptionService(db)
    return service.generate_printable_prescription(prescription_id)


@router.post("/prescriptions/{prescription_id}/items", response_model=PrescriptionItemResponse, status_code=status.HTTP_201_CREATED)
def add_prescription_item(
    prescription_id: uuid.UUID,
    item_data: PrescriptionItemCreate,
    db = Depends(get_db),
    current_user = Depends(require_permissions([Permissions.PATIENTS_UPDATE, "prescriptions:update"]))
):
    """Add item to prescription"""
    service = PrescriptionService(db)
    return service.add_prescription_item(prescription_id, item_data.model_dump())


@router.patch("/prescriptions/items/{item_id}", response_model=PrescriptionItemResponse)
def update_prescription_item(
    item_id: uuid.UUID,
    update_data: PrescriptionItemUpdate,
    db = Depends(get_db),
    current_user = Depends(require_permissions([Permissions.PATIENTS_UPDATE, "prescriptions:update"]))
):
    """Update prescription item"""
    service = PrescriptionService(db)
    return service.update_prescription_item(item_id, update_data.model_dump(exclude_unset=True))


@router.delete("/prescriptions/items/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_prescription_item(
    item_id: uuid.UUID,
    db = Depends(get_db),
    current_user = Depends(require_permissions([Permissions.PATIENTS_UPDATE, "prescriptions:update"]))
):
    """Delete prescription item"""
    service = PrescriptionService(db)
    if not service.delete_prescription_item(item_id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Prescription item not found"
        )
