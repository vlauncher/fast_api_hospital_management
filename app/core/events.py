from typing import Optional, Dict, Any, List
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import Request, Response, HTTPException, status
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse
import json
import uuid
import time
from datetime import datetime
import logging

from app.domain.audit.models import (
    AuditLog, 
    AuditAction, 
    AuditResource, 
    AuditSeverity,
    SystemEvent,
    SecurityEvent,
    DataAccessLog
)
from app.infrastructure.database import get_db
from app.core.security import verify_token


logger = logging.getLogger(__name__)


class AuditMiddleware(BaseHTTPMiddleware):
    """Middleware to capture and log all HTTP requests and responses"""
    
    # Routes that don't require audit logging
    EXCLUDED_ROUTES = [
        "/health",
        "/metrics",
        "/docs",
        "/redoc",
        "/openapi.json"
    ]
    
    # Sensitive fields to mask in logs
    SENSITIVE_FIELDS = [
        "password", "token", "secret", "key", "authorization",
        "cookie", "session", "csrf", "ssn", "credit_card"
    ]
    
    async def dispatch(self, request: Request, call_next):
        # Skip audit logging for excluded routes
        if any(request.url.path.startswith(route) for route in self.EXCLUDED_ROUTES):
            return await call_next(request)
        
        # Get request details
        start_time = time.time()
        request_id = str(uuid.uuid4())
        
        # Store request ID for correlation
        request.state.request_id = request_id
        
        # Extract request information
        method = request.method
        path = request.url.path
        query_params = dict(request.query_params)
        client_ip = self._get_client_ip(request)
        user_agent = request.headers.get("user-agent", "")
        
        # Get user information if authenticated
        user_info = await self._get_user_info(request)
        
        # Log request start
        await self._log_request_start(
            request_id=request_id,
            method=method,
            path=path,
            query_params=query_params,
            client_ip=client_ip,
            user_agent=user_agent,
            user_info=user_info
        )
        
        try:
            # Process request
            response = await call_next(request)
            
            # Calculate processing time
            processing_time = time.time() - start_time
            
            # Log successful request
            if response.status_code < 400:
                await self._log_request_success(
                    request_id=request_id,
                    method=method,
                    path=path,
                    status_code=response.status_code,
                    processing_time=processing_time,
                    client_ip=client_ip,
                    user_agent=user_agent,
                    user_info=user_info
                )
            else:
                # Log error response
                await self._log_request_error(
                    request_id=request_id,
                    method=method,
                    path=path,
                    status_code=response.status_code,
                    processing_time=processing_time,
                    client_ip=client_ip,
                    user_agent=user_agent,
                    user_info=user_info,
                    error_message=await self._get_error_message(response)
                )
            
            # Add audit headers to response
            response.headers["X-Request-ID"] = request_id
            response.headers["X-Audit-Logged"] = "true"
            
            return response
            
        except HTTPException as http_exc:
            # Log HTTP exceptions
            await self._log_http_exception(
                request_id=request_id,
                method=method,
                path=path,
                status_code=http_exc.status_code,
                client_ip=client_ip,
                user_agent=user_agent,
                user_info=user_info,
                error_detail=http_exc.detail
            )
            raise
            
        except Exception as exc:
            # Log unexpected exceptions
            await self._log_system_exception(
                request_id=request_id,
                method=method,
                path=path,
                client_ip=client_ip,
                user_agent=user_agent,
                user_info=user_info,
                exception=exc
            )
            raise
    
    def _get_client_ip(self, request: Request) -> str:
        """Get client IP address from request"""
        # Check for forwarded headers first
        forwarded_for = request.headers.get("x-forwarded-for")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()
        
        real_ip = request.headers.get("x-real-ip")
        if real_ip:
            return real_ip
        
        # Fall back to direct connection
        return request.client.host if request.client else "unknown"
    
    async def _get_user_info(self, request: Request) -> Optional[Dict[str, Any]]:
        """Extract user information from request"""
        try:
            auth_header = request.headers.get("Authorization")
            if not auth_header or not auth_header.startswith("Bearer "):
                return None
            
            token = auth_header.split(" ")[1]
            payload = verify_token(token, "access")
            
            if not payload:
                return None
            
            return {
                "user_id": payload.get("sub"),
                "username": payload.get("username"),
                "role": payload.get("role"),
                "permissions": payload.get("permissions", [])
            }
        except Exception:
            return None
    
    def _mask_sensitive_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Mask sensitive data in request/response payloads"""
        if not isinstance(data, dict):
            return data
        
        masked_data = {}
        for key, value in data.items():
            key_lower = key.lower()
            if any(sensitive in key_lower for sensitive in self.SENSITIVE_FIELDS):
                masked_data[key] = "***MASKED***"
            elif isinstance(value, dict):
                masked_data[key] = self._mask_sensitive_data(value)
            elif isinstance(value, list):
                masked_data[key] = [
                    self._mask_sensitive_data(item) if isinstance(item, dict) else item
                    for item in value
                ]
            else:
                masked_data[key] = value
        
        return masked_data
    
    async def _log_request_start(
        self,
        request_id: str,
        method: str,
        path: str,
        query_params: Dict[str, Any],
        client_ip: str,
        user_agent: str,
        user_info: Optional[Dict[str, Any]]
    ):
        """Log the start of a request"""
        try:
            # Determine resource type from path
            resource_type = self._get_resource_type_from_path(path)
            
            # Create audit log entry
            audit_data = {
                "action": AuditAction.READ if method == "GET" else AuditAction.UPDATE,
                "resource_type": resource_type,
                "endpoint": path,
                "method": method,
                "ip_address": client_ip,
                "user_agent": user_agent,
                "success": "IN_PROGRESS",
                "severity": AuditSeverity.LOW
            }
            
            if user_info:
                audit_data.update({
                    "user_id": uuid.UUID(user_info["user_id"]) if user_info["user_id"] else None,
                    "username": user_info["username"]
                })
            
            # Log asynchronously (in production, this would be a background task)
            logger.info(f"Request started: {request_id} {method} {path}")
            
        except Exception as e:
            logger.error(f"Failed to log request start: {e}")
    
    async def _log_request_success(
        self,
        request_id: str,
        method: str,
        path: str,
        status_code: int,
        processing_time: float,
        client_ip: str,
        user_agent: str,
        user_info: Optional[Dict[str, Any]]
    ):
        """Log successful request completion"""
        try:
            resource_type = self._get_resource_type_from_path(path)
            action = self._get_action_from_method(method)
            
            audit_data = {
                "action": action,
                "resource_type": resource_type,
                "endpoint": path,
                "method": method,
                "ip_address": client_ip,
                "user_agent": user_agent,
                "status_code": str(status_code),
                "success": "SUCCESS",
                "severity": self._get_severity_from_status(status_code)
            }
            
            if user_info:
                audit_data.update({
                    "user_id": uuid.UUID(user_info["user_id"]) if user_info["user_id"] else None,
                    "username": user_info["username"]
                })
            
            logger.info(
                f"Request completed: {request_id} {method} {path} "
                f"- {status_code} in {processing_time:.3f}s"
            )
            
        except Exception as e:
            logger.error(f"Failed to log request success: {e}")
    
    async def _log_request_error(
        self,
        request_id: str,
        method: str,
        path: str,
        status_code: int,
        processing_time: float,
        client_ip: str,
        user_agent: str,
        user_info: Optional[Dict[str, Any]],
        error_message: Optional[str]
    ):
        """Log request with error response"""
        try:
            resource_type = self._get_resource_type_from_path(path)
            action = self._get_action_from_method(method)
            
            audit_data = {
                "action": action,
                "resource_type": resource_type,
                "endpoint": path,
                "method": method,
                "ip_address": client_ip,
                "user_agent": user_agent,
                "status_code": str(status_code),
                "success": "FAILURE",
                "error_message": error_message,
                "severity": self._get_severity_from_status(status_code)
            }
            
            if user_info:
                audit_data.update({
                    "user_id": uuid.UUID(user_info["user_id"]) if user_info["user_id"] else None,
                    "username": user_info["username"]
                })
            
            logger.warning(
                f"Request failed: {request_id} {method} {path} "
                f"- {status_code} in {processing_time:.3f}s"
            )
            
        except Exception as e:
            logger.error(f"Failed to log request error: {e}")
    
    async def _log_http_exception(
        self,
        request_id: str,
        method: str,
        path: str,
        status_code: int,
        client_ip: str,
        user_agent: str,
        user_info: Optional[Dict[str, Any]],
        error_detail: str
    ):
        """Log HTTP exception"""
        try:
            resource_type = self._get_resource_type_from_path(path)
            action = self._get_action_from_method(method)
            
            # Log as audit event
            audit_data = {
                "action": action,
                "resource_type": resource_type,
                "endpoint": path,
                "method": method,
                "ip_address": client_ip,
                "user_agent": user_agent,
                "status_code": str(status_code),
                "success": "FAILURE",
                "error_message": error_detail,
                "severity": self._get_severity_from_status(status_code)
            }
            
            if user_info:
                audit_data.update({
                    "user_id": uuid.UUID(user_info["user_id"]) if user_info["user_id"] else None,
                    "username": user_info["username"]
                })
            
            # Log security events for authentication failures
            if status_code == 401 or status_code == 403:
                await self._log_security_event(
                    event_type="AUTHENTICATION_FAILURE" if status_code == 401 else "AUTHORIZATION_FAILURE",
                    source_ip=client_ip,
                    target_user_id=user_info["user_id"] if user_info else None,
                    endpoint=path,
                    details={"error_detail": error_detail}
                )
            
            logger.warning(
                f"HTTP exception: {request_id} {method} {path} "
                f"- {status_code} - {error_detail}"
            )
            
        except Exception as e:
            logger.error(f"Failed to log HTTP exception: {e}")
    
    async def _log_system_exception(
        self,
        request_id: str,
        method: str,
        path: str,
        client_ip: str,
        user_agent: str,
        user_info: Optional[Dict[str, Any]],
        exception: Exception
    ):
        """Log system exception"""
        try:
            logger.error(
                f"System exception: {request_id} {method} {path} "
                f"- {type(exception).__name__}: {str(exception)}"
            )
            
            # Create system event
            await self._log_system_event(
                event_type="SYSTEM_EXCEPTION",
                event_category="ERROR",
                severity=AuditSeverity.HIGH,
                title=f"System Exception in {method} {path}",
                description=str(exception),
                source_service="api",
                source_ip=client_ip,
                details={
                    "exception_type": type(exception).__name__,
                    "exception_message": str(exception),
                    "request_id": request_id,
                    "method": method,
                    "path": path
                }
            )
            
        except Exception as e:
            logger.error(f"Failed to log system exception: {e}")
    
    async def _log_security_event(
        self,
        event_type: str,
        source_ip: str,
        target_user_id: Optional[str],
        endpoint: str,
        details: Dict[str, Any]
    ):
        """Log security event"""
        try:
            # This would create a SecurityEvent record
            # For now, just log it
            logger.warning(
                f"Security event: {event_type} from {source_ip} "
                f"on {endpoint} - {details}"
            )
            
        except Exception as e:
            logger.error(f"Failed to log security event: {e}")
    
    async def _log_system_event(
        self,
        event_type: str,
        event_category: str,
        severity: AuditSeverity,
        title: str,
        description: str,
        source_service: str,
        source_ip: str,
        details: Dict[str, Any]
    ):
        """Log system event"""
        try:
            # This would create a SystemEvent record
            # For now, just log it
            logger.info(
                f"System event: {event_type} - {title} "
                f"from {source_service} at {source_ip}"
            )
            
        except Exception as e:
            logger.error(f"Failed to log system event: {e}")
    
    async def _get_error_message(self, response: Response) -> Optional[str]:
        """Extract error message from response"""
        try:
            if hasattr(response, 'body'):
                body = response.body
                if isinstance(body, bytes):
                    body = body.decode('utf-8')
                
                try:
                    data = json.loads(body)
                    return data.get('detail') or data.get('message')
                except (json.JSONDecodeError, ValueError):
                    return body
            
            return None
        except Exception:
            return None
    
    def _get_resource_type_from_path(self, path: str) -> AuditResource:
        """Determine audit resource type from request path"""
        path_lower = path.lower()
        
        if "/auth/" in path_lower:
            return AuditResource.USER
        elif "/patients/" in path_lower:
            return AuditResource.PATIENT
        elif "/emergency-contacts" in path_lower:
            return AuditResource.EMERGENCY_CONTACT
        elif "/insurance" in path_lower:
            return AuditResource.INSURANCE
        elif "/visits" in path_lower:
            return AuditResource.PATIENT_VISIT
        elif "/departments" in path_lower:
            return AuditResource.DEPARTMENT
        elif "/audit" in path_lower:
            return AuditResource.AUDIT_LOG
        else:
            return AuditResource.SYSTEM
    
    def _get_action_from_method(self, method: str) -> AuditAction:
        """Determine audit action from HTTP method"""
        action_map = {
            "GET": AuditAction.READ,
            "POST": AuditAction.CREATE,
            "PUT": AuditAction.UPDATE,
            "PATCH": AuditAction.UPDATE,
            "DELETE": AuditAction.DELETE
        }
        return action_map.get(method, AuditAction.SYSTEM)
    
    def _get_severity_from_status(self, status_code: int) -> AuditSeverity:
        """Determine audit severity from HTTP status code"""
        if status_code < 300:
            return AuditSeverity.LOW
        elif status_code < 400:
            return AuditSeverity.LOW
        elif status_code < 500:
            return AuditSeverity.MEDIUM
        else:
            return AuditSeverity.HIGH


class AuditLogger:
    """Service for creating audit log entries"""
    
    @staticmethod
    async def log_data_access(
        db: AsyncSession,
        resource_type: AuditResource,
        resource_id: uuid.UUID,
        field_name: str,
        field_value: Any,
        user_id: Optional[uuid.UUID],
        username: Optional[str],
        ip_address: Optional[str],
        user_agent: Optional[str],
        endpoint: Optional[str],
        access_purpose: Optional[str] = None,
        legal_basis: Optional[str] = None
    ):
        """Log data access for sensitive fields"""
        try:
            from app.infrastructure.encryption import generate_data_hash
            
            access_log = DataAccessLog(
                resource_type=resource_type,
                resource_id=resource_id,
                field_name=field_name,
                field_value_hash=generate_data_hash(str(field_value)) if field_value else None,
                user_id=user_id,
                username=username,
                ip_address=ip_address,
                user_agent=user_agent,
                endpoint=endpoint,
                access_purpose=access_purpose,
                legal_basis=legal_basis,
                data_sensitivity="HIGH" if field_name in [
                    "ssn", "national_id", "passport_number", "driver_license"
                ] else "MEDIUM"
            )
            
            db.add(access_log)
            await db.commit()
            
        except Exception as e:
            logger.error(f"Failed to log data access: {e}")
    
    @staticmethod
    async def log_user_action(
        db: AsyncSession,
        action: AuditAction,
        resource_type: AuditResource,
        resource_id: Optional[uuid.UUID],
        user_id: Optional[uuid.UUID],
        username: Optional[str],
        ip_address: Optional[str],
        user_agent: Optional[str],
        endpoint: Optional[str],
        old_values: Optional[Dict[str, Any]] = None,
        new_values: Optional[Dict[str, Any]] = None,
        success: str = "SUCCESS",
        error_message: Optional[str] = None,
        severity: AuditSeverity = AuditSeverity.LOW
    ):
        """Log user action"""
        try:
            audit_log = AuditLog(
                action=action,
                resource_type=resource_type,
                resource_id=resource_id,
                user_id=user_id,
                username=username,
                ip_address=ip_address,
                user_agent=user_agent,
                endpoint=endpoint,
                old_values=old_values,
                new_values=new_values,
                success=success,
                error_message=error_message,
                severity=severity
            )
            
            # Encrypt sensitive data
            audit_log.encrypt_sensitive_data()
            
            db.add(audit_log)
            await db.commit()
            
        except Exception as e:
            logger.error(f"Failed to log user action: {e}")
    
    @staticmethod
    async def log_login_event(
        db: AsyncSession,
        username: str,
        ip_address: Optional[str],
        user_agent: Optional[str],
        success: bool,
        error_message: Optional[str] = None
    ):
        """Log login event"""
        try:
            action = AuditAction.LOGIN if success else AuditAction.ACCESS_DENIED
            success_status = "SUCCESS" if success else "FAILURE"
            severity = AuditSeverity.LOW if success else AuditSeverity.MEDIUM
            
            audit_log = AuditLog(
                action=action,
                resource_type=AuditResource.USER,
                username=username,
                ip_address=ip_address,
                user_agent=user_agent,
                endpoint="/auth/login",
                success=success_status,
                error_message=error_message,
                severity=severity
            )
            
            db.add(audit_log)
            await db.commit()
            
        except Exception as e:
            logger.error(f"Failed to log login event: {e}")
