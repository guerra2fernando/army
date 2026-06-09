"""
Test Configuration and Fixtures
"""
import os
import pytest
import asyncio
from typing import AsyncGenerator, Generator
from datetime import datetime
from uuid import uuid4

# Set test environment before importing app modules
os.environ["MONGODB_URI"] = "mongodb://localhost:27017"
os.environ["MONGODB_DB_NAME"] = "armlenquant_test"
os.environ["JWT_SECRET"] = "test-super-secret-jwt-key-for-testing-purposes"
os.environ["AGENT_SECRET"] = "test-agent-secret-key"
os.environ["MTLS_REQUIRED"] = "false"
os.environ["SIGNATURE_GRACE_PERIOD_SECONDS"] = "300"
os.environ["TOKEN_EXPIRY_HOURS"] = "24"
os.environ["OPENAI_API_KEY"] = "sk-test-key"
os.environ["COINGECKO_API_KEY"] = ""
os.environ["CRYPTOPANIC_API_KEY"] = ""
os.environ["DEBUG"] = "true"
os.environ["TASK_LEASE_DURATION_MINUTES"] = "30"
os.environ["MAX_TASK_RETRIES"] = "3"
os.environ["IDEMPOTENCY_WINDOW_HOURS"] = "1"
os.environ["LEASE_RENEWAL_INTERVAL_SECONDS"] = "60"

import base64
import json
from typing import Optional
from httpx import AsyncClient, ASGITransport
from mongomock_motor import AsyncMongoMockClient

from app.main import app
from app.db import Database
from app.utils.auth import hash_password, create_access_token
from app.utils.security import build_signed_headers, seed_agent_credentials


@pytest.fixture(scope="session")
def event_loop() -> Generator:
    """Create an event loop for the session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(autouse=True)
async def setup_database():
    """Set up mock database for each test."""
    # Use mongomock for testing
    Database.client = AsyncMongoMockClient()
    Database.db = Database.client["armlenquant_test"]
    
    # Initialize collections (without indexes for mock)
    yield
    
    # Cleanup after test
    if Database.client:
        # Drop all collections
        for collection_name in await Database.db.list_collection_names():
            await Database.db[collection_name].drop()


@pytest.fixture
async def client() -> AsyncGenerator[AsyncClient, None]:
    """Create async test client."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.fixture
async def test_user() -> dict:
    """Create a test user in the database."""
    users = Database.get_collection("users")
    
    user_id = str(uuid4())
    user_doc = {
        "_id": user_id,
        "email": "test@example.com",
        "password_hash": hash_password("password123"),
        "name": "Test User",
        "is_active": True,
        "is_admin": False,
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow(),
    }
    
    await users.insert_one(user_doc)
    return user_doc


@pytest.fixture
async def admin_user() -> dict:
    """Create an admin user in the database."""
    users = Database.get_collection("users")
    
    user_id = str(uuid4())
    user_doc = {
        "_id": user_id,
        "email": "admin@example.com",
        "password_hash": hash_password("adminpass123"),
        "name": "Admin User",
        "is_active": True,
        "is_admin": True,
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow(),
    }
    
    await users.insert_one(user_doc)
    return user_doc


@pytest.fixture
def auth_token(test_user: dict) -> str:
    """Get JWT token for test user."""
    token, _ = create_access_token(
        user_id=test_user["_id"],
        email=test_user["email"],
        is_admin=test_user["is_admin"]
    )
    return token


@pytest.fixture
def admin_token(admin_user: dict) -> str:
    """Get JWT token for admin user."""
    token, _ = create_access_token(
        user_id=admin_user["_id"],
        email=admin_user["email"],
        is_admin=admin_user["is_admin"]
    )
    return token


@pytest.fixture
def auth_headers(auth_token: str) -> dict:
    """Get authorization headers for test user."""
    return {"Authorization": f"Bearer {auth_token}"}


@pytest.fixture
def admin_headers(admin_token: str) -> dict:
    """Get authorization headers for admin user."""
    return {"Authorization": f"Bearer {admin_token}"}


@pytest.fixture
async def agent_credentials() -> dict:
    """Seed HMAC key and scoped token for agent traffic."""
    agent_name = "LOCAL_POLLER"
    hmac_key = base64.b64encode(b"0123456789abcdef0123456789abcdef").decode()
    token = "test-agent-token"
    key_version = 1
    await seed_agent_credentials(
        agent_name=agent_name,
        hmac_key=hmac_key,
        token=token,
        key_version=key_version,
    )
    return {
        "agent_name": agent_name,
        "hmac_key": hmac_key,
        "token": token,
        "key_version": key_version,
    }


@pytest.fixture
def agent_headers(agent_credentials) -> callable:
    """Build signed agent headers for a given request."""

    def _build(method: str, path: str, body: object = None, extra: Optional[dict] = None) -> dict:
        body_str = (
            json.dumps(body, separators=(",", ":"), sort_keys=False)
            if isinstance(body, dict)
            else (body or "")
        )
        return build_signed_headers(
            agent_name=agent_credentials["agent_name"],
            hmac_key=agent_credentials["hmac_key"],
            key_version=agent_credentials["key_version"],
            token=agent_credentials["token"],
            method=method,
            path=path,
            body=body_str,
            extra=extra,
        )

    return _build


@pytest.fixture
async def test_task(test_user: dict) -> dict:
    """Create a test task in the database."""
    tasks = Database.get_collection("task_queue")
    
    task_id = str(uuid4())
    idem_key = f"JOB_HUNTER-{task_id}"
    task_doc = {
        "_id": task_id,
        "task_id": task_id,
        "idempotency_key": idem_key,
        "agent_target": "JOB_HUNTER",
        "payload": {"action": "search", "query": "python developer"},
        "title": "search: python developer",
        "status": "PENDING",
        "priority": 5,
        "worker_id": None,
        "picked_up_by": None,
        "lease_until": None,
        "last_execution_started": None,
        "execution_count": 0,
        "retry_count": 0,
        "max_retries": 3,
        "error_log": [],
        "result": None,
        "created_by": test_user["_id"],
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow(),
    }
    
    await tasks.insert_one(task_doc)
    return task_doc


@pytest.fixture
async def test_agent() -> dict:
    """Create a test agent in the database."""
    agents = Database.get_collection("agent_registry")
    
    agent_id = str(uuid4())
    agent_doc = {
        "_id": agent_id,
        "agent_id": agent_id,
        "agent_name": "TEST_AGENT",
        "version": "1.0.0",
        "location": "LOCAL",
        "trigger_type": "TASK_QUEUE",
        "trigger_config": None,
        "capabilities": ["test", "example"],
        "code_path": "/path/to/agent",
        "status": "ACTIVE",
        "performance": {
            "success_rate": 1.0,
            "total_runs": 10,
            "failed_runs": 0,
            "avg_execution_time_ms": 500,
            "last_run_at": None,
            "last_error": None,
        },
        "created_by": "SYSTEM",
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow(),
    }
    
    await agents.insert_one(agent_doc)
    return agent_doc

