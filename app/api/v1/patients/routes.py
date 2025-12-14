from fastapi import APIRouter, Depends, HTTPException, status, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional
import uuid
import math

from app.core.permissions import require_permissions, Permissions
from app.domain.patients.service import (
    PatientService, 
    EmergencyContactService, 
    InsuranceService,
    PatientVisitService
)
from app.api.v1.patients.schemas import (
    PatientCreate,
    PatientResponse,
    PatientUpdate,
    PatientListResponse,
    EmergencyContactCreate,
    EmergencyContactResponse,
    EmergencyContactUpdate,
    InsuranceCreate,
    InsuranceResponse,
    InsuranceUpdate,
    PatientVisitCreate,
    PatientVisitResponse,
    PatientVisitUpdate,
    PatientVisitListResponse,
    SuccessResponse
)
from app.infrastructure.database import get_db

router = APIRouter(prefix="/patients", tags=["Patients"])


# Patient endpoints
@router.post("/", response_model=PatientResponse, status_code=status.HTTP_201_CREATED)
async def create_patient(
    patient_data: PatientCreate,
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """Create a new patient"""
    user_payload = require_permissions([Permissions.PATIENTS_CREATE])(request)
    user_id = uuid.UUID(user_payload["sub"])
    user_department = user_payload.get("department_id")
    
    patient_service = PatientService(db)
    patient = await patient_service.create_patient(patient_data, user_id)
    
    # Check access permissions
    if not patient_service.can_access_patient(
        user_permissions=user_payload.get("permissions", []),
        user_id=str(user_id),
        user_department=user_department,
        patient=patient
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions to access this patient"
        )
    
    return PatientResponse.from_orm(patient)


@router.get("/", response_model=PatientListResponse, status_code=status.HTTP_200_OK)
async def get_patients(
    request: Request,
    db: AsyncSession = Depends(get_db),
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    is_active: Optional[bool] = None,
    search: Optional[str] = None,
    blood_type: Optional[str] = None,
    gender: Optional[str] = None,
    date_of_birth_from: Optional[str] = None,
    date_of_birth_to: Optional[str] = None
):
    """Get patients with filtering and pagination"""
    user_payload = require_permissions([Permissions.PATIENTS_READ])(request)
    
    # Parse date filters
    from datetime import datetime
    dob_from = None
    dob_to = None
    
    if date_of_birth_from:
        try:
            dob_from = datetime.strptime(date_of_birth_from, "%Y-%m-%d").date()
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid date_of_birth_from format. Use YYYY-MM-DD"
            )
    
    if date_of_birth_to:
        try:
            dob_to = datetime.strptime(date_of_birth_to, "%Y-%m-%d").date()
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid date_of_birth_to format. Use YYYY-MM-DD"
            )
    
    patient_service = PatientService(db)
    patients = await patient_service.get_patients(
        skip=skip,
        limit=limit,
        is_active=is_active,
        search=search,
        blood_type=blood_type,
        gender=gender,
        date_of_birth_from=dob_from,
        date_of_birth_to=dob_to
    )
    
    total = await patient_service.count_patients(
        is_active=is_active,
        blood_type=blood_type,
        gender=gender
    )
    
    pages = math.ceil(total / limit) if limit > 0 else 0
    
    return PatientListResponse(
        items=[PatientResponse.from_orm(patient) for patient in patients],
        total=total,
        page=skip // limit + 1 if limit > 0 else 1,
        limit=limit,
        pages=pages
    )


@router.get("/{patient_id}", response_model=PatientResponse, status_code=status.HTTP_200_OK)
async def get_patient(
    patient_id: uuid.UUID,
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """Get patient by ID"""
    user_payload = require_permissions([Permissions.PATIENTS_READ])(request)
    user_id = user_payload["sub"]
    user_department = user_payload.get("department_id")
    
    patient_service = PatientService(db)
    patient = await patient_service.get_patient_by_id(patient_id)
    
    if not patient:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Patient not found"
        )
    
    # Check access permissions
    if not patient_service.can_access_patient(
        user_permissions=user_payload.get("permissions", []),
        user_id=user_id,
        user_department=user_department,
        patient=patient
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions to access this patient"
        )
    
    return PatientResponse.from_orm(patient)


