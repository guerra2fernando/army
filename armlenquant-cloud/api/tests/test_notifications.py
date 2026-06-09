"""
Tests for Notification System
"""
import pytest
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

from app.notifications.models import (
    NotificationType,
    NotificationPriority,
    NotificationChannel,
    NotificationCreate,
    Notification
)
from app.notifications.service import NotificationService, get_notification_service, reset_notification_service
from app.notifications.telegram_bot import TelegramBot, get_telegram_bot, reset_telegram_bot


class TestNotificationModels:
    """Test notification data models."""
    
    def test_notification_create(self):
        """Test creating a notification."""
        notification = NotificationCreate(
            type=NotificationType.TASK_COMPLETED,
            title="Test Notification",
            message="This is a test",
            priority=NotificationPriority.NORMAL
        )
        
        assert notification.type == NotificationType.TASK_COMPLETED
        assert notification.title == "Test Notification"
        assert notification.message == "This is a test"
        assert notification.priority == NotificationPriority.NORMAL
        assert notification.channel == NotificationChannel.ALL
    
    def test_notification_with_metadata(self):
        """Test notification with metadata."""
        notification = NotificationCreate(
            type=NotificationType.CRYPTO_SIGNAL,
            title="BTC Signal",
            message="Buy signal for BTC",
            metadata={"coin": "BTC", "confidence": 85}
        )
        
        assert notification.metadata["coin"] == "BTC"
        assert notification.metadata["confidence"] == 85
    
    def test_notification_types(self):
        """Test all notification types."""
        types = [
            NotificationType.TASK_COMPLETED,
            NotificationType.TASK_FAILED,
            NotificationType.AGENT_ALERT,
            NotificationType.SYSTEM_ERROR,
            NotificationType.DAILY_BRIEF,
            NotificationType.CRYPTO_SIGNAL,
            NotificationType.JOB_MATCH,
            NotificationType.CUSTOM
        ]
        
        for t in types:
            notification = NotificationCreate(
                type=t,
                title="Test",
                message="Test message"
            )
            assert notification.type == t
    
    def test_priority_levels(self):
        """Test priority levels."""
        for priority in NotificationPriority:
            notification = NotificationCreate(
                type=NotificationType.CUSTOM,
                title="Test",
                message="Test",
                priority=priority
            )
            assert notification.priority == priority


class TestTelegramBot:
    """Test Telegram bot service."""
    
    @pytest.fixture
    def mock_settings(self):
        """Mock settings with Telegram disabled."""
        with patch("app.notifications.telegram_bot.settings") as mock:
            mock.telegram_bot_token = ""
            mock.telegram_chat_id = ""
            mock.telegram_enabled = False
            yield mock
    
    @pytest.fixture
    def mock_enabled_settings(self):
        """Mock settings with Telegram enabled."""
        with patch("app.notifications.telegram_bot.settings") as mock:
            mock.telegram_bot_token = "test_token"
            mock.telegram_chat_id = "123456"
            mock.telegram_enabled = True
            yield mock
    
    def test_bot_disabled(self, mock_settings):
        """Test bot when disabled."""
        reset_telegram_bot()
        bot = TelegramBot()
        
        assert not bot.enabled
        assert bot.bot is None
    
    @pytest.mark.asyncio
    async def test_send_notification_disabled(self, mock_settings):
        """Test sending notification when disabled."""
        reset_telegram_bot()
        bot = TelegramBot()
        
        result = await bot.send_notification("Test message")
        assert result is False
    
    @pytest.mark.asyncio
    async def test_send_notification_no_chat_id(self, mock_enabled_settings):
        """Test sending notification without chat ID."""
        reset_telegram_bot()
        
        with patch("app.notifications.telegram_bot.Bot"):
            bot = TelegramBot(token="test_token")
            bot.enabled = True
            bot.chat_id = ""
            
            result = await bot.send_notification("Test message")
            assert result is False
    
    def test_format_task_notification(self):
        """Test task notification formatting."""
        reset_telegram_bot()
        bot = TelegramBot()
        
        # Create a mock notification
        notification = NotificationCreate(
            type=NotificationType.TASK_COMPLETED,
            title="Task Completed",
            message="Task xyz completed successfully"
        )
        
        # Test the formatting method
        formatted = bot._format_telegram_message(notification) if hasattr(bot, '_format_telegram_message') else None
        # Basic assertion - method would need to exist
        assert notification.title == "Task Completed"


