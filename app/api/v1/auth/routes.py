from fastapi import APIRouter, Depends, HTTPException, status, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional
import uuid
import math

from app.core.permissions import require_permissions, Permissions
from app.core.security import verify_token
from app.domain.auth.service import AuthenticationService, UserService
from app.domain.auth.models import UserRole
from app.api.v1.auth.schemas import (
    LoginRequest,
    TokenResponse,
    UserCreate,
    UserResponse,
    UserUpdate,
    UserListResponse,
    PasswordChangeRequest,
    SessionResponse,
    SessionListResponse,
    SuccessResponse
)
from app.infrastructure.database import get_db

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/login", response_model=TokenResponse, status_code=status.HTTP_200_OK)
async def login(
    login_data: LoginRequest,
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """Authenticate user and return tokens"""
    auth_service = AuthenticationService(db)
    
    # Get client information
    ip_address = request.client.host
    user_agent = request.headers.get("user-agent")
    
    return await auth_service.authenticate_user(
        login_data=login_data,
        ip_address=ip_address,
        user_agent=user_agent
    )


@router.post("/refresh", response_model=TokenResponse, status_code=status.HTTP_200_OK)
async def refresh_token(
    refresh_token_data: dict,
    db: AsyncSession = Depends(get_db)
):
    """Refresh access token using refresh token"""
    refresh_token = refresh_token_data.get("refresh_token")
    if not refresh_token:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Refresh token is required"
        )
    
    auth_service = AuthenticationService(db)
    return await auth_service.refresh_access_token(refresh_token)


@router.post("/logout", status_code=status.HTTP_200_OK)
async def logout(
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """Logout and revoke current session"""
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Access token is required"
        )
    
    access_token = auth_header.split(" ")[1]
    auth_service = AuthenticationService(db)
    await auth_service.logout_user(access_token)
    
    return SuccessResponse(message="Logged out successfully")


