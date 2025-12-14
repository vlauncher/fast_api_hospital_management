from typing import Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete, and_, or_, func
from sqlalchemy.orm import joinedload, selectinload
from datetime import datetime, date
from app.domain.patients.models import Patient, EmergencyContact, Insurance, PatientVisit
import uuid


class PatientRepository:
    """Repository for patient data access operations"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def create(self, patient_data: dict) -> Patient:
        """Create a new patient"""
        patient = Patient(**patient_data)
        
        # Encrypt sensitive data
        patient.encrypt_sensitive_data()
        
        self.db.add(patient)
        await self.db.commit()
        await self.db.refresh(patient)
        
        return patient
    
    async def get_by_id(self, patient_id: uuid.UUID) -> Optional[Patient]:
        """Get patient by ID"""
        result = await self.db.execute(
            select(Patient)
            .options(
                selectinload(Patient.emergency_contacts),
                selectinload(Patient.insurance_records),
                selectinload(Patient.visits),
                selectinload(Patient.creator),
                selectinload(Patient.updater)
            )
            .where(Patient.id == patient_id)
        )
        patient = result.scalar_one_or_none()
        
        if patient:
            patient.decrypt_sensitive_data()
            # Decrypt related records
            for contact in patient.emergency_contacts:
                contact.decrypt_sensitive_data()
            for insurance in patient.insurance_records:
                insurance.decrypt_sensitive_data()
        
        return patient
    
    async def get_by_patient_number(self, patient_number: str) -> Optional[Patient]:
        """Get patient by patient number"""
        result = await self.db.execute(
            select(Patient)
            .options(
                selectinload(Patient.emergency_contacts),
                selectinload(Patient.insurance_records),
                selectinload(Patient.visits)
            )
            .where(Patient.patient_number == patient_number)
        )
        patient = result.scalar_one_or_none()
        
        if patient:
            patient.decrypt_sensitive_data()
            # Decrypt related records
            for contact in patient.emergency_contacts:
                contact.decrypt_sensitive_data()
            for insurance in patient.insurance_records:
                insurance.decrypt_sensitive_data()
        
        return patient
    
    async def get_all(
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
        query = select(Patient).options(
            selectinload(Patient.emergency_contacts),
            selectinload(Patient.insurance_records)
        )
        
        if is_active is not None:
            query = query.where(Patient.is_active == is_active)
        
        if blood_type:
            query = query.where(Patient.blood_type == blood_type)
        
        if gender:
            query = query.where(Patient.gender == gender)
        
        if date_of_birth_from:
            query = query.where(Patient.date_of_birth >= date_of_birth_from)
        
        if date_of_birth_to:
            query = query.where(Patient.date_of_birth <= date_of_birth_to)
        
        if search:
            # Search by patient number (non-encrypted)
            query = query.where(Patient.patient_number.ilike(f"%{search}%"))
        
        query = query.order_by(Patient.created_at.desc()).offset(skip).limit(limit)
        
        result = await self.db.execute(query)
        patients = result.scalars().all()
        
        # Decrypt sensitive data for all patients
        for patient in patients:
            patient.decrypt_sensitive_data()
            for contact in patient.emergency_contacts:
                contact.decrypt_sensitive_data()
            for insurance in patient.insurance_records:
                insurance.decrypt_sensitive_data()
        
        return patients
    
    async def update(self, patient_id: uuid.UUID, update_data: dict) -> Optional[Patient]:
        """Update patient information"""
        # Remove sensitive fields that should be encrypted separately
        sensitive_fields = [
            'first_name', 'last_name', 'middle_name', 'date_of_birth',
            'phone_primary', 'phone_secondary', 'email', 'address',
            'national_id', 'passport_number', 'driver_license',
            'emergency_contact_name', 'emergency_contact_phone'
        ]
        
        encrypted_data = {}
        for field in sensitive_fields:
            if field in update_data:
                encrypted_data[field] = update_data.pop(field)
        
        # Update non-sensitive fields
        if update_data:
            await self.db.execute(
                update(Patient)
                .where(Patient.id == patient_id)
                .values(**update_data)
            )
        
        # Update sensitive fields with encryption
        if encrypted_data:
            patient = await self.get_by_id(patient_id)
            if patient:
                for field, value in encrypted_data.items():
                    setattr(patient, field, value)
                patient.encrypt_sensitive_data()
        
        await self.db.commit()
        return await self.get_by_id(patient_id)
    
    async def deactivate(self, patient_id: uuid.UUID) -> None:
        """Deactivate patient record"""
        await self.db.execute(
            update(Patient)
            .where(Patient.id == patient_id)
            .values(is_active=False)
        )
        await self.db.commit()
    
    async def delete(self, patient_id: uuid.UUID) -> bool:
        """Delete patient record"""
        result = await self.db.execute(
            delete(Patient).where(Patient.id == patient_id)
        )
        await self.db.commit()
        return result.rowcount > 0
    
    async def count(
        self,
        is_active: Optional[bool] = None,
        blood_type: Optional[str] = None,
        gender: Optional[str] = None
    ) -> int:
        """Count patients with optional filters"""
        query = select(func.count(Patient.id))
        
        if is_active is not None:
            query = query.where(Patient.is_active == is_active)
        
        if blood_type:
            query = query.where(Patient.blood_type == blood_type)
        
        if gender:
            query = query.where(Patient.gender == gender)
        
        result = await self.db.execute(query)
        return result.scalar()
    
    async def search_by_name(self, name: str, limit: int = 10) -> List[Patient]:
        """Search patients by name (limited due to encryption)"""
        # Since names are encrypted, we can't search them directly
        # This would need to be implemented with a separate search index
        # For now, return empty list or implement alternative search strategy
        return []


class EmergencyContactRepository:
    """Repository for emergency contact data access operations"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def create(self, contact_data: dict) -> EmergencyContact:
        """Create a new emergency contact"""
        contact = EmergencyContact(**contact_data)
        
        # Encrypt sensitive data
        contact.encrypt_sensitive_data()
        
        self.db.add(contact)
        await self.db.commit()
        await self.db.refresh(contact)
        
        return contact
    
    async def get_by_id(self, contact_id: uuid.UUID) -> Optional[EmergencyContact]:
        """Get emergency contact by ID"""
        result = await self.db.execute(
            select(EmergencyContact).where(EmergencyContact.id == contact_id)
        )
        contact = result.scalar_one_or_none()
        
        if contact:
            contact.decrypt_sensitive_data()
        
        return contact
    
    async def get_by_patient_id(self, patient_id: uuid.UUID) -> List[EmergencyContact]:
        """Get all emergency contacts for a patient"""
        result = await self.db.execute(
            select(EmergencyContact)
            .where(EmergencyContact.patient_id == patient_id)
            .order_by(EmergencyContact.is_primary.desc(), EmergencyContact.created_at.asc())
        )
        contacts = result.scalars().all()
        
        # Decrypt sensitive data for all contacts
        for contact in contacts:
            contact.decrypt_sensitive_data()
        
        return contacts
    
    async def update(self, contact_id: uuid.UUID, update_data: dict) -> Optional[EmergencyContact]:
        """Update emergency contact information"""
        # Handle sensitive fields
        sensitive_fields = ['name', 'phone', 'phone_secondary', 'email', 'address']
        encrypted_data = {}
        
        for field in sensitive_fields:
            if field in update_data:
                encrypted_data[field] = update_data.pop(field)
        
        # Update non-sensitive fields
        if update_data:
            await self.db.execute(
                update(EmergencyContact)
                .where(EmergencyContact.id == contact_id)
                .values(**update_data)
            )
        
        # Update sensitive fields with encryption
        if encrypted_data:
            contact = await self.get_by_id(contact_id)
            if contact:
                for field, value in encrypted_data.items():
                    setattr(contact, field, value)
                contact.encrypt_sensitive_data()
        
        await self.db.commit()
        return await self.get_by_id(contact_id)
    
    async def delete(self, contact_id: uuid.UUID) -> bool:
        """Delete emergency contact"""
        result = await self.db.execute(
            delete(EmergencyContact).where(EmergencyContact.id == contact_id)
        )
        await self.db.commit()
        return result.rowcount > 0
    
    async def set_primary(self, contact_id: uuid.UUID, patient_id: uuid.UUID) -> None:
        """Set contact as primary and unset others"""
        # Unset all primary contacts for this patient
        await self.db.execute(
            update(EmergencyContact)
            .where(EmergencyContact.patient_id == patient_id)
            .values(is_primary=False)
        )
        
        # Set this contact as primary
        await self.db.execute(
            update(EmergencyContact)
            .where(EmergencyContact.id == contact_id)
            .values(is_primary=True)
        )
        
        await self.db.commit()


