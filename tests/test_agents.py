"""
Tests for Agent Registry Endpoints
"""
import pytest
from httpx import AsyncClient
from datetime import datetime

from app.db import Database


class TestAgentRegistration:
    """Tests for agent registration."""

    @pytest.mark.asyncio
    async def test_register_new_agent_success(
        self, client: AsyncClient, agent_headers
    ):
        """Test successful new agent registration."""
        payload = {
            "agent_name": "NEW_TEST_AGENT",
            "version": "1.0.0",
            "location": "LOCAL",
            "trigger_type": "TASK_QUEUE",
            "capabilities": ["testing", "example"]
        }
        response = await client.post(
            "/api/v1/agents/register",
            json=payload,
            headers=agent_headers("POST", "/api/v1/agents/register", payload),
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "agent_id" in data
        assert data["agent_name"] == "NEW_TEST_AGENT"
        assert data["version"] == "1.0.0"
        assert data["location"] == "LOCAL"
        assert data["status"] == "ACTIVE"

    @pytest.mark.asyncio
    async def test_register_updates_existing_agent(
        self, client: AsyncClient, test_agent: dict, agent_headers
    ):
        """Test that registering existing agent updates it."""
        payload = {
            "agent_name": test_agent["agent_name"],
            "version": "2.0.0",  # Updated version
            "location": "CLOUD",
            "trigger_type": "CRON",
            "capabilities": ["updated", "capabilities"]
        }
        response = await client.post(
            "/api/v1/agents/register",
            json=payload,
            headers=agent_headers("POST", "/api/v1/agents/register", payload),
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["version"] == "2.0.0"
        assert data["location"] == "CLOUD"

    @pytest.mark.asyncio
    async def test_register_without_agent_secret_fails(self, client: AsyncClient):
        """Test registration without agent secret fails."""
        response = await client.post(
            "/api/v1/agents/register",
            json={
                "agent_name": "UNAUTHORIZED_AGENT",
                "version": "1.0.0",
                "location": "LOCAL",
                "trigger_type": "TASK_QUEUE"
            }
        )
        
        assert response.status_code == 401  # Missing security headers

    @pytest.mark.asyncio
    async def test_register_invalid_location(
        self, client: AsyncClient, agent_headers
    ):
        """Test registration with invalid location fails."""
        payload = {
            "agent_name": "BAD_AGENT",
            "version": "1.0.0",
            "location": "INVALID_LOCATION",
            "trigger_type": "TASK_QUEUE"
        }
        response = await client.post(
            "/api/v1/agents/register",
            json=payload,
            headers=agent_headers("POST", "/api/v1/agents/register", payload),
        )
        
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_register_invalid_trigger_type(
        self, client: AsyncClient, agent_headers
    ):
        """Test registration with invalid trigger type fails."""
        payload = {
            "agent_name": "BAD_AGENT",
            "version": "1.0.0",
            "location": "LOCAL",
            "trigger_type": "INVALID_TRIGGER"
        }
        response = await client.post(
            "/api/v1/agents/register",
            json=payload,
            headers=agent_headers("POST", "/api/v1/agents/register", payload),
        )
        
        assert response.status_code == 422


class TestListAgents:
    """Tests for listing agents."""

    @pytest.mark.asyncio
    async def test_list_agents_success(
        self, client: AsyncClient, test_user: dict, auth_headers: dict, test_agent: dict
    ):
        """Test listing all agents."""
        response = await client.get("/api/v1/agents", headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 1
        
        # Check agent structure
        agent = data[0]
        assert "agent_id" in agent
        assert "agent_name" in agent
        assert "status" in agent
        assert "performance" in agent

    @pytest.mark.asyncio
    async def test_list_agents_without_auth_fails(self, client: AsyncClient):
        """Test listing agents without authentication fails."""
        response = await client.get("/api/v1/agents")
        assert response.status_code == 403  # FastAPI returns 403 for missing credentials

    @pytest.mark.asyncio
    async def test_list_agents_returns_performance_metrics(
        self, client: AsyncClient, test_user: dict, auth_headers: dict, test_agent: dict
    ):
        """Test that agent list includes performance metrics."""
        response = await client.get("/api/v1/agents", headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        agent = next(a for a in data if a["agent_name"] == test_agent["agent_name"])
        
        assert "performance" in agent
        assert "success_rate" in agent["performance"]
        assert "total_runs" in agent["performance"]


class TestAgentHeartbeat:
    """Tests for agent heartbeat."""

    @pytest.mark.asyncio
    async def test_heartbeat_success(
        self, client: AsyncClient, test_agent: dict, agent_headers
    ):
        """Test successful heartbeat."""
        payload = {
            "agent_name": test_agent["agent_name"],
            "worker_id": "WORKER_01",
            "status": "HEALTHY"
        }
        response = await client.post(
            "/api/v1/agents/heartbeat",
            json=payload,
            headers=agent_headers("POST", "/api/v1/agents/heartbeat", payload),
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["message"] == "Heartbeat received"

    @pytest.mark.asyncio
    async def test_heartbeat_updates_agent_status(
        self, client: AsyncClient, test_agent: dict, agent_headers
    ):
        """Test that heartbeat updates agent status."""
        payload = {
            "agent_name": test_agent["agent_name"],
            "worker_id": "WORKER_01",
            "status": "HEALTHY"
        }
        await client.post(
            "/api/v1/agents/heartbeat",
            json=payload,
            headers=agent_headers("POST", "/api/v1/agents/heartbeat", payload),
        )
        
        # Verify agent was updated
        agents = Database.get_collection("agent_registry")
        agent = await agents.find_one({"agent_name": test_agent["agent_name"]})
        assert agent["status"] == "ACTIVE"
        assert agent["performance"]["last_run_at"] is not None

    @pytest.mark.asyncio
    async def test_heartbeat_with_task_info(
        self, client: AsyncClient, test_agent: dict, agent_headers
    ):
        """Test heartbeat with current task information."""
        payload = {
            "agent_name": test_agent["agent_name"],
            "worker_id": "WORKER_01",
            "status": "HEALTHY",
            "current_task": "task-123",
            "metrics": {"cpu_usage": 45.2, "memory_mb": 512},
        }
        response = await client.post(
            "/api/v1/agents/heartbeat",
            json=payload,
            headers=agent_headers("POST", "/api/v1/agents/heartbeat", payload),
        )
        
        assert response.status_code == 200
        
        # Verify health record stored
        health = Database.get_collection("system_health")
        record = await health.find_one({
            "type": "agent_heartbeat",
            "agent_name": test_agent["agent_name"]
        })
        assert record is not None
        assert record["current_task"] == "task-123"
        assert record["metrics"]["cpu_usage"] == 45.2

    @pytest.mark.asyncio
    async def test_heartbeat_without_agent_secret_fails(self, client: AsyncClient):
        """Test heartbeat without agent secret fails."""
        response = await client.post(
            "/api/v1/agents/heartbeat",
            json={
                "agent_name": "TEST_AGENT",
                "worker_id": "WORKER_01",
                "status": "HEALTHY"
            }
        )
        
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_unhealthy_heartbeat_marks_agent_failed(
        self, client: AsyncClient, test_agent: dict, agent_headers
    ):
        """Test that unhealthy heartbeat marks agent as FAILED."""
        payload = {
            "agent_name": test_agent["agent_name"],
            "worker_id": "WORKER_01",
            "status": "FAILED"
        }
        await client.post(
            "/api/v1/agents/heartbeat",
            json=payload,
            headers=agent_headers("POST", "/api/v1/agents/heartbeat", payload),
        )
        
        agents = Database.get_collection("agent_registry")
        agent = await agents.find_one({"agent_name": test_agent["agent_name"]})
        assert agent["status"] == "FAILED"


class TestUpdateAgentStatus:
    """Tests for updating agent status."""

    @pytest.mark.asyncio
    async def test_update_agent_status_success(
        self, client: AsyncClient, test_user: dict, auth_headers: dict, test_agent: dict
    ):
        """Test updating agent status."""
        response = await client.patch(
            f"/api/v1/agents/{test_agent['agent_name']}/status?status=PAUSED",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

    @pytest.mark.asyncio
    async def test_update_nonexistent_agent_fails(
        self, client: AsyncClient, test_user: dict, auth_headers: dict
    ):
        """Test updating non-existent agent returns 404."""
        response = await client.patch(
            "/api/v1/agents/NONEXISTENT_AGENT/status?status=PAUSED",
            headers=auth_headers
        )
        
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_update_agent_status_without_auth_fails(
        self, client: AsyncClient, test_agent: dict
    ):
        """Test updating agent status without authentication fails."""
        response = await client.patch(
            f"/api/v1/agents/{test_agent['agent_name']}/status?status=PAUSED"
        )
        
        assert response.status_code == 403  # FastAPI returns 403 for missing credentials

    @pytest.mark.asyncio
    async def test_update_agent_invalid_status(
        self, client: AsyncClient, test_user: dict, auth_headers: dict, test_agent: dict
    ):
        """Test updating agent with invalid status fails."""
        response = await client.patch(
            f"/api/v1/agents/{test_agent['agent_name']}/status?status=INVALID_STATUS",
            headers=auth_headers
        )
        
        assert response.status_code == 422