@router.get("/number/{patient_number}", response_model=PatientResponse, status_code=status.HTTP_200_OK)
async def get_patient_by_number(
    patient_number: str,
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """Get patient by patient number"""
    user_payload = require_permissions([Permissions.PATIENTS_READ])(request)
    user_id = user_payload["sub"]
    user_department = user_payload.get("department_id")
    
    patient_service = PatientService(db)
    patient = await patient_service.get_patient_by_number(patient_number)
    
    if not patient:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Patient not found"
        )
    
    # Check access permissions
    if not patient_service.can_access_patient(
        user_permissions=user_payload.get("permissions", []),
        user_id=user_id,
        user_department=user_department,
        patient=patient
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions to access this patient"
        )
    
    return PatientResponse.from_orm(patient)


@router.put("/{patient_id}", response_model=PatientResponse, status_code=status.HTTP_200_OK)
async def update_patient(
    patient_id: uuid.UUID,
    patient_data: PatientUpdate,
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """Update patient information"""
    user_payload = require_permissions([Permissions.PATIENTS_UPDATE])(request)
    user_id = uuid.UUID(user_payload["sub"])
    user_department = user_payload.get("department_id")
    
    patient_service = PatientService(db)
    
    # First get the patient to check permissions
    patient = await patient_service.get_patient_by_id(patient_id)
    if not patient:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Patient not found"
        )
    
    # Check modify permissions
    if not patient_service.can_modify_patient(
        user_permissions=user_payload.get("permissions", []),
        user_id=str(user_id),
        user_department=user_department,
        patient=patient
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions to modify this patient"
        )
    
    updated_patient = await patient_service.update_patient(patient_id, patient_data, user_id)
    
    return PatientResponse.from_orm(updated_patient)


@router.post("/{patient_id}/deactivate", status_code=status.HTTP_200_OK)
async def deactivate_patient(
    patient_id: uuid.UUID,
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """Deactivate patient record"""
    user_payload = require_permissions([Permissions.PATIENTS_UPDATE])(request)
    user_id = user_payload["sub"]
    user_department = user_payload.get("department_id")
    
    patient_service = PatientService(db)
    
    # First get the patient to check permissions
    patient = await patient_service.get_patient_by_id(patient_id)
    if not patient:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Patient not found"
        )
    
    # Check modify permissions
    if not patient_service.can_modify_patient(
        user_permissions=user_payload.get("permissions", []),
        user_id=user_id,
        user_department=user_department,
        patient=patient
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions to modify this patient"
        )
    
    await patient_service.deactivate_patient(patient_id)
    
    return SuccessResponse(message="Patient deactivated successfully")


@router.delete("/{patient_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_patient(
    patient_id: uuid.UUID,
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """Delete patient record"""
    user_payload = require_permissions([Permissions.PATIENTS_DELETE])(request)
    user_id = user_payload["sub"]
    user_department = user_payload.get("department_id")
    
    patient_service = PatientService(db)
    
    # First get the patient to check permissions
    patient = await patient_service.get_patient_by_id(patient_id)
    if not patient:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Patient not found"
        )
    
    # Check modify permissions (delete requires same permissions as modify)
    if not patient_service.can_modify_patient(
        user_permissions=user_payload.get("permissions", []),
        user_id=user_id,
        user_department=user_department,
        patient=patient
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions to delete this patient"
        )
    
    success = await patient_service.delete_patient(patient_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Patient not found"
        )


# Emergency Contact endpoints
@router.post("/{patient_id}/emergency-contacts", response_model=EmergencyContactResponse, status_code=status.HTTP_201_CREATED)
async def create_emergency_contact(
    patient_id: uuid.UUID,
    contact_data: EmergencyContactCreate,
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """Create a new emergency contact for a patient"""
    user_payload = require_permissions([Permissions.PATIENTS_UPDATE])(request)
    user_id = user_payload["sub"]
    user_department = user_payload.get("department_id")
    
    patient_service = PatientService(db)
    
    # Check patient access permissions
    patient = await patient_service.get_patient_by_id(patient_id)
    if not patient:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Patient not found"
        )
    
    if not patient_service.can_modify_patient(
        user_permissions=user_payload.get("permissions", []),
        user_id=user_id,
        user_department=user_department,
        patient=patient
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions to modify this patient"
        )
    
    emergency_contact_service = EmergencyContactService(db)
    contact = await emergency_contact_service.create_emergency_contact(patient_id, contact_data)
    
    return EmergencyContactResponse.from_orm(contact)


