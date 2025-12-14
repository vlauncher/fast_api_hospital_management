from typing import Dict, Any, Optional
from fastapi import HTTPException, status
from pydantic import BaseModel
import logging

logger = logging.getLogger(__name__)


class BaseCustomException(Exception):
    """Base class for custom exceptions"""
    
    def __init__(
        self,
        message: str,
        status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR,
        details: Optional[Dict[str, Any]] = None,
        error_code: Optional[str] = None
    ):
        self.message = message
        self.status_code = status_code
        self.details = details or {}
        self.error_code = error_code
        super().__init__(self.message)


class ValidationError(BaseCustomException):
    """Exception for validation errors"""
    
    def __init__(
        self,
        message: str = "Validation failed",
        details: Optional[Dict[str, Any]] = None,
        error_code: Optional[str] = None
    ):
        super().__init__(
            message=message,
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            details=details,
            error_code=error_code or "VALIDATION_ERROR"
        )


class AuthenticationError(BaseCustomException):
    """Exception for authentication errors"""
    
    def __init__(
        self,
        message: str = "Authentication failed",
        details: Optional[Dict[str, Any]] = None,
        error_code: Optional[str] = None
    ):
        super().__init__(
            message=message,
            status_code=status.HTTP_401_UNAUTHORIZED,
            details=details,
            error_code=error_code or "AUTHENTICATION_ERROR"
        )


class AuthorizationError(BaseCustomException):
    """Exception for authorization errors"""
    
    def __init__(
        self,
        message: str = "Access denied",
        details: Optional[Dict[str, Any]] = None,
        error_code: Optional[str] = None
    ):
        super().__init__(
            message=message,
            status_code=status.HTTP_403_FORBIDDEN,
            details=details,
            error_code=error_code or "AUTHORIZATION_ERROR"
        )


class NotFoundError(BaseCustomException):
    """Exception for resource not found errors"""
    
    def __init__(
        self,
        message: str = "Resource not found",
        details: Optional[Dict[str, Any]] = None,
        error_code: Optional[str] = None
    ):
        super().__init__(
            message=message,
            status_code=status.HTTP_404_NOT_FOUND,
            details=details,
            error_code=error_code or "NOT_FOUND_ERROR"
        )


class ConflictError(BaseCustomException):
    """Exception for conflict errors"""
    
    def __init__(
        self,
        message: str = "Resource conflict",
        details: Optional[Dict[str, Any]] = None,
        error_code: Optional[str] = None
    ):
        super().__init__(
            message=message,
            status_code=status.HTTP_409_CONFLICT,
            details=details,
            error_code=error_code or "CONFLICT_ERROR"
        )


class RateLimitError(BaseCustomException):
    """Exception for rate limit errors"""
    
    def __init__(
        self,
        message: str = "Rate limit exceeded",
        details: Optional[Dict[str, Any]] = None,
        error_code: Optional[str] = None
    ):
        super().__init__(
            message=message,
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            details=details,
            error_code=error_code or "RATE_LIMIT_ERROR"
        )


class DatabaseError(BaseCustomException):
    """Exception for database errors"""
    
    def __init__(
        self,
        message: str = "Database operation failed",
        details: Optional[Dict[str, Any]] = None,
        error_code: Optional[str] = None
    ):
        super().__init__(
            message=message,
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            details=details,
            error_code=error_code or "DATABASE_ERROR"
        )


class ExternalServiceError(BaseCustomException):
    """Exception for external service errors"""
    
    def __init__(
        self,
        message: str = "External service error",
        details: Optional[Dict[str, Any]] = None,
        error_code: Optional[str] = None
    ):
        super().__init__(
            message=message,
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            details=details,
            error_code=error_code or "EXTERNAL_SERVICE_ERROR"
        )


