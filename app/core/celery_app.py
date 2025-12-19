from celery import Celery
from app.core.config import settings

celery_app = Celery("hospital_tasks", broker=settings.REDIS_URL, backend=settings.REDIS_URL)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
)

# Auto-discover tasks from app/tasks directory
celery_app.autodiscover_tasks(["app"])
