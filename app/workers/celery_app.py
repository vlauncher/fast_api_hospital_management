from celery import Celery
from celery.schedules import crontab
import os
from app.core.config import settings

# Create Celery app
celery_app = Celery(
    "hospital_management",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
    include=[
        "app.workers.tasks",
        "app.workers.email_tasks",
        "app.workers.report_tasks",
        "app.workers.audit_tasks",
        "app.workers.data_tasks"
    ]
)

# Celery configuration
celery_app.conf.update(
    # Task settings
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    
    # Worker settings
    worker_prefetch_multiplier=1,
    task_acks_late=True,
    worker_max_tasks_per_child=1000,
    worker_disable_rate_limits=False,
    
    # Task routing
    task_routes={
        "app.workers.email_tasks.*": {"queue": "email"},
        "app.workers.report_tasks.*": {"queue": "reports"},
        "app.workers.audit_tasks.*": {"queue": "audit"},
        "app.workers.data_tasks.*": {"queue": "data_processing"},
        "app.workers.tasks.*": {"queue": "default"},
    },
    
    # Queue definitions
    task_queues={
        "default": {
            "exchange": "default",
            "routing_key": "default",
        },
        "email": {
            "exchange": "email",
            "routing_key": "email",
        },
        "reports": {
            "exchange": "reports",
            "routing_key": "reports",
        },
        "audit": {
            "exchange": "audit",
            "routing_key": "audit",
        },
        "data_processing": {
            "exchange": "data_processing",
            "routing_key": "data_processing",
        },
    },
    
    # Beat schedule (periodic tasks)
    beat_schedule={
        # Daily tasks
        "daily-audit-cleanup": {
            "task": "app.workers.audit_tasks.cleanup_old_audit_logs",
            "schedule": crontab(hour=2, minute=0),  # 2:00 AM UTC
        },
        "daily-session-cleanup": {
            "task": "app.workers.tasks.cleanup_expired_sessions",
            "schedule": crontab(hour=3, minute=0),  # 3:00 AM UTC
        },
        "daily-cache-cleanup": {
            "task": "app.workers.tasks.cleanup_expired_cache",
            "schedule": crontab(hour=4, minute=0),  # 4:00 AM UTC
        },
        
        # Weekly tasks
        "weekly-compliance-report": {
            "task": "app.workers.report_tasks.generate_weekly_compliance_report",
            "schedule": crontab(hour=6, minute=0, day_of_week=1),  # Monday 6:00 AM UTC
        },
        "weekly-security-report": {
            "task": "app.workers.report_tasks.generate_weekly_security_report",
            "schedule": crontab(hour=7, minute=0, day_of_week=1),  # Monday 7:00 AM UTC
        },
        
        # Monthly tasks
        "monthly-data-retention": {
            "task": "app.workers.audit_tasks.apply_data_retention_policy",
            "schedule": crontab(hour=1, minute=0, day_of_month=1),  # 1st of month 1:00 AM UTC
        },
        "monthly-user-activity-report": {
            "task": "app.workers.report_tasks.generate_monthly_user_activity_report",
            "schedule": crontab(hour=8, minute=0, day_of_month=1),  # 1st of month 8:00 AM UTC
        },
        
        # Hourly tasks
        "hourly-health-check": {
            "task": "app.workers.tasks.system_health_check",
            "schedule": crontab(minute=0),  # Every hour
        },
        "hourly-metrics-collection": {
            "task": "app.workers.tasks.collect_system_metrics",
            "schedule": crontab(minute=5),  # Every hour at 5 minutes past
        },
        
        # Frequent tasks
        "every-5-min-rate-limit-cleanup": {
            "task": "app.workers.tasks.cleanup_rate_limit_data",
            "schedule": crontab(minute="*/5"),  # Every 5 minutes
        },
    },
    
    # Result backend settings
    result_expires=3600,  # 1 hour
    result_backend_transport_options={
        "master_name": "mymaster",
    },
    
    # Security settings
    broker_transport_options={
        "visibility_timeout": 3600,
        "max_connections": 20,
        "heartbeat": 30,
    },
    
    # Error handling
    task_reject_on_worker_lost=True,
    task_ignore_result=False,
    
    # Monitoring
    worker_send_task_events=True,
    task_send_sent_event=True,
    
    # Performance
    broker_connection_retry_on_startup=True,
    broker_connection_retry=True,
    broker_connection_max_retries=10,
)

# Optional: Configure for production
if os.getenv("ENVIRONMENT") == "production":
    celery_app.conf.update(
        # Production-specific settings
        worker_log_format="[%(asctime)s: %(levelname)s/%(processName)s] %(message)s",
        worker_task_log_format="[%(asctime)s: %(levelname)s/%(processName)s][%(task_name)s(%(task_id)s)] %(message)s",
        worker_log_color=False,
        
        # Increase concurrency for production
        worker_concurrency=4,
        
        # Enable monitoring
        worker_send_task_events=True,
        task_send_sent_event=True,
        
        # Optimize for performance
        broker_pool_limit=10,
        broker_connection_timeout=30,
        result_backend_pool_limit=10,
    )


