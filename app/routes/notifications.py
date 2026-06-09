"""
Notification API Routes
"""
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from datetime import datetime

from app.utils.auth import get_current_user
from app.notifications.service import get_notification_service
from app.models.user import User
from app.notifications.models import (
    NotificationCreate,
    NotificationResponse,
    NotificationType,
    NotificationPriority,
    NotificationChannel
)

router = APIRouter(prefix="/notifications", tags=["Notifications"])


class SendNotificationRequest(BaseModel):
    """Request to send a notification."""
    title: str
    message: str
    type: NotificationType = NotificationType.CUSTOM
    priority: NotificationPriority = NotificationPriority.NORMAL
    channel: NotificationChannel = NotificationChannel.ALL


class NotificationItem(BaseModel):
    """Single notification item."""
    notification_id: str
    type: str
    title: str
    message: str
    priority: str
    delivered: bool
    created_at: datetime


class NotificationListResponse(BaseModel):
    """Response containing list of notifications."""
    success: bool
    notifications: List[NotificationItem]
    count: int


class TelegramStatusResponse(BaseModel):
    """Telegram bot status."""
    enabled: bool
    connected: bool
    chat_id_configured: bool


@router.post("/send", response_model=NotificationResponse)
async def send_notification(
    request: SendNotificationRequest,
    current_user: User = Depends(get_current_user)
):
    """
    Send a custom notification.
    
    This endpoint allows you to send notifications through
    configured channels (Telegram, Dashboard, or both).
    """
    service = get_notification_service()
    
    notification = NotificationCreate(
        type=request.type,
        title=request.title,
        message=request.message,
        priority=request.priority,
        channel=request.channel,
        metadata={
            "sent_by": getattr(current_user, "user_id", None)
            if not isinstance(current_user, dict)
            else current_user.get("user_id")
        }
    )
    
    return await service.send(notification)


@router.get("/recent", response_model=NotificationListResponse)
async def get_recent_notifications(
    limit: int = 50,
    type: Optional[NotificationType] = None,
    current_user: dict = Depends(get_current_user)
):
    """Get recent notifications."""
    service = get_notification_service()
    
    notifications = await service.get_recent_notifications(
        limit=limit,
        notification_type=type
    )
    
    items = [
        NotificationItem(
            notification_id=n["notification_id"],
            type=n["type"],
            title=n["title"],
            message=n["message"],
            priority=n["priority"],
            delivered=n.get("delivered", False),
            created_at=n["created_at"]
        )
        for n in notifications
    ]
    
    return NotificationListResponse(
        success=True,
        notifications=items,
        count=len(items)
    )


@router.get("/telegram/status", response_model=TelegramStatusResponse)
async def get_telegram_status(current_user: dict = Depends(get_current_user)):
    """Get Telegram bot status."""
    from app.notifications.telegram_bot import get_telegram_bot
    from app.config import get_settings
    
    settings = get_settings()
    bot = get_telegram_bot()
    
    return TelegramStatusResponse(
        enabled=bot.enabled,
        connected=bot._running if hasattr(bot, '_running') else False,
        chat_id_configured=bool(settings.telegram_chat_id)
    )


@router.post("/telegram/test")
async def test_telegram_notification(current_user: dict = Depends(get_current_user)):
    """Send a test notification to Telegram."""
    from app.notifications.telegram_bot import get_telegram_bot
    
    bot = get_telegram_bot()
    
    if not bot.enabled:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Telegram bot is not enabled. Set TELEGRAM_BOT_TOKEN and TELEGRAM_ENABLED=true"
        )
    
    success = await bot.send_notification(
        "🧪 *Test Notification*\n\n"
        "This is a test notification from ArmLenQuant!\n\n"
        f"Sent by: {current_user.get('email', 'Unknown')}\n"
        f"Time: {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}"
    )
    
    if success:
        return {"success": True, "message": "Test notification sent!"}
    else:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to send test notification"
        )


@router.post("/alert")
async def send_alert(
    title: str,
    message: str,
    level: str = "info",
    current_user: dict = Depends(get_current_user)
):
    """Send an alert notification."""
    service = get_notification_service()
    
    return await service.notify_agent_alert(
        agent="Manual",
        alert_message=f"*{title}*\n\n{message}",
        level=level
    )


