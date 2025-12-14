import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import uuid4

from app.domain.patients.models import Patient, Gender, BloodType, MaritalStatus


@pytest.mark.patients
@pytest.mark.integration
class TestPatientManagement:
    """Test patient management endpoints and functionality."""

    async def test_create_patient_success(
        self, 
        authenticated_client: AsyncClient, 
        sample_patient_data: dict
    ) -> None:
        """Test successful patient creation."""
        response = await authenticated_client.post("/api/v1/patients/", json=sample_patient_data)
        
        assert response.status_code == 201
        data = response.json()
        assert data["first_name"] == sample_patient_data["first_name"]
        assert data["last_name"] == sample_patient_data["last_name"]
        assert data["gender"] == sample_patient_data["gender"]
        assert "patient_number" in data
        assert "id" in data

    async def test_create_patient_validation_error(self, authenticated_client: AsyncClient) -> None:
        """Test patient creation with invalid data."""
        invalid_data = {
            "first_name": "",  # Empty first name
            "last_name": "Doe",
            "date_of_birth": "invalid-date",  # Invalid date
            "gender": "INVALID_GENDER"  # Invalid gender
        }
        
        response = await authenticated_client.post("/api/v1/patients/", json=invalid_data)
        
        assert response.status_code == 422
        assert "validation" in response.json()["detail"].lower()

    async def test_get_patient_success(
        self, 
        authenticated_client: AsyncClient, 
        sample_patient_data: dict
    ) -> None:
        """Test getting a specific patient."""
        # Create patient first
        create_response = await authenticated_client.post("/api/v1/patients/", json=sample_patient_data)
        patient_id = create_response.json()["id"]
        
        # Get patient
        response = await authenticated_client.get(f"/api/v1/patients/{patient_id}")
        
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == patient_id
        assert data["first_name"] == sample_patient_data["first_name"]

    async def test_get_patient_not_found(self, authenticated_client: AsyncClient) -> None:
        """Test getting a non-existent patient."""
        fake_id = str(uuid4())
        response = await authenticated_client.get(f"/api/v1/patients/{fake_id}")
        
        assert response.status_code == 404

    async def test_get_patients_list(
        self, 
        authenticated_client: AsyncClient, 
        sample_patient_data: dict
    ) -> None:
        """Test getting list of patients."""
        # Create multiple patients
        for i in range(3):
            patient_data = sample_patient_data.copy()
            patient_data["first_name"] = f"Patient{i}"
            patient_data["email"] = f"patient{i}@example.com"
            await authenticated_client.post("/api/v1/patients/", json=patient_data)
        
        # Get patients list
        response = await authenticated_client.get("/api/v1/patients/")
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 3

    async def test_update_patient_success(
        self, 
        authenticated_client: AsyncClient, 
        sample_patient_data: dict
    ) -> None:
        """Test updating patient information."""
        # Create patient first
        create_response = await authenticated_client.post("/api/v1/patients/", json=sample_patient_data)
        patient_id = create_response.json()["id"]
        
        # Update patient
        update_data = {
            "first_name": "Updated",
            "phone_number": "+9876543210"
        }
        
        response = await authenticated_client.put(f"/api/v1/patients/{patient_id}", json=update_data)
        
        assert response.status_code == 200
        data = response.json()
        assert data["first_name"] == update_data["first_name"]
        assert data["phone_number"] == update_data["phone_number"]

    async def test_delete_patient_success(
        self, 
        authenticated_client: AsyncClient, 
        sample_patient_data: dict
    ) -> None:
        """Test deleting a patient."""
        # Create patient first
        create_response = await authenticated_client.post("/api/v1/patients/", json=sample_patient_data)
        patient_id = create_response.json()["id"]
        
        # Delete patient
        response = await authenticated_client.delete(f"/api/v1/patients/{patient_id}")
        
        assert response.status_code == 200
        assert response.json()["message"] == "Patient deleted successfully"
        
        # Verify patient is deleted
        get_response = await authenticated_client.get(f"/api/v1/patients/{patient_id}")
        assert get_response.status_code == 404

    async def test_search_patients_by_name(
        self, 
        authenticated_client: AsyncClient, 
        sample_patient_data: dict
    ) -> None:
        """Test searching patients by name."""
        # Create patient
        await authenticated_client.post("/api/v1/patients/", json=sample_patient_data)
        
        # Search by first name
        response = await authenticated_client.get(
            "/api/v1/patients/search", 
            params={"search": sample_patient_data["first_name"]}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        if data:  # If results found
            assert sample_patient_data["first_name"].lower() in data[0]["first_name"].lower()

    async def test_filter_patients_by_gender(
        self, 
        authenticated_client: AsyncClient, 
        sample_patient_data: dict
    ) -> None:
        """Test filtering patients by gender."""
        # Create patient
        await authenticated_client.post("/api/v1/patients/", json=sample_patient_data)
        
        # Filter by gender
        response = await authenticated_client.get(
            "/api/v1/patients/", 
            params={"gender": sample_patient_data["gender"]}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        for patient in data:
            assert patient["gender"] == sample_patient_data["gender"]


@pytest.mark.patients
@pytest.mark.integration
class TestEmergencyContacts:
    """Test emergency contact management."""

    async def test_add_emergency_contact_success(
        self, 
        authenticated_client: AsyncClient, 
        sample_patient_data: dict,
        sample_emergency_contact_data: dict
    ) -> None:
        """Test adding emergency contact to patient."""
        # Create patient first
        create_response = await authenticated_client.post("/api/v1/patients/", json=sample_patient_data)
        patient_id = create_response.json()["id"]
        
        # Add emergency contact
        response = await authenticated_client.post(
            f"/api/v1/patients/{patient_id}/emergency-contacts", 
            json=sample_emergency_contact_data
        )
        
        assert response.status_code == 201
        data = response.json()
        assert data["first_name"] == sample_emergency_contact_data["first_name"]
        assert data["relationship_type"] == sample_emergency_contact_data["relationship"]

    async def test_get_emergency_contacts(
        self, 
        authenticated_client: AsyncClient, 
        sample_patient_data: dict,
        sample_emergency_contact_data: dict
    ) -> None:
        """Test getting patient emergency contacts."""
        # Create patient first
        create_response = await authenticated_client.post("/api/v1/patients/", json=sample_patient_data)
        patient_id = create_response.json()["id"]
        
        # Add emergency contact
        await authenticated_client.post(
            f"/api/v1/patients/{patient_id}/emergency-contacts", 
            json=sample_emergency_contact_data
        )
        
        # Get emergency contacts
        response = await authenticated_client.get(f"/api/v1/patients/{patient_id}/emergency-contacts")
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 1
        assert data[0]["first_name"] == sample_emergency_contact_data["first_name"]

    async def test_update_emergency_contact(
        self, 
        authenticated_client: AsyncClient, 
        sample_patient_data: dict,
        sample_emergency_contact_data: dict
    ) -> None:
        """Test updating emergency contact."""
        # Create patient first
        create_response = await authenticated_client.post("/api/v1/patients/", json=sample_patient_data)
        patient_id = create_response.json()["id"]
        
        # Add emergency contact
        contact_response = await authenticated_client.post(
            f"/api/v1/patients/{patient_id}/emergency-contacts", 
            json=sample_emergency_contact_data
        )
        contact_id = contact_response.json()["id"]
        
        # Update emergency contact
        update_data = {
            "phone_number": "+9876543210",
            "is_primary": True
        }
        
        response = await authenticated_client.put(
            f"/api/v1/patients/{patient_id}/emergency-contacts/{contact_id}", 
            json=update_data
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["phone_number"] == update_data["phone_number"]
        assert data["is_primary"] == update_data["is_primary"]

    async def test_delete_emergency_contact(
        self, 
        authenticated_client: AsyncClient, 
        sample_patient_data: dict,
        sample_emergency_contact_data: dict
    ) -> None:
        """Test deleting emergency contact."""
        # Create patient first
        create_response = await authenticated_client.post("/api/v1/patients/", json=sample_patient_data)
        patient_id = create_response.json()["id"]
        
        # Add emergency contact
        contact_response = await authenticated_client.post(
            f"/api/v1/patients/{patient_id}/emergency-contacts", 
            json=sample_emergency_contact_data
        )
        contact_id = contact_response.json()["id"]
        
        # Delete emergency contact
        response = await authenticated_client.delete(
            f"/api/v1/patients/{patient_id}/emergency-contacts/{contact_id}"
        )
        
        assert response.status_code == 200


@pytest.mark.patients
@pytest.mark.integration
class TestInsuranceManagement:
    """Test insurance information management."""

    async def test_add_insurance_success(
        self, 
        authenticated_client: AsyncClient, 
        sample_patient_data: dict,
        sample_insurance_data: dict
    ) -> None:
        """Test adding insurance information to patient."""
        # Create patient first
        create_response = await authenticated_client.post("/api/v1/patients/", json=sample_patient_data)
        patient_id = create_response.json()["id"]
        
        # Add insurance
        response = await authenticated_client.post(
            f"/api/v1/patients/{patient_id}/insurance", 
            json=sample_insurance_data
        )
        
        assert response.status_code == 201
        data = response.json()
        assert data["provider_name"] == sample_insurance_data["provider_name"]
        assert data["policy_number"] == sample_insurance_data["policy_number"]

    async def test_get_insurance_info(
        self, 
        authenticated_client: AsyncClient, 
        sample_patient_data: dict,
        sample_insurance_data: dict
    ) -> None:
        """Test getting patient insurance information."""
        # Create patient first
        create_response = await authenticated_client.post("/api/v1/patients/", json=sample_patient_data)
        patient_id = create_response.json()["id"]
        
        # Add insurance
        await authenticated_client.post(
            f"/api/v1/patients/{patient_id}/insurance", 
            json=sample_insurance_data
        )
        
        # Get insurance info
        response = await authenticated_client.get(f"/api/v1/patients/{patient_id}/insurance")
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 1
        assert data[0]["provider_name"] == sample_insurance_data["provider_name"]

    async def test_update_insurance(
        self, 
        authenticated_client: AsyncClient, 
        sample_patient_data: dict,
        sample_insurance_data: dict
    ) -> None:
        """Test updating insurance information."""
        # Create patient first
        create_response = await authenticated_client.post("/api/v1/patients/", json=sample_patient_data)
        patient_id = create_response.json()["id"]
        
        # Add insurance
        insurance_response = await authenticated_client.post(
            f"/api/v1/patients/{patient_id}/insurance", 
            json=sample_insurance_data
        )
        insurance_id = insurance_response.json()["id"]
        
        # Update insurance
        update_data = {
            "copay_amount": 25.00,
            "deductible_amount": 1500.00
        }
        
        response = await authenticated_client.put(
            f"/api/v1/patients/{patient_id}/insurance/{insurance_id}", 
            json=update_data
        )
        
        assert response.status_code == 200
        data = response.json()
        assert float(data["copay_amount"]) == update_data["copay_amount"]
        assert float(data["deductible_amount"]) == update_data["deductible_amount"]


@pytest.mark.patients
@pytest.mark.integration
class TestPatientVisits:
    """Test patient visit management."""

    async def test_create_patient_visit_success(
        self, 
        authenticated_client: AsyncClient, 
        sample_patient_data: dict,
        sample_patient_visit_data: dict
    ) -> None:
        """Test creating a patient visit record."""
        # Create patient first
        create_response = await authenticated_client.post("/api/v1/patients/", json=sample_patient_data)
        patient_id = create_response.json()["id"]
        
        # Create patient visit
        response = await authenticated_client.post(
            f"/api/v1/patients/{patient_id}/visits", 
            json=sample_patient_visit_data
        )
        
        assert response.status_code == 201
        data = response.json()
        assert data["visit_type"] == sample_patient_visit_data["visit_type"]
        assert data["physician"] == sample_patient_visit_data["physician"]

    async def test_get_patient_visits(
        self, 
        authenticated_client: AsyncClient, 
        sample_patient_data: dict,
        sample_patient_visit_data: dict
    ) -> None:
        """Test getting patient visit history."""
        # Create patient first
        create_response = await authenticated_client.post("/api/v1/patients/", json=sample_patient_data)
        patient_id = create_response.json()["id"]
        
        # Create patient visit
        await authenticated_client.post(
            f"/api/v1/patients/{patient_id}/visits", 
            json=sample_patient_visit_data
        )
        
        # Get visits
        response = await authenticated_client.get(f"/api/v1/patients/{patient_id}/visits")
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 1

    async def test_get_patient_visits_by_date_range(
        self, 
        authenticated_client: AsyncClient, 
        sample_patient_data: dict,
        sample_patient_visit_data: dict
    ) -> None:
        """Test getting patient visits within date range."""
        # Create patient first
        create_response = await authenticated_client.post("/api/v1/patients/", json=sample_patient_data)
        patient_id = create_response.json()["id"]
        
        # Create patient visit
        await authenticated_client.post(
            f"/api/v1/patients/{patient_id}/visits", 
            json=sample_patient_visit_data
        )
        
        # Get visits with date range
        from datetime import datetime, timedelta
        today = datetime.now().date()
        start_date = today - timedelta(days=1)
        end_date = today + timedelta(days=1)
        
        response = await authenticated_client.get(
            f"/api/v1/patients/{patient_id}/visits",
            params={
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat()
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)


@pytest.mark.patients
@pytest.mark.integration
@pytest.mark.slow
class TestPatientWorkflow:
    """Test complete patient management workflow."""

    async def test_complete_patient_lifecycle(
        self, 
        authenticated_client: AsyncClient, 
        sample_patient_data: dict,
        sample_emergency_contact_data: dict,
        sample_insurance_data: dict,
        sample_patient_visit_data: dict
    ) -> None:
        """Test complete patient lifecycle from creation to visit management."""
        # Create patient
        patient_response = await authenticated_client.post("/api/v1/patients/", json=sample_patient_data)
        assert patient_response.status_code == 201
        patient_id = patient_response.json()["id"]
        
        # Add emergency contact
        contact_response = await authenticated_client.post(
            f"/api/v1/patients/{patient_id}/emergency-contacts", 
            json=sample_emergency_contact_data
        )
        assert contact_response.status_code == 201
        
        # Add insurance
        insurance_response = await authenticated_client.post(
            f"/api/v1/patients/{patient_id}/insurance", 
            json=sample_insurance_data
        )
        assert insurance_response.status_code == 201
        
        # Create patient visit
        visit_response = await authenticated_client.post(
            f"/api/v1/patients/{patient_id}/visits", 
            json=sample_patient_visit_data
        )
        assert visit_response.status_code == 201
        
        # Get complete patient profile
        profile_response = await authenticated_client.get(f"/api/v1/patients/{patient_id}")
        assert profile_response.status_code == 200
        
        # Verify all data is present
        patient_data = profile_response.json()
        assert patient_data["first_name"] == sample_patient_data["first_name"]
        
        # Get emergency contacts
        contacts_response = await authenticated_client.get(f"/api/v1/patients/{patient_id}/emergency-contacts")
        assert contacts_response.status_code == 200
        assert len(contacts_response.json()) >= 1
        
        # Get insurance info
        insurance_get_response = await authenticated_client.get(f"/api/v1/patients/{patient_id}/insurance")
        assert insurance_get_response.status_code == 200
        assert len(insurance_get_response.json()) >= 1
        
        # Get visit history
        visits_response = await authenticated_client.get(f"/api/v1/patients/{patient_id}/visits")
        assert visits_response.status_code == 200
        assert len(visits_response.json()) >= 1
        
        # Update patient information
        update_data = {
            "phone_number": "+9876543210",
            "address": "456 Updated St"
        }
        update_response = await authenticated_client.put(f"/api/v1/patients/{patient_id}", json=update_data)
        assert update_response.status_code == 200
        
        # Verify update
        updated_patient_response = await authenticated_client.get(f"/api/v1/patients/{patient_id}")
        updated_data = updated_patient_response.json()
        assert updated_data["phone_number"] == update_data["phone_number"]
        assert updated_data["address"] == update_data["address"]
