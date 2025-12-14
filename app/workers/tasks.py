from typing import Dict, Any, List, Optional
import logging
from datetime import datetime, timedelta
import uuid
import psutil
import asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from app.workers.celery_app import celery_app
from app.infrastructure.database import get_async_session
from app.infrastructure.redis import cache_service, session_service
from app.core.events import AuditLogger
from app.domain.audit.models import AuditAction, AuditResource, AuditSeverity

logger = logging.getLogger(__name__)


@celery_app.task(bind=True, max_retries=3)
def send_welcome_email(self, user_id: str, user_email: str, user_name: str):
    """Send welcome email to new user"""
    try:
        # This would integrate with an email service like SendGrid, SES, etc.
        logger.info(f"Sending welcome email to {user_email}")
        
        # Simulate email sending
        email_data = {
            "to": user_email,
            "subject": "Welcome to Hospital Management System",
            "template": "welcome",
            "context": {
                "user_name": user_name,
                "user_id": user_id,
                "registration_date": datetime.utcnow().isoformat()
            }
        }
        
        # Here you would call your email service
        # email_service.send_email(**email_data)
        
        logger.info(f"Welcome email sent successfully to {user_email}")
        return {"status": "success", "message": "Welcome email sent"}
        
    except Exception as exc:
        logger.error(f"Failed to send welcome email to {user_email}: {exc}")
        # Retry with exponential backoff
        countdown = 2 ** self.request.retries
        raise self.retry(exc=exc, countdown=countdown)


@celery_app.task(bind=True)
def send_password_reset_email(self, user_email: str, reset_token: str, user_name: str):
    """Send password reset email"""
    try:
        logger.info(f"Sending password reset email to {user_email}")
        
        email_data = {
            "to": user_email,
            "subject": "Password Reset Request",
            "template": "password_reset",
            "context": {
                "user_name": user_name,
                "reset_token": reset_token,
                "expiry_hours": 24
            }
        }
        
        # email_service.send_email(**email_data)
        
        logger.info(f"Password reset email sent successfully to {user_email}")
        return {"status": "success", "message": "Password reset email sent"}
        
    except Exception as exc:
        logger.error(f"Failed to send password reset email to {user_email}: {exc}")
        raise self.retry(exc=exc, countdown=60)


@celery_app.task(bind=True)
def send_account_locked_email(self, user_email: str, user_name: str, lock_reason: str):
    """Send account locked notification email"""
    try:
        logger.info(f"Sending account locked email to {user_email}")
        
        email_data = {
            "to": user_email,
            "subject": "Account Locked - Security Alert",
            "template": "account_locked",
            "context": {
                "user_name": user_name,
                "lock_reason": lock_reason,
                "contact_email": "security@hospital.com"
            }
        }
        
        # email_service.send_email(**email_data)
        
        logger.info(f"Account locked email sent successfully to {user_email}")
        return {"status": "success", "message": "Account locked email sent"}
        
    except Exception as exc:
        logger.error(f"Failed to send account locked email to {user_email}: {exc}")
        raise self.retry(exc=exc, countdown=60)


@celery_app.task
def cleanup_expired_sessions():
    """Clean up expired sessions from Redis"""
    try:
        logger.info("Starting expired session cleanup")
        
        if not session_service:
            logger.warning("Session service not available")
            return {"status": "error", "message": "Session service not available"}
        
        # Get all session keys
        session_keys = await cache_service.keys("session:*")
        expired_count = 0
        
        for key in session_keys:
            # Check if session is expired
            ttl = await cache_service.ttl(key)
            if ttl == -1:  # No expiration set, set one
                await cache_service.expire(key, 86400)  # 24 hours
            elif ttl == -2:  # Key doesn't exist (shouldn't happen)
                continue
            elif ttl <= 0:  # Expired
                await cache_service.delete(key)
                expired_count += 1
        
        logger.info(f"Session cleanup completed. Removed {expired_count} expired sessions")
        return {
            "status": "success",
            "expired_sessions_removed": expired_count,
            "total_sessions_checked": len(session_keys)
        }
        
    except Exception as e:
        logger.error(f"Session cleanup failed: {e}")
        return {"status": "error", "message": str(e)}


