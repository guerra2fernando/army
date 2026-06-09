"""
Capability registry for the cloud API.

Stores an allowlist of capabilities and seeds default definitions so that
agent registrations can reference them consistently.
"""
from __future__ import annotations

from datetime import datetime
from typing import List, Dict, Any

from loguru import logger

DEFAULT_CAPABILITIES: List[Dict[str, Any]] = [
    {
        "capability_id": "file_read",
        "name": "file_read",
        "category": "filesystem",
        "description": "Read files from allowed paths",
        "policy": {
            "allowed_paths": ["~/Projects/**", "~/Job_Drafts/**"],
            "blocked_paths": ["~/.ssh/**", "~/secrets/**"],
        },
        "limits": {"daily_quota": None},
        "status": "ACTIVE",
        "created_at": datetime.utcnow(),
        "created_by": "SYSTEM",
    },
    {
        "capability_id": "file_write",
        "name": "file_write",
        "category": "filesystem",
        "description": "Write files to allowed paths",
        "policy": {
            "allowed_paths": ["~/Projects/**", "~/Job_Drafts/**"],
            "blocked_paths": ["~/.ssh/**", "~/secrets/**"],
            "max_file_size_mb": 100,
        },
        "limits": {"daily_quota": 100},
        "status": "ACTIVE",
        "created_at": datetime.utcnow(),
        "created_by": "SYSTEM",
    },
    {
        "capability_id": "directory_create",
        "name": "directory_create",
        "category": "filesystem",
        "description": "Create directories within allowed roots",
        "policy": {"allowed_paths": ["~/Projects/**", "~/Job_Drafts/**"]},
        "limits": {},
        "status": "ACTIVE",
        "created_at": datetime.utcnow(),
        "created_by": "SYSTEM",
    },
    {
        "capability_id": "web_scraping",
        "name": "web_scraping",
        "category": "network",
        "description": "Fetch or scrape web content",
        "policy": {
            "allowed_domains": ["*.linkedin.com", "*.indeed.com", "*.glassdoor.com", "*.com", "*.org"],
            "blocked_domains": [],
            "max_requests_per_minute": 60,
        },
        "limits": {},
        "status": "ACTIVE",
        "created_at": datetime.utcnow(),
        "created_by": "SYSTEM",
    },
    {
        "capability_id": "browser_navigate",
        "name": "browser_navigate",
        "category": "browser",
        "description": "Automate browser navigation within allowlist",
        "policy": {"allowed_domains": ["*.linkedin.com", "*.indeed.com"]},
        "limits": {},
        "status": "ACTIVE",
        "created_at": datetime.utcnow(),
        "created_by": "SYSTEM",
    },
    {
        "capability_id": "command_execute",
        "name": "command_execute",
        "category": "system",
        "description": "Execute approved shell commands",
        "policy": {"extra": {"allowed_commands": "git,npm,python"}},
        "limits": {"daily_quota": 50},
        "status": "ACTIVE",
        "created_at": datetime.utcnow(),
        "created_by": "SYSTEM",
    },
    {
        "capability_id": "file_modify",
        "name": "file_modify",
        "category": "filesystem",
        "description": "Modify existing files in controlled roots",
        "policy": {
            "allowed_paths": ["~/Projects/**", "~/poller/**", "~/agents/**"],
        },
        "limits": {},
        "status": "ACTIVE",
        "created_at": datetime.utcnow(),
        "created_by": "SYSTEM",
    },
]


async def seed_default_capabilities(db) -> None:
    """
    Seed the capability registry with defaults. Best-effort/no-op on failures.

    Args:
        db: Motor database instance
    """
    capabilities = db.capabilities

    for definition in DEFAULT_CAPABILITIES:
        try:
            await capabilities.update_one(
                {"capability_id": definition["capability_id"]},
                {"$setOnInsert": definition},
                upsert=True,
            )
        except Exception as exc:  # pragma: no cover - defensive
            logger.warning(f"Seed capability '{definition['capability_id']}' skipped: {exc}")










