import pytest
import asyncio
from typing import Generator, AsyncGenerator
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from fastapi.testclient import TestClient

from app.main import app
from app.core.config import settings
from app.infrastructure.database import get_db, Base
from app.core.security import create_access_token, get_password_hash
from app.domain.auth.models import User, Role


# Test database URL
TEST_DATABASE_URL = "postgresql+asyncpg://postgres:postgres@localhost:5432/test_hospital_management"

# Create test engine
test_engine = create_async_engine(
    TEST_DATABASE_URL,
    echo=True,
    pool_pre_ping=True,
)

# Create test session
TestSessionLocal = sessionmaker(
    test_engine, class_=AsyncSession, expire_on_commit=False
)


@pytest.fixture(scope="session")
def event_loop() -> Generator:
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="function")
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    """Create a fresh database session for each test."""
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    async with TestSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()
    
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest.fixture(scope="function")
async def client(db_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    """Create a test client with database dependency override."""
    
    def override_get_db():
        return db_session
    
    app.dependency_overrides[get_db] = override_get_db
    
    async with AsyncClient(app=app, base_url="http://test") as ac:
        yield ac
    
    app.dependency_overrides.clear()


@pytest.fixture(scope="function")
async def test_user(db_session: AsyncSession) -> User:
    """Create a test user for authentication tests."""
    # Create test role
    role = Role(
        name="test_role",
        description="Test role for testing",
        permissions=["read:patients", "write:patients"]
    )
    db_session.add(role)
    await db_session.commit()
    await db_session.refresh(role)
    
    # Create test user
    user = User(
        username="testuser",
        email="test@example.com",
        password_hash=get_password_hash("testpassword123"),
        full_name="Test User",
        phone_number="+1234567890",
        is_active=True,
        is_verified=True
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    
    return user


@pytest.fixture(scope="function")
async def admin_user(db_session: AsyncSession) -> User:
    """Create an admin user for admin tests."""
    # Create admin role
    role = Role(
        name="admin",
        description="Administrator role",
        permissions=["*"]  # All permissions
    )
    db_session.add(role)
    await db_session.commit()
    await db_session.refresh(role)
    
    # Create admin user
    user = User(
        username="admin",
        email="admin@example.com",
        password_hash=get_password_hash("adminpassword123"),
        full_name="Admin User",
        phone_number="+1234567890",
        is_active=True,
        is_verified=True
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    
    return user


@pytest.fixture(scope="function")
def test_token(test_user: User) -> str:
    """Create a test JWT token for authentication."""
    return create_access_token(
        data={"sub": test_user.username, "user_id": str(test_user.id)}
    )


@pytest.fixture(scope="function")
def admin_token(admin_user: User) -> str:
    """Create an admin JWT token for admin authentication."""
    return create_access_token(
        data={"sub": admin_user.username, "user_id": str(admin_user.id)}
    )


@pytest.fixture(scope="function")
async def authenticated_client(
    client: AsyncClient, 
    test_token: str
) -> AsyncGenerator[AsyncClient, None]:
    """Create an authenticated test client."""
    client.headers.update({"Authorization": f"Bearer {test_token}"})
    yield client


@pytest.fixture(scope="function")
async def admin_client(
    client: AsyncClient, 
    admin_token: str
) -> AsyncGenerator[AsyncClient, None]:
    """Create an admin authenticated test client."""
    client.headers.update({"Authorization": f"Bearer {admin_token}"})
    yield client


@pytest.fixture(scope="function")
def sample_patient_data() -> dict:
    """Sample patient data for testing."""
    return {
        "first_name": "John",
        "last_name": "Doe",
        "date_of_birth": "1990-01-01",
        "gender": "MALE",
        "blood_type": "O_POSITIVE",
        "phone_number": "+1234567890",
        "email": "john.doe@example.com",
        "address": "123 Main St",
        "city": "New York",
        "state": "NY",
        "postal_code": "10001",
        "country": "USA",
        "marital_status": "SINGLE",
        "emergency_contact_name": "Jane Doe",
        "emergency_contact_phone": "+1234567891",
        "emergency_contact_relationship": "Spouse",
        "primary_care_physician": "Dr. Smith",
        "allergies": "Penicillin",
        "medical_conditions": "Hypertension",
        "medications": "Lisinopril"
    }


@pytest.fixture(scope="function")
def sample_emergency_contact_data() -> dict:
    """Sample emergency contact data for testing."""
    return {
        "first_name": "Jane",
        "last_name": "Doe",
        "relationship": "Spouse",
        "phone_number": "+1234567891",
        "email": "jane.doe@example.com",
        "address": "123 Main St",
        "city": "New York",
        "state": "NY",
        "postal_code": "10001",
        "country": "USA",
        "is_primary": True
    }


@pytest.fixture(scope="function")
def sample_insurance_data() -> dict:
    """Sample insurance data for testing."""
    return {
        "provider_name": "Blue Cross Blue Shield",
        "policy_number": "POL123456",
        "group_number": "GRP789012",
        "subscriber_name": "John Doe",
        "subscriber_relationship": "Self",
        "coverage_type": "PPO",
        "copay_amount": 20.00,
        "deductible_amount": 1000.00,
        "effective_date": "2024-01-01",
        "expiration_date": "2024-12-31"
    }


@pytest.fixture(scope="function")
def sample_patient_visit_data() -> dict:
    """Sample patient visit data for testing."""
    return {
        "visit_type": "Regular Checkup",
        "department": "General Medicine",
        "physician": "Dr. Smith",
        "chief_complaint": "Annual physical examination",
        "diagnosis": "Healthy",
        "treatment": "Routine checkup completed",
        "notes": "Patient in good health"
    }


# Pytest configuration
def pytest_configure(config):
    """Configure pytest with custom markers."""
    config.addinivalue_line(
        "markers", "unit: mark test as a unit test"
    )
    config.addinivalue_line(
        "markers", "integration: mark test as an integration test"
    )
    config.addinivalue_line(
        "markers", "auth: mark test as authentication related"
    )
    config.addinivalue_line(
        "markers", "patients: mark test as patient management related"
    )
    config.addinivalue_line(
        "markers", "audit: mark test as audit logging related"
    )
    config.addinivalue_line(
        "markers", "slow: mark test as slow running"
    )


@pytest.fixture(autouse=True)
async def cleanup_redis():
    """Clean up Redis before and after each test."""
    try:
        from app.infrastructure.redis import get_redis_client
        redis_client = await get_redis_client()
        await redis_client.flushdb()
    except Exception:
        pass  # Redis might not be available in test environment


@pytest.fixture(scope="session")
async def setup_test_database():
    """Set up the test database before running tests."""
    try:
        async with test_engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        yield
    finally:
        async with test_engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