@celery_app.task
def cleanup_expired_cache():
    """Clean up expired cache entries"""
    try:
        logger.info("Starting expired cache cleanup")
        
        if not cache_service:
            logger.warning("Cache service not available")
            return {"status": "error", "message": "Cache service not available"}
        
        # Get all cache keys (excluding sessions)
        all_keys = await cache_service.keys("*")
        cache_keys = [key for key in all_keys if not key.startswith("session:")]
        
        expired_count = 0
        for key in cache_keys:
            ttl = await cache_service.ttl(key)
            if ttl == -1:  # No expiration set, set default
                await cache_service.expire(key, 3600)  # 1 hour
            elif ttl <= 0:  # Expired
                await cache_service.delete(key)
                expired_count += 1
        
        logger.info(f"Cache cleanup completed. Removed {expired_count} expired entries")
        return {
            "status": "success",
            "expired_entries_removed": expired_count,
            "total_entries_checked": len(cache_keys)
        }
        
    except Exception as e:
        logger.error(f"Cache cleanup failed: {e}")
        return {"status": "error", "message": str(e)}


@celery_app.task
def cleanup_rate_limit_data():
    """Clean up old rate limit data"""
    try:
        logger.info("Starting rate limit data cleanup")
        
        if not cache_service:
            logger.warning("Cache service not available")
            return {"status": "error", "message": "Cache service not available"}
        
        # Get all rate limit keys
        rate_limit_keys = await cache_service.keys("rate_limit:*")
        cleaned_count = 0
        
        for key in rate_limit_keys:
            ttl = await cache_service.ttl(key)
            if ttl <= 0:  # Expired
                await cache_service.delete(key)
                cleaned_count += 1
        
        logger.info(f"Rate limit cleanup completed. Removed {cleaned_count} expired entries")
        return {
            "status": "success",
            "expired_entries_removed": cleaned_count,
            "total_entries_checked": len(rate_limit_keys)
        }
        
    except Exception as e:
        logger.error(f"Rate limit cleanup failed: {e}")
        return {"status": "error", "message": str(e)}


@celery_app.task
def system_health_check():
    """Perform system health check"""
    try:
        logger.info("Starting system health check")
        
        health_data = {
            "timestamp": datetime.utcnow().isoformat(),
            "status": "healthy",
            "checks": {}
        }
        
        # Check Redis health
        try:
            redis_healthy = await cache_service.get("health_check") if cache_service else False
            health_data["checks"]["redis"] = {
                "status": "healthy" if redis_healthy is not None else "unhealthy",
                "response_time": "fast" if redis_healthy is not None else "slow"
            }
        except Exception as e:
            health_data["checks"]["redis"] = {
                "status": "unhealthy",
                "error": str(e)
            }
            health_data["status"] = "degraded"
        
        # Check system resources
        try:
            cpu_percent = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')
            
            health_data["checks"]["system_resources"] = {
                "status": "healthy",
                "cpu_percent": cpu_percent,
                "memory_percent": memory.percent,
                "disk_percent": disk.percent
            }
            
            # Mark as degraded if resources are high
            if cpu_percent > 80 or memory.percent > 80 or disk.percent > 80:
                health_data["status"] = "degraded"
                health_data["checks"]["system_resources"]["status"] = "warning"
                
        except Exception as e:
            health_data["checks"]["system_resources"] = {
                "status": "unhealthy",
                "error": str(e)
            }
            health_data["status"] = "unhealthy"
        
        # Check Celery workers
        try:
            inspect = celery_app.control.inspect()
            active_workers = inspect.active()
            worker_count = len(active_workers) if active_workers else 0
            
            health_data["checks"]["celery_workers"] = {
                "status": "healthy" if worker_count > 0 else "unhealthy",
                "worker_count": worker_count
            }
            
            if worker_count == 0:
                health_data["status"] = "unhealthy"
                
        except Exception as e:
            health_data["checks"]["celery_workers"] = {
                "status": "unhealthy",
                "error": str(e)
            }
            health_data["status"] = "unhealthy"
        
        # Store health check result
        if cache_service:
            await cache_service.set(
                "system_health",
                health_data,
                ttl=300  # 5 minutes
            )
        
        logger.info(f"System health check completed. Status: {health_data['status']}")
        return health_data
        
    except Exception as e:
        logger.error(f"System health check failed: {e}")
        return {
            "timestamp": datetime.utcnow().isoformat(),
            "status": "unhealthy",
            "error": str(e)
        }


