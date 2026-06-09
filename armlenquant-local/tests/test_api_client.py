"""
Tests for Cloud API Client
"""
import pytest
import httpx
import respx
from datetime import datetime


class TestCloudAPIClient:
    """Tests for CloudAPIClient."""

    @pytest.mark.asyncio
    @respx.mock
    async def test_health_check_success(self):
        """Test successful health check."""
        from poller.api_client import CloudAPIClient
        
        respx.get("http://test-api.local/health").mock(
            return_value=httpx.Response(200, json={"status": "healthy"})
        )
        
        client = CloudAPIClient()
        result = await client.health_check()
        await client.close()
        
        assert result is True

    @pytest.mark.asyncio
    @respx.mock
    async def test_health_check_failure(self):
        """Test health check when server is down."""
        from poller.api_client import CloudAPIClient
        
        respx.get("http://test-api.local/health").mock(
            side_effect=httpx.ConnectError("Connection refused")
        )
        
        client = CloudAPIClient()
        result = await client.health_check()
        await client.close()
        
        assert result is False

    @pytest.mark.asyncio
    @respx.mock
    async def test_pickup_task_success(self, mock_api_response_task):
        """Test successful task pickup."""
        from poller.api_client import CloudAPIClient
        
        respx.post("http://test-api.local/api/v1/tasks/pickup").mock(
            return_value=httpx.Response(200, json=mock_api_response_task)
        )
        
        client = CloudAPIClient()
        task = await client.pickup_task(["JOB_HUNTER"])
        await client.close()
        
        assert task is not None
        assert task["task_id"] == "test-task-123"
        assert task["agent_target"] == "JOB_HUNTER"

    @pytest.mark.asyncio
    @respx.mock
    async def test_pickup_task_no_tasks_available(self):
        """Test task pickup when no tasks available."""
        from poller.api_client import CloudAPIClient
        
        respx.post("http://test-api.local/api/v1/tasks/pickup").mock(
            return_value=httpx.Response(404, json={"detail": "No tasks available"})
        )
        
        client = CloudAPIClient()
        task = await client.pickup_task(["JOB_HUNTER"])
        await client.close()
        
        assert task is None

    @pytest.mark.asyncio
    @respx.mock
    async def test_update_task_status_success(self):
        """Test successful task status update."""
        from poller.api_client import CloudAPIClient
        
        respx.patch("http://test-api.local/api/v1/tasks/test-task-123/status").mock(
            return_value=httpx.Response(200, json={"success": True})
        )
        
        client = CloudAPIClient()
        result = await client.update_task_status(
            task_id="test-task-123",
            status="COMPLETED",
            result={"data": "test"}
        )
        await client.close()
        
        assert result is True

    @pytest.mark.asyncio
    @respx.mock
    async def test_update_task_status_with_error(self):
        """Test task status update with error message."""
        from poller.api_client import CloudAPIClient
        
        respx.patch("http://test-api.local/api/v1/tasks/test-task-123/status").mock(
            return_value=httpx.Response(200, json={"success": True})
        )
        
        client = CloudAPIClient()
        result = await client.update_task_status(
            task_id="test-task-123",
            status="FAILED",
            error_message="Connection timeout"
        )
        await client.close()
        
        assert result is True

    @pytest.mark.asyncio
    @respx.mock
    async def test_register_agent_success(self):
        """Test successful agent registration."""
        from poller.api_client import CloudAPIClient
        
        respx.post("http://test-api.local/api/v1/agents/register").mock(
            return_value=httpx.Response(200, json={
                "agent_id": "agent-123",
                "agent_name": "JOB_HUNTER",
                "status": "ACTIVE"
            })
        )
        
        client = CloudAPIClient()
        result = await client.register_agent(
            agent_name="JOB_HUNTER",
            version="2.0.0",
            location="LOCAL",
            trigger_type="TASK_QUEUE",
            capabilities=["job_search", "resume_tailoring"]
        )
        await client.close()
        
        assert result["agent_name"] == "JOB_HUNTER"

    @pytest.mark.asyncio
    @respx.mock
    async def test_send_heartbeat_success(self):
        """Test successful heartbeat."""
        from poller.api_client import CloudAPIClient
        
        respx.post("http://test-api.local/api/v1/agents/heartbeat").mock(
            return_value=httpx.Response(200, json={"success": True})
        )
        
        client = CloudAPIClient()
        result = await client.send_heartbeat(
            agent_name="LOCAL_POLLER",
            status="HEALTHY",
            metrics={"cpu_percent": 25.0}
        )
        await client.close()
        
        assert result is True

    @pytest.mark.asyncio
    @respx.mock
    async def test_send_heartbeat_failure(self):
        """Test heartbeat failure handling."""
        from poller.api_client import CloudAPIClient
        
        respx.post("http://test-api.local/api/v1/agents/heartbeat").mock(
            return_value=httpx.Response(500, json={"detail": "Server error"})
        )
        
        client = CloudAPIClient()
        result = await client.send_heartbeat(
            agent_name="LOCAL_POLLER",
            status="HEALTHY"
        )
        await client.close()
        
        assert result is False

    @pytest.mark.asyncio
    @respx.mock
    async def test_api_client_includes_headers(self):
        """Test that API client includes required headers."""
        from poller.api_client import CloudAPIClient
        from poller.config import get_settings
        settings = get_settings()
        
        request_made = None
        
        def capture_request(request):
            nonlocal request_made
            request_made = request
            return httpx.Response(200, json={"task_id": "t1", "agent_target": "JOB_HUNTER"})
        
        respx.post("http://test-api.local/api/v1/tasks/pickup").mock(side_effect=capture_request)
        
        client = CloudAPIClient()
        await client.pickup_task(["JOB_HUNTER"])
        await client.close()
        
        assert request_made is not None
        assert request_made.headers.get("X-Agent") == settings.agent_name
        assert request_made.headers.get("X-Agent-Token") == settings.agent_token
        assert request_made.headers.get("X-Key-Version") == str(settings.hmac_key_version)
        assert "X-Signature" in request_made.headers
        assert request_made.headers.get("X-Worker-ID") == "TEST_WORKER_01"

