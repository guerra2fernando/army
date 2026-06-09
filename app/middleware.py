"""
Security Middleware
Phase 10: Integration & Polish
"""
from fastapi import Request, HTTPException
from collections import defaultdict
from datetime import datetime, timedelta
import asyncio
from typing import Dict, List

from app.config import get_settings

settings = get_settings()


class RateLimiter:
    """
    Simple in-memory rate limiter.
    
    Tracks requests per identifier (IP or user) and blocks
    requests that exceed the rate limit.
    """
    
    def __init__(self, requests_per_minute: int = 60):
        """
        Initialize rate limiter.
        
        Args:
            requests_per_minute: Maximum requests allowed per minute per identifier
        """
        self.requests_per_minute = requests_per_minute
        self.requests: Dict[str, List[datetime]] = defaultdict(list)
        self._lock = asyncio.Lock()
    
    async def check(self, identifier: str) -> bool:
        """
        Check if a request should be allowed.
        
        Args:
            identifier: Unique identifier for the requester (IP, user ID, etc.)
            
        Returns:
            True if request is allowed, False if rate limited
        """
        async with self._lock:
            now = datetime.utcnow()
            minute_ago = now - timedelta(minutes=1)
            
            # Clean old requests (older than 1 minute)
            self.requests[identifier] = [
                req_time for req_time in self.requests[identifier]
                if req_time > minute_ago
            ]
            
            # Check if over limit
            if len(self.requests[identifier]) >= self.requests_per_minute:
                return False
            
            # Record this request
            self.requests[identifier].append(now)
            return True
    
    def get_remaining(self, identifier: str) -> int:
        """
        Get remaining requests for an identifier.
        
        Args:
            identifier: Unique identifier for the requester
            
        Returns:
            Number of remaining requests allowed
        """
        now = datetime.utcnow()
        minute_ago = now - timedelta(minutes=1)
        
        current_count = len([
            req_time for req_time in self.requests[identifier]
            if req_time > minute_ago
        ])
        
        return max(0, self.requests_per_minute - current_count)


# Default rate limiter instance
rate_limiter = RateLimiter(requests_per_minute=100)


async def rate_limit_middleware(request: Request, call_next):
    """
    Rate limiting middleware for FastAPI.
    
    Args:
        request: The incoming request
        call_next: The next middleware/handler in the chain
        
    Returns:
        Response from the next handler or 429 if rate limited
    """
    # Get identifier (IP or user)
    identifier = request.client.host if request.client else "unknown"
    
    # Check auth header for user-based limiting
    auth_header = request.headers.get("Authorization")
    if auth_header:
        # Use part of token as identifier for authenticated users
        identifier = f"auth:{auth_header[:50]}"
    
    if not await rate_limiter.check(identifier):
        raise HTTPException(
            status_code=429,
            detail="Too many requests. Please slow down.",
            headers={"Retry-After": "60"}
        )
    
    return await call_next(request)


class SecurityHeaders:
    """Add security headers to responses."""
    
    HEADERS = {
        "X-Content-Type-Options": "nosniff",
        "X-Frame-Options": "SAMEORIGIN",
        "X-XSS-Protection": "1; mode=block",
        "Referrer-Policy": "strict-origin-when-cross-origin"
    }
    
    @classmethod
    async def add_headers(cls, request: Request, call_next):
        """Add security headers to response."""
        response = await call_next(request)
        
        for header, value in cls.HEADERS.items():
            response.headers[header] = value
        
        return response


async def mtls_middleware(request: Request, call_next):
    """
    Enforce mutual TLS via upstream-provided client certificate header.
    """
    if not settings.mtls_required:
        return await call_next(request)

    client_cert = request.headers.get("X-Client-Cert")
    if not client_cert:
        raise HTTPException(status_code=401, detail="Client certificate required")

    request.state.client_cert = client_cert
    return await call_next(request)