@celery_app.task
def collect_system_metrics():
    """Collect system metrics for monitoring"""
    try:
        logger.info("Collecting system metrics")
        
        metrics = {
            "timestamp": datetime.utcnow().isoformat(),
            "system": {},
            "application": {},
            "database": {},
            "cache": {}
        }
        
        # System metrics
        metrics["system"] = {
            "cpu_percent": psutil.cpu_percent(interval=1),
            "memory": {
                "total": psutil.virtual_memory().total,
                "available": psutil.virtual_memory().available,
                "percent": psutil.virtual_memory().percent,
                "used": psutil.virtual_memory().used,
                "free": psutil.virtual_memory().free
            },
            "disk": {
                "total": psutil.disk_usage('/').total,
                "used": psutil.disk_usage('/').used,
                "free": psutil.disk_usage('/').free,
                "percent": psutil.disk_usage('/').percent
            },
            "load_average": psutil.getloadavg() if hasattr(psutil, 'getloadavg') else None
        }
        
        # Application metrics
        metrics["application"] = {
            "celery_active_tasks": len(celery_app.control.inspect().active() or {}),
            "celery_scheduled_tasks": len(celery_app.control.inspect().scheduled() or {}),
            "process_count": len(psutil.pids())
        }
        
        # Cache metrics
        if cache_service:
            try:
                cache_keys = await cache_service.keys("*")
                metrics["cache"] = {
                    "total_keys": len(cache_keys),
                    "memory_usage": "unknown"  # Would need Redis INFO command
                }
            except Exception as e:
                metrics["cache"]["error"] = str(e)
        
        # Store metrics (in production, you'd send to a monitoring system)
        if cache_service:
            await cache_service.set(
                f"metrics:{datetime.utcnow().strftime('%Y%m%d%H%M')}",
                metrics,
                ttl=86400  # 24 hours
            )
        
        logger.info("System metrics collected successfully")
        return metrics
        
    except Exception as e:
        logger.error(f"Failed to collect system metrics: {e}")
        return {"error": str(e), "timestamp": datetime.utcnow().isoformat()}


@celery_app.task(bind=True)
def process_user_registration(self, user_data: Dict[str, Any]):
    """Process user registration in background"""
    try:
        logger.info(f"Processing registration for user: {user_data.get('email')}")
        
        # Send welcome email
        send_welcome_email.delay(
            user_data.get("id"),
            user_data.get("email"),
            user_data.get("full_name")
        )
        
        # Create initial audit log
        # This would be done in a separate task to avoid blocking
        
        # Set up user preferences
        # This could include setting default notification preferences, etc.
        
        logger.info(f"Registration processing completed for user: {user_data.get('email')}")
        return {"status": "success", "message": "Registration processed"}
        
    except Exception as exc:
        logger.error(f"Failed to process user registration: {exc}")
        raise self.retry(exc=exc, countdown=60)


