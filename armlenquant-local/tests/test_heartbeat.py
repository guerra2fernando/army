"""
Tests for Heartbeat Manager
"""
import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch


class TestHeartbeatManager:
    """Tests for HeartbeatManager class."""

    @pytest.mark.asyncio
    async def test_heartbeat_manager_initialization(self):
        """Test heartbeat manager initialization."""
        from poller.heartbeat import HeartbeatManager
        
        mock_api_client = MagicMock()
        mock_task_router = MagicMock()
        
        manager = HeartbeatManager(mock_api_client, mock_task_router)
        
        assert manager._running is False

    @pytest.mark.asyncio
    async def test_heartbeat_start_and_stop(self):
        """Test starting and stopping heartbeat."""
        from poller.heartbeat import HeartbeatManager
        
        mock_api_client = MagicMock()
        mock_api_client.send_heartbeat = AsyncMock(return_value=True)
        mock_task_router = MagicMock()
        mock_task_router.get_all_statuses.return_value = {}
        
        manager = HeartbeatManager(mock_api_client, mock_task_router)
        
        await manager.start()
        assert manager._running is True
        
        # Give it a moment to run
        await asyncio.sleep(0.1)
        
        await manager.stop()
        assert manager._running is False

    @pytest.mark.asyncio
    @patch('poller.heartbeat.psutil')
    async def test_collect_metrics(self, mock_psutil):
        """Test metrics collection."""
        from poller.heartbeat import HeartbeatManager
        
        mock_psutil.cpu_percent.return_value = 25.5
        mock_psutil.virtual_memory.return_value = MagicMock(percent=60.0)
        mock_psutil.disk_usage.return_value = MagicMock(percent=45.0)
        
        mock_api_client = MagicMock()
        mock_task_router = MagicMock()
        
        manager = HeartbeatManager(mock_api_client, mock_task_router)
        metrics = manager._collect_metrics()
        
        assert "cpu_percent" in metrics
        assert "memory_percent" in metrics
        assert "disk_percent" in metrics
        assert "timestamp" in metrics

    @pytest.mark.asyncio
    async def test_heartbeat_sends_to_api(self):
        """Test that heartbeat sends data to API."""
        from poller.heartbeat import HeartbeatManager
        
        mock_api_client = MagicMock()
        mock_api_client.send_heartbeat = AsyncMock(return_value=True)
        mock_task_router = MagicMock()
        mock_task_router.get_all_statuses.return_value = {}
        
        manager = HeartbeatManager(mock_api_client, mock_task_router)
        
        with patch.object(manager, '_collect_metrics', return_value={
            "cpu_percent": 25.0,
            "memory_percent": 50.0,
            "disk_percent": 40.0,
            "timestamp": "2024-01-01T00:00:00"
        }):
            await manager._send_heartbeat()
        
        mock_api_client.send_heartbeat.assert_called_once()
        call_kwargs = mock_api_client.send_heartbeat.call_args[1]
        assert call_kwargs["agent_name"] == "LOCAL_POLLER"
        assert call_kwargs["status"] == "HEALTHY"

    @pytest.mark.asyncio
    async def test_heartbeat_detects_high_resource_usage(self):
        """Test that heartbeat reports degraded status on high resource usage."""
        from poller.heartbeat import HeartbeatManager
        
        mock_api_client = MagicMock()
        mock_api_client.send_heartbeat = AsyncMock(return_value=True)
        mock_task_router = MagicMock()
        mock_task_router.get_all_statuses.return_value = {}
        
        manager = HeartbeatManager(mock_api_client, mock_task_router)
        
        with patch.object(manager, '_collect_metrics', return_value={
            "cpu_percent": 95.0,  # High CPU
            "memory_percent": 50.0,
            "disk_percent": 40.0,
            "timestamp": "2024-01-01T00:00:00"
        }):
            await manager._send_heartbeat()
        
        call_kwargs = mock_api_client.send_heartbeat.call_args[1]
        assert call_kwargs["status"] == "DEGRADED"

    @pytest.mark.asyncio
    async def test_heartbeat_includes_current_task(self):
        """Test that heartbeat includes current task info."""
        from poller.heartbeat import HeartbeatManager
        
        mock_api_client = MagicMock()
        mock_api_client.send_heartbeat = AsyncMock(return_value=True)
        mock_task_router = MagicMock()
        mock_task_router.get_all_statuses.return_value = {
            "JOB_HUNTER": {
                "is_running": True,
                "current_task": "task-abc-123"
            }
        }
        
        manager = HeartbeatManager(mock_api_client, mock_task_router)
        
        with patch.object(manager, '_collect_metrics', return_value={
            "cpu_percent": 25.0,
            "memory_percent": 50.0,
            "disk_percent": 40.0,
            "timestamp": "2024-01-01T00:00:00"
        }):
            await manager._send_heartbeat()
        
        call_kwargs = mock_api_client.send_heartbeat.call_args[1]
        assert call_kwargs["current_task"] == "task-abc-123"