@router.get("/{patient_id}/emergency-contacts", response_model=List[EmergencyContactResponse], status_code=status.HTTP_200_OK)
async def get_patient_emergency_contacts(
    patient_id: uuid.UUID,
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """Get all emergency contacts for a patient"""
    user_payload = require_permissions([Permissions.PATIENTS_READ])(request)
    user_id = user_payload["sub"]
    user_department = user_payload.get("department_id")
    
    patient_service = PatientService(db)
    
    # Check patient access permissions
    patient = await patient_service.get_patient_by_id(patient_id)
    if not patient:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Patient not found"
        )
    
    if not patient_service.can_access_patient(
        user_permissions=user_payload.get("permissions", []),
        user_id=user_id,
        user_department=user_department,
        patient=patient
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions to access this patient"
        )
    
    emergency_contact_service = EmergencyContactService(db)
    contacts = await emergency_contact_service.get_patient_emergency_contacts(patient_id)
    
    return [EmergencyContactResponse.from_orm(contact) for contact in contacts]


@router.put("/emergency-contacts/{contact_id}", response_model=EmergencyContactResponse, status_code=status.HTTP_200_OK)
async def update_emergency_contact(
    contact_id: uuid.UUID,
    contact_data: EmergencyContactUpdate,
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """Update emergency contact"""
    user_payload = require_permissions([Permissions.PATIENTS_UPDATE])(request)
    user_id = user_payload["sub"]
    user_department = user_payload.get("department_id")
    
    emergency_contact_service = EmergencyContactService(db)
    
    # Get contact to check patient access
    contact = await emergency_contact_service.get_emergency_contact_by_id(contact_id)
    if not contact:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Emergency contact not found"
        )
    
    patient_service = PatientService(db)
    patient = await patient_service.get_patient_by_id(contact.patient_id)
    
    if not patient_service.can_modify_patient(
        user_permissions=user_payload.get("permissions", []),
        user_id=user_id,
        user_department=user_department,
        patient=patient
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions to modify this patient"
        )
    
    updated_contact = await emergency_contact_service.update_emergency_contact(contact_id, contact_data)
    
    return EmergencyContactResponse.from_orm(updated_contact)


@router.delete("/emergency-contacts/{contact_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_emergency_contact(
    contact_id: uuid.UUID,
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """Delete emergency contact"""
    user_payload = require_permissions([Permissions.PATIENTS_UPDATE])(request)
    user_id = user_payload["sub"]
    user_department = user_payload.get("department_id")
    
    emergency_contact_service = EmergencyContactService(db)
    
    # Get contact to check patient access
    contact = await emergency_contact_service.get_emergency_contact_by_id(contact_id)
    if not contact:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Emergency contact not found"
        )
    
    patient_service = PatientService(db)
    patient = await patient_service.get_patient_by_id(contact.patient_id)
    
    if not patient_service.can_modify_patient(
        user_permissions=user_payload.get("permissions", []),
        user_id=user_id,
        user_department=user_department,
        patient=patient
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions to modify this patient"
        )
    
    success = await emergency_contact_service.delete_emergency_contact(contact_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Emergency contact not found"
        )


# Insurance endpoints
@router.post("/{patient_id}/insurance", response_model=InsuranceResponse, status_code=status.HTTP_201_CREATED)
async def create_insurance(
    patient_id: uuid.UUID,
    insurance_data: InsuranceCreate,
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """Create a new insurance record for a patient"""
    user_payload = require_permissions([Permissions.PATIENTS_UPDATE])(request)
    user_id = user_payload["sub"]
    user_department = user_payload.get("department_id")
    
    patient_service = PatientService(db)
    
    # Check patient access permissions
    patient = await patient_service.get_patient_by_id(patient_id)
    if not patient:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Patient not found"
        )
    
    if not patient_service.can_modify_patient(
        user_permissions=user_payload.get("permissions", []),
        user_id=user_id,
        user_department=user_department,
        patient=patient
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions to modify this patient"
        )
    
    insurance_service = InsuranceService(db)
    insurance = await insurance_service.create_insurance(patient_id, insurance_data)
    
    return InsuranceResponse.from_orm(insurance)


@router.get("/{patient_id}/insurance", response_model=List[InsuranceResponse], status_code=status.HTTP_200_OK)
async def get_patient_insurance_records(
    patient_id: uuid.UUID,
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """Get all insurance records for a patient"""
    user_payload = require_permissions([Permissions.PATIENTS_READ])(request)
    user_id = user_payload["sub"]
    user_department = user_payload.get("department_id")
    
    patient_service = PatientService(db)
    
    # Check patient access permissions
    patient = await patient_service.get_patient_by_id(patient_id)
    if not patient:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Patient not found"
        )
    
    if not patient_service.can_access_patient(
        user_permissions=user_payload.get("permissions", []),
        user_id=user_id,
        user_department=user_department,
        patient=patient
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions to access this patient"
        )
    
    insurance_service = InsuranceService(db)
    insurance_records = await insurance_service.get_patient_insurance_records(patient_id)
    
    return [InsuranceResponse.from_orm(insurance) for insurance in insurance_records]


