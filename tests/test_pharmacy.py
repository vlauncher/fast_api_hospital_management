import pytest
from sqlalchemy.ext.asyncio import AsyncSession
from app.domain.pharmacy.service import PharmacyService


@pytest.fixture
async def pharmacy_service(db: AsyncSession):
    """Pharmacy service fixture"""
    return PharmacyService(db)


@pytest.mark.asyncio
async def test_create_drug(pharmacy_service: PharmacyService):
    """Test creating a drug"""
    drug_in = {
        "name": "Aspirin",
        "code": "ASP001",
        "description": "Pain reliever",
        "unit_price": 500
    }
    drug = await pharmacy_service.create_drug(drug_in)
    assert drug.name == "Aspirin"
    assert drug.code == "ASP001"


@pytest.mark.asyncio
async def test_list_drugs(pharmacy_service: PharmacyService):
    """Test listing drugs"""
    # Create a test drug first
    drug_in = {"name": "Test Drug", "code": "TEST001"}
    await pharmacy_service.create_drug(drug_in)
    
    drugs = await pharmacy_service.list_drugs(limit=100)
    assert len(drugs) >= 1


@pytest.mark.asyncio
async def test_dispense_invalid_quantity(pharmacy_service: PharmacyService):
    """Test dispensing with invalid quantity"""
    dispensing_data = {"patient_id": "test-patient"}
    items = [{"drug_id": "test-drug", "quantity": 0}]
    
    with pytest.raises(ValueError):
        await pharmacy_service.dispense(dispensing_data, items)
