"""
Tests for Global Error Handling
Phase 10: Integration & Polish
"""
import pytest
from datetime import datetime
from unittest.mock import patch, MagicMock, AsyncMock
from fastapi import HTTPException
from httpx import AsyncClient

from app.db import Database


class TestGlobalExceptionHandler:
    """Test global exception handling in the API."""
    
    @pytest.mark.asyncio
    async def test_http_exceptions_preserve_status_code(self, client: AsyncClient):
        """Test that HTTP exceptions preserve their status codes."""
        # Attempt to access protected route without auth
        response = await client.get("/api/v1/auth/me")
        
        assert response.status_code == 403  # Forbidden without bearer token
    
    @pytest.mark.asyncio
    async def test_validation_errors_return_422(self, client: AsyncClient, auth_headers: dict):
        """Test that validation errors return 422."""
        # Send invalid data
        response = await client.post(
            "/api/v1/tasks",
            headers=auth_headers,
            json={"invalid_field": "value"}  # Missing required fields
        )
        
        assert response.status_code == 422
    
    @pytest.mark.asyncio
    async def test_404_for_nonexistent_routes(self, client: AsyncClient):
        """Test 404 for non-existent routes."""
        response = await client.get("/api/v1/nonexistent")
        
        assert response.status_code == 404
    
    @pytest.mark.asyncio
    async def test_global_exception_handler_exists(self, client: AsyncClient):
        """Test that the global exception handler is configured."""
        from app.main import app
        
        # Verify exception handler is registered
        assert Exception in app.exception_handlers


class TestHTTPExceptionResponses:
    """Test specific HTTP exception responses."""
    
    @pytest.mark.asyncio
    async def test_unauthorized_without_token(self, client: AsyncClient):
        """Test 403 when no token provided to protected route."""
        response = await client.get("/api/v1/tasks")
        
        assert response.status_code == 403
    
    @pytest.mark.asyncio
    async def test_unauthorized_with_invalid_token(self, client: AsyncClient):
        """Test 401 with invalid token."""
        headers = {"Authorization": "Bearer invalid-token"}
        response = await client.get("/api/v1/tasks", headers=headers)
        
        assert response.status_code == 401
    
    @pytest.mark.asyncio
    async def test_not_found_for_missing_task(self, client: AsyncClient, auth_headers: dict):
        """Test 404 for non-existent task."""
        response = await client.get(
            "/api/v1/tasks/nonexistent-task-id",
            headers=auth_headers
        )
        
        assert response.status_code == 404
    
    @pytest.mark.asyncio
    async def test_bad_request_for_invalid_agent_target(self, client: AsyncClient, auth_headers: dict):
        """Test 422 for invalid agent target."""
        response = await client.post(
            "/api/v1/tasks",
            headers=auth_headers,
            json={
                "agent_target": "INVALID_AGENT",
                "payload": {},
                "priority": 5
            }
        )
        
        assert response.status_code == 422


class TestErrorResponseFormat:
    """Test error response format consistency."""
    
    @pytest.mark.asyncio
    async def test_error_response_has_required_fields(self, client: AsyncClient):
        """Test that error responses have consistent structure."""
        response = await client.get("/api/v1/nonexistent")
        
        data = response.json()
        assert "detail" in data or "error" in data or "message" in data
    
    @pytest.mark.asyncio
    async def test_validation_error_includes_details(self, client: AsyncClient, auth_headers: dict):
        """Test validation errors include field details."""
        response = await client.post(
            "/api/v1/tasks",
            headers=auth_headers,
            json={}  # Empty payload
        )
        
        assert response.status_code == 422
        data = response.json()
        assert "detail" in data

