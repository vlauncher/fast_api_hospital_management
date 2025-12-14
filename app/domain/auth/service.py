from typing import Optional, List, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime, timedelta
import uuid
import secrets
from fastapi import HTTPException, status

from app.domain.auth.models import User, UserSession, UserStatus
from app.domain.auth.repository import UserRepository, UserSessionRepository
from app.core.security import (
    verify_password, 
    create_access_token, 
    create_refresh_token,
    verify_token
)
from app.api.v1.auth.schemas import (
    UserCreate, 
    UserUpdate, 
    LoginRequest,
    TokenResponse,
    PasswordChangeRequest
)
from app.core.config import settings


class AuthenticationService:
    """Service layer for authentication operations"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self.user_repo = UserRepository(db)
        self.session_repo = UserSessionRepository(db)
    
    async def register_user(self, user_data: UserCreate) -> User:
        """Register a new user"""
        # Check if username already exists
        existing_user = await self.user_repo.get_by_username(user_data.username)
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Username already exists"
            )
        
        # Check if email already exists
        existing_email = await self.user_repo.get_by_email(user_data.email)
        if existing_email:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Email already exists"
            )
        
        # Create user
        user_dict = user_data.dict()
        user_dict['password'] = user_data.password  # Will be hashed in model
        
        user = await self.user_repo.create(user_dict)
        
        # Create initial session (optional)
        # await self._create_user_session(user.id, "registration", None, None)
        
        return user
    
    async def authenticate_user(self, login_data: LoginRequest, ip_address: str = None, user_agent: str = None) -> TokenResponse:
        """Authenticate user and return tokens"""
        # Find user by username
        user = await self.user_repo.get_by_username(login_data.username)
        
        if not user:
            # Increment failed attempts for non-existent username (optional)
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid username or password"
            )
        
        # Check if account is locked
        if user.locked_until and user.locked_until > datetime.utcnow():
            raise HTTPException(
                status_code=status.HTTP_423_LOCKED,
                detail="Account is temporarily locked"
            )
        
        # Check if account is active
        if not user.is_active or user.status != UserStatus.ACTIVE:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Account is not active"
            )
        
        # Verify password
        if not user.verify_password(login_data.password):
            # Increment failed login attempts
            await self.user_repo.increment_failed_login(user.id)
            
            # Check if should lock account
            if user.failed_login_attempts >= 4:  # Lock after 5 failed attempts
                await self.user_repo.lock_account(user.id)
                raise HTTPException(
                    status_code=status.HTTP_423_LOCKED,
                    detail="Account locked due to multiple failed login attempts"
                )
            
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid username or password"
            )
        
        # Reset failed login attempts
        await self.user_repo.reset_failed_login(user.id)
        
        # Update last login
        await self.user_repo.update_last_login(user.id)
        
        # Create tokens
        access_token = create_access_token(str(user.id), {
            "username": user.username,
            "email": user.email,
            "role": user.role.value,
            "permissions": user.get_permissions(),
            "department_id": str(user.department_id) if user.department_id else None
        })
        
        refresh_token = create_refresh_token(str(user.id), {
            "username": user.username
        })
        
        # Create session
        await self._create_user_session(user.id, access_token, refresh_token, ip_address, user_agent)
        
        return TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            token_type="bearer",
            expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60
        )
    
    async def refresh_access_token(self, refresh_token: str) -> TokenResponse:
        """Refresh access token using refresh token"""
        # Validate refresh token
        payload = verify_token(refresh_token, "refresh")
        if not payload:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired refresh token"
            )
        
        user_id = payload.get("sub")
        user = await self.user_repo.get_by_id(uuid.UUID(user_id))
        
        if not user or not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found or inactive"
            )
        
        # Check if refresh token session exists and is active
        session = await self.session_repo.get_by_refresh_token(refresh_token)
        if not session or not session.is_active or session.is_expired():
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid session"
            )
        
        # Create new access token
        access_token = create_access_token(str(user.id), {
            "username": user.username,
            "email": user.email,
            "role": user.role.value,
            "permissions": user.get_permissions(),
            "department_id": str(user.department_id) if user.department_id else None
        })
        
        # Update session
        await self.session_repo.update_last_accessed(session.id)
        
        return TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,  # Keep same refresh token
            token_type="bearer",
            expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60
        )
    
    async def logout_user(self, access_token: str) -> None:
        """Logout user by revoking session"""
        # Get token payload
        payload = verify_token(access_token, "access")
        if not payload:
            return  # Token is invalid, nothing to logout
        
        # Find and revoke session
        session = await self.session_repo.get_by_token(access_token)
        if session:
            await self.session_repo.revoke(session.id)
    
    async def logout_all_sessions(self, user_id: uuid.UUID) -> None:
        """Logout user from all devices"""
        await self.session_repo.revoke_all_user_sessions(user_id)
    
    async def change_password(self, user_id: uuid.UUID, password_data: PasswordChangeRequest) -> None:
        """Change user password"""
        user = await self.user_repo.get_by_id(user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        # Verify current password
        if not user.verify_password(password_data.current_password):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Current password is incorrect"
            )
        
        # Update password
        user.set_password(password_data.new_password)
        await self.db.commit()
        
        # Revoke all sessions (force re-login with new password)
        await self.session_repo.revoke_all_user_sessions(user_id)
    
    async def get_user_sessions(self, user_id: uuid.UUID) -> List[UserSession]:
        """Get all active sessions for a user"""
        return await self.session_repo.get_active_sessions(user_id)
    
    async def revoke_session(self, session_id: uuid.UUID) -> None:
        """Revoke a specific session"""
        await self.session_repo.revoke(session_id)
    
    async def _create_user_session(
        self, 
        user_id: uuid.UUID, 
        access_token: str, 
        refresh_token: str,
        ip_address: str = None,
        user_agent: str = None
    ) -> UserSession:
        """Create a new user session"""
        expires_at = datetime.utcnow() + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
        
        session_data = {
            "user_id": user_id,
            "session_token": access_token,
            "refresh_token": refresh_token,
            "ip_address": ip_address,
            "user_agent": user_agent,
            "expires_at": expires_at
        }
        
        return await self.session_repo.create(session_data)


class UserService:
    """Service layer for user management operations"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self.user_repo = UserRepository(db)
    
    async def create_user(self, user_data: UserCreate) -> User:
        """Create a new user (admin function)"""
        return await AuthenticationService(self.db).register_user(user_data)
    
    async def get_user_by_id(self, user_id: uuid.UUID) -> Optional[User]:
        """Get user by ID"""
        return await self.user_repo.get_by_id(user_id)
    
    async def get_users(
        self,
        skip: int = 0,
        limit: int = 20,
        role: Optional[str] = None,
        department_id: Optional[uuid.UUID] = None,
        is_active: Optional[bool] = None,
        search: Optional[str] = None
    ) -> List[User]:
        """Get users with filtering and pagination"""
        return await self.user_repo.get_all(
            skip=skip,
            limit=limit,
            role=role,
            department_id=department_id,
            is_active=is_active,
            search=search
        )
    
    async def update_user(self, user_id: uuid.UUID, user_data: UserUpdate) -> Optional[User]:
        """Update user information"""
        # Check if email is being updated and if it already exists
        if user_data.email:
            existing_user = await self.user_repo.get_by_email(user_data.email)
            if existing_user and existing_user.id != user_id:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Email already exists"
                )
        
        update_dict = user_data.dict(exclude_unset=True)
        return await self.user_repo.update(user_id, update_dict)
    
    async def deactivate_user(self, user_id: uuid.UUID) -> None:
        """Deactivate user account"""
        await self.user_repo.deactivate(user_id)
    
    async def delete_user(self, user_id: uuid.UUID) -> bool:
        """Delete user account"""
        return await self.user_repo.delete(user_id)
    
    async def count_users(
        self,
        role: Optional[str] = None,
        department_id: Optional[uuid.UUID] = None,
        is_active: Optional[bool] = None
    ) -> int:
        """Count users with optional filters"""
        return await self.user_repo.count(
            role=role,
            department_id=department_id,
            is_active=is_active
        )
