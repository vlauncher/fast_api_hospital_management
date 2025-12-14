# FastAPI Hospital Management System - Phase 1 Implementation Plan

## Overview
This document outlines the detailed implementation plan for Phase 1: Foundation of the Hospital Management System.

## Phase 1 Scope
- **Duration**: Weeks 1-4
- **Focus**: Core infrastructure, authentication, patient management, and audit logging

## 1. Project Structure Setup

### 1.1 Directory Structure
```
hospital-management-system/
├── app/
│   ├── main.py                  # FastAPI application entry point
│   ├── core/
│   │   ├── config.py            # Configuration management
│   │   ├── security.py          # Authentication and security utilities
│   │   ├── permissions.py       # RBAC and ABAC permission system
│   │   ├── events.py            # Event system for audit logging
│   │   └── exceptions.py        # Custom exception handlers
│   ├── api/v1/
│   │   ├── auth/
│   │   │   ├── routes.py         # Authentication endpoints
│   │   │   ├── schemas.py        # Auth request/response models
│   │   │   └── service.py        # Auth business logic
│   │   └── patients/
│   │       ├── routes.py         # Patient endpoints
│   │       ├── schemas.py        # Patient request/response models
│   │       └── service.py        # Patient business logic
│   ├── domain/
│   │   ├── auth/
│   │   │   ├── models.py         # User, Role, Session models
│   │   │   ├── repository.py     # Auth data access
│   │   │   └── service.py        # Auth domain logic
│   │   └── patients/
│   │       ├── models.py         # Patient, EmergencyContact, etc. models
│   │       ├── repository.py     # Patient data access
│   │       └── service.py        # Patient domain logic
│   ├── infrastructure/
│   │   ├── database.py          # Database session management
│   │   ├── redis.py             # Redis connection management
│   │   ├── encryption.py        # PII encryption utilities
│   │   └── audit.py             # Audit logging utilities
│   └── workers/
│       ├── celery_app.py        # Celery configuration
│       └── tasks.py             # Background tasks
├── migrations/                   # Alembic migrations
├── tests/
│   ├── unit/                    # Unit tests
│   └── integration/             # Integration tests
├── docker/                      # Docker configurations
├── docs/                        # Documentation
├── scripts/                     # Utility scripts
├── requirements.txt             # Production dependencies
├── requirements-dev.txt         # Development dependencies
├── Dockerfile                   # Docker build configuration
└── docker-compose.yml           # Development environment
```

### 1.2 Technology Stack
- **Backend**: FastAPI 0.109+
- **Python**: 3.11+
- **Database**: PostgreSQL 15+
- **ORM**: SQLAlchemy 2.0+ (async)
- **Migrations**: Alembic
- **Cache**: Redis 7+
- **Async**: Celery for background tasks
- **Security**: JWT, bcrypt, Argon2
- **Containerization**: Docker

## 2. Core Configuration

### 2.1 Configuration Management (`app/core/config.py`)
```python
from pydantic_settings import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    # Application
    APP_NAME: str = "Hospital Management System"
    APP_VERSION: str = "1.0.0"
    APP_ENV: str = "development"
    
    # Database
    DATABASE_URL: str = "postgresql+asyncpg://user:pass@localhost:5432/hospital"
    DATABASE_POOL_SIZE: int = 20
    DATABASE_MAX_OVERFLOW: int = 10
    
    # Security
    SECRET_KEY: str = "your-secret-key-here"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    ALGORITHM: str = "HS256"
    
    # Encryption
    ENCRYPTION_KEY: str = "your-encryption-key-here"
    
    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"
    
    # Rate Limiting
    RATE_LIMIT: int = 100
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

settings = Settings()
```

