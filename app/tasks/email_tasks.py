from app.core.celery_app import celery_app
from loguru import logger
from app.services.email import send_otp_email as sync_send_otp_email
import asyncio

@celery_app.task(name="app.tasks.email_tasks.send_otp_email_task")
def send_otp_email_task(email: str, otp: str):
    """
    Celery task to send OTP email.
    """
    logger.info(f"Background task: Sending OTP to {email}")
    # Since our service is async, we need a way to run it in sync Celery
    loop = asyncio.get_event_loop()
    loop.run_until_complete(sync_send_otp_email(email, otp))
    return True