class CeleryConfig:
    """Celery configuration class for easy access"""
    
    @staticmethod
    def get_celery_app() -> Celery:
        """Get configured Celery app"""
        return celery_app
    
    @staticmethod
    def configure_for_testing() -> Celery:
        """Configure Celery for testing"""
        test_celery = Celery(
            "hospital_management_test",
            broker="memory://",
            backend="cache+memory://",
            include=["app.workers.tasks"]
        )
        
        test_celery.conf.update(
            task_always_eager=True,
            task_eager_propagates=True,
            task_serializer="json",
            accept_content=["json"],
            result_serializer="json",
            timezone="UTC",
            enable_utc=True,
        )
        
        return test_celery
    
    @staticmethod
    def configure_for_development() -> Celery:
        """Configure Celery for development"""
        dev_celery = Celery(
            "hospital_management_dev",
            broker=settings.REDIS_URL,
            backend=settings.REDIS_URL,
            include=["app.workers.tasks"]
        )
        
        dev_celery.conf.update(
            task_serializer="json",
            accept_content=["json"],
            result_serializer="json",
            timezone="UTC",
            enable_utc=True,
            
            # Development settings
            worker_log_format="[%(asctime)s: %(levelname)s/%(processName)s] %(message)s",
            worker_task_log_format="[%(asctime)s: %(levelname)s/%(processName)s][%(task_name)s(%(task_id)s)] %(message)s",
            worker_log_color=True,
            
            # Lower concurrency for development
            worker_concurrency=2,
            
            # Enable task tracking
            task_track_started=True,
            task_send_sent_event=True,
        )
        
        return dev_celery


# Task decorators for common patterns
def periodic_task(schedule, **options):
    """Decorator for periodic tasks"""
    return celery_app.task(
        bind=True,
        **options
    )


def background_task(queue="default", **options):
    """Decorator for background tasks"""
    return celery_app.task(
        bind=True,
        queue=queue,
        **options
    )


def email_task(**options):
    """Decorator for email tasks"""
    return celery_app.task(
        bind=True,
        queue="email",
        **options
    )


def report_task(**options):
    """Decorator for report generation tasks"""
    return celery_app.task(
        bind=True,
        queue="reports",
        **options
    )


def audit_task(**options):
    """Decorator for audit-related tasks"""
    return celery_app.task(
        bind=True,
        queue="audit",
        **options
    )


def data_processing_task(**options):
    """Decorator for data processing tasks"""
    return celery_app.task(
        bind=True,
        queue="data_processing",
        **options
    )


# Health check task
@celery_app.task(bind=True)
def health_check(self):
    """Simple health check task"""
    return {"status": "healthy", "timestamp": self.request.now}


# Task monitoring
@celery_app.task(bind=True)
def monitor_tasks(self):
    """Monitor task execution and performance"""
    inspect = celery_app.control.inspect()
    
    # Get active tasks
    active_tasks = inspect.active()
    
    # Get scheduled tasks
    scheduled_tasks = inspect.scheduled()
    
    # Get reserved tasks
    reserved_tasks = inspect.reserved()
    
    return {
        "active_tasks": active_tasks,
        "scheduled_tasks": scheduled_tasks,
        "reserved_tasks": reserved_tasks,
        "timestamp": self.request.now,
    }


# Error handling
@celery_app.task(bind=True)
def error_handler(self, task_id, error, traceback):
    """Handle task errors"""
    # Log error details
    print(f"Task {task_id} failed with error: {error}")
    print(f"Traceback: {traceback}")
    
    # Here you could:
    # - Send error notifications
    # - Log to external monitoring systems
    # - Trigger retry logic
    # - Update error metrics
    
    return {
        "task_id": task_id,
        "error": str(error),
        "traceback": traceback,
        "timestamp": self.request.now,
    }


# Set up error handling for all tasks
# Note: Signal connections removed due to compatibility issues with newer Celery versions
# Error handling is now handled in the BaseTask class

# Custom task base class for common functionality
class BaseTask(celery_app.Task):
    """Base task class with common functionality"""
    
    def on_success(self, retval, task_id, args, kwargs):
        """Called when task succeeds"""
        print(f"Task {task_id} completed successfully")
    
    def on_failure(self, exc, task_id, args, kwargs, einfo):
        """Called when task fails"""
        print(f"Task {task_id} failed: {exc}")
        # Trigger error handling task
        error_handler.delay(task_id, str(exc), str(einfo))
    
    def on_retry(self, exc, task_id, args, kwargs, einfo):
        """Called when task is retried"""
        print(f"Task {task_id} is being retried: {exc}")


# Set default task base class
celery_app.Task = BaseTask


if __name__ == "__main__":
    celery_app.start()
