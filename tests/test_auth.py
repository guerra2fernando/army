"""
Tests for Authentication Endpoints
"""
import pytest
from httpx import AsyncClient

from app.db import Database


class TestUserRegistration:
    """Tests for user registration."""

    @pytest.mark.asyncio
    async def test_register_new_user_success(self, client: AsyncClient):
        """Test successful user registration."""
        response = await client.post(
            "/api/v1/auth/register",
            json={
                "email": "newuser@example.com",
                "password": "securepass123",
                "name": "New User"
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["message"] == "User registered successfully"
        assert "user_id" in data["data"]

    @pytest.mark.asyncio
    async def test_register_duplicate_email_fails(
        self, client: AsyncClient, test_user: dict
    ):
        """Test registration with existing email fails."""
        response = await client.post(
            "/api/v1/auth/register",
            json={
                "email": test_user["email"],
                "password": "password123",
                "name": "Another User"
            }
        )
        
        assert response.status_code == 400
        assert "already registered" in response.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_register_invalid_email_fails(self, client: AsyncClient):
        """Test registration with invalid email fails."""
        response = await client.post(
            "/api/v1/auth/register",
            json={
                "email": "not-an-email",
                "password": "password123",
                "name": "Invalid Email User"
            }
        )
        
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_register_short_password_fails(self, client: AsyncClient):
        """Test registration with short password fails."""
        response = await client.post(
            "/api/v1/auth/register",
            json={
                "email": "short@example.com",
                "password": "short",
                "name": "Short Password User"
            }
        )
        
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_register_missing_fields_fails(self, client: AsyncClient):
        """Test registration with missing fields fails."""
        response = await client.post(
            "/api/v1/auth/register",
            json={"email": "missing@example.com"}
        )
        
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_register_short_name_fails(self, client: AsyncClient):
        """Test registration with too short name fails."""
        response = await client.post(
            "/api/v1/auth/register",
            json={
                "email": "short@example.com",
                "password": "password123",
                "name": "A"  # Too short
            }
        )
        
        assert response.status_code == 422


class TestUserLogin:
    """Tests for user login."""

    @pytest.mark.asyncio
    async def test_login_success(self, client: AsyncClient, test_user: dict):
        """Test successful login returns token."""
        response = await client.post(
            "/api/v1/auth/login",
            json={
                "email": test_user["email"],
                "password": "password123"
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"
        assert "expires_in" in data
        assert "user" in data
        assert data["user"]["email"] == test_user["email"]

    @pytest.mark.asyncio
    async def test_login_wrong_password_fails(
        self, client: AsyncClient, test_user: dict
    ):
        """Test login with wrong password fails."""
        response = await client.post(
            "/api/v1/auth/login",
            json={
                "email": test_user["email"],
                "password": "wrongpassword"
            }
        )
        
        assert response.status_code == 401
        assert "invalid" in response.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_login_nonexistent_user_fails(self, client: AsyncClient):
        """Test login with non-existent user fails."""
        response = await client.post(
            "/api/v1/auth/login",
            json={
                "email": "nobody@example.com",
                "password": "password123"
            }
        )
        
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_login_disabled_user_fails(self, client: AsyncClient):
        """Test login with disabled user fails."""
        # Create disabled user
        users = Database.get_collection("users")
        from app.utils.auth import hash_password
        from uuid import uuid4
        from datetime import datetime
        
        await users.insert_one({
            "_id": str(uuid4()),
            "email": "disabled@example.com",
            "password_hash": hash_password("password123"),
            "name": "Disabled User",
            "is_active": False,
            "is_admin": False,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
        })
        
        response = await client.post(
            "/api/v1/auth/login",
            json={
                "email": "disabled@example.com",
                "password": "password123"
            }
        )
        
        assert response.status_code == 403
        assert "disabled" in response.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_login_updates_last_login(
        self, client: AsyncClient, test_user: dict
    ):
        """Test login updates last_login timestamp."""
        users = Database.get_collection("users")
        
        # Login
        await client.post(
            "/api/v1/auth/login",
            json={
                "email": test_user["email"],
                "password": "password123"
            }
        )
        
        # Check last_login was updated
        user = await users.find_one({"_id": test_user["_id"]})
        assert user["last_login"] is not None


class TestGetCurrentUser:
    """Tests for getting current user info."""

    @pytest.mark.asyncio
    async def test_get_me_success(
        self, client: AsyncClient, test_user: dict, auth_headers: dict
    ):
        """Test getting current user info."""
        response = await client.get("/api/v1/auth/me", headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert data["email"] == test_user["email"]
        assert data["name"] == test_user["name"]
        assert "id" in data
        assert "created_at" in data

    @pytest.mark.asyncio
    async def test_get_me_without_token_fails(self, client: AsyncClient):
        """Test getting current user without token fails."""
        response = await client.get("/api/v1/auth/me")
        assert response.status_code == 403  # FastAPI returns 403 for missing credentials

    @pytest.mark.asyncio
    async def test_get_me_invalid_token_fails(self, client: AsyncClient):
        """Test getting current user with invalid token fails."""
        response = await client.get(
            "/api/v1/auth/me",
            headers={"Authorization": "Bearer invalid-token"}
        )
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_get_me_expired_token_fails(self, client: AsyncClient):
        """Test getting current user with expired token fails."""
        # Create an expired token (would require mocking time or using an actual expired token)
        # For now, we just test invalid format
        response = await client.get(
            "/api/v1/auth/me",
            headers={"Authorization": "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIiwiZXhwIjoxfQ.invalid"}
        )
        assert response.status_code == 401