class EncryptionError(BaseCustomException):
    """Exception for encryption/decryption errors"""
    
    def __init__(
        self,
        message: str = "Encryption operation failed",
        details: Optional[Dict[str, Any]] = None,
        error_code: Optional[str] = None
    ):
        super().__init__(
            message=message,
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            details=details,
            error_code=error_code or "ENCRYPTION_ERROR"
        )


class ConfigurationError(BaseCustomException):
    """Exception for configuration errors"""
    
    def __init__(
        self,
        message: str = "Configuration error",
        details: Optional[Dict[str, Any]] = None,
        error_code: Optional[str] = None
    ):
        super().__init__(
            message=message,
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            details=details,
            error_code=error_code or "CONFIGURATION_ERROR"
        )


class BusinessLogicError(BaseCustomException):
    """Exception for business logic errors"""
    
    def __init__(
        self,
        message: str = "Business logic error",
        details: Optional[Dict[str, Any]] = None,
        error_code: Optional[str] = None
    ):
        super().__init__(
            message=message,
            status_code=status.HTTP_400_BAD_REQUEST,
            details=details,
            error_code=error_code or "BUSINESS_LOGIC_ERROR"
        )


class PatientError(BaseCustomException):
    """Exception for patient-related errors"""
    
    def __init__(
        self,
        message: str = "Patient operation failed",
        details: Optional[Dict[str, Any]] = None,
        error_code: Optional[str] = None
    ):
        super().__init__(
            message=message,
            status_code=status.HTTP_400_BAD_REQUEST,
            details=details,
            error_code=error_code or "PATIENT_ERROR"
        )


class UserError(BaseCustomException):
    """Exception for user-related errors"""
    
    def __init__(
        self,
        message: str = "User operation failed",
        details: Optional[Dict[str, Any]] = None,
        error_code: Optional[str] = None
    ):
        super().__init__(
            message=message,
            status_code=status.HTTP_400_BAD_REQUEST,
            details=details,
            error_code=error_code or "USER_ERROR"
        )


class SessionError(BaseCustomException):
    """Exception for session-related errors"""
    
    def __init__(
        self,
        message: str = "Session error",
        details: Optional[Dict[str, Any]] = None,
        error_code: Optional[str] = None
    ):
        super().__init__(
            message=message,
            status_code=status.HTTP_401_UNAUTHORIZED,
            details=details,
            error_code=error_code or "SESSION_ERROR"
        )


class CacheError(BaseCustomException):
    """Exception for cache-related errors"""
    
    def __init__(
        self,
        message: str = "Cache operation failed",
        details: Optional[Dict[str, Any]] = None,
        error_code: Optional[str] = None
    ):
        super().__init__(
            message=message,
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            details=details,
            error_code=error_code or "CACHE_ERROR"
        )


# Response models for errors
class ErrorResponse(BaseModel):
    """Standard error response model"""
    error: str
    message: str
    error_code: Optional[str] = None
    details: Optional[Dict[str, Any]] = None
    timestamp: Optional[str] = None
    request_id: Optional[str] = None


class ValidationErrorResponse(BaseModel):
    """Validation error response model"""
    error: str = "Validation Error"
    message: str
    error_code: Optional[str] = None
    validation_errors: Optional[Dict[str, list]] = None
    timestamp: Optional[str] = None
    request_id: Optional[str] = None


class AuthenticationErrorResponse(BaseModel):
    """Authentication error response model"""
    error: str = "Authentication Error"
    message: str
    error_code: Optional[str] = None
    requires_login: bool = True
    timestamp: Optional[str] = None
    request_id: Optional[str] = None


class AuthorizationErrorResponse(BaseModel):
    """Authorization error response model"""
    error: str = "Authorization Error"
    message: str
    error_code: Optional[str] = None
    required_permissions: Optional[list] = None
    timestamp: Optional[str] = None
    request_id: Optional[str] = None


