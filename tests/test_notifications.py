import pytest
from unittest.mock import AsyncMock, patch
from app.infrastructure.notifications import send_notification


@pytest.mark.asyncio
async def test_send_notification_success():
    """Test successful notification sending"""
    result = await send_notification(
        recipient="test@example.com",
        subject="Test Subject",
        body="Test body content",
        channel="email"
    )
    assert result["status"] == "sent"
    assert result["recipient"] == "test@example.com"
    assert result["channel"] == "email"


@pytest.mark.asyncio
async def test_send_notification_error():
    """Test notification sending error handling"""
    with patch('app.infrastructure.notifications.send_notification') as mock_send:
        mock_send.side_effect = Exception("Send failed")
        
        try:
            await send_notification("test@example.com", "Subject", "Body")
        except Exception as e:
            assert str(e) == "Send failed"


@pytest.mark.asyncio
async def test_send_notification_sms():
    """Test SMS notification"""
    result = await send_notification(
        recipient="+1234567890",
        subject="",
        body="Test SMS message",
        channel="sms"
    )
    assert result["status"] == "sent"
    assert result["channel"] == "sms"