### 2.2 Database Setup (`app/infrastructure/database.py`)
```python
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, declarative_base
from app.core.config import settings

# Database engine
engine = create_async_engine(
    settings.DATABASE_URL,
    pool_size=settings.DATABASE_POOL_SIZE,
    max_overflow=settings.DATABASE_MAX_OVERFLOW,
    pool_pre_ping=True,
    pool_recycle=3600
)

# Session factory
AsyncSessionLocal = sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False
)

# Base model
Base = declarative_base()

async def get_db():
    """Dependency to get database session"""
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
```

## 3. Authentication & Authorization System

### 3.1 Security Utilities (`app/core/security.py`)
```python
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
import jwt
from passlib.context import CryptContext
from app.core.config import settings

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)

def create_access_token(subject: str, data: Dict[str, Any]) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({
        "exp": expire,
        "iat": datetime.utcnow(),
        "sub": subject,
        "token_type": "access"
    })
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt

def create_refresh_token(subject: str, data: Dict[str, Any]) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    to_encode.update({
        "exp": expire,
        "iat": datetime.utcnow(),
        "sub": subject,
        "token_type": "refresh"
    })
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt

def decode_token(token: str) -> Optional[Dict[str, Any]]:
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        return payload
    except jwt.PyJWTError:
        return None
```

### 3.2 Permission System (`app/core/permissions.py`)
```python
from typing import List, Dict, Any
from functools import wraps
from fastapi import Request, HTTPException, status
from app.core.security import decode_token

def has_permission(required_permissions: List[str]):
    """Dependency to check user permissions"""
    def decorator(func):
        @wraps(func)
        async def wrapper(request: Request, *args, **kwargs):
            # Extract token from Authorization header
            auth_header = request.headers.get("Authorization")
            if not auth_header or not auth_header.startswith("Bearer "):
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Authentication required"
                )
            
            token = auth_header.split(" ")[1]
            payload = decode_token(token)
            
            if not payload:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid token"
                )
            
            user_permissions = payload.get("permissions", [])
            
            # Check if user has any of the required permissions
            has_access = any(
                perm in user_permissions 
                for perm in required_permissions
            )
            
            if not has_access:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Insufficient permissions"
                )
            
            # Add user info to request state
            request.state.user = payload
            
            return await func(request, *args, **kwargs)
        return wrapper
    return decorator

# Permission constants
class Permissions:
    # User management
    USERS_CREATE = "users:create"
    USERS_READ = "users:read"
    USERS_UPDATE = "users:update"
    USERS_DELETE = "users:delete"
    
    # Patient management
    PATIENTS_CREATE = "patients:create"
    PATIENTS_READ = "patients:read"
    PATIENTS_READ_OWN = "patients:read:own"
    PATIENTS_READ_DEPARTMENT = "patients:read:department"
    PATIENTS_UPDATE = "patients:update"
    PATIENTS_DELETE = "patients:delete"
    
    # System
    AUDIT_READ = "audit:read"
```

### 3.3 Authentication Routes (`app/api/v1/auth/routes.py`)
```python
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.security import (
    create_access_token,
    create_refresh_token,
    verify_password,
    get_password_hash
)
from app.core.permissions import has_permission
from app.domain.auth.models import User
from app.domain.auth.repository import UserRepository
from app.domain.auth.schemas import (
    TokenResponse,
    UserCreate,
    UserResponse,
    LoginRequest
)
from app.infrastructure.database import get_db

router = APIRouter(prefix="/api/v1/auth", tags=["Authentication"])

@router.post("/login", response_model=TokenResponse)
async def login(
    login_data: LoginRequest,
    db: AsyncSession = Depends(get_db)
):
    """Authenticate user and return tokens"""
    user_repo = UserRepository(db)
    
    # Find user by username
    user = await user_repo.get_by_username(login_data.username)
    
    if not user or not verify_password(login_data.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password"
        )
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is inactive"
        )
    
    # Create tokens
    access_token = create_access_token(str(user.id), {
        "username": user.username,
        "email": user.email,
        "role": user.role,
        "permissions": user.permissions,
        "department_id": str(user.department_id) if user.department_id else None
    })
    
    refresh_token = create_refresh_token(str(user.id), {
        "username": user.username
    })
    
    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60
    )

@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(
    refresh_token: str,
    db: AsyncSession = Depends(get_db)
):
    """Refresh access token using refresh token"""
    # Validate refresh token and issue new access token
    # Implementation to be completed
    pass

@router.post("/logout")
async def logout(
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """Logout and revoke current session"""
    # Implementation to be completed
    pass

@router.get("/me", response_model=UserResponse)
@has_permission([Permissions.USERS_READ])
async def get_current_user(
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """Get current user profile"""
    user_id = request.state.user["sub"]
    user_repo = UserRepository(db)
    
    user = await user_repo.get_by_id(user_id)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    return UserResponse.from_orm(user)
```