@router.put("/insurance/{insurance_id}", response_model=InsuranceResponse, status_code=status.HTTP_200_OK)
async def update_insurance(
    insurance_id: uuid.UUID,
    insurance_data: InsuranceUpdate,
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """Update insurance record"""
    user_payload = require_permissions([Permissions.PATIENTS_UPDATE])(request)
    user_id = user_payload["sub"]
    user_department = user_payload.get("department_id")
    
    insurance_service = InsuranceService(db)
    
    # Get insurance to check patient access
    insurance = await insurance_service.get_insurance_by_id(insurance_id)
    if not insurance:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Insurance record not found"
        )
    
    patient_service = PatientService(db)
    patient = await patient_service.get_patient_by_id(insurance.patient_id)
    
    if not patient_service.can_modify_patient(
        user_permissions=user_payload.get("permissions", []),
        user_id=user_id,
        user_department=user_department,
        patient=patient
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions to modify this patient"
        )
    
    updated_insurance = await insurance_service.update_insurance(insurance_id, insurance_data)
    
    return InsuranceResponse.from_orm(updated_insurance)


@router.delete("/insurance/{insurance_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_insurance(
    insurance_id: uuid.UUID,
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """Delete insurance record"""
    user_payload = require_permissions([Permissions.PATIENTS_UPDATE])(request)
    user_id = user_payload["sub"]
    user_department = user_payload.get("department_id")
    
    insurance_service = InsuranceService(db)
    
    # Get insurance to check patient access
    insurance = await insurance_service.get_insurance_by_id(insurance_id)
    if not insurance:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Insurance record not found"
        )
    
    patient_service = PatientService(db)
    patient = await patient_service.get_patient_by_id(insurance.patient_id)
    
    if not patient_service.can_modify_patient(
        user_permissions=user_payload.get("permissions", []),
        user_id=user_id,
        user_department=user_department,
        patient=patient
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions to modify this patient"
        )
    
    success = await insurance_service.delete_insurance(insurance_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Insurance record not found"
        )


# Patient Visit endpoints
@router.post("/{patient_id}/visits", response_model=PatientVisitResponse, status_code=status.HTTP_201_CREATED)
async def create_patient_visit(
    patient_id: uuid.UUID,
    visit_data: PatientVisitCreate,
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """Create a new patient visit"""
    user_payload = require_permissions([Permissions.PATIENTS_UPDATE])(request)
    user_id = user_payload["sub"]
    user_department = user_payload.get("department_id")
    
    patient_service = PatientService(db)
    
    # Check patient access permissions
    patient = await patient_service.get_patient_by_id(patient_id)
    if not patient:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Patient not found"
        )
    
    if not patient_service.can_modify_patient(
        user_permissions=user_payload.get("permissions", []),
        user_id=user_id,
        user_department=user_department,
        patient=patient
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions to modify this patient"
        )
    
    visit_service = PatientVisitService(db)
    visit = await visit_service.create_visit(patient_id, visit_data)
    
    return PatientVisitResponse.from_orm(visit)


@router.get("/{patient_id}/visits", response_model=PatientVisitListResponse, status_code=status.HTTP_200_OK)
async def get_patient_visits(
    patient_id: uuid.UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    visit_type: Optional[str] = None,
    status: Optional[str] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None
):
    """Get patient visits with filtering and pagination"""
    user_payload = require_permissions([Permissions.PATIENTS_READ])(request)
    user_id = user_payload["sub"]
    user_department = user_payload.get("department_id")
    
    patient_service = PatientService(db)
    
    # Check patient access permissions
    patient = await patient_service.get_patient_by_id(patient_id)
    if not patient:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Patient not found"
        )
    
    if not patient_service.can_access_patient(
        user_permissions=user_payload.get("permissions", []),
        user_id=user_id,
        user_department=user_department,
        patient=patient
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions to access this patient"
        )
    
    # Parse date filters
    from datetime import datetime
    visit_date_from = None
    visit_date_to = None
    
    if date_from:
        try:
            visit_date_from = datetime.strptime(date_from, "%Y-%m-%d").date()
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid date_from format. Use YYYY-MM-DD"
            )
    
    if date_to:
        try:
            visit_date_to = datetime.strptime(date_to, "%Y-%m-%d").date()
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid date_to format. Use YYYY-MM-DD"
            )
    
    visit_service = PatientVisitService(db)
    visits = await visit_service.get_patient_visits(
        patient_id=patient_id,
        skip=skip,
        limit=limit,
        visit_type=visit_type,
        status=status,
        date_from=visit_date_from,
        date_to=visit_date_to
    )
    
    # For simplicity, we'll return total as length of visits
    # In a real implementation, you'd have a separate count method
    total = len(visits)
    pages = math.ceil(total / limit) if limit > 0 else 0
    
    return PatientVisitListResponse(
        items=[PatientVisitResponse.from_orm(visit) for visit in visits],
        total=total,
        page=skip // limit + 1 if limit > 0 else 1,
        limit=limit,
        pages=pages
    )


