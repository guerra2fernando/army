"""
Capability enforcement layer for local agents.
Implements an allowlist-first sandbox with policy and quota checks.
"""
from __future__ import annotations

import fnmatch
from datetime import datetime, timedelta
from pathlib import Path
from typing import Callable, Dict, List, Optional, Awaitable, Any
from urllib.parse import urlparse

from loguru import logger

from models.capability import (
    CapabilityDefinition,
    CapabilityGrant,
    CapabilityLimits,
    CapabilityPolicy,
)


class CapabilityError(Exception):
    """Raised when a capability policy is violated or missing."""


class QuotaExceededError(CapabilityError):
    """Raised when a capability exceeds its configured limits."""


class UsageTracker:
    """Simple in-memory usage tracker."""

    def __init__(self):
        self.usage: Dict[str, Dict[str, List[datetime]]] = {}

    def _trim_old(self, agent: str, capability: str):
        """Remove entries older than 24h for daily quotas."""
        if agent not in self.usage or capability not in self.usage[agent]:
            return
        cutoff = datetime.utcnow() - timedelta(days=1)
        self.usage[agent][capability] = [
            ts for ts in self.usage[agent][capability] if ts >= cutoff
        ]

    async def check_limits(
        self,
        agent_name: str,
        capability: str,
        grant: CapabilityGrant,
        definition: CapabilityDefinition,
    ) -> bool:
        """Validate quota before execution."""
        limits = grant.limits_override or definition.limits
        if not limits:
            return True

        self._trim_old(agent_name, capability)
        daily_usage = len(self.usage.get(agent_name, {}).get(capability, []))

        if limits.daily_quota is not None and daily_usage >= limits.daily_quota:
            return False

        return True

    async def record_usage(self, agent_name: str, capability: str) -> None:
        """Record a usage event."""
        self.usage.setdefault(agent_name, {}).setdefault(capability, [])
        self.usage[agent_name][capability].append(datetime.utcnow())


def _resolve_path(path: str | Path) -> Path:
    return Path(path).expanduser().resolve()


def _match_path(path: Path, patterns: List[str]) -> bool:
    resolved = str(path)
    for pattern in patterns:
        expanded = str(_resolve_path(pattern)) if pattern.startswith("~") else pattern
        if fnmatch.fnmatch(resolved, expanded) or fnmatch.fnmatchcase(resolved, expanded):
            return True
    return False


def _match_domain(url: str, allowed: List[str], blocked: List[str]) -> bool:
    parsed = urlparse(url)
    hostname = parsed.hostname or ""
    if not hostname:
        return False

    # Block list takes precedence
    if blocked:
        for domain in blocked:
            if fnmatch.fnmatch(hostname, domain):
                return False

    if not allowed:
        return True

    for domain in allowed:
        if fnmatch.fnmatch(hostname, domain):
            return True
    return False