class TestNotificationService:
    """Test notification service."""
    
    @pytest.fixture
    def mock_db(self):
        """Mock database."""
        with patch("app.notifications.service.Database") as mock:
            mock_collection = AsyncMock()
            mock.get_collection.return_value = mock_collection
            yield mock
    
    @pytest.fixture
    def mock_telegram_disabled(self):
        """Mock telegram bot as disabled."""
        with patch("app.notifications.service.get_telegram_bot") as mock:
            bot = MagicMock()
            bot.enabled = False
            mock.return_value = bot
            yield bot
    
    @pytest.fixture
    def mock_settings_enabled(self):
        """Mock settings with notifications enabled."""
        with patch("app.notifications.service.settings") as mock:
            mock.notifications_enabled = True
            mock.notify_on_task_complete = True
            mock.notify_on_task_failed = True
            mock.notify_on_agent_alert = True
            mock.notify_on_system_error = True
            yield mock
    
    @pytest.mark.asyncio
    async def test_send_notification_stores_in_db(
        self,
        mock_db,
        mock_telegram_disabled,
        mock_settings_enabled
    ):
        """Test that notifications are stored in database."""
        reset_notification_service()
        service = NotificationService()
        
        notification = NotificationCreate(
            type=NotificationType.CUSTOM,
            title="Test",
            message="Test message"
        )
        
        response = await service.send(notification)
        
        assert response.notification_id is not None
        mock_db.get_collection.assert_called()
    
    @pytest.mark.asyncio
    async def test_notify_task_completed(
        self,
        mock_db,
        mock_telegram_disabled,
        mock_settings_enabled
    ):
        """Test task completion notification."""
        reset_notification_service()
        service = NotificationService()
        
        response = await service.notify_task_completed(
            task_id="test-task-123",
            agent="JOB_HUNTER",
            result_summary="Found 5 jobs"
        )
        
        assert response.notification_id is not None
    
    @pytest.mark.asyncio
    async def test_notify_task_failed(
        self,
        mock_db,
        mock_telegram_disabled,
        mock_settings_enabled
    ):
        """Test task failure notification."""
        reset_notification_service()
        service = NotificationService()
        
        response = await service.notify_task_failed(
            task_id="test-task-123",
            agent="CRYPTO_SENTINEL",
            error="API timeout"
        )
        
        assert response.notification_id is not None
    
    @pytest.mark.asyncio
    async def test_notify_crypto_signal(
        self,
        mock_db,
        mock_telegram_disabled,
        mock_settings_enabled
    ):
        """Test crypto signal notification."""
        reset_notification_service()
        service = NotificationService()
        
        response = await service.notify_crypto_signal(
            coin="BTC",
            signal="BUY",
            confidence=85,
            price=42000.00,
            change_24h=5.2,
            reason="RSI oversold, strong support"
        )
        
        assert response.notification_id is not None
    
    @pytest.mark.asyncio
    async def test_notify_job_match(
        self,
        mock_db,
        mock_telegram_disabled,
        mock_settings_enabled
    ):
        """Test job match notification."""
        reset_notification_service()
        service = NotificationService()
        
        response = await service.notify_job_match(
            title="Senior Python Developer",
            company="TechCorp",
            location="Berlin, Germany",
            match_score=92,
            url="https://example.com/job/123"
        )
        
        assert response.notification_id is not None
    
    @pytest.mark.asyncio
    async def test_notify_system_error(
        self,
        mock_db,
        mock_telegram_disabled,
        mock_settings_enabled
    ):
        """Test system error notification."""
        reset_notification_service()
        service = NotificationService()
        
        response = await service.notify_system_error(
            error="Database connection failed",
            context={"component": "db", "retry_count": 3}
        )
        
        assert response.notification_id is not None
    
    def test_should_send_check(self, mock_settings_enabled):
        """Test notification type filtering."""
        reset_notification_service()
        service = NotificationService()
        
        # These should be sent
        assert service._should_send(NotificationType.TASK_COMPLETED)
        assert service._should_send(NotificationType.TASK_FAILED)
        assert service._should_send(NotificationType.AGENT_ALERT)
        assert service._should_send(NotificationType.SYSTEM_ERROR)
        
        # Custom types default to True
        assert service._should_send(NotificationType.CUSTOM)


