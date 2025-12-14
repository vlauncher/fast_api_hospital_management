from typing import Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete, and_, or_
from sqlalchemy.orm import joinedload, selectinload
from datetime import datetime, timedelta
from app.domain.auth.models import User, UserSession, Department, UserRole, UserStatus
import uuid


class UserRepository:
    """Repository for user data access operations"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def create(self, user_data: dict) -> User:
        """Create a new user"""
        user = User(**user_data)
        
        # Encrypt sensitive data
        user.encrypt_sensitive_data()
        
        self.db.add(user)
        await self.db.commit()
        await self.db.refresh(user)
        
        return user
    
    async def get_by_id(self, user_id: uuid.UUID) -> Optional[User]:
        """Get user by ID"""
        result = await self.db.execute(
            select(User)
            .options(selectinload(User.department))
            .where(User.id == user_id)
        )
        user = result.scalar_one_or_none()
        
        if user:
            user.decrypt_sensitive_data()
        
        return user
    
    async def get_by_username(self, username: str) -> Optional[User]:
        """Get user by username"""
        result = await self.db.execute(
            select(User)
            .options(selectinload(User.department))
            .where(User.username == username)
        )
        user = result.scalar_one_or_none()
        
        if user:
            user.decrypt_sensitive_data()
        
        return user
    
    async def get_by_email(self, email: str) -> Optional[User]:
        """Get user by email"""
        result = await self.db.execute(
            select(User)
            .options(selectinload(User.department))
            .where(User.email == email)
        )
        user = result.scalar_one_or_none()
        
        if user:
            user.decrypt_sensitive_data()
        
        return user
    
    async def get_all(
        self,
        skip: int = 0,
        limit: int = 20,
        role: Optional[UserRole] = None,
        department_id: Optional[uuid.UUID] = None,
        is_active: Optional[bool] = None,
        search: Optional[str] = None
    ) -> List[User]:
        """Get all users with filtering and pagination"""
        query = select(User).options(selectinload(User.department))
        
        if role:
            query = query.where(User.role == role)
        
        if department_id:
            query = query.where(User.department_id == department_id)
        
        if is_active is not None:
            query = query.where(User.is_active == is_active)
        
        if search:
            # Search by username, email, or name (note: name fields are encrypted)
            query = query.where(
                or_(
                    User.username.ilike(f"%{search}%"),
                    User.email.ilike(f"%{search}%")
                )
            )
        
        query = query.offset(skip).limit(limit)
        
        result = await self.db.execute(query)
        users = result.scalars().all()
        
        # Decrypt sensitive data for all users
        for user in users:
            user.decrypt_sensitive_data()
        
        return users
    
    async def update(self, user_id: uuid.UUID, update_data: dict) -> Optional[User]:
        """Update user information"""
        # Remove sensitive fields that should be encrypted separately
        sensitive_fields = ['first_name', 'last_name', 'middle_name', 'phone']
        encrypted_data = {}
        
        for field in sensitive_fields:
            if field in update_data:
                encrypted_data[field] = update_data.pop(field)
        
        # Update non-sensitive fields
        if update_data:
            await self.db.execute(
                update(User)
                .where(User.id == user_id)
                .values(**update_data)
            )
        
        # Update sensitive fields with encryption
        if encrypted_data:
            user = await self.get_by_id(user_id)
            if user:
                for field, value in encrypted_data.items():
                    setattr(user, field, value)
                user.encrypt_sensitive_data()
        
        await self.db.commit()
        return await self.get_by_id(user_id)
    
    async def update_last_login(self, user_id: uuid.UUID) -> None:
        """Update user's last login timestamp"""
        await self.db.execute(
            update(User)
            .where(User.id == user_id)
            .values(last_login_at=datetime.utcnow())
        )
        await self.db.commit()
    
    async def increment_failed_login(self, user_id: uuid.UUID) -> None:
        """Increment failed login attempts"""
        await self.db.execute(
            update(User)
            .where(User.id == user_id)
            .values(failed_login_attempts=User.failed_login_attempts + 1)
        )
        await self.db.commit()
    
    async def reset_failed_login(self, user_id: uuid.UUID) -> None:
        """Reset failed login attempts"""
        await self.db.execute(
            update(User)
            .where(User.id == user_id)
            .values(failed_login_attempts=0, locked_until=None)
        )
        await self.db.commit()
    
    async def lock_account(self, user_id: uuid.UUID, lock_duration_hours: int = 24) -> None:
        """Lock user account for specified duration"""
        lock_until = datetime.utcnow() + timedelta(hours=lock_duration_hours)
        await self.db.execute(
            update(User)
            .where(User.id == user_id)
            .values(locked_until=lock_until, status=UserStatus.SUSPENDED)
        )
        await self.db.commit()
    
    async def deactivate(self, user_id: uuid.UUID) -> None:
        """Deactivate user account"""
        await self.db.execute(
            update(User)
            .where(User.id == user_id)
            .values(is_active=False, status=UserStatus.INACTIVE)
        )
        await self.db.commit()
    
    async def delete(self, user_id: uuid.UUID) -> bool:
        """Delete user account"""
        result = await self.db.execute(
            delete(User).where(User.id == user_id)
        )
        await self.db.commit()
        return result.rowcount > 0
    
    async def count(
        self,
        role: Optional[UserRole] = None,
        department_id: Optional[uuid.UUID] = None,
        is_active: Optional[bool] = None
    ) -> int:
        """Count users with optional filters"""
        query = select(User.id)
        
        if role:
            query = query.where(User.role == role)
        
        if department_id:
            query = query.where(User.department_id == department_id)
        
        if is_active is not None:
            query = query.where(User.is_active == is_active)
        
        result = await self.db.execute(query)
        return len(result.all())