class CapabilityManager:
    """Registers capabilities and enforces policy/limits."""

    def __init__(self, definitions: Optional[List[CapabilityDefinition]] = None):
        self.capabilities: Dict[str, CapabilityDefinition] = {}
        self.agent_grants: Dict[str, List[CapabilityGrant]] = {}
        self.usage_tracker = UsageTracker()
        if definitions:
            for definition in definitions:
                self.capabilities[definition.capability_id] = definition
        else:
            self._load_default_capabilities()

    # ------------------------------------------------------------------ #
    # Registration
    # ------------------------------------------------------------------ #
    def _load_default_capabilities(self) -> None:
        """Seed a default set of sandbox capabilities."""
        home = Path.home()
        projects_glob = str(home / "Projects" / "**")
        drafts_glob = str(home / "Job_Drafts" / "**")
        job_drafts_root = str(home / "Job_Drafts")
        projects_root = str(home / "Projects")
        secrets_glob = str(home / "secrets" / "**")
        ssh_glob = str(home / ".ssh" / "**")
        defaults = [
            CapabilityDefinition(
                capability_id="file_read",
                name="file_read",
                category="filesystem",
                description="Read local files",
                policy=CapabilityPolicy(
                    allowed_paths=[projects_glob, drafts_glob]
                ),
            ),
            CapabilityDefinition(
                capability_id="file_write",
                name="file_write",
                category="filesystem",
                description="Write local files",
                policy=CapabilityPolicy(
                    allowed_paths=[projects_glob, drafts_glob, job_drafts_root],
                    blocked_paths=[ssh_glob, secrets_glob],
                    max_file_size_mb=100,
                ),
                limits=CapabilityLimits(daily_quota=100),
            ),
            CapabilityDefinition(
                capability_id="directory_create",
                name="directory_create",
                category="filesystem",
                description="Create local directories",
                policy=CapabilityPolicy(
                    allowed_paths=[projects_glob, drafts_glob]
                ),
            ),
            CapabilityDefinition(
                capability_id="web_scraping",
                name="web_scraping",
                category="network",
                description="Scrape or fetch web content",
                policy=CapabilityPolicy(
                    allowed_domains=[
                        "*.linkedin.com",
                        "*.indeed.com",
                        "*.glassdoor.com",
                        "*.com",
                        "*.org",
                    ],
                    blocked_domains=[],
                    max_requests_per_minute=60,
                ),
            ),
            CapabilityDefinition(
                capability_id="browser_navigate",
                name="browser_navigate",
                category="browser",
                description="Automate browser navigation",
                policy=CapabilityPolicy(allowed_domains=["*.linkedin.com", "*.indeed.com"]),
            ),
            CapabilityDefinition(
                capability_id="command_execute",
                name="command_execute",
                category="system",
                description="Run local commands",
                policy=CapabilityPolicy(extra={"allowed_commands": "git,npm,python"}),
                limits=CapabilityLimits(daily_quota=50),
            ),
            CapabilityDefinition(
                capability_id="file_modify",
                name="file_modify",
                category="filesystem",
                description="Modify existing files",
                policy=CapabilityPolicy(
                    allowed_paths=[
                        projects_glob,
                        str(home / "poller" / "**"),
                        str(home / "agents" / "**"),
                    ]
                ),
            ),
        ]

        for definition in defaults:
            self.capabilities[definition.capability_id] = definition

    def register_agent(self, agent_name: str, grants: Optional[List[CapabilityGrant]] = None) -> None:
        """Register an agent with optional explicit grants."""
        if grants:
            self.agent_grants[agent_name] = grants
        else:
            # Default to granting all known capabilities
            self.agent_grants[agent_name] = [
                CapabilityGrant(capability_id=cap_id) for cap_id in self.capabilities.keys()
            ]

    async def get_agent_grants(self, agent_name: str) -> List[CapabilityGrant]:
        if agent_name not in self.agent_grants:
            self.register_agent(agent_name)
        return self.agent_grants.get(agent_name, [])

    # ------------------------------------------------------------------ #
    # Enforcement
    # ------------------------------------------------------------------ #
    async def get_capability_policy(self, capability_id: str, grant: CapabilityGrant) -> CapabilityPolicy:
        definition = self.capabilities.get(capability_id)
        if not definition:
            raise CapabilityError(f"Unknown capability: {capability_id}")
        if grant.policy_override:
            base = definition.policy.model_copy(deep=True)
            override = grant.policy_override
            # Merge while preserving defaults
            base.allowed_paths = override.allowed_paths or base.allowed_paths
            base.blocked_paths = override.blocked_paths or base.blocked_paths
            base.allowed_domains = override.allowed_domains or base.allowed_domains
            base.blocked_domains = override.blocked_domains or base.blocked_domains
            base.max_file_size_mb = override.max_file_size_mb or base.max_file_size_mb
            base.allowed_extensions = override.allowed_extensions or base.allowed_extensions
            base.require_confirmation = override.require_confirmation or base.require_confirmation
            base.max_requests_per_minute = override.max_requests_per_minute or base.max_requests_per_minute
            base.max_size_mb = override.max_size_mb or base.max_size_mb
            base.max_runtime_seconds = override.max_runtime_seconds or base.max_runtime_seconds
            base.extra = {**base.extra, **override.extra}
            return base
        return definition.policy

    async def check_permission(
        self,
        agent_name: str,
        capability: str,
        policy_params: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """Validate that the agent can use the capability for provided params."""
        grants = await self.get_agent_grants(agent_name)
        grant = next((g for g in grants if g.capability_id == capability), None)

        if not grant:
            raise CapabilityError(f"Agent {agent_name} not granted capability {capability}")

        definition = self.capabilities.get(capability)
        if not definition:
            raise CapabilityError(f"Unknown capability: {capability}")

        policy = await self.get_capability_policy(capability, grant)
        params = policy_params or {}
        if not await self._check_policy_compliance(policy, params):
            raise CapabilityError(f"Policy violation for capability {capability}")

        if not await self.usage_tracker.check_limits(agent_name, capability, grant, definition):
            raise QuotaExceededError(f"Quota exceeded for capability {capability}")

        return True

    async def execute_with_capability(
        self,
        agent_name: str,
        capability: str,
        action: Callable[..., Awaitable[Any]],
        policy_params: Optional[Dict[str, Any]] = None,
        **kwargs,
    ):
        """Execute an action with capability enforcement."""
        await self.check_permission(agent_name, capability, policy_params=policy_params)

        try:
            result = await action(**kwargs)
            await self.usage_tracker.record_usage(agent_name, capability)
            await self.audit_log(agent_name, capability, "SUCCESS", kwargs)
            return result
        except Exception as exc:  # pragma: no cover - passthrough
            await self.audit_log(agent_name, capability, "FAILED", kwargs, error=str(exc))
            raise

    async def audit_log(
        self,
        agent_name: str,
        capability: str,
        status: str,
        params: Dict[str, Any],
        error: Optional[str] = None,
    ) -> None:
        """Lightweight audit log hook."""
        log = logger.bind(component="capability_manager", agent=agent_name)
        message = f"{status} :: {capability}"
        if error:
            log.error(f"{message} - {error} | params={params}")
        else:
            log.info(f"{message} | params={params}")

    async def _check_policy_compliance(self, policy: CapabilityPolicy, params: Dict[str, Any]) -> bool:
        """Check if parameters comply with capability policy."""
        path = params.get("path")
        url = params.get("url")
        size_mb = params.get("size_mb")
        extension = params.get("extension")

        if path:
            resolved = _resolve_path(path)
            # Blocked paths first
            if policy.blocked_paths and _match_path(resolved, policy.blocked_paths):
                return False
            if policy.allowed_paths and not _match_path(resolved, policy.allowed_paths):
                return False

            if policy.allowed_extensions and extension:
                if not any(fnmatch.fnmatch(extension, ext) for ext in policy.allowed_extensions):
                    return False

            if policy.max_file_size_mb is not None and size_mb is not None:
                if size_mb > policy.max_file_size_mb:
                    return False

        if url:
            if not _match_domain(url, policy.allowed_domains, policy.blocked_domains):
                return False

        if size_mb is not None and policy.max_size_mb is not None:
            if size_mb > policy.max_size_mb:
                return False

        return True


# Shared instance for convenience
default_capability_manager = CapabilityManager()