@router.put("/visits/{visit_id}", response_model=PatientVisitResponse, status_code=status.HTTP_200_OK)
async def update_patient_visit(
    visit_id: uuid.UUID,
    visit_data: PatientVisitUpdate,
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """Update patient visit"""
    user_payload = require_permissions([Permissions.PATIENTS_UPDATE])(request)
    user_id = user_payload["sub"]
    user_department = user_payload.get("department_id")
    
    visit_service = PatientVisitService(db)
    
    # Get visit to check patient access
    visit = await visit_service.get_visit_by_id(visit_id)
    if not visit:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Patient visit not found"
        )
    
    patient_service = PatientService(db)
    patient = await patient_service.get_patient_by_id(visit.patient_id)
    
    if not patient_service.can_modify_patient(
        user_permissions=user_payload.get("permissions", []),
        user_id=user_id,
        user_department=user_department,
        patient=patient
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions to modify this patient"
        )
    
    updated_visit = await visit_service.update_visit(visit_id, visit_data)
    
    return PatientVisitResponse.from_orm(updated_visit)


@router.post("/visits/{visit_id}/check-in", response_model=PatientVisitResponse, status_code=status.HTTP_200_OK)
async def check_in_patient(
    visit_id: uuid.UUID,
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """Check in patient for visit"""
    user_payload = require_permissions([Permissions.PATIENTS_UPDATE])(request)
    user_id = user_payload["sub"]
    user_department = user_payload.get("department_id")
    
    visit_service = PatientVisitService(db)
    
    # Get visit to check patient access
    visit = await visit_service.get_visit_by_id(visit_id)
    if not visit:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Patient visit not found"
        )
    
    patient_service = PatientService(db)
    patient = await patient_service.get_patient_by_id(visit.patient_id)
    
    if not patient_service.can_modify_patient(
        user_permissions=user_payload.get("permissions", []),
        user_id=user_id,
        user_department=user_department,
        patient=patient
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions to modify this patient"
        )
    
    updated_visit = await visit_service.check_in_patient(visit_id)
    
    return PatientVisitResponse.from_orm(updated_visit)


@router.post("/visits/{visit_id}/complete", response_model=PatientVisitResponse, status_code=status.HTTP_200_OK)
async def complete_patient_visit(
    visit_id: uuid.UUID,
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """Complete patient visit"""
    user_payload = require_permissions([Permissions.PATIENTS_UPDATE])(request)
    user_id = user_payload["sub"]
    user_department = user_payload.get("department_id")
    
    visit_service = PatientVisitService(db)
    
    # Get visit to check patient access
    visit = await visit_service.get_visit_by_id(visit_id)
    if not visit:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Patient visit not found"
        )
    
    patient_service = PatientService(db)
    patient = await patient_service.get_patient_by_id(visit.patient_id)
    
    if not patient_service.can_modify_patient(
        user_permissions=user_payload.get("permissions", []),
        user_id=user_id,
        user_department=user_department,
        patient=patient
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions to modify this patient"
        )
    
    updated_visit = await visit_service.complete_visit(visit_id)
    
    return PatientVisitResponse.from_orm(updated_visit)


@router.delete("/visits/{visit_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_patient_visit(
    visit_id: uuid.UUID,
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """Delete patient visit"""
    user_payload = require_permissions([Permissions.PATIENTS_DELETE])(request)
    user_id = user_payload["sub"]
    user_department = user_payload.get("department_id")
    
    visit_service = PatientVisitService(db)
    
    # Get visit to check patient access
    visit = await visit_service.get_visit_by_id(visit_id)
    if not visit:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Patient visit not found"
        )
    
    patient_service = PatientService(db)
    patient = await patient_service.get_patient_by_id(visit.patient_id)
    
    if not patient_service.can_modify_patient(
        user_permissions=user_payload.get("permissions", []),
        user_id=user_id,
        user_department=user_department,
        patient=patient
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions to modify this patient"
        )
    
    success = await visit_service.delete_visit(visit_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Patient visit not found"
        )