class UserSessionRepository:
    """Repository for user session data access operations"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def create(self, session_data: dict) -> UserSession:
        """Create a new user session"""
        session = UserSession(**session_data)
        self.db.add(session)
        await self.db.commit()
        await self.db.refresh(session)
        return session
    
    async def get_by_token(self, session_token: str) -> Optional[UserSession]:
        """Get session by token"""
        result = await self.db.execute(
            select(UserSession)
            .options(selectinload(UserSession.user))
            .where(UserSession.session_token == session_token)
        )
        return result.scalar_one_or_none()
    
    async def get_by_refresh_token(self, refresh_token: str) -> Optional[UserSession]:
        """Get session by refresh token"""
        result = await self.db.execute(
            select(UserSession)
            .options(selectinload(UserSession.user))
            .where(UserSession.refresh_token == refresh_token)
        )
        return result.scalar_one_or_none()
    
    async def get_active_sessions(self, user_id: uuid.UUID) -> List[UserSession]:
        """Get all active sessions for a user"""
        result = await self.db.execute(
            select(UserSession)
            .where(
                and_(
                    UserSession.user_id == user_id,
                    UserSession.is_active == True,
                    UserSession.expires_at > datetime.utcnow()
                )
            )
        )
        return result.scalars().all()
    
    async def update_last_accessed(self, session_id: uuid.UUID) -> None:
        """Update session's last accessed timestamp"""
        await self.db.execute(
            update(UserSession)
            .where(UserSession.id == session_id)
            .values(last_accessed_at=datetime.utcnow())
        )
        await self.db.commit()
    
    async def revoke(self, session_id: uuid.UUID) -> None:
        """Revoke a session"""
        await self.db.execute(
            update(UserSession)
            .where(UserSession.id == session_id)
            .values(is_active=False)
        )
        await self.db.commit()
    
    async def revoke_all_user_sessions(self, user_id: uuid.UUID) -> None:
        """Revoke all sessions for a user"""
        await self.db.execute(
            update(UserSession)
            .where(UserSession.user_id == user_id)
            .values(is_active=False)
        )
        await self.db.commit()
    
    async def cleanup_expired_sessions(self) -> int:
        """Clean up expired sessions"""
        result = await self.db.execute(
            delete(UserSession)
            .where(UserSession.expires_at < datetime.utcnow())
        )
        await self.db.commit()
        return result.rowcount


class DepartmentRepository:
    """Repository for department data access operations"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def create(self, department_data: dict) -> Department:
        """Create a new department"""
        department = Department(**department_data)
        self.db.add(department)
        await self.db.commit()
        await self.db.refresh(department)
        return department
    
    async def get_by_id(self, department_id: uuid.UUID) -> Optional[Department]:
        """Get department by ID"""
        result = await self.db.execute(
            select(Department).where(Department.id == department_id)
        )
        return result.scalar_one_or_none()
    
    async def get_by_code(self, code: str) -> Optional[Department]:
        """Get department by code"""
        result = await self.db.execute(
            select(Department).where(Department.code == code)
        )
        return result.scalar_one_or_none()
    
    async def get_all(self, is_active: Optional[bool] = None) -> List[Department]:
        """Get all departments"""
        query = select(Department)
        
        if is_active is not None:
            query = query.where(Department.is_active == is_active)
        
        result = await self.db.execute(query)
        return result.scalars().all()
    
    async def update(self, department_id: uuid.UUID, update_data: dict) -> Optional[Department]:
        """Update department information"""
        await self.db.execute(
            update(Department)
            .where(Department.id == department_id)
            .values(**update_data)
        )
        await self.db.commit()
        return await self.get_by_id(department_id)
    
    async def delete(self, department_id: uuid.UUID) -> bool:
        """Delete department"""
        result = await self.db.execute(
            delete(Department).where(Department.id == department_id)
        )
        await self.db.commit()
        return result.rowcount > 0
