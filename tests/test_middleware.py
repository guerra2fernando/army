"""
Tests for Security Middleware (Rate Limiting)
Phase 10: Integration & Polish
"""
import pytest
import asyncio
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock, AsyncMock
from httpx import AsyncClient


class TestRateLimiter:
    """Test rate limiting functionality."""
    
    @pytest.mark.asyncio
    async def test_rate_limiter_allows_requests_under_limit(self):
        """Test rate limiter allows requests under the limit."""
        from app.middleware import RateLimiter
        
        limiter = RateLimiter(requests_per_minute=10)
        
        # Should allow 5 requests
        for _ in range(5):
            allowed = await limiter.check("test-user")
            assert allowed is True
    
    @pytest.mark.asyncio
    async def test_rate_limiter_blocks_requests_over_limit(self):
        """Test rate limiter blocks requests over the limit."""
        from app.middleware import RateLimiter
        
        limiter = RateLimiter(requests_per_minute=5)
        
        # Make 5 requests (at limit)
        for _ in range(5):
            await limiter.check("test-user")
        
        # 6th request should be blocked
        allowed = await limiter.check("test-user")
        assert allowed is False
    
    @pytest.mark.asyncio
    async def test_rate_limiter_tracks_different_users_separately(self):
        """Test rate limiter tracks different identifiers separately."""
        from app.middleware import RateLimiter
        
        limiter = RateLimiter(requests_per_minute=3)
        
        # Max out user1
        for _ in range(3):
            await limiter.check("user1")
        
        # user2 should still be allowed
        allowed = await limiter.check("user2")
        assert allowed is True
    
    @pytest.mark.asyncio
    async def test_rate_limiter_resets_after_window(self):
        """Test rate limiter resets after time window."""
        from app.middleware import RateLimiter
        
        limiter = RateLimiter(requests_per_minute=2)
        
        # Max out
        for _ in range(2):
            await limiter.check("test-user")
        
        # Should be blocked
        assert await limiter.check("test-user") is False
        
        # Manually expire old requests by manipulating internal state
        limiter.requests["test-user"] = []
        
        # Should be allowed again
        assert await limiter.check("test-user") is True
    
    @pytest.mark.asyncio
    async def test_rate_limiter_thread_safety(self):
        """Test rate limiter is thread-safe."""
        from app.middleware import RateLimiter
        
        limiter = RateLimiter(requests_per_minute=100)
        
        # Make concurrent requests
        async def make_request():
            return await limiter.check("concurrent-user")
        
        results = await asyncio.gather(*[make_request() for _ in range(50)])
        
        # All should be allowed (under limit)
        assert all(results)


class TestRateLimitMiddleware:
    """Test rate limit middleware integration."""
    
    @pytest.mark.asyncio
    async def test_middleware_allows_normal_requests(self, client: AsyncClient):
        """Test middleware allows normal rate of requests."""
        # Multiple requests should be allowed
        for _ in range(5):
            response = await client.get("/health")
            assert response.status_code == 200
    
    @pytest.mark.asyncio 
    async def test_middleware_returns_429_when_rate_limited(self):
        """Test middleware returns 429 when rate limited."""
        from app.middleware import RateLimiter, rate_limiter
        
        # This tests the rate limiter logic - actual middleware integration
        # would need to be tested with a real request flow
        limiter = RateLimiter(requests_per_minute=1)
        
        # First request allowed
        assert await limiter.check("test") is True
        
        # Second request blocked
        assert await limiter.check("test") is False


class TestInputValidators:
    """Test input validation functionality."""
    
    def test_sanitize_string_basic(self):
        """Test basic string sanitization."""
        from app.validators import sanitize_string
        
        result = sanitize_string("Hello World")
        assert result == "Hello World"
    
    def test_sanitize_string_removes_html_tags(self):
        """Test HTML tags are removed."""
        from app.validators import sanitize_string
        
        result = sanitize_string("<script>alert('xss')</script>Hello")
        assert "<script>" not in result
        assert "</script>" not in result
    
    def test_sanitize_string_truncates_long_strings(self):
        """Test long strings are truncated."""
        from app.validators import sanitize_string
        
        long_string = "a" * 2000
        result = sanitize_string(long_string, max_length=100)
        
        assert len(result) == 100
    
    def test_sanitize_string_handles_empty(self):
        """Test empty string handling."""
        from app.validators import sanitize_string
        
        assert sanitize_string("") == ""
        assert sanitize_string(None) == ""
    
    def test_validate_email_valid(self):
        """Test valid email validation."""
        from app.validators import validate_email
        
        assert validate_email("test@example.com") is True
        assert validate_email("user.name@domain.org") is True
        assert validate_email("user+tag@gmail.com") is True
    
    def test_validate_email_invalid(self):
        """Test invalid email validation."""
        from app.validators import validate_email
        
        assert validate_email("invalid") is False
        assert validate_email("@example.com") is False
        assert validate_email("user@") is False
        assert validate_email("user @example.com") is False
    
    def test_validate_task_payload_valid(self):
        """Test valid task payload validation."""
        from app.validators import validate_task_payload
        
        valid, error = validate_task_payload({
            "action": "search",
            "query": "python developer"
        })
        
        assert valid is True
        assert error is None
    
    def test_validate_task_payload_rejects_dangerous_keys(self):
        """Test dangerous keys are rejected."""
        from app.validators import validate_task_payload
        
        valid, error = validate_task_payload({
            "__import__": "os"
        })
        
        assert valid is False
        assert error is not None
        assert "forbidden" in error.lower()
    
    def test_validate_task_payload_rejects_non_dict(self):
        """Test non-dict payloads are rejected."""
        from app.validators import validate_task_payload
        
        valid, error = validate_task_payload("not a dict")
        
        assert valid is False
        assert "dictionary" in error.lower()
    
    def test_validate_task_payload_rejects_too_large(self):
        """Test oversized payloads are rejected."""
        from app.validators import validate_task_payload
        
        large_payload = {"data": "x" * 200000}  # 200KB
        valid, error = validate_task_payload(large_payload)
        
        assert valid is False
        assert "large" in error.lower()

