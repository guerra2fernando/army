"""
Security utilities for mTLS, HMAC request signing, scoped tokens, and
secret rotation.
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import time
from collections import defaultdict
from datetime import datetime, timedelta
from typing import Callable, Dict, List, Optional
from uuid import uuid4

from fastapi import HTTPException, Request, status
from passlib.context import CryptContext

from app.config import get_settings
from app.db import Database

settings = get_settings()

# Bcrypt for scoped tokens
# Use PBKDF2 for token hashing to avoid native bcrypt dependency
token_context = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")

# In-memory nonce cache to prevent simple replay attacks within the grace window
_nonce_cache: Dict[str, Dict[str, float]] = defaultdict(dict)


def _cleanup_nonces(agent_name: str) -> None:
    """Drop expired nonces for an agent based on grace period."""
    now = time.time()
    grace = settings.signature_grace_period_seconds
    cache = _nonce_cache[agent_name]
    for nonce, ts in list(cache.items()):
        if now - ts > grace:
            cache.pop(nonce, None)


async def _register_nonce(agent_name: str, nonce: str, timestamp: float) -> bool:
    """Register nonce and detect replay attempts."""
    _cleanup_nonces(agent_name)
    cache = _nonce_cache[agent_name]
    if nonce in cache:
        return False
    cache[nonce] = timestamp
    return True


def _build_signing_string(method: str, path: str, timestamp: str, nonce: str, body: str) -> str:
    """Create deterministic signing string."""
    return f"{method.upper()}\n{path}\n{timestamp}\n{nonce}\n{body}"


async def get_active_secret(agent_name: str, key_version: Optional[int] = None) -> dict:
    """Fetch the active secret for an agent (optionally by version)."""
    secrets = Database.get_collection("secrets")
    query: Dict[str, object] = {"agent_name": agent_name, "status": "ACTIVE"}
    if key_version is not None:
        query["key_version"] = key_version

    secret = await secrets.find_one(query, sort=[("key_version", -1)])
    if not secret:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="No active signing key found",
        )
    return secret


async def verify_request_signature(request: Request, body: str) -> dict:
    """
    Verify HMAC signature headers and return agent context.
    """
    headers = request.headers
    required_headers = [
        "X-Agent",
        "X-Timestamp",
        "X-Nonce",
        "X-Signature",
        "X-Key-Version",
    ]
    missing = [h for h in required_headers if h not in headers]
    if missing:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Missing auth headers: {', '.join(missing)}",
        )

    agent_name = headers["X-Agent"]
    try:
        timestamp = float(headers["X-Timestamp"])
    except ValueError:
        raise HTTPException(status_code=401, detail="Invalid timestamp")  # noqa: B904

    if abs(time.time() - timestamp) > settings.signature_grace_period_seconds:
        raise HTTPException(status_code=401, detail="Signature expired")

    nonce = headers["X-Nonce"]
    if not await _register_nonce(agent_name, nonce, timestamp):
        raise HTTPException(status_code=409, detail="Replay detected")

    key_version = int(headers["X-Key-Version"])
    secret = await get_active_secret(agent_name, key_version)

    signing_string = _build_signing_string(
        request.method,
        request.url.path,
        headers["X-Timestamp"],
        nonce,
        body,
    )
    expected_signature = hmac.new(
        base64.b64decode(secret["hmac_key"]),
        signing_string.encode(),
        hashlib.sha256,
    ).hexdigest()

    supplied_signature = headers["X-Signature"]
    if not hmac.compare_digest(expected_signature, supplied_signature):
        # Accept the canonical JSON representation used by the signed client
        # when an intermediary/client reformats an equivalent JSON body.
        try:
            canonical_body = json.dumps(json.loads(body), separators=(",", ":"), sort_keys=False)
        except (TypeError, ValueError):
            canonical_body = body
        canonical_string = _build_signing_string(
            request.method,
            request.url.path,
            headers["X-Timestamp"],
            nonce,
            canonical_body,
        )
        canonical_signature = hmac.new(
            base64.b64decode(secret["hmac_key"]),
            canonical_string.encode(),
            hashlib.sha256,
        ).hexdigest()
        if not hmac.compare_digest(canonical_signature, supplied_signature):
            raise HTTPException(status_code=401, detail="Invalid signature")

    return {
        "agent_name": agent_name,
        "key_version": secret["key_version"],
        "secret_id": secret["secret_id"],
    }


async def validate_scoped_token(
    agent_name: str,
    token: str,
    required_scopes: List[str],
    client_ip: Optional[str],
    user_agent: Optional[str],
) -> dict:
    """Validate scoped token against access control rules."""
    tokens = Database.get_collection("access_tokens")

    cursor = tokens.find(
        {"agent_name": agent_name, "status": "ACTIVE"},
        sort=[("created_at", -1)],
    )
    token_docs = await cursor.to_list(length=None)

    matched = next((doc for doc in token_docs if token_context.verify(token, doc["token_hash"])), None)
    if not matched:
        raise HTTPException(status_code=401, detail="Invalid agent token")

    now = datetime.utcnow()
    if matched.get("expires_at") and now > matched["expires_at"]:
        raise HTTPException(status_code=401, detail="Token expired")

    max_uses = matched.get("max_uses") or settings.max_token_uses
    current_uses = matched.get("current_uses", 0)
    if max_uses and current_uses >= max_uses:
        raise HTTPException(status_code=401, detail="Token usage limit reached")

    ip_restrictions = matched.get("ip_restrictions") or []
    if ip_restrictions and client_ip not in ip_restrictions:
        raise HTTPException(status_code=403, detail="IP not allowed for token")

    # Scoped capabilities
    scopes = matched.get("scopes", [])
    if any(scope not in scopes for scope in required_scopes):
        raise HTTPException(status_code=403, detail="Missing required scope")

    denied = matched.get("denied_capabilities", [])
    for scope in required_scopes:
        for deny in denied:
            if scope.startswith((deny.split(":")[0])):
                raise HTTPException(status_code=403, detail="Capability denied")

    await tokens.update_one(
        {"token_id": matched["token_id"]},
        {
            "$inc": {"current_uses": 1},
            "$set": {"last_used": now},
        },
    )
    return matched


async def verify_agent_request(request: Request, required_scopes: List[str]) -> dict:
    """Combined HMAC signature + scoped token verification."""
    raw_body = await request.body()
    body_str = raw_body.decode("utf-8") if raw_body else ""

    signature_context = await verify_request_signature(request, body_str)

    token = request.headers.get("X-Agent-Token")
    if not token:
        raise HTTPException(status_code=401, detail="Agent token required")

    client_ip = request.client.host if request.client else None
    token_context_doc = await validate_scoped_token(
        signature_context["agent_name"],
        token,
        required_scopes,
        client_ip=client_ip,
        user_agent=request.headers.get("User-Agent"),
    )

    request.state.agent_identity = {
        "agent_name": signature_context["agent_name"],
        "key_version": signature_context["key_version"],
        "token_id": token_context_doc["token_id"],
    }
    return request.state.agent_identity


def require_agent_security(required_scopes: List[str]) -> Callable:
    """Dependency factory for agent-facing endpoints."""

    async def _dependency(request: Request):
        return await verify_agent_request(request, required_scopes)

    return _dependency


def build_signed_headers(
    *,
    agent_name: str,
    hmac_key: str,
    key_version: int,
    token: str,
    method: str,
    path: str,
    body: str = "",
    extra: Optional[Dict[str, str]] = None,
) -> Dict[str, str]:
    """
    Helper to build signed headers (used by poller and tests).
    """
    timestamp = str(int(time.time()))
    nonce = str(uuid4())
    signing_string = _build_signing_string(method, path, timestamp, nonce, body)
    signature = hmac.new(
        base64.b64decode(hmac_key),
        signing_string.encode(),
        hashlib.sha256,
    ).hexdigest()

    headers = {
        "Content-Type": "application/json",
        "X-Agent": agent_name,
        "X-Timestamp": timestamp,
        "X-Nonce": nonce,
        "X-Signature": signature,
        "X-Key-Version": str(key_version),
        "X-Agent-Token": token,
    }
    if extra:
        headers.update(extra)
    return headers


async def seed_agent_credentials(
    *,
    agent_name: str,
    hmac_key: str,
    token: str,
    key_version: int = 1,
    expires_at: Optional[datetime] = None,
) -> dict:
    """
    Create or upsert secrets and scoped token for an agent (used in tests/bootstrap).
    """
    secrets = Database.get_collection("secrets")
    access_tokens = Database.get_collection("access_tokens")

    secret_doc = {
        "secret_id": str(uuid4()),
        "agent_name": agent_name,
        "key_version": key_version,
        "hmac_key": hmac_key,
        "created_at": datetime.utcnow(),
        "expires_at": expires_at or datetime.utcnow() + timedelta(days=settings.secret_rotation_days),
        "status": "ACTIVE",
    }
    await secrets.update_one(
        {"agent_name": agent_name, "key_version": key_version},
        {"$set": secret_doc},
        upsert=True,
    )

    token_doc = {
        "token_id": str(uuid4()),
        "token_hash": token_context.hash(token),
        "agent_name": agent_name,
        "scopes": [
            "task:read",
            "task:update",
            "task:lease",
            "agent:register",
            "agent:heartbeat",
            "agent:read",
            "workflow:read",
            "workflow:update",
        ],
        "denied_capabilities": [],
        "expires_at": datetime.utcnow() + timedelta(hours=settings.token_expiry_hours),
        "max_uses": settings.max_token_uses,
        "current_uses": 0,
        "ip_restrictions": [],
        "created_at": datetime.utcnow(),
        "last_used": None,
        "status": "ACTIVE",
    }
    await access_tokens.update_one(
        {"agent_name": agent_name},
        {"$set": token_doc},
        upsert=True,
    )

    return {"secret": secret_doc, "token": token_doc}


class SecretRotationService:
    """Rotate HMAC keys and clean up expired secrets."""

    def __init__(self):
        self.secrets = Database.get_collection("secrets")

    async def rotate_secrets(self):
        agents = Database.get_collection("agent_registry")
        registered = await agents.find({"location": "LOCAL"}).to_list(length=None)

        for agent in registered:
            new_key = base64.b64encode(os.urandom(32)).decode()
            current_version = agent.get("current_key_version", 0)
            key_version = current_version + 1
            secret_doc = {
                "secret_id": str(uuid4()),
                "agent_name": agent["agent_name"],
                "key_version": key_version,
                "hmac_key": new_key,
                "created_at": datetime.utcnow(),
                "expires_at": datetime.utcnow() + timedelta(days=settings.secret_rotation_days),
                "status": "ACTIVE",
            }
            await self.secrets.insert_one(secret_doc)

            await self.secrets.update_many(
                {
                    "agent_name": agent["agent_name"],
                    "status": "ACTIVE",
                    "key_version": {"$lt": key_version},
                },
                {"$set": {"status": "EXPIRED"}},
            )

            await agents.update_one(
                {"agent_name": agent["agent_name"]},
                {"$set": {"current_key_version": key_version}},
            )

    async def cleanup_expired_secrets(self):
        grace_period = datetime.utcnow() - timedelta(days=settings.key_overlap_days)
        await self.secrets.delete_many(
            {
                "status": "EXPIRED",
                "expires_at": {"$lt": grace_period},
            }
        )