## 4. Patient Management Module

### 4.1 Patient Models (`app/domain/patients/models.py`)
```python
from sqlalchemy import Column, String, Date, Boolean, JSON, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from app.infrastructure.database import Base
import uuid

class Patient(Base):
    __tablename__ = "patients"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    patient_number = Column(String(50), unique=True, nullable=False)
    first_name = Column(String(100), nullable=False)  # Will be encrypted
    last_name = Column(String(100), nullable=False)   # Will be encrypted
    middle_name = Column(String(100))                # Will be encrypted
    date_of_birth = Column(Date, nullable=False)     # Will be encrypted
    gender = Column(String(30), nullable=False)
    blood_type = Column(String(10))
    phone_primary = Column(String(20), nullable=False)  # Will be encrypted
    phone_secondary = Column(String(20))               # Will be encrypted
    email = Column(String(255))                        # Will be encrypted
    address = Column(JSON)                            # Will be encrypted
    national_id = Column(String(50), unique=True)      # Will be encrypted
    marital_status = Column(String(20))
    occupation = Column(String(100))
    photo_url = Column(String(500))
    is_active = Column(Boolean, default=True)
    registered_date = Column(DateTime, default=func.now())
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    created_by = Column(UUID(as_uuid=True), ForeignKey("users.id"))

class EmergencyContact(Base):
    __tablename__ = "emergency_contacts"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    patient_id = Column(UUID(as_uuid=True), ForeignKey("patients.id", ondelete="CASCADE"))
    name = Column(String(100), nullable=False)
    relationship = Column(String(50), nullable=False)
    phone = Column(String(20), nullable=False)
    email = Column(String(255))
    address = Column(String(500))
    is_primary = Column(Boolean, default=False)
    created_at = Column(DateTime, default=func.now())

class Insurance(Base):
    __tablename__ = "insurance"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    patient_id = Column(UUID(as_uuid=True), ForeignKey("patients.id", ondelete="CASCADE"))
    provider_name = Column(String(200), nullable=False)
    policy_number = Column(String(100), unique=True, nullable=False)
    group_number = Column(String(100))
    policy_holder_name = Column(String(200))
    relationship_to_patient = Column(String(50))
    coverage_start_date = Column(Date, nullable=False)
    coverage_end_date = Column(Date)
    copay_amount = Column(Float)
    coverage_percentage = Column(Float)
    max_coverage = Column(Float)
    is_active = Column(Boolean, default=True)
    verification_status = Column(String(20), default="PENDING")
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
```

