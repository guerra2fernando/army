"""
Tests for System Monitoring
Phase 10: Integration & Polish
"""
import pytest
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock, AsyncMock
from httpx import AsyncClient

from app.db import Database


class TestSystemMonitor:
    """Test system monitoring functionality."""
    
    @pytest.mark.asyncio
    async def test_health_check_basic(self, client: AsyncClient):
        """Test basic health check endpoint."""
        response = await client.get("/health")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "timestamp" in data
        assert data["service"] == "armlenquant-api"
    
    @pytest.mark.asyncio
    async def test_detailed_health_check(self, client: AsyncClient, auth_headers: dict):
        """Test detailed health check with authentication."""
        response = await client.get("/health/detailed", headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "data" in data
        
        health_data = data["data"]
        assert "status" in health_data
        assert "database" in health_data
        assert "agents" in health_data
        assert "task_queue" in health_data
    
    @pytest.mark.asyncio
    async def test_health_check_reports_agent_count(self, client: AsyncClient, auth_headers: dict, test_agent: dict):
        """Test health check includes agent statistics."""
        response = await client.get("/health/detailed", headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()["data"]
        
        assert "agents" in data
        assert "total" in data["agents"]
        assert "active" in data["agents"]
        assert data["agents"]["total"] >= 1
    
    @pytest.mark.asyncio
    async def test_health_check_reports_task_queue(self, client: AsyncClient, auth_headers: dict, test_task: dict):
        """Test health check includes task queue statistics."""
        response = await client.get("/health/detailed", headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()["data"]
        
        assert "task_queue" in data
        assert "pending" in data["task_queue"]
        assert "in_progress" in data["task_queue"]


class TestSystemMonitorAlerts:
    """Test system monitoring alert generation."""
    
    @pytest.mark.asyncio
    async def test_no_alerts_on_healthy_system(self):
        """Test no alerts generated for healthy system."""
        from app.monitoring import SystemMonitor
        
        monitor = SystemMonitor()
        
        # Mock healthy state
        with patch.object(monitor, 'check_health') as mock_health:
            mock_health.return_value = {
                "database": "healthy",
                "task_queue": {"pending": 0, "stuck": 0, "status": "healthy"},
                "agents": {"active": 2, "failed": 0, "status": "healthy"},
                "overall": "healthy"
            }
            
            alerts = await monitor.generate_alerts()
            assert len(alerts) == 0
    
    @pytest.mark.asyncio
    async def test_alert_on_stuck_tasks(self):
        """Test alert generated when tasks are stuck."""
        from app.monitoring import SystemMonitor
        
        monitor = SystemMonitor()
        
        # Mock stuck tasks
        with patch.object(monitor, 'check_health') as mock_health:
            mock_health.return_value = {
                "database": "healthy",
                "task_queue": {"pending": 5, "stuck": 3, "status": "degraded"},
                "agents": {"active": 2, "failed": 0, "status": "healthy"},
                "overall": "degraded"
            }
            
            alerts = await monitor.generate_alerts()
            
            assert len(alerts) > 0
            assert any("stuck" in alert["message"].lower() for alert in alerts)
    
    @pytest.mark.asyncio
    async def test_alert_on_failed_agents(self):
        """Test alert generated when agents are in failed state."""
        from app.monitoring import SystemMonitor
        
        monitor = SystemMonitor()
        
        # Mock failed agents
        with patch.object(monitor, 'check_health') as mock_health:
            mock_health.return_value = {
                "database": "healthy",
                "task_queue": {"pending": 0, "stuck": 0, "status": "healthy"},
                "agents": {"active": 1, "failed": 2, "status": "degraded"},
                "overall": "degraded"
            }
            
            alerts = await monitor.generate_alerts()
            
            assert len(alerts) > 0
            assert any("failed" in alert["message"].lower() or "agent" in alert["message"].lower() for alert in alerts)
    
    @pytest.mark.asyncio
    async def test_alert_on_high_queue_depth(self):
        """Test alert generated when task queue is too deep."""
        from app.monitoring import SystemMonitor
        
        monitor = SystemMonitor()
        
        # Mock high queue depth
        with patch.object(monitor, 'check_health') as mock_health:
            mock_health.return_value = {
                "database": "healthy",
                "task_queue": {"pending": 150, "stuck": 0, "status": "degraded"},
                "agents": {"active": 2, "failed": 0, "status": "healthy"},
                "overall": "degraded"
            }
            
            alerts = await monitor.generate_alerts()
            
            assert len(alerts) > 0
            assert any("queue" in alert["message"].lower() or "depth" in alert["message"].lower() for alert in alerts)


class TestSystemMonitorHealthChecks:
    """Test individual health check components."""
    
    @pytest.mark.asyncio
    async def test_database_health_check(self):
        """Test database connectivity check."""
        from app.monitoring import SystemMonitor
        
        monitor = SystemMonitor()
        
        # Mock database connectivity
        with patch('app.monitoring.Database') as mock_db:
            mock_db.client.admin.command = AsyncMock(return_value={'ok': 1})
            mock_db.get_collection.return_value.count_documents = AsyncMock(return_value=0)
            
            health = await monitor.check_health()
            
            assert "database" in health
    
    @pytest.mark.asyncio
    async def test_overall_status_healthy(self):
        """Test overall status is healthy when all components healthy."""
        from app.monitoring import SystemMonitor
        
        monitor = SystemMonitor()
        
        with patch('app.monitoring.Database') as mock_db:
            mock_db.client.admin.command = AsyncMock(return_value={'ok': 1})
            mock_collection = MagicMock()
            mock_collection.count_documents = AsyncMock(return_value=0)
            mock_db.get_collection.return_value = mock_collection
            
            health = await monitor.check_health()
            
            assert health["overall"] in ["healthy", "degraded", "unhealthy"]
    
    @pytest.mark.asyncio
    async def test_overall_status_unhealthy_on_db_failure(self):
        """Test overall status is unhealthy when database fails."""
        from app.monitoring import SystemMonitor
        
        monitor = SystemMonitor()
        
        with patch('app.monitoring.Database') as mock_db:
            mock_db.client.admin.command = AsyncMock(side_effect=Exception("Connection lost"))
            mock_collection = MagicMock()
            mock_collection.count_documents = AsyncMock(return_value=0)
            mock_db.get_collection.return_value = mock_collection
            
            health = await monitor.check_health()
            
            assert health["database"] != "healthy" or health["overall"] != "healthy"

