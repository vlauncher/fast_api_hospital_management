from typing import Optional, List, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime, date
import uuid
import math
from fastapi import HTTPException, status

from app.domain.patients.models import Patient, EmergencyContact, Insurance, PatientVisit
from app.domain.patients.repository import (
    PatientRepository, 
    EmergencyContactRepository, 
    InsuranceRepository,
    PatientVisitRepository
)
from app.api.v1.patients.schemas import (
    PatientCreate, 
    PatientUpdate,
    EmergencyContactCreate,
    EmergencyContactUpdate,
    InsuranceCreate,
    InsuranceUpdate,
    PatientVisitCreate,
    PatientVisitUpdate
)
from app.core.permissions import PermissionChecker


class PatientService:
    """Service layer for patient management operations"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self.patient_repo = PatientRepository(db)
        self.emergency_contact_repo = EmergencyContactRepository(db)
        self.insurance_repo = InsuranceRepository(db)
        self.visit_repo = PatientVisitRepository(db)
    
    def _generate_patient_number(self) -> str:
        """Generate a unique patient number"""
        import random
        import string
        
        # Format: PT + YYYY + 6-digit random number
        year = datetime.now().year
        random_digits = ''.join(random.choices(string.digits, k=6))
        return f"PT{year}{random_digits}"
    
    async def create_patient(self, patient_data: PatientCreate, created_by: uuid.UUID) -> Patient:
        """Create a new patient"""
        # Generate unique patient number
        patient_number = self._generate_patient_number()
        
        # Check if patient number already exists (very unlikely but possible)
        existing_patient = await self.patient_repo.get_by_patient_number(patient_number)
        while existing_patient:
            patient_number = self._generate_patient_number()
            existing_patient = await self.patient_repo.get_by_patient_number(patient_number)
        
        # Create patient data dictionary
        patient_dict = patient_data.dict()
        patient_dict.update({
            'patient_number': patient_number,
            'created_by': created_by,
            'registered_date': datetime.utcnow()
        })
        
        patient = await self.patient_repo.create(patient_dict)
        
        # Create emergency contact if provided
        if (patient_data.emergency_contact_name and 
            patient_data.emergency_contact_phone and 
            patient_data.emergency_contact_relationship):
            
            emergency_contact_data = {
                'patient_id': patient.id,
                'name': patient_data.emergency_contact_name,
                'phone': patient_data.emergency_contact_phone,
                'relationship': patient_data.emergency_contact_relationship,
                'is_primary': True
            }
            await self.emergency_contact_repo.create(emergency_contact_data)
        
        # Create insurance record if provided
        if (patient_data.insurance_provider and 
            patient_data.insurance_policy_number):
            
            insurance_data = {
                'patient_id': patient.id,
                'provider_name': patient_data.insurance_provider,
                'policy_number': patient_data.insurance_policy_number,
                'group_number': patient_data.insurance_group_number,
                'coverage_start_date': datetime.utcnow().date(),
                'is_primary': True
            }
            await self.insurance_repo.create(insurance_data)
        
        return await self.patient_repo.get_by_id(patient.id)
    
    async def get_patient_by_id(self, patient_id: uuid.UUID) -> Optional[Patient]:
        """Get patient by ID"""
        return await self.patient_repo.get_by_id(patient_id)
    
    async def get_patient_by_number(self, patient_number: str) -> Optional[Patient]:
        """Get patient by patient number"""
        return await self.patient_repo.get_by_patient_number(patient_number)
    
    async def get_patients(
        self,
        skip: int = 0,
        limit: int = 20,
        is_active: Optional[bool] = None,
        search: Optional[str] = None,
        blood_type: Optional[str] = None,
        gender: Optional[str] = None,
        date_of_birth_from: Optional[date] = None,
        date_of_birth_to: Optional[date] = None
    ) -> List[Patient]:
        """Get patients with filtering and pagination"""
        return await self.patient_repo.get_all(
            skip=skip,
            limit=limit,
            is_active=is_active,
            search=search,
            blood_type=blood_type,
            gender=gender,
            date_of_birth_from=date_of_birth_from,
            date_of_birth_to=date_of_birth_to
        )
    
    async def update_patient(self, patient_id: uuid.UUID, patient_data: PatientUpdate, updated_by: uuid.UUID) -> Optional[Patient]:
        """Update patient information"""
        update_dict = patient_data.dict(exclude_unset=True)
        update_dict['updated_by'] = updated_by
        update_dict['updated_at'] = datetime.utcnow()
        
        return await self.patient_repo.update(patient_id, update_dict)
    
    async def deactivate_patient(self, patient_id: uuid.UUID) -> None:
        """Deactivate patient record"""
        await self.patient_repo.deactivate(patient_id)
    
    async def delete_patient(self, patient_id: uuid.UUID) -> bool:
        """Delete patient record"""
        return await self.patient_repo.delete(patient_id)
    
    async def count_patients(
        self,
        is_active: Optional[bool] = None,
        blood_type: Optional[str] = None,
        gender: Optional[str] = None
    ) -> int:
        """Count patients with optional filters"""
        return await self.patient_repo.count(
            is_active=is_active,
            blood_type=blood_type,
            gender=gender
        )
    
    def can_access_patient(
        self, 
        user_permissions: List[str], 
        user_id: str, 
        user_department: Optional[str],
        patient: Patient
    ) -> bool:
        """Check if user can access a specific patient"""
        return PermissionChecker.can_access_patient(
            user_permissions=user_permissions,
            user_id=user_id,
            user_department=user_department,
            patient_owner_id=str(patient.created_by) if patient.created_by else None,
            patient_department=user_department  # Simplified - in real implementation, patient would have department
        )
    
    def can_modify_patient(
        self, 
        user_permissions: List[str], 
        user_id: str, 
        user_department: Optional[str],
        patient: Patient
    ) -> bool:
        """Check if user can modify a specific patient"""
        return PermissionChecker.can_modify_patient(
            user_permissions=user_permissions,
            user_id=user_id,
            user_department=user_department,
            patient_owner_id=str(patient.created_by) if patient.created_by else None,
            patient_department=user_department  # Simplified - in real implementation, patient would have department
        )


class EmergencyContactService:
    """Service layer for emergency contact management"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self.contact_repo = EmergencyContactRepository(db)
    
    async def create_emergency_contact(self, patient_id: uuid.UUID, contact_data: EmergencyContactCreate) -> EmergencyContact:
        """Create a new emergency contact"""
        contact_dict = contact_data.dict()
        contact_dict['patient_id'] = patient_id
        
        contact = await self.contact_repo.create(contact_dict)
        
        # If this is set as primary, unset other primary contacts
        if contact_data.is_primary:
            await self.contact_repo.set_primary(contact.id, patient_id)
        
        return contact
    
    async def get_emergency_contact_by_id(self, contact_id: uuid.UUID) -> Optional[EmergencyContact]:
        """Get emergency contact by ID"""
        return await self.contact_repo.get_by_id(contact_id)
    
    async def get_patient_emergency_contacts(self, patient_id: uuid.UUID) -> List[EmergencyContact]:
        """Get all emergency contacts for a patient"""
        return await self.contact_repo.get_by_patient_id(patient_id)
    
    async def update_emergency_contact(self, contact_id: uuid.UUID, contact_data: EmergencyContactUpdate) -> Optional[EmergencyContact]:
        """Update emergency contact information"""
        update_dict = contact_data.dict(exclude_unset=True)
        
        # Get the contact to check if it's being set as primary
        contact = await self.contact_repo.get_by_id(contact_id)
        if not contact:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Emergency contact not found"
            )
        
        # If being set as primary, unset others
        if contact_data.is_primary and not contact.is_primary:
            await self.contact_repo.set_primary(contact_id, contact.patient_id)
        
        return await self.contact_repo.update(contact_id, update_dict)
    
    async def delete_emergency_contact(self, contact_id: uuid.UUID) -> bool:
        """Delete emergency contact"""
        return await self.contact_repo.delete(contact_id)
    
    async def set_primary_contact(self, contact_id: uuid.UUID) -> None:
        """Set emergency contact as primary"""
        contact = await self.contact_repo.get_by_id(contact_id)
        if not contact:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Emergency contact not found"
            )
        
        await self.contact_repo.set_primary(contact_id, contact.patient_id)