### 4.2 Patient Repository (`app/domain/patients/repository.py`)
```python
from typing import Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete
from sqlalchemy.orm import joinedload
from app.domain.patients.models import Patient, EmergencyContact, Insurance
from app.domain.patients.schemas import PatientCreate, PatientUpdate
from app.infrastructure.encryption import encrypt_data, decrypt_data
import uuid

class PatientRepository:
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def create(self, patient_data: PatientCreate, created_by: uuid.UUID) -> Patient:
        """Create a new patient"""
        # Generate patient number
        patient_number = self._generate_patient_number()
        
        # Encrypt sensitive data
        encrypted_data = {
            "first_name": encrypt_data(patient_data.first_name),
            "last_name": encrypt_data(patient_data.last_name),
            "middle_name": encrypt_data(patient_data.middle_name) if patient_data.middle_name else None,
            "date_of_birth": encrypt_data(str(patient_data.date_of_birth)),
            "phone_primary": encrypt_data(patient_data.phone_primary),
            "phone_secondary": encrypt_data(patient_data.phone_secondary) if patient_data.phone_secondary else None,
            "email": encrypt_data(patient_data.email) if patient_data.email else None,
            "address": encrypt_data(str(patient_data.address)) if patient_data.address else None,
            "national_id": encrypt_data(patient_data.national_id) if patient_data.national_id else None,
        }
        
        # Create patient
        patient = Patient(
            patient_number=patient_number,
            **encrypted_data,
            gender=patient_data.gender,
            blood_type=patient_data.blood_type,
            marital_status=patient_data.marital_status,
            occupation=patient_data.occupation,
            created_by=created_by
        )
        
        self.db.add(patient)
        await self.db.commit()
        await self.db.refresh(patient)
        
        return patient
    
    async def get_by_id(self, patient_id: uuid.UUID) -> Optional[Patient]:
        """Get patient by ID"""
        result = await self.db.execute(
            select(Patient).where(Patient.id == patient_id)
        )
        return result.scalar_one_or_none()
    
    async def get_by_patient_number(self, patient_number: str) -> Optional[Patient]:
        """Get patient by patient number"""
        result = await self.db.execute(
            select(Patient).where(Patient.patient_number == patient_number)
        )
        return result.scalar_one_or_none()
    
    async def get_all(
        self,
        skip: int = 0,
        limit: int = 20,
        search: Optional[str] = None,
        is_active: Optional[bool] = None
    ) -> List[Patient]:
        """Get all patients with pagination and filtering"""
        query = select(Patient)
        
        if search:
            # Search by patient number, name, phone, etc.
            # Note: This would need to decrypt data for proper search
            # For now, we'll search on encrypted fields (not ideal)
            query = query.where(
                Patient.patient_number.ilike(f"%{search}%") |
                Patient.first_name.ilike(f"%{search}%") |
                Patient.last_name.ilike(f"%{search}%") |
                Patient.phone_primary.ilike(f"%{search}%")
            )
        
        if is_active is not None:
            query = query.where(Patient.is_active == is_active)
        
        query = query.offset(skip).limit(limit)
        
        result = await self.db.execute(query)
        return result.scalars().all()
    
    async def update(self, patient_id: uuid.UUID, patient_data: PatientUpdate) -> Optional[Patient]:
        """Update patient information"""
        # Implementation to be completed
        pass
    
    async def _generate_patient_number(self) -> str:
        """Generate unique patient number"""
        # Format: PT-YYYYMMDD-XXXX
        import datetime
        today = datetime.date.today()
        date_str = today.strftime("%Y%m%d")
        
        # Get count of patients created today
        result = await self.db.execute(
            select(func.count()).where(Patient.patient_number.like(f"PT-{date_str}-%"))
        )
        count = result.scalar() + 1
        
        return f"PT-{date_str}-{count:04d}"
```