class RateLimitErrorResponse(BaseModel):
    """Rate limit error response model"""
    error: str = "Rate Limit Exceeded"
    message: str
    error_code: Optional[str] = None
    retry_after: Optional[int] = None
    limit: Optional[int] = None
    remaining: Optional[int] = None
    reset_time: Optional[int] = None
    timestamp: Optional[str] = None
    request_id: Optional[str] = None


class DatabaseErrorResponse(BaseModel):
    """Database error response model"""
    error: str = "Database Error"
    message: str
    error_code: Optional[str] = None
    operation: Optional[str] = None
    timestamp: Optional[str] = None
    request_id: Optional[str] = None


class ExternalServiceErrorResponse(BaseModel):
    """External service error response model"""
    error: str = "External Service Error"
    message: str
    error_code: Optional[str] = None
    service_name: Optional[str] = None
    service_status: Optional[str] = None
    timestamp: Optional[str] = None
    request_id: Optional[str] = None


# Exception handler functions
def create_error_response(
    exception: BaseCustomException,
    request_id: Optional[str] = None
) -> Dict[str, Any]:
    """Create standardized error response"""
    from datetime import datetime
    
    response = {
        "error": exception.__class__.__name__.replace("Error", " Error"),
        "message": exception.message,
        "error_code": exception.error_code,
        "timestamp": datetime.utcnow().isoformat(),
        "request_id": request_id
    }
    
    if exception.details:
        response["details"] = exception.details
    
    return response


def create_validation_error_response(
    exception: ValidationError,
    validation_errors: Optional[Dict[str, list]] = None,
    request_id: Optional[str] = None
) -> Dict[str, Any]:
    """Create validation error response"""
    from datetime import datetime
    
    response = {
        "error": "Validation Error",
        "message": exception.message,
        "error_code": exception.error_code,
        "timestamp": datetime.utcnow().isoformat(),
        "request_id": request_id
    }
    
    if validation_errors:
        response["validation_errors"] = validation_errors
    
    if exception.details:
        response["details"] = exception.details
    
    return response


def create_authentication_error_response(
    exception: AuthenticationError,
    request_id: Optional[str] = None
) -> Dict[str, Any]:
    """Create authentication error response"""
    from datetime import datetime
    
    response = {
        "error": "Authentication Error",
        "message": exception.message,
        "error_code": exception.error_code,
        "requires_login": True,
        "timestamp": datetime.utcnow().isoformat(),
        "request_id": request_id
    }
    
    if exception.details:
        response["details"] = exception.details
    
    return response


def create_authorization_error_response(
    exception: AuthorizationError,
    required_permissions: Optional[list] = None,
    request_id: Optional[str] = None
) -> Dict[str, Any]:
    """Create authorization error response"""
    from datetime import datetime
    
    response = {
        "error": "Authorization Error",
        "message": exception.message,
        "error_code": exception.error_code,
        "timestamp": datetime.utcnow().isoformat(),
        "request_id": request_id
    }
    
    if required_permissions:
        response["required_permissions"] = required_permissions
    
    if exception.details:
        response["details"] = exception.details
    
    return response


def create_rate_limit_error_response(
    exception: RateLimitError,
    rate_limit_info: Optional[Dict[str, Any]] = None,
    request_id: Optional[str] = None
) -> Dict[str, Any]:
    """Create rate limit error response"""
    from datetime import datetime
    
    response = {
        "error": "Rate Limit Exceeded",
        "message": exception.message,
        "error_code": exception.error_code,
        "timestamp": datetime.utcnow().isoformat(),
        "request_id": request_id
    }
    
    if rate_limit_info:
        response.update(rate_limit_info)
    
    if exception.details:
        response["details"] = exception.details
    
    return response


# Utility functions for common error scenarios
def handle_database_error(error: Exception, operation: str = "database operation") -> DatabaseError:
    """Handle database errors and convert to DatabaseError"""
    logger.error(f"Database error during {operation}: {error}")
    
    error_message = "Database operation failed"
    if "connection" in str(error).lower():
        error_message = "Database connection failed"
    elif "timeout" in str(error).lower():
        error_message = "Database operation timed out"
    elif "constraint" in str(error).lower():
        error_message = "Database constraint violation"
    
    return DatabaseError(
        message=error_message,
        details={"operation": operation, "original_error": str(error)},
        error_code="DATABASE_OPERATION_ERROR"
    )


