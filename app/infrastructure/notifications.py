import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)


async def send_notification(recipient: str, subject: str, body: str, channel: str = "email") -> Dict[str, Any]:
    """Lightweight notification sender used by services/tasks.

    This is a placeholder adapter that should be replaced with real
    provider integrations (SMTP, Twilio, push, etc.) as needed.
    """
    try:
        logger.info(f"Sending {channel} notification to {recipient}: {subject}")
        # TODO: integrate with actual provider
        # For now simulate success
        return {"status": "sent", "recipient": recipient, "channel": channel}
    except Exception as e:
        logger.error(f"Failed to send notification: {e}")
        return {"status": "error", "error": str(e)}