### 4.3 Patient Routes (`app/api/v1/patients/routes.py`)
```python
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional
from app.core.permissions import has_permission, Permissions
from app.domain.patients.schemas import (
    PatientCreate,
    PatientResponse,
    PatientUpdate,
    PatientListResponse
)
from app.domain.patients.repository import PatientRepository
from app.infrastructure.database import get_db
from app.core.security import decode_token
from fastapi import Request

router = APIRouter(prefix="/api/v1/patients", tags=["Patients"])

@router.post("/", response_model=PatientResponse, status_code=status.HTTP_201_CREATED)
@has_permission([Permissions.PATIENTS_CREATE])
async def create_patient(
    patient_data: PatientCreate,
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """Create a new patient"""
    user_id = request.state.user["sub"]
    patient_repo = PatientRepository(db)
    
    # Check if patient with same national ID already exists
    existing_patient = await patient_repo.get_by_national_id(patient_data.national_id)
    if existing_patient:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Patient with this national ID already exists"
        )
    
    patient = await patient_repo.create(patient_data, uuid.UUID(user_id))
    
    return PatientResponse.from_orm(patient)

@router.get("/", response_model=PatientListResponse)
@has_permission([
    Permissions.PATIENTS_READ,
    Permissions.PATIENTS_READ_OWN,
    Permissions.PATIENTS_READ_DEPARTMENT
])
async def get_patients(
    request: Request,
    db: AsyncSession = Depends(get_db),
    skip: int = Query(0, ge=0),
    limit: int = Query(20, le=100),
    search: Optional[str] = None,
    is_active: Optional[bool] = None
):
    """Get list of patients"""
    patient_repo = PatientRepository(db)
    
    # Apply permission-based filtering
    user_permissions = request.state.user["permissions"]
    user_department = request.state.user.get("department_id")
    
    patients = await patient_repo.get_all(
        skip=skip,
        limit=limit,
        search=search,
        is_active=is_active
    )
    
    # Apply field-level access control based on permissions
    # This would involve decrypting only allowed fields
    
    total = len(patients)
    
    return PatientListResponse(
        items=patients,
        total=total,
        page=skip // limit + 1,
        limit=limit
    )

@router.get("/{patient_id}", response_model=PatientResponse)
@has_permission([
    Permissions.PATIENTS_READ,
    Permissions.PATIENTS_READ_OWN,
    Permissions.PATIENTS_READ_DEPARTMENT
])
async def get_patient(
    patient_id: str,
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """Get patient by ID"""
    patient_repo = PatientRepository(db)
    
    patient = await patient_repo.get_by_id(patient_id)
    
    if not patient:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Patient not found"
        )
    
    # Apply permission checks
    # Check if user has access to this patient based on their permissions
    
    return PatientResponse.from_orm(patient)

@router.patch("/{patient_id}", response_model=PatientResponse)
@has_permission([Permissions.PATIENTS_UPDATE])
async def update_patient(
    patient_id: str,
    patient_data: PatientUpdate,
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """Update patient information"""
    patient_repo = PatientRepository(db)
    
    patient = await patient_repo.get_by_id(patient_id)
    
    if not patient:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Patient not found"
        )
    
    updated_patient = await patient_repo.update(patient_id, patient_data)
    
    return PatientResponse.from_orm(updated_patient)

@router.delete("/{patient_id}", status_code=status.HTTP_204_NO_CONTENT)
@has_permission([Permissions.PATIENTS_DELETE])
async def delete_patient(
    patient_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Soft delete patient"""
    patient_repo = PatientRepository(db)
    
    patient = await patient_repo.get_by_id(patient_id)
    
    if not patient:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Patient not found"
        )
    
    await patient_repo.soft_delete(patient_id)
```

## 5. Audit Logging System

### 5.1 Audit Log Model (`app/domain/audit/models.py`)
```python
from sqlalchemy import Column, String, JSON, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from app.infrastructure.database import Base
import uuid

class AuditLog(Base):
    __tablename__ = "audit_logs"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"))
    action = Column(String(50), nullable=False)
    resource_type = Column(String(100), nullable=False)
    resource_id = Column(UUID(as_uuid=True))
    ip_address = Column(String(45))
    user_agent = Column(String(500))
    changes = Column(JSON)
    timestamp = Column(DateTime, default=func.now())
    session_id = Column(UUID(as_uuid=True))
```

