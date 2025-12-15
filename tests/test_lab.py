import pytest
from sqlalchemy.ext.asyncio import AsyncSession
from app.domain.lab.service import LabService


@pytest.fixture
async def lab_service(db: AsyncSession):
    """Lab service fixture"""
    return LabService(db)


@pytest.mark.asyncio
async def test_create_order(lab_service: LabService):
    """Test creating a lab order"""
    order_in = {
        "patient_id": "test-patient-id",
        "ordered_by": "test-doctor-id",
    }
    order = await lab_service.create_order(order_in)
    assert order.patient_id == "test-patient-id"
    assert order.status == "pending"


@pytest.mark.asyncio
async def test_add_result(lab_service: LabService):
    """Test adding a lab result"""
    # First create an order
    order_in = {"patient_id": "test-patient-id", "ordered_by": "test-doctor-id"}
    order = await lab_service.create_order(order_in)
    
    # Add a result
    result_in = {
        "order_id": order.id,
        "result": "Normal"
    }
    result = await lab_service.add_result(result_in)
    assert result.result == "Normal"
    assert result.verified is False
