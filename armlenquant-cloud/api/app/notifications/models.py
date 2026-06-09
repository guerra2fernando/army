"""
Notification Models
"""
from datetime import datetime
from enum import Enum
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field


class NotificationType(str, Enum):
    """Types of notifications."""
    TASK_COMPLETED = "task_completed"
    TASK_FAILED = "task_failed"
    AGENT_ALERT = "agent_alert"
    SYSTEM_ERROR = "system_error"
    DAILY_BRIEF = "daily_brief"
    CRYPTO_SIGNAL = "crypto_signal"
    JOB_MATCH = "job_match"
    CUSTOM = "custom"


class NotificationPriority(str, Enum):
    """Notification priority levels."""
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    URGENT = "urgent"


class NotificationChannel(str, Enum):
    """Available notification channels."""
    TELEGRAM = "telegram"
    DASHBOARD = "dashboard"
    ALL = "all"


class Notification(BaseModel):
    """Notification data model."""
    notification_id: str
    type: NotificationType
    title: str
    message: str
    priority: NotificationPriority = NotificationPriority.NORMAL
    channel: NotificationChannel = NotificationChannel.ALL
    metadata: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    sent_at: Optional[datetime] = None
    delivered: bool = False
    error: Optional[str] = None


class NotificationCreate(BaseModel):
    """Request model for creating notifications."""
    type: NotificationType
    title: str
    message: str
    priority: NotificationPriority = NotificationPriority.NORMAL
    channel: NotificationChannel = NotificationChannel.ALL
    metadata: Dict[str, Any] = Field(default_factory=dict)


class NotificationResponse(BaseModel):
    """Response model for notifications."""
    success: bool
    notification_id: Optional[str] = None
    message: str
    delivered_to: List[str] = Field(default_factory=list)


class TelegramUserLink(BaseModel):
    """Links a Telegram user to the system."""
    telegram_user_id: int
    telegram_username: Optional[str] = None
    chat_id: int
    user_id: Optional[str] = None  # Internal user ID
    is_admin: bool = False
    notifications_enabled: bool = True
    created_at: datetime = Field(default_factory=datetime.utcnow)
    last_interaction: Optional[datetime] = None


class NotificationPreferences(BaseModel):
    """User notification preferences."""
    user_id: str
    telegram_enabled: bool = True
    dashboard_enabled: bool = True
    notify_task_complete: bool = True
    notify_task_failed: bool = True
    notify_agent_alerts: bool = True
    notify_crypto_signals: bool = True
    notify_job_matches: bool = True
    notify_daily_brief: bool = True
    quiet_hours_start: Optional[int] = None  # Hour (0-23)
    quiet_hours_end: Optional[int] = None