### 5.2 Audit Logging Middleware (`app/core/events.py`)
```python
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from sqlalchemy.ext.asyncio import AsyncSession
from app.domain.audit.models import AuditLog
from app.infrastructure.database import get_db
import uuid
import json
from datetime import datetime

class AuditLoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        # Skip audit logging for health checks and public endpoints
        if request.url.path in ["/health", "/docs", "/openapi.json", "/api/v1/auth/login"]:
            return await call_next(request)
        
        # Get database session
        db = next(get_db())
        
        # Capture request information
        user_id = None
        username = None
        
        if hasattr(request.state, 'user'):
            user_id = request.state.user.get('sub')
            username = request.state.user.get('username')
        
        # Capture response
        response = await call_next(request)
        
        # Create audit log entry
        audit_log = AuditLog(
            user_id=user_id,
            action=request.method,
            resource_type=request.url.path.split('/')[3] if len(request.url.path.split('/')) > 3 else "system",
            resource_id=None,  # Would be set based on response
            ip_address=request.client.host,
            user_agent=str(request.headers.get('user-agent')),
            changes={
                "method": request.method,
                "path": request.url.path,
                "status_code": response.status_code,
                "user": username,
                "timestamp": datetime.utcnow().isoformat()
            },
            session_id=str(uuid.uuid4())
        )
        
        db.add(audit_log)
        await db.commit()
        
        return response
```

## 6. Main Application Setup

### 6.1 FastAPI Application (`app/main.py`)
```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.core.events import AuditLoggingMiddleware
from app.api.v1.auth.routes import router as auth_router
from app.api.v1.patients.routes import router as patients_router
from app.infrastructure.database import Base, engine
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="Hospital Management System API",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json"
)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Audit Logging Middleware
app.add_middleware(AuditLoggingMiddleware)

# Include routers
app.include_router(auth_router)
app.include_router(patients_router)

# Health check endpoint
@app.get("/health")
async def health_check():
    return {"status": "healthy", "version": settings.APP_VERSION}

# Database initialization
@app.on_event("startup")
async def on_startup():
    # Create tables (in production, use migrations)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    logger.info("Application started successfully")

@app.on_event("shutdown")
async def on_shutdown():
    logger.info("Application shutting down")
```

## 7. Database Migrations

### 7.1 Alembic Setup
```bash
# Initialize Alembic
alembic init migrations

# Configure alembic.ini
sqlalchemy.url = postgresql+asyncpg://user:pass@localhost:5432/hospital

# Create first migration
alembic revision --autogenerate -m "Initial migration"

# Apply migrations
alembic upgrade head
```

## 8. Docker Setup

### 8.1 Dockerfile
```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Set environment variables
ENV PYTHONPATH=/app
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Run application
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
```

### 8.2 docker-compose.yml
```yaml
version: '3.8'

services:
  api:
    build: .
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=postgresql+asyncpg://user:pass@postgres:5432/hospital
      - REDIS_URL=redis://redis:6379/0
      - SECRET_KEY=your-secret-key-here
      - ENCRYPTION_KEY=your-encryption-key-here
    depends_on:
      - postgres
      - redis
    volumes:
      - .:/app
    restart: unless-stopped

  postgres:
    image: postgres:15
    environment:
      - POSTGRES_DB=hospital
      - POSTGRES_USER=user
      - POSTGRES_PASSWORD=pass
    ports:
      - "5432:5432"
    volumes:
      - pgdata:/var/lib/postgresql/data
    restart: unless-stopped

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    restart: unless-stopped

  celery-worker:
    build: .
    command: celery -A app.workers.celery_app worker --loglevel=info
    environment:
      - DATABASE_URL=postgresql+asyncpg://user:pass@postgres:5432/hospital
      - REDIS_URL=redis://redis:6379/0
    depends_on:
      - postgres
      - redis
      - api
    volumes:
      - .:/app
    restart: unless-stopped

volumes:
  pgdata:
```

## 9. Testing Framework

### 9.1 Test Structure
```
tests/
├── unit/
│   ├── test_auth.py
│   ├── test_patients.py
│   └── test_permissions.py
├── integration/
│   ├── test_api_auth.py
│   ├── test_api_patients.py
│   └── test_database.py
└── conftest.py
```

