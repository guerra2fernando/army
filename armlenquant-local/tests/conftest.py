"""
Test Configuration and Fixtures for Local Poller
"""
import os
import pytest
import asyncio
from typing import AsyncGenerator, Generator
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock

# Set test environment before importing app modules
os.environ["API_URL"] = "http://test-api.local"
os.environ["AGENT_NAME"] = "LOCAL_POLLER"
os.environ["AGENT_TOKEN"] = "test-agent-token"
os.environ["HMAC_KEY"] = "MDEyMzQ1Njc4OWFiY2RlZjAxMjM0NTY3ODlhYmNkZWY="
os.environ["HMAC_KEY_VERSION"] = "1"
os.environ["WORKER_ID"] = "TEST_WORKER_01"
os.environ["POLL_INTERVAL_SECONDS"] = "5"
os.environ["TASK_TIMEOUT_SECONDS"] = "30"
os.environ["HEARTBEAT_INTERVAL_SECONDS"] = "10"
os.environ["TASK_LEASE_DURATION_MINUTES"] = "30"
os.environ["LEASE_RENEWAL_INTERVAL_SECONDS"] = "5"
os.environ["MAX_TASK_RETRIES"] = "3"
os.environ["IDEMPOTENCY_WINDOW_HOURS"] = "1"

# LLM Configuration for tests
os.environ["LLM_PROVIDER"] = "gemini"  # Default to Gemini
os.environ["LLM_AUTO_FALLBACK"] = "true"
os.environ["GEMINI_API_KEY"] = "test-gemini-key"
os.environ["GEMINI_MODEL"] = "gemini-2.0-flash"
os.environ["OPENAI_API_KEY"] = "sk-test-key"
os.environ["OPENAI_MODEL"] = "gpt-4o"

os.environ["LOG_LEVEL"] = "DEBUG"


@pytest.fixture
def mock_api_response_task():
    """Mock task response from cloud API."""
    return {
        "task_id": "test-task-123",
        "agent_target": "JOB_HUNTER",
        "payload": {"action": "search", "query": "python developer"},
        "priority": 5
    }


@pytest.fixture
def mock_api_response_empty():
    """Mock empty response (no tasks)."""
    return None


@pytest.fixture
def mock_health_response():
    """Mock health check response."""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "service": "armlenquant-api"
    }


@pytest.fixture
def sample_task_payload():
    """Sample task payload for testing."""
    return {
        "action": "search",
        "query": "python developer",
        "location": "remote"
    }


@pytest.fixture
def sample_agent_result():
    """Sample agent execution result."""
    return {
        "success": True,
        "data": {
            "jobs_found": 5,
            "matches": ["job1", "job2", "job3"]
        },
        "error": None,
        "execution_time_ms": 1500,
        "timestamp": datetime.utcnow().isoformat()
    }


@pytest.fixture
def mock_llm_response():
    """Mock LLM response for testing."""
    from agents.llm_client import LLMResponse
    
    def _create_response(content: str):
        return LLMResponse(content=content)
    
    return _create_response


@pytest.fixture
def mock_llm_client():
    """Create a mock LLM client for testing."""
    from agents.llm_client import LLMClient, LLMResponse
    
    mock_client = MagicMock(spec=LLMClient)
    mock_client.is_available = True
    mock_client.active_provider = "gemini"
    
    async def mock_chat(*args, **kwargs):
        return LLMResponse(content='{"test": "response"}')
    
    mock_client.chat = AsyncMock(side_effect=mock_chat)
    
    return mock_client