@router.post("/logout-all", status_code=status.HTTP_200_OK)
async def logout_all_sessions(
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """Logout from all devices"""
    user_payload = require_permissions([])(request)
    user_id = uuid.UUID(user_payload["sub"])
    
    auth_service = AuthenticationService(db)
    await auth_service.logout_all_sessions(user_id)
    
    return SuccessResponse(message="Logged out from all devices successfully")


@router.post("/change-password", status_code=status.HTTP_200_OK)
async def change_password(
    password_data: PasswordChangeRequest,
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """Change user password"""
    user_payload = require_permissions([])(request)
    user_id = uuid.UUID(user_payload["sub"])
    
    auth_service = AuthenticationService(db)
    await auth_service.change_password(user_id, password_data)
    
    return SuccessResponse(message="Password changed successfully")


@router.get("/me", response_model=UserResponse, status_code=status.HTTP_200_OK)
async def get_current_user(
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """Get current user profile"""
    user_payload = require_permissions([Permissions.USERS_READ])(request)
    user_id = uuid.UUID(user_payload["sub"])
    
    user_service = UserService(db)
    user = await user_service.get_user_by_id(user_id)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    return UserResponse.from_orm(user)


@router.put("/me", response_model=UserResponse, status_code=status.HTTP_200_OK)
async def update_current_user(
    user_data: UserUpdate,
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """Update current user profile"""
    user_payload = require_permissions([Permissions.USERS_UPDATE])(request)
    user_id = uuid.UUID(user_payload["sub"])
    
    # Users can only update their own profile (not role, permissions, or active status)
    restricted_data = user_data.dict(exclude_unset=True)
    restricted_data.pop("role", None)
    restricted_data.pop("permissions", None)
    restricted_data.pop("is_active", None)
    
    user_service = UserService(db)
    user = await user_service.update_user(user_id, UserUpdate(**restricted_data))
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    return UserResponse.from_orm(user)


@router.get("/sessions", response_model=SessionListResponse, status_code=status.HTTP_200_OK)
async def get_user_sessions(
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """Get current user's active sessions"""
    user_payload = require_permissions([])(request)
    user_id = uuid.UUID(user_payload["sub"])
    
    auth_service = AuthenticationService(db)
    sessions = await auth_service.get_user_sessions(user_id)
    
    return SessionListResponse(
        items=[SessionResponse.from_orm(session) for session in sessions],
        total=len(sessions)
    )


@router.delete("/sessions/{session_id}", status_code=status.HTTP_200_OK)
async def revoke_session(
    session_id: uuid.UUID,
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """Revoke a specific session"""
    user_payload = require_permissions([])(request)
    user_id = uuid.UUID(user_payload["sub"])
    
    auth_service = AuthenticationService(db)
    
    # Verify session belongs to current user
    sessions = await auth_service.get_user_sessions(user_id)
    session_ids = [session.id for session in sessions]
    
    if session_id not in session_ids:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found"
        )
    
    await auth_service.revoke_session(session_id)
    
    return SuccessResponse(message="Session revoked successfully")


# Admin-only user management endpoints
@router.post("/users", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def create_user(
    user_data: UserCreate,
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """Create a new user (admin only)"""
    require_permissions([Permissions.USERS_CREATE])(request)
    
    user_service = UserService(db)
    user = await user_service.create_user(user_data)
    
    return UserResponse.from_orm(user)


@router.get("/users", response_model=UserListResponse, status_code=status.HTTP_200_OK)
async def get_users(
    request: Request,
    db: AsyncSession = Depends(get_db),
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    role: Optional[UserRole] = None,
    department_id: Optional[uuid.UUID] = None,
    is_active: Optional[bool] = None,
    search: Optional[str] = None
):
    """Get users with filtering and pagination (admin only)"""
    require_permissions([Permissions.USERS_READ])(request)
    
    user_service = UserService(db)
    users = await user_service.get_users(
        skip=skip,
        limit=limit,
        role=role,
        department_id=department_id,
        is_active=is_active,
        search=search
    )
    
    total = await user_service.count_users(
        role=role,
        department_id=department_id,
        is_active=is_active
    )
    
    pages = math.ceil(total / limit) if limit > 0 else 0
    
    return UserListResponse(
        items=[UserResponse.from_orm(user) for user in users],
        total=total,
        page=skip // limit + 1 if limit > 0 else 1,
        limit=limit,
        pages=pages
    )


@router.get("/users/{user_id}", response_model=UserResponse, status_code=status.HTTP_200_OK)
async def get_user(
    user_id: uuid.UUID,
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """Get user by ID (admin only)"""
    require_permissions([Permissions.USERS_READ])(request)
    
    user_service = UserService(db)
    user = await user_service.get_user_by_id(user_id)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    return UserResponse.from_orm(user)


@router.put("/users/{user_id}", response_model=UserResponse, status_code=status.HTTP_200_OK)
async def update_user(
    user_id: uuid.UUID,
    user_data: UserUpdate,
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """Update user (admin only)"""
    require_permissions([Permissions.USERS_UPDATE])(request)
    
    user_service = UserService(db)
    user = await user_service.update_user(user_id, user_data)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    return UserResponse.from_orm(user)


@router.delete("/users/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(
    user_id: uuid.UUID,
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """Delete user (admin only)"""
    require_permissions([Permissions.USERS_DELETE])(request)
    
    user_service = UserService(db)
    success = await user_service.delete_user(user_id)
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )


@router.post("/users/{user_id}/deactivate", status_code=status.HTTP_200_OK)
async def deactivate_user(
    user_id: uuid.UUID,
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """Deactivate user account (admin only)"""
    require_permissions([Permissions.USERS_UPDATE])(request)
    
    user_service = UserService(db)
    await user_service.deactivate_user(user_id)
    
    return SuccessResponse(message="User deactivated successfully")
