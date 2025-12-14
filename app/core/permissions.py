from typing import List, Dict, Any, Optional
from functools import wraps
from fastapi import Request, HTTPException, status, Depends
from app.core.security import verify_token
import uuid


class Permissions:
    """Permission constants for the hospital management system"""
    
    # User management
    USERS_CREATE = "users:create"
    USERS_READ = "users:read"
    USERS_READ_OWN = "users:read:own"
    USERS_UPDATE = "users:update"
    USERS_DELETE = "users:delete"
    
    # Patient management
    PATIENTS_CREATE = "patients:create"
    PATIENTS_READ = "patients:read"
    PATIENTS_READ_OWN = "patients:read:own"
    PATIENTS_READ_DEPARTMENT = "patients:read:department"
    PATIENTS_UPDATE = "patients:update"
    PATIENTS_DELETE = "patients:delete"
    
    # Appointments
    APPOINTMENTS_CREATE = "appointments:create"
    APPOINTMENTS_READ = "appointments:read"
    APPOINTMENTS_READ_OWN = "appointments:read:own"
    APPOINTMENTS_UPDATE = "appointments:update"
    APPOINTMENTS_DELETE = "appointments:delete"
    
    # EMR (Electronic Medical Records)
    EMR_CREATE = "emr:create"
    EMR_READ = "emr:read"
    EMR_UPDATE = "emr:update"
    EMR_SIGN = "emr:sign"
    EMR_UPDATE_VITALS = "emr:update_vitals"
    
    # Diagnoses
    DIAGNOSES_CREATE = "diagnoses:create"
    DIAGNOSES_READ = "diagnoses:read"
    DIAGNOSES_UPDATE = "diagnoses:update"
    DIAGNOSES_DELETE = "diagnoses:delete"
    
    # Procedures
    PROCEDURES_CREATE = "procedures:create"
    PROCEDURES_READ = "procedures:read"
    PROCEDURES_UPDATE = "procedures:update"
    
    # Clinical Notes
    CLINICAL_NOTES_CREATE = "clinical_notes:create"
    CLINICAL_NOTES_READ = "clinical_notes:read"
    CLINICAL_NOTES_UPDATE = "clinical_notes:update"
    CLINICAL_NOTES_SIGN = "clinical_notes:sign"
    
    # Prescriptions
    PRESCRIPTIONS_CREATE = "prescriptions:create"
    PRESCRIPTIONS_READ = "prescriptions:read"
    PRESCRIPTIONS_UPDATE = "prescriptions:update"
    PRESCRIPTIONS_VERIFY = "prescriptions:verify"
    
    # Queue Management
    QUEUE_MANAGE = "queue:manage"
    QUEUE_READ = "queue:read"
    
    # Schedules
    SCHEDULES_CREATE = "schedules:create"
    SCHEDULES_READ = "schedules:read"
    SCHEDULES_UPDATE = "schedules:update"
    SCHEDULES_DELETE = "schedules:delete"
    
    # Leaves
    LEAVES_CREATE = "leaves:create"
    LEAVES_READ = "leaves:read"
    LEAVES_APPROVE = "leaves:approve"
    LEAVES_CANCEL = "leaves:cancel"
    
    # System
    AUDIT_READ = "audit:read"
    SYSTEM_ADMIN = "system:admin"


def get_current_user(request: Request) -> Dict[str, Any]:
    """Extract and validate user from request"""
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    token = auth_header.split(" ")[1]
    payload = verify_token(token, "access")
    
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    return payload


def has_permission(required_permissions: List[str]):
    """Decorator to check if user has required permissions"""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Find the request argument
            request = None
            for arg in args:
                if isinstance(arg, Request):
                    request = arg
                    break
            
            if not request:
                # Try to get request from kwargs
                request = kwargs.get('request')
            
            if not request:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Request object not found"
                )
            
            # Get user from request state or validate token
            if hasattr(request.state, 'user'):
                user_payload = request.state.user
            else:
                user_payload = get_current_user(request)
                request.state.user = user_payload
            
            user_permissions = user_payload.get("permissions", [])
            
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
            
            return await func(*args, **kwargs)
        return wrapper
    return decorator


def require_permissions(required_permissions: List[str]):
    """Dependency function to check permissions"""
    def permission_checker(request: Request) -> Dict[str, Any]:
        user_payload = get_current_user(request)
        request.state.user = user_payload
        
        user_permissions = user_payload.get("permissions", [])
        
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
        
        return user_payload
    
    return permission_checker


def check_resource_access(
    user_permissions: List[str],
    user_id: str,
    user_department: Optional[str],
    resource_owner_id: Optional[str],
    resource_department: Optional[str],
    required_permissions: List[str]
) -> bool:
    """
    Check if user has access to a specific resource based on RBAC and ABAC rules
    """
    # Check basic permission
    has_basic_permission = any(
        perm in user_permissions 
        for perm in required_permissions
    )
    
    if not has_basic_permission:
        return False
    
    # System admin has access to everything
    if Permissions.SYSTEM_ADMIN in user_permissions:
        return True
    
    # Check ownership permissions
    for permission in required_permissions:
        if permission.endswith(":own"):
            if resource_owner_id and user_id == resource_owner_id:
                return True
        
        elif permission.endswith(":department"):
            if resource_department and user_department == resource_department:
                return True
    
    return False


class PermissionChecker:
    """Helper class for checking complex permission scenarios"""
    
    @staticmethod
    def can_access_patient(
        user_permissions: List[str],
        user_id: str,
        user_department: Optional[str],
        patient_owner_id: Optional[str],
        patient_department: Optional[str]
    ) -> bool:
        """Check if user can access a specific patient"""
        required_permissions = [
            Permissions.PATIENTS_READ,
            Permissions.PATIENTS_READ_OWN,
            Permissions.PATIENTS_READ_DEPARTMENT
        ]
        
        return check_resource_access(
            user_permissions=user_permissions,
            user_id=user_id,
            user_department=user_department,
            resource_owner_id=patient_owner_id,
            resource_department=patient_department,
            required_permissions=required_permissions
        )
    
    @staticmethod
    def can_modify_patient(
        user_permissions: List[str],
        user_id: str,
        user_department: Optional[str],
        patient_owner_id: Optional[str],
        patient_department: Optional[str]
    ) -> bool:
        """Check if user can modify a specific patient"""
        required_permissions = [
            Permissions.PATIENTS_UPDATE,
            Permissions.PATIENTS_DELETE
        ]
        
        return check_resource_access(
            user_permissions=user_permissions,
            user_id=user_id,
            user_department=user_department,
            resource_owner_id=patient_owner_id,
            resource_department=patient_department,
            required_permissions=required_permissions
        )
