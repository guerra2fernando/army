"""
Data contract utilities for logs, events, and daily briefs.

Implements the hard separation defined in Phase 5:
- Internal logs (never user-visible)
- User-facing events (broadcast to dashboard/notifications)
- Daily briefs (immutable snapshots)
"""
from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, Optional
from uuid import uuid4

from loguru import logger

from app.db import Database

EVENT_PRIORITIES = {"LOW", "NORMAL", "HIGH", "URGENT"}


class DataContractLogger:
    """Centralized logger that enforces data contracts."""

    async def log_internal(
        self,
        level: str,
        action: str,
        *,
        agent: Optional[str] = None,
        entity_type: Optional[str] = None,
        entity_id: Optional[str] = None,
        message: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        request_id: Optional[str] = None,
        duration_ms: Optional[int] = None,
        error_stack: Optional[str] = None,
        extra: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Write an internal-only audit log entry."""

        now = datetime.utcnow()
        entry: Dict[str, Any] = {
            "log_id": str(uuid4()),
            "timestamp": now,
            "created_at": now,
            "level": level.upper(),
            "agent": agent or "SYSTEM",
            "action": action,
            "entity_type": entity_type,
            "entity_id": entity_id,
            "message": message,
            "details": details or {},
            "request_id": request_id,
            "duration_ms": duration_ms,
            "error_stack": error_stack,
            "internal_only": True,
        }

        if extra:
            entry["extra"] = extra

        self._validate_log_entry(entry)

        try:
            await Database.get_collection("logs").insert_one(entry)
        except Exception as exc:  # pragma: no cover - best effort persistence
            logger.warning(f"[DataContracts] Failed to persist log: {exc}")

        return entry

    async def emit_event(
        self,
        event_type: str,
        title: str,
        *,
        description: Optional[str] = None,
        priority: str = "NORMAL",
        icon: Optional[str] = None,
        action_required: bool = False,
        action_url: Optional[str] = None,
        action_label: Optional[str] = None,
        agent_name: Optional[str] = None,
        entity_type: Optional[str] = None,
        entity_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        notify_telegram: bool = False,
        notify_email: bool = False,
        broadcast: bool = True,
        payload: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Emit a user-visible event to the `event_stream` collection."""

        now = datetime.utcnow()
        normalized_priority = (priority or "NORMAL").upper()
        if normalized_priority not in EVENT_PRIORITIES:
            normalized_priority = "NORMAL"

        event: Dict[str, Any] = {
            "event_id": str(uuid4()),
            "timestamp": now,
            "created_at": now,
            "event_type": event_type,
            "priority": normalized_priority,
            "title": title,
            "description": description,
            "icon": icon,
            "action_required": action_required,
            "action_url": action_url,
            "action_label": action_label,
            "agent_name": agent_name,
            "entity_type": entity_type,
            "entity_id": entity_id,
            "metadata": metadata or {},
            "notify_telegram": notify_telegram,
            "notify_email": notify_email,
            "broadcast": bool(broadcast),
            # Preserve legacy payload field for dashboards/tests
            "payload": payload or {},
        }

        self._validate_event_entry(event)

        try:
            await Database.get_collection("event_stream").insert_one(event)
        except Exception as exc:  # pragma: no cover - best effort persistence
            logger.warning(f"[DataContracts] Failed to persist event: {exc}")

        return event

    async def record_brief(
        self,
        date: str,
        brief_sections: Dict[str, Any],
        *,
        version: str = "1.0",
    ) -> Dict[str, Any]:
        """Record or upsert an immutable daily brief snapshot."""

        now = datetime.utcnow()
        brief_doc: Dict[str, Any] = {
            "date": date,
            "version": version,
            "crypto": brief_sections.get("crypto", {}) or {},
            "jobs": brief_sections.get("jobs", {}) or {},
            "projects": brief_sections.get("projects", {}) or {},
            "system": brief_sections.get("system", {}) or {},
            "generated_at": brief_sections.get("generated_at", now),
            "generation_duration_ms": brief_sections.get("generation_duration_ms"),
            "data_freshness": brief_sections.get("data_freshness", {}),
            "immutable": True,
        }

        self._validate_brief_entry(brief_doc)

        try:
            briefs = Database.get_collection("daily_brief")
            await briefs.update_one(
                {"date": date},
                {"$set": brief_doc},
                upsert=True,
            )
        except Exception as exc:  # pragma: no cover - best effort persistence
            logger.warning(f"[DataContracts] Failed to persist brief: {exc}")

        return brief_doc

    # --------------------------------------------------------------------- #
    # Validation helpers
    # --------------------------------------------------------------------- #
    @staticmethod
    def _validate_log_entry(entry: Dict[str, Any]) -> None:
        required_fields = {"log_id", "timestamp", "level", "action", "internal_only"}
        missing = required_fields - set(entry.keys())
        if missing:
            raise ValueError(f"Log entry missing fields: {missing}")
        if entry["internal_only"] is not True:
            raise ValueError("Logs must be internal_only=True")
        if entry["level"] not in {"DEBUG", "INFO", "WARN", "ERROR"}:
            raise ValueError(f"Invalid log level: {entry['level']}")

    @staticmethod
    def _validate_event_entry(entry: Dict[str, Any]) -> None:
        required_fields = {"event_id", "timestamp", "event_type", "title"}
        missing = required_fields - set(entry.keys())
        if missing:
            raise ValueError(f"Event entry missing fields: {missing}")
        if entry.get("broadcast") is not True:
            # All events are intended for dashboard consumption
            raise ValueError("Events must be broadcast=True")
        if "internal_only" in entry:
            raise ValueError("Events cannot include internal_only flag")

    @staticmethod
    def _validate_brief_entry(entry: Dict[str, Any]) -> None:
        if entry.get("immutable") is not True:
            raise ValueError("Briefs must be immutable")
        required_sections = {"crypto", "jobs", "projects", "system"}
        missing = required_sections - set(entry.keys())
        if missing:
            raise ValueError(f"Brief entry missing sections: {missing}")
        if "date" not in entry:
            raise ValueError("Brief entry must include date")


# Shared singleton for convenience
contract_logger = DataContractLogger()