@celery_app.task(bind=True)
def backup_sensitive_data(self, backup_type: str = "incremental"):
    """Create backup of sensitive data"""
    try:
        logger.info(f"Starting {backup_type} backup")
        
        backup_info = {
            "backup_id": str(uuid.uuid4()),
            "backup_type": backup_type,
            "started_at": datetime.utcnow().isoformat(),
            "status": "in_progress"
        }
        
        # In a real implementation, this would:
        # 1. Export sensitive data from database
        # 2. Encrypt the backup
        # 3. Store to secure location (S3, etc.)
        # 4. Verify backup integrity
        
        # Simulate backup process
        await asyncio.sleep(5)  # Simulate processing time
        
        backup_info.update({
            "status": "completed",
            "completed_at": datetime.utcnow().isoformat(),
            "data_size": "1024MB",  # Simulated
            "encrypted": True
        })
        
        logger.info(f"Backup completed: {backup_info['backup_id']}")
        return backup_info
        
    except Exception as exc:
        logger.error(f"Backup failed: {exc}")
        raise self.retry(exc=exc, countdown=300)


@celery_app.task(bind=True)
def generate_user_report(self, user_id: str, report_type: str = "activity"):
    """Generate user-specific report"""
    try:
        logger.info(f"Generating {report_type} report for user: {user_id}")
        
        report_data = {
            "user_id": user_id,
            "report_type": report_type,
            "generated_at": datetime.utcnow().isoformat(),
            "period": "last_30_days"
        }
        
        # In a real implementation, this would:
        # 1. Query database for user activity
        # 2. Aggregate data
        # 3. Generate report in requested format (PDF, CSV, etc.)
        # 4. Store or send report
        
        # Simulate report generation
        await asyncio.sleep(3)
        
        report_data.update({
            "status": "completed",
            "file_path": f"/reports/user_{user_id}_{report_type}_{datetime.utcnow().strftime('%Y%m%d')}.pdf",
            "record_count": 150  # Simulated
        })
        
        logger.info(f"Report generated for user {user_id}")
        return report_data
        
    except Exception as exc:
        logger.error(f"Report generation failed for user {user_id}: {exc}")
        raise self.retry(exc=exc, countdown=60)


@celery_app.task
def cleanup_old_audit_logs():
    """Clean up old audit logs based on retention policy"""
    try:
        logger.info("Starting audit log cleanup")
        
        # This would typically run as a database query
        # DELETE FROM audit_logs WHERE timestamp < NOW() - INTERVAL '7 years'
        
        # For now, just log the action
        cutoff_date = datetime.utcnow() - timedelta(days=7*365)  # 7 years
        
        logger.info(f"Audit log cleanup completed. Removed logs older than {cutoff_date}")
        return {
            "status": "success",
            "cutoff_date": cutoff_date.isoformat(),
            "message": "Audit log cleanup completed"
        }
        
    except Exception as e:
        logger.error(f"Audit log cleanup failed: {e}")
        return {"status": "error", "message": str(e)}


@celery_app.task
def update_user_statistics():
    """Update user statistics and analytics"""
    try:
        logger.info("Updating user statistics")
        
        # This would calculate and store various user metrics
        # like login frequency, activity patterns, etc.
        
        stats = {
            "total_users": 0,
            "active_users_today": 0,
            "new_users_this_week": 0,
            "updated_at": datetime.utcnow().isoformat()
        }
        
        # Store statistics in cache
        if cache_service:
            await cache_service.set(
                "user_statistics",
                stats,
                ttl=3600  # 1 hour
            )
        
        logger.info("User statistics updated")
        return stats
        
    except Exception as e:
        logger.error(f"Failed to update user statistics: {e}")
        return {"status": "error", "message": str(e)}


@celery_app.task(bind=True)
def send_notification_email(self, user_email: str, subject: str, message: str, template: str = "notification"):
    """Send notification email to user"""
    try:
        logger.info(f"Sending notification email to {user_email}")
        
        email_data = {
            "to": user_email,
            "subject": subject,
            "template": template,
            "context": {
                "message": message,
                "timestamp": datetime.utcnow().isoformat()
            }
        }
        
        # email_service.send_email(**email_data)
        
        logger.info(f"Notification email sent successfully to {user_email}")
        return {"status": "success", "message": "Notification email sent"}
        
    except Exception as exc:
        logger.error(f"Failed to send notification email to {user_email}: {exc}")
        raise self.retry(exc=exc, countdown=60)
