from pydantic import BaseModel, EmailStr, Field, validator
from typing import Optional, List
from datetime import datetime
import uuid
from app.domain.auth.models import UserRole, UserStatus


class BaseUserSchema(BaseModel):
    """Base schema for user data"""
    email: EmailStr
    first_name: str = Field(..., min_length=1, max_length=100)
    last_name: str = Field(..., min_length=1, max_length=100)
    phone: Optional[str] = Field(None, max_length=20)
    role: UserRole
    department_id: Optional[uuid.UUID] = None
    
    @validator('phone')
    def validate_phone(cls, v):
        if v and not v.replace('+', '').replace('-', '').replace(' ', '').isdigit():
            raise ValueError('Phone number must contain only digits, +, -, and spaces')
        return v


class UserCreate(BaseUserSchema):
    """Schema for creating a new user"""
    password: str = Field(..., min_length=8, max_length=128)
    
    @validator('password')
    def validate_password(cls, v):
        if len(v) < 8:
            raise ValueError('Password must be at least 8 characters long')
        if not any(c.isupper() for c in v):
            raise ValueError('Password must contain at least one uppercase letter')
        if not any(c.islower() for c in v):
            raise ValueError('Password must contain at least one lowercase letter')
        if not any(c.isdigit() for c in v):
            raise ValueError('Password must contain at least one digit')
        return v


class UserUpdate(BaseModel):
    """Schema for updating user information"""
    email: Optional[EmailStr] = None
    first_name: Optional[str] = Field(None, min_length=1, max_length=100)
    last_name: Optional[str] = Field(None, min_length=1, max_length=100)
    phone: Optional[str] = Field(None, max_length=20)
    role: Optional[UserRole] = None
    department_id: Optional[uuid.UUID] = None
    is_active: Optional[bool] = None
    permissions: Optional[List[str]] = None


class UserResponse(BaseUserSchema):
    """Schema for user response data"""
    id: uuid.UUID
    is_active: bool
    status: UserStatus
    is_verified: bool
    permissions: List[str]
    created_at: datetime
    updated_at: datetime
    last_login_at: Optional[datetime] = None
    department: Optional['DepartmentResponse'] = None
    
    class Config:
        from_attributes = True


class DepartmentResponse(BaseModel):
    """Schema for department response data"""
    id: uuid.UUID
    name: str
    code: str
    description: Optional[str] = None
    is_active: bool
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class DepartmentCreate(BaseModel):
    """Schema for creating a new department"""
    name: str = Field(..., min_length=1, max_length=200)
    code: str = Field(..., min_length=2, max_length=20)
    description: Optional[str] = Field(None, max_length=500)
    
    @validator('code')
    def validate_code(cls, v):
        if not v.isalnum():
            raise ValueError('Department code must contain only alphanumeric characters')
        return v.upper()


class DepartmentUpdate(BaseModel):
    """Schema for updating department information"""
    name: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = Field(None, max_length=500)
    is_active: Optional[bool] = None


class LoginRequest(BaseModel):
    """Schema for login request"""
    email: EmailStr
    password: str = Field(..., min_length=1)


class TokenResponse(BaseModel):
    """Schema for token response"""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int


class RefreshTokenRequest(BaseModel):
    """Schema for refresh token request"""
    refresh_token: str


class PasswordChangeRequest(BaseModel):
    """Schema for password change request"""
    current_password: str = Field(..., min_length=1)
    new_password: str = Field(..., min_length=8, max_length=128)
    
    @validator('new_password')
    def validate_new_password(cls, v):
        if len(v) < 8:
            raise ValueError('Password must be at least 8 characters long')
        if not any(c.isupper() for c in v):
            raise ValueError('Password must contain at least one uppercase letter')
        if not any(c.islower() for c in v):
            raise ValueError('Password must contain at least one lowercase letter')
        if not any(c.isdigit() for c in v):
            raise ValueError('Password must contain at least one digit')
        return v


class PasswordResetRequest(BaseModel):
    """Schema for password reset request"""
    email: EmailStr


class PasswordResetConfirm(BaseModel):
    """Schema for password reset confirmation"""
    token: str
    new_password: str = Field(..., min_length=8, max_length=128)
    
    @validator('new_password')
    def validate_new_password(cls, v):
        if len(v) < 8:
            raise ValueError('Password must be at least 8 characters long')
        if not any(c.isupper() for c in v):
            raise ValueError('Password must contain at least one uppercase letter')
        if not any(c.islower() for c in v):
            raise ValueError('Password must contain at least one lowercase letter')
        if not any(c.isdigit() for c in v):
            raise ValueError('Password must contain at least one digit')
        return v


class UserListResponse(BaseModel):
    """Schema for paginated user list response"""
    items: List[UserResponse]
    total: int
    page: int
    limit: int
    pages: int


class DepartmentListResponse(BaseModel):
    """Schema for department list response"""
    items: List[DepartmentResponse]
    total: int


class SessionResponse(BaseModel):
    """Schema for session response"""
    id: uuid.UUID
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    is_active: bool
    created_at: datetime
    last_accessed_at: datetime
    expires_at: datetime
    
    class Config:
        from_attributes = True


class SessionListResponse(BaseModel):
    """Schema for session list response"""
    items: List[SessionResponse]
    total: int


class ErrorResponse(BaseModel):
    """Schema for error responses"""
    error: str
    message: str
    details: Optional[dict] = None


class SuccessResponse(BaseModel):
    """Schema for success responses"""
    success: bool = True
    message: str
    data: Optional[dict] = None


# Update forward references
UserResponse.model_rebuild()