### 9.2 Sample Test (`tests/unit/test_patients.py`)
```python
import pytest
from sqlalchemy.ext.asyncio import AsyncSession
from app.domain.patients.repository import PatientRepository
from app.domain.patients.schemas import PatientCreate
import uuid

@pytest.mark.asyncio
async def test_create_patient(db_session: AsyncSession):
    """Test patient creation"""
    repo = PatientRepository(db_session)
    
    patient_data = PatientCreate(
        first_name="John",
        last_name="Doe",
        date_of_birth="1990-01-01",
        gender="MALE",
        phone_primary="+1234567890",
        national_id="123-45-6789"
    )
    
    created_by = uuid.uuid4()
    patient = await repo.create(patient_data, created_by)
    
    assert patient is not None
    assert patient.id is not None
    assert patient.patient_number.startswith("PT-")
    assert patient.first_name != "John"  # Should be encrypted
    assert patient.is_active == True
```

## 10. Implementation Timeline

### Week 1: Project Setup & Core Infrastructure
- [ ] Set up project structure
- [ ] Configure database and ORM
- [ ] Implement configuration management
- [ ] Set up logging and error handling
- [ ] Create Docker development environment

### Week 2: Authentication & Authorization
- [ ] Implement JWT authentication
- [ ] Create permission system (RBAC + ABAC)
- [ ] Implement user management
- [ ] Create session management
- [ ] Set up rate limiting

### Week 3: Patient Management
- [ ] Implement patient models and repository
- [ ] Create patient API endpoints
- [ ] Implement PII encryption/decryption
- [ ] Add validation and business logic
- [ ] Implement search and filtering

### Week 4: Audit Logging & Testing
- [ ] Implement audit logging system
- [ ] Create comprehensive middleware
- [ ] Write unit tests
- [ ] Write integration tests
- [ ] Set up CI/CD pipeline
- [ ] Create API documentation

## 11. Key Technical Decisions

### 11.1 Database Choice
- **PostgreSQL**: Chosen for its reliability, JSON support, and advanced features
- **Async SQLAlchemy**: For better performance with async/await
- **Alembic**: For database migrations

### 11.2 Authentication
- **JWT with Refresh Tokens**: Balances security and user experience
- **Short-lived Access Tokens**: 30-minute expiration for security
- **Long-lived Refresh Tokens**: 7-day expiration with rotation

### 11.3 Security
- **PII Encryption**: All sensitive patient data encrypted at rest
- **RBAC + ABAC**: Fine-grained permission control
- **Audit Logging**: Comprehensive tracking of all operations

### 11.4 Performance
- **Async I/O**: Throughout the application for better scalability
- **Connection Pooling**: Database connection pooling
- **Caching**: Redis for session management and caching

## 12. Risk Assessment

### 12.1 Technical Risks
- **Complex Permission System**: May require iterative refinement
- **PII Encryption**: Performance impact on search operations
- **Async ORM**: Learning curve for team members

### 12.2 Mitigation Strategies
- **Incremental Implementation**: Start with basic RBAC, add ABAC later
- **Search Optimization**: Implement dedicated search endpoints
- **Team Training**: Async programming workshops

## 13. Success Criteria

### 13.1 Functional
- ✅ User authentication with JWT tokens
- ✅ Role-based access control
- ✅ Patient CRUD operations
- ✅ PII encryption at rest
- ✅ Comprehensive audit logging

### 13.2 Non-Functional
- ✅ API response time < 500ms for 95% of requests
- ✅ Support 50 concurrent users
- ✅ 99% test coverage for core modules
- ✅ Dockerized development environment

## 14. Next Steps

After completing Phase 1, the team should proceed with:

1. **Phase 2**: Appointments & Scheduling modules
2. **Phase 3**: Electronic Medical Records core
3. **Phase 4**: Prescription management

This implementation plan provides a solid foundation for the Hospital Management System with proper security, scalability, and maintainability.