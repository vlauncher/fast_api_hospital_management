from fastapi import FastAPI, Request, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
import logging
import time
from typing import Dict, Any

from app.core.config import settings
from app.core.events import AuditMiddleware
from app.infrastructure.database import init_db, close_db
from app.infrastructure.redis import init_redis_services, close_redis_services
from app.api.v1.auth.routes import router as auth_router
from app.api.v1.patients.routes import router as patients_router
from app.api.v1.appointments.routes import router as appointments_router
from app.api.v1.emr.routes import router as emr_router
from app.workers.celery_app import celery_app

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    # Startup
    logger.info("Starting Hospital Management System...")
    
    try:
        # Initialize database
        await init_db()
        logger.info("Database initialized")
        
        # Initialize Redis services
        await init_redis_services(settings.REDIS_URL)
        logger.info("Redis services initialized")
        
        # Start Celery worker (in production, this would be a separate process)
        if settings.APP_ENV == "development":
            logger.info("Celery app configured (workers should be started separately)")
        
        logger.info("Hospital Management System started successfully")
        
    except Exception as e:
        logger.error(f"Failed to start application: {e}")
        raise
    
    yield
    
    # Shutdown
    logger.info("Shutting down Hospital Management System...")
    
    try:
        # Close Redis services
        await close_redis_services()
        logger.info("Redis services closed")
        
        # Close database connections
        await close_db()
        logger.info("Database connections closed")
        
        logger.info("Hospital Management System shut down successfully")
        
    except Exception as e:
        logger.error(f"Error during shutdown: {e}")


# Create FastAPI application
app = FastAPI(
    title="Hospital Management System API",
    description="A comprehensive hospital management system with authentication, patient management, and audit logging",
    version="1.0.0",
    docs_url="/docs" if settings.APP_ENV != "production" else None,
    redoc_url="/redoc" if settings.APP_ENV != "production" else None,
    openapi_url="/openapi.json" if settings.APP_ENV != "production" else None,
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"],
    allow_headers=["*"],
)

# Add trusted host middleware for production
if settings.APP_ENV == "production":
    app.add_middleware(
        TrustedHostMiddleware,
        allowed_hosts=["localhost", "127.0.0.1"]
    )

# Add audit logging middleware
app.add_middleware(AuditMiddleware)


# Include API routers
app.include_router(
    auth_router,
    prefix="/api/v1/auth",
    tags=["Authentication"]
)

app.include_router(
    patients_router,
    prefix="/api/v1",
    tags=["Patients"]
)

app.include_router(
    appointments_router,
    prefix="/api/v1/appointments",
    tags=["Appointments"]
)

app.include_router(
    emr_router,
    prefix="/api/v1/emr",
    tags=["EMR"]
)


@app.get("/health", tags=["Health"])
async def health_check() -> Dict[str, Any]:
    """Basic health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": time.time(),
        "version": "1.0.0"
    }


@app.get("/health/detailed", tags=["Health"])
async def health_check_detailed() -> Dict[str, Any]:
    """Detailed health check with system status"""
    health_status = {
        "status": "healthy",
        "timestamp": time.time(),
        "version": "1.0.0",
        "environment": settings.ENVIRONMENT,
        "services": {}
    }
    
    # Check database
    try:
        from app.infrastructure.database import engine
        async with engine.begin() as conn:
            await conn.execute("SELECT 1")
        health_status["services"]["database"] = {"status": "healthy"}
    except Exception as e:
        health_status["services"]["database"] = {"status": "unhealthy", "error": str(e)}
        health_status["status"] = "degraded"
    
    # Check Redis
    try:
        from app.infrastructure.redis import cache_service
        if cache_service:
            await cache_service.get("health_check")
            health_status["services"]["redis"] = {"status": "healthy"}
        else:
            health_status["services"]["redis"] = {"status": "unavailable"}
    except Exception as e:
        health_status["services"]["redis"] = {"status": "unhealthy", "error": str(e)}
        health_status["status"] = "degraded"
    
    return health_status


@app.get("/metrics", tags=["Monitoring"])
async def get_metrics() -> Dict[str, Any]:
    """Get system metrics"""
    try:
        from app.infrastructure.redis import cache_service
        
        if cache_service:
            metrics = await cache_service.get("system_health")
            if metrics:
                return metrics
        
        return {
            "timestamp": time.time(),
            "message": "Metrics not available"
        }
    except Exception as e:
        return {
            "timestamp": time.time(),
            "error": str(e)
        }


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "Hospital Management System API",
        "version": "1.0.0",
        "docs": "/docs",
        "health": "/health"
    }


# Global exception handlers
@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """Handle HTTP exceptions"""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": "HTTP Exception",
            "message": exc.detail,
            "status_code": exc.status_code
        }
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Handle general exceptions"""
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": "Internal Server Error",
            "message": "An unexpected error occurred",
            "status_code": 500
        }
    )


# Startup and shutdown events (legacy, kept for compatibility)
@app.on_event("startup")
async def startup_event():
    """Legacy startup event"""
    logger.info("Application startup event triggered")


@app.on_event("shutdown")
async def shutdown_event():
    """Legacy shutdown event"""
    logger.info("Application shutdown event triggered")


# Middleware for request timing
@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    """Add processing time header to responses"""
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    response.headers["X-Process-Time"] = str(process_time)
    return response


# Middleware for request ID
@app.middleware("http")
async def add_request_id(request: Request, call_next):
    """Add unique request ID to requests"""
    import uuid
    request_id = str(uuid.uuid4())
    request.state.request_id = request_id
    response = await call_next(request)
    response.headers["X-Request-ID"] = request_id
    return response


# Rate limiting middleware (simplified)
@app.middleware("http")
async def rate_limit_middleware(request: Request, call_next):
    """Basic rate limiting middleware"""
    # This is a simplified version - in production, use proper rate limiting
    client_ip = request.client.host if request.client else "unknown"
    
    # Log request for rate limiting
    logger.debug(f"Request from {client_ip}: {request.method} {request.url.path}")
    
    response = await call_next(request)
    
    # Add rate limit headers
    response.headers["X-RateLimit-Limit"] = "1000"
    response.headers["X-RateLimit-Remaining"] = "999"
    response.headers["X-RateLimit-Reset"] = str(int(time.time()) + 3600)
    
    return response


# Security headers middleware
@app.middleware("http")
async def security_headers_middleware(request: Request, call_next):
    """Add security headers to responses"""
    response = await call_next(request)
    
    # Add security headers
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    
    # Add security headers (relaxed for development/docs)
    if settings.APP_ENV == "development":
        # Allow external CDN resources for Swagger UI in development
        response.headers["Content-Security-Policy"] = "default-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net"
    else:
        # More restrictive CSP for production
        response.headers["Content-Security-Policy"] = "default-src 'self'"
    
    return response


# Celery task endpoint for monitoring
@app.get("/celery/status", tags=["Monitoring"])
async def celery_status():
    """Get Celery worker status"""
    try:
        inspect = celery_app.control.inspect()
        stats = inspect.stats()
        active = inspect.active()
        
        return {
            "status": "healthy" if stats else "unhealthy",
            "workers": stats,
            "active_tasks": active,
            "timestamp": time.time()
        }
    except Exception as e:
        logger.error(f"Failed to get Celery status: {e}")
        return {
            "status": "unhealthy",
            "error": str(e),
            "timestamp": time.time()
        }


# Configuration endpoint (development only)
if settings.APP_ENV == "development":
    @app.get("/config", tags=["Development"])
    async def get_config():
        """Get current configuration (development only)"""
        return {
            "environment": settings.APP_ENV,
            "database_url": settings.DATABASE_URL,
            "redis_url": settings.REDIS_URL,
            "log_level": settings.LOG_LEVEL,
            "allowed_origins": settings.CORS_ORIGINS,
            "allowed_hosts": ["localhost", "127.0.0.1"]
        }


# Test endpoint for development
if settings.APP_ENV == "development":
    @app.post("/test/audit", tags=["Development"])
    async def test_audit_logging(request: Request):
        """Test audit logging functionality"""
        from app.core.events import AuditLogger
        from app.domain.audit.models import AuditAction, AuditResource, AuditSeverity
        from app.infrastructure.database import get_async_session
        
        async for session in get_async_session():
            await AuditLogger.log_user_action(
                db=session,
                action=AuditAction.CREATE,
                resource_type=AuditResource.USER,
                resource_id=None,
                user_id=None,
                username="test_user",
                ip_address=request.client.host if request.client else "unknown",
                user_agent=request.headers.get("user-agent", ""),
                endpoint="/test/audit",
                new_values={"test": "data"},
                severity=AuditSeverity.LOW
            )
            break
        
        return {"message": "Audit log test completed"}


# Background task test endpoint
if settings.APP_ENV == "development":
    @app.post("/test/task", tags=["Development"])
    async def test_background_task():
        """Test background task functionality"""
        from app.workers.tasks import send_welcome_email
        
        task = send_welcome_email.delay(
            "test-user-id",
            "test@example.com",
            "Test User"
        )
        
        return {
            "message": "Background task queued",
            "task_id": task.id,
            "status": task.status
        }


# Redis test endpoint
if settings.APP_ENV == "development":
    @app.post("/test/redis", tags=["Development"])
    async def test_redis():
        """Test Redis functionality"""
        from app.infrastructure.redis import cache_service
        
        if not cache_service:
            return {"error": "Redis service not available"}
        
        # Test set/get
        await cache_service.set("test_key", "test_value", ttl=60)
        value = await cache_service.get("test_key")
        
        # Clean up
        await cache_service.delete("test_key")
        
        return {
            "message": "Redis test completed",
            "test_value": value,
            "success": value == "test_value"
        }


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.ENVIRONMENT == "development",
        log_level=settings.LOG_LEVEL.lower()
    )
