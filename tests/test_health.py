"""
Tests for Health Endpoints
"""
import pytest
from httpx import AsyncClient


class TestHealthEndpoints:
    """Tests for /health endpoints."""

    @pytest.mark.asyncio
    async def test_health_check_returns_healthy(self, client: AsyncClient):
        """Test basic health check returns healthy status."""
        response = await client.get("/health")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["service"] == "armlenquant-api"
        assert "timestamp" in data

    @pytest.mark.asyncio
    async def test_health_check_no_auth_required(self, client: AsyncClient):
        """Test health check doesn't require authentication."""
        response = await client.get("/health")
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_detailed_health_requires_auth(self, client: AsyncClient):
        """Test detailed health check requires authentication."""
        response = await client.get("/health/detailed")
        assert response.status_code == 403  # FastAPI returns 403 for missing credentials

    @pytest.mark.asyncio
    async def test_detailed_health_with_auth(
        self, client: AsyncClient, test_user: dict, auth_headers: dict
    ):
        """Test detailed health check with valid authentication."""
        response = await client.get("/health/detailed", headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "data" in data
        assert "status" in data["data"]
        assert "database" in data["data"]
        assert "agents" in data["data"]
        assert "task_queue" in data["data"]

    @pytest.mark.asyncio
    async def test_detailed_health_shows_agent_counts(
        self, client: AsyncClient, test_user: dict, auth_headers: dict, test_agent: dict
    ):
        """Test detailed health shows correct agent counts."""
        response = await client.get("/health/detailed", headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert data["data"]["agents"]["total"] >= 1
        assert data["data"]["agents"]["active"] >= 1

    @pytest.mark.asyncio
    async def test_detailed_health_shows_task_counts(
        self, client: AsyncClient, test_user: dict, auth_headers: dict, test_task: dict
    ):
        """Test detailed health shows correct task counts."""
        response = await client.get("/health/detailed", headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert data["data"]["task_queue"]["pending"] >= 1


class TestRootEndpoint:
    """Tests for root endpoint."""

    @pytest.mark.asyncio
    async def test_root_returns_api_info(self, client: AsyncClient):
        """Test root endpoint returns API information."""
        response = await client.get("/")
        
        assert response.status_code == 200
        data = response.json()
        assert "name" in data
        assert "version" in data
        assert data["status"] == "running"
        assert data["docs"] == "/docs"


class TestCORS:
    """Production CORS must be an explicit origin allowlist."""

    @pytest.mark.asyncio
    async def test_configured_dashboard_origin_is_allowed(self, client: AsyncClient):
        response = await client.get(
            "/health",
            headers={"Origin": "https://army.lengrowth.com"},
        )
        assert response.status_code == 200
        assert response.headers["access-control-allow-origin"] == "https://army.lengrowth.com"
        assert response.headers["access-control-allow-credentials"] == "true"

    @pytest.mark.asyncio
    async def test_unrelated_origin_is_rejected(self, client: AsyncClient):
        response = await client.get(
            "/health",
            headers={"Origin": "https://unrelated.example"},
        )
        assert response.status_code == 200
        assert "access-control-allow-origin" not in response.headers