def handle_external_service_error(
    error: Exception,
    service_name: str,
    operation: str = "request"
) -> ExternalServiceError:
    """Handle external service errors"""
    logger.error(f"External service error for {service_name}: {error}")
    
    return ExternalServiceError(
        message=f"External service {service_name} unavailable",
        details={
            "service_name": service_name,
            "operation": operation,
            "original_error": str(error)
        },
        error_code="EXTERNAL_SERVICE_ERROR"
    )


def handle_encryption_error(error: Exception, operation: str = "encryption operation") -> EncryptionError:
    """Handle encryption errors"""
    logger.error(f"Encryption error during {operation}: {error}")
    
    return EncryptionError(
        message="Encryption operation failed",
        details={
            "operation": operation,
            "original_error": str(error)
        },
        error_code="ENCRYPTION_ERROR"
    )


def handle_validation_error(
    error: Exception,
    field: Optional[str] = None,
    value: Optional[Any] = None
) -> ValidationError:
    """Handle validation errors"""
    logger.error(f"Validation error: {error}")
    
    details = {"original_error": str(error)}
    if field:
        details["field"] = field
    if value is not None:
        details["value"] = str(value)
    
    return ValidationError(
        message="Validation failed",
        details=details,
        error_code="VALIDATION_ERROR"
    )


# Exception mapping for common scenarios
EXCEPTION_MAPPING = {
    "ValueError": ValidationError,
    "TypeError": ValidationError,
    "KeyError": ValidationError,
    "AttributeError": ValidationError,
    "PermissionError": AuthorizationError,
    "ConnectionError": ExternalServiceError,
    "TimeoutError": ExternalServiceError,
}


def map_exception_to_custom(error: Exception) -> BaseCustomException:
    """Map standard exceptions to custom exceptions"""
    error_type = type(error).__name__
    
    if error_type in EXCEPTION_MAPPING:
        custom_exception_class = EXCEPTION_MAPPING[error_type]
        return custom_exception_class(
            message=str(error),
            details={"original_error": str(error)},
            error_code=f"{error_type.upper()}_ERROR"
        )
    
    # Default to generic BaseCustomException
    return BaseCustomException(
        message="An unexpected error occurred",
        details={"original_error": str(error)},
        error_code="UNEXPECTED_ERROR"
    )


# Context manager for error handling
class ErrorHandler:
    """Context manager for consistent error handling"""
    
    def __init__(
        self,
        operation: str,
        default_exception_class: type = BaseCustomException,
        log_errors: bool = True
    ):
        self.operation = operation
        self.default_exception_class = default_exception_class
        self.log_errors = log_errors
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is not None:
            if self.log_errors:
                logger.error(f"Error in {self.operation}: {exc_val}")
            
            # Convert to custom exception if needed
            if not issubclass(exc_type, BaseCustomException):
                custom_exception = map_exception_to_custom(exc_val)
                custom_exception.operation = self.operation
                raise custom_exception from exc_val
        
        return False  # Don't suppress exceptions


# Decorator for error handling
def handle_errors(
    default_exception_class: type = BaseCustomException,
    log_errors: bool = True,
    return_error_response: bool = False
):
    """Decorator for handling errors in functions"""
    def decorator(func):
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except BaseCustomException:
                raise  # Re-raise custom exceptions
            except Exception as e:
                if log_errors:
                    logger.error(f"Error in {func.__name__}: {e}")
                
                custom_exception = map_exception_to_custom(e)
                
                if return_error_response:
                    return create_error_response(custom_exception)
                else:
                    raise custom_exception from e
        
        return wrapper
    return decorator