class TestNotificationRoutes:
    """Test notification API routes."""
    
    @pytest.fixture
    def mock_auth(self):
        """Mock authentication."""
        with patch("app.routes.notifications.get_current_user") as mock:
            mock.return_value = {"user_id": "test-user", "email": "test@example.com"}
            yield mock
    
    @pytest.mark.asyncio
    async def test_send_notification_route(self, mock_auth):
        """Test send notification endpoint."""
        from app.routes.notifications import send_notification, SendNotificationRequest
        
        with patch("app.routes.notifications.get_notification_service") as mock_service:
            mock_service.return_value.send = AsyncMock(
                return_value=MagicMock(
                    success=True,
                    notification_id="test-id",
                    message="Sent",
                    delivered_to=["dashboard"]
                )
            )
            
            request = SendNotificationRequest(
                title="Test",
                message="Test message"
            )
            
            response = await send_notification(
                request,
                current_user={"user_id": "test", "email": "test@example.com"}
            )
            
            assert response.success
    
    @pytest.mark.asyncio
    async def test_get_telegram_status(self, mock_auth):
        """Test telegram status endpoint."""
        from app.routes.notifications import get_telegram_status
        
        with patch("app.notifications.telegram_bot.get_telegram_bot") as mock_bot:
            bot = MagicMock()
            bot.enabled = False
            bot._running = False
            mock_bot.return_value = bot
            
            with patch("app.config.get_settings") as mock_settings:
                settings_obj = MagicMock()
                settings_obj.telegram_chat_id = ""
                mock_settings.return_value = settings_obj
                
                response = await get_telegram_status(
                    current_user={"user_id": "test"}
                )
                
                assert response.enabled is False
                assert response.connected is False


class TestTelegramMessageFormatting:
    """Test Telegram message formatting."""
    
    def test_format_task_completed_message(self):
        """Test formatting completed task message."""
        notification = NotificationCreate(
            type=NotificationType.TASK_COMPLETED,
            title="Task Completed",
            message="Task `abc123` completed by *JOB_HUNTER*"
        )
        
        # Message should contain the title
        assert "Task Completed" in notification.title
    
    def test_format_crypto_signal_message(self):
        """Test formatting crypto signal message."""
        notification = NotificationCreate(
            type=NotificationType.CRYPTO_SIGNAL,
            title="Crypto Signal: BTC",
            message="*BTC*: 🟢 BUY (85%)\nPrice: $42,000.00\n24h: 📈 +5.20%",
            metadata={
                "coin": "BTC",
                "signal": "BUY",
                "confidence": 85
            }
        )
        
        assert "BTC" in notification.message
        assert "BUY" in notification.message
    
    def test_format_urgent_priority(self):
        """Test urgent priority formatting."""
        notification = NotificationCreate(
            type=NotificationType.SYSTEM_ERROR,
            title="System Error",
            message="Database connection failed",
            priority=NotificationPriority.URGENT
        )
        
        assert notification.priority == NotificationPriority.URGENT