class InsuranceService:
    """Service layer for insurance management"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self.insurance_repo = InsuranceRepository(db)
    
    async def create_insurance(self, patient_id: uuid.UUID, insurance_data: InsuranceCreate) -> Insurance:
        """Create a new insurance record"""
        # Check if policy number already exists
        if insurance_data.policy_number:
            existing_insurance = await self.insurance_repo.get_by_policy_number(insurance_data.policy_number)
            if existing_insurance:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Policy number already exists"
                )
        
        insurance_dict = insurance_data.dict()
        insurance_dict['patient_id'] = patient_id
        
        insurance = await self.insurance_repo.create(insurance_dict)
        
        # If this is set as primary, unset other primary insurance
        if insurance_data.is_primary:
            await self.insurance_repo.set_primary(insurance.id, patient_id)
        
        return insurance
    
    async def get_insurance_by_id(self, insurance_id: uuid.UUID) -> Optional[Insurance]:
        """Get insurance record by ID"""
        return await self.insurance_repo.get_by_id(insurance_id)
    
    async def get_patient_insurance_records(self, patient_id: uuid.UUID) -> List[Insurance]:
        """Get all insurance records for a patient"""
        return await self.insurance_repo.get_by_patient_id(patient_id)
    
    async def update_insurance(self, insurance_id: uuid.UUID, insurance_data: InsuranceUpdate) -> Optional[Insurance]:
        """Update insurance information"""
        update_dict = insurance_data.dict(exclude_unset=True)
        
        # Get the insurance to check if policy number is being updated
        insurance = await self.insurance_repo.get_by_id(insurance_id)
        if not insurance:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Insurance record not found"
            )
        
        # Check if policy number is being updated and if it already exists
        if 'policy_number' in update_dict and update_dict['policy_number'] != insurance.policy_number:
            existing_insurance = await self.insurance_repo.get_by_policy_number(update_dict['policy_number'])
            if existing_insurance:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Policy number already exists"
                )
        
        # If being set as primary, unset others
        if insurance_data.is_primary and not insurance.is_primary:
            await self.insurance_repo.set_primary(insurance_id, insurance.patient_id)
        
        return await self.insurance_repo.update(insurance_id, update_dict)
    
    async def delete_insurance(self, insurance_id: uuid.UUID) -> bool:
        """Delete insurance record"""
        return await self.insurance_repo.delete(insurance_id)
    
    async def set_primary_insurance(self, insurance_id: uuid.UUID) -> None:
        """Set insurance as primary"""
        insurance = await self.insurance_repo.get_by_id(insurance_id)
        if not insurance:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Insurance record not found"
            )
        
        await self.insurance_repo.set_primary(insurance_id, insurance.patient_id)
    
    async def verify_insurance(self, insurance_id: uuid.UUID, verified_by: uuid.UUID) -> None:
        """Verify insurance record"""
        insurance = await self.insurance_repo.get_by_id(insurance_id)
        if not insurance:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Insurance record not found"
            )
        
        await self.insurance_repo.verify_insurance(insurance_id, verified_by)


class PatientVisitService:
    """Service layer for patient visit management"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self.visit_repo = PatientVisitRepository(db)
    
    async def create_visit(self, patient_id: uuid.UUID, visit_data: PatientVisitCreate) -> PatientVisit:
        """Create a new patient visit"""
        visit_dict = visit_data.dict()
        visit_dict['patient_id'] = patient_id
        
        return await self.visit_repo.create(visit_dict)
    
    async def get_visit_by_id(self, visit_id: uuid.UUID) -> Optional[PatientVisit]:
        """Get patient visit by ID"""
        return await self.visit_repo.get_by_id(visit_id)
    
    async def get_patient_visits(
        self,
        patient_id: uuid.UUID,
        skip: int = 0,
        limit: int = 20,
        visit_type: Optional[str] = None,
        status: Optional[str] = None,
        date_from: Optional[date] = None,
        date_to: Optional[date] = None
    ) -> List[PatientVisit]:
        """Get patient visits with filtering"""
        return await self.visit_repo.get_by_patient_id(
            patient_id=patient_id,
            skip=skip,
            limit=limit,
            visit_type=visit_type,
            status=status,
            date_from=date_from,
            date_to=date_to
        )
    
    async def update_visit(self, visit_id: uuid.UUID, visit_data: PatientVisitUpdate) -> Optional[PatientVisit]:
        """Update patient visit"""
        update_dict = visit_data.dict(exclude_unset=True)
        return await self.visit_repo.update(visit_id, update_dict)
    
    async def delete_visit(self, visit_id: uuid.UUID) -> bool:
        """Delete patient visit"""
        return await self.visit_repo.delete(visit_id)
    
    async def check_in_patient(self, visit_id: uuid.UUID) -> Optional[PatientVisit]:
        """Check in patient for visit"""
        return await self.visit_repo.update(visit_id, {
            'check_in_time': datetime.utcnow(),
            'status': 'CHECKED_IN'
        })
    
    async def complete_visit(self, visit_id: uuid.UUID) -> Optional[PatientVisit]:
        """Complete patient visit"""
        return await self.visit_repo.update(visit_id, {
            'check_out_time': datetime.utcnow(),
            'status': 'COMPLETED'
        })