class InsuranceRepository:
    """Repository for insurance data access operations"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def create(self, insurance_data: dict) -> Insurance:
        """Create a new insurance record"""
        insurance = Insurance(**insurance_data)
        
        # Encrypt sensitive data
        insurance.encrypt_sensitive_data()
        
        self.db.add(insurance)
        await self.db.commit()
        await self.db.refresh(insurance)
        
        return insurance
    
    async def get_by_id(self, insurance_id: uuid.UUID) -> Optional[Insurance]:
        """Get insurance record by ID"""
        result = await self.db.execute(
            select(Insurance)
            .options(selectinload(Insurance.verifier))
            .where(Insurance.id == insurance_id)
        )
        insurance = result.scalar_one_or_none()
        
        if insurance:
            insurance.decrypt_sensitive_data()
        
        return insurance
    
    async def get_by_patient_id(self, patient_id: uuid.UUID) -> List[Insurance]:
        """Get all insurance records for a patient"""
        result = await self.db.execute(
            select(Insurance)
            .options(selectinload(Insurance.verifier))
            .where(Insurance.patient_id == patient_id)
            .order_by(Insurance.is_primary.desc(), Insurance.created_at.desc())
        )
        insurance_records = result.scalars().all()
        
        # Decrypt sensitive data for all records
        for insurance in insurance_records:
            insurance.decrypt_sensitive_data()
        
        return insurance_records
    
    async def get_by_policy_number(self, policy_number: str) -> Optional[Insurance]:
        """Get insurance record by policy number"""
        result = await self.db.execute(
            select(Insurance).where(Insurance.policy_number == policy_number)
        )
        insurance = result.scalar_one_or_none()
        
        if insurance:
            insurance.decrypt_sensitive_data()
        
        return insurance
    
    async def update(self, insurance_id: uuid.UUID, update_data: dict) -> Optional[Insurance]:
        """Update insurance information"""
        # Handle sensitive fields
        sensitive_fields = [
            'policy_holder_name', 'policy_holder_dob', 'policy_holder_ssn',
            'insurance_phone', 'insurance_address'
        ]
        encrypted_data = {}
        
        for field in sensitive_fields:
            if field in update_data:
                encrypted_data[field] = update_data.pop(field)
        
        # Update non-sensitive fields
        if update_data:
            await self.db.execute(
                update(Insurance)
                .where(Insurance.id == insurance_id)
                .values(**update_data)
            )
        
        # Update sensitive fields with encryption
        if encrypted_data:
            insurance = await self.get_by_id(insurance_id)
            if insurance:
                for field, value in encrypted_data.items():
                    setattr(insurance, field, value)
                insurance.encrypt_sensitive_data()
        
        await self.db.commit()
        return await self.get_by_id(insurance_id)
    
    async def delete(self, insurance_id: uuid.UUID) -> bool:
        """Delete insurance record"""
        result = await self.db.execute(
            delete(Insurance).where(Insurance.id == insurance_id)
        )
        await self.db.commit()
        return result.rowcount > 0
    
    async def set_primary(self, insurance_id: uuid.UUID, patient_id: uuid.UUID) -> None:
        """Set insurance as primary and unset others"""
        # Unset all primary insurance for this patient
        await self.db.execute(
            update(Insurance)
            .where(Insurance.patient_id == patient_id)
            .values(is_primary=False)
        )
        
        # Set this insurance as primary
        await self.db.execute(
            update(Insurance)
            .where(Insurance.id == insurance_id)
            .values(is_primary=True)
        )
        
        await self.db.commit()
    
    async def verify_insurance(self, insurance_id: uuid.UUID, verified_by: uuid.UUID) -> None:
        """Verify insurance record"""
        await self.db.execute(
            update(Insurance)
            .where(Insurance.id == insurance_id)
            .values(
                verification_status="VERIFIED",
                verified_date=datetime.utcnow(),
                verified_by=verified_by
            )
        )
        await self.db.commit()


class PatientVisitRepository:
    """Repository for patient visit data access operations"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def create(self, visit_data: dict) -> PatientVisit:
        """Create a new patient visit"""
        visit = PatientVisit(**visit_data)
        self.db.add(visit)
        await self.db.commit()
        await self.db.refresh(visit)
        return visit
    
    async def get_by_id(self, visit_id: uuid.UUID) -> Optional[PatientVisit]:
        """Get patient visit by ID"""
        result = await self.db.execute(
            select(PatientVisit)
            .options(
                selectinload(PatientVisit.patient),
                selectinload(PatientVisit.attending_physician),
                selectinload(PatientVisit.nurse)
            )
            .where(PatientVisit.id == visit_id)
        )
        return result.scalar_one_or_none()
    
    async def get_by_patient_id(
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
        query = select(PatientVisit).options(
            selectinload(PatientVisit.attending_physician),
            selectinload(PatientVisit.nurse)
        ).where(PatientVisit.patient_id == patient_id)
        
        if visit_type:
            query = query.where(PatientVisit.visit_type == visit_type)
        
        if status:
            query = query.where(PatientVisit.status == status)
        
        if date_from:
            query = query.where(PatientVisit.visit_date >= date_from)
        
        if date_to:
            query = query.where(PatientVisit.visit_date <= date_to)
        
        query = query.order_by(PatientVisit.visit_date.desc()).offset(skip).limit(limit)
        
        result = await self.db.execute(query)
        return result.scalars().all()
    
    async def update(self, visit_id: uuid.UUID, update_data: dict) -> Optional[PatientVisit]:
        """Update patient visit"""
        await self.db.execute(
            update(PatientVisit)
            .where(PatientVisit.id == visit_id)
            .values(**update_data)
        )
        await self.db.commit()
        return await self.get_by_id(visit_id)
    
    async def delete(self, visit_id: uuid.UUID) -> bool:
        """Delete patient visit"""
        result = await self.db.execute(
            delete(PatientVisit).where(PatientVisit.id == visit_id)
        )
        await self.db.commit()
        return result.rowcount > 0
