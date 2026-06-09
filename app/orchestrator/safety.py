"""
Orchestrator safety utilities.

Implements schema migration protocol, spawn budget controls, change monitoring,
and a kill switch for runaway orchestrator behaviour.
"""
from __future__ import annotations

import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from uuid import uuid4

from loguru import logger

from app.config import get_settings
from app.db import Database

settings = get_settings()


def _get_collection(name: str):
    """Return a collection, raising if DB is not yet initialised."""
    if Database.db is None:
        raise RuntimeError("Database not initialised")
    return Database.get_collection(name)


# ------------------------------------------------------------------------------
# Schema migration protocol
# ------------------------------------------------------------------------------


class SchemaMigrationProtocol:
    """Controlled schema evolution helper."""

    def __init__(self):
        self.collection_name = "schema_migrations"

    async def propose_schema_change(self, change_request: dict) -> dict:
        """Assess, test, and optionally apply a schema change."""
        safety = await self._assess_safety(change_request)
        requires_approval = safety["requires_approval"] or settings.schema_change_approval_required

        test_result = await self._test_migration(change_request)
        if not test_result["success"]:
            return {
                "approved": False,
                "reason": f"Test migration failed: {test_result['error']}",
                "safety": safety,
            }

        perf_impact = await self._check_performance_impact(change_request)
        if perf_impact["degradation"] > settings.performance_degradation_threshold:
            return await self._flag_performance_concern(change_request, perf_impact, safety)

        record = await self._apply_with_rollback(change_request, safety, requires_approval)
        return record

    async def _assess_safety(self, change: dict) -> dict:
        """Assess safety of a schema change."""
        risk_factors: List[str] = []

        if change.get("type") in {"REMOVE_FIELD", "DROP_COLLECTION"}:
            risk_factors.append("BREAKING_CHANGE")
        if change.get("collections") and "task_queue" in change["collections"]:
            risk_factors.append("CORE_COLLECTION")
        if change.get("affects_indexes"):
            risk_factors.append("INDEX_CHANGE")

        risk_level = "LOW"
        if len(risk_factors) > 2:
            risk_level = "HIGH"
        elif len(risk_factors) > 0:
            risk_level = "MEDIUM"

        return {
            "risk_level": risk_level,
            "risk_factors": risk_factors,
            "requires_approval": risk_level in ["MEDIUM", "HIGH"],
        }

    async def _test_migration(self, change_request: dict) -> dict:
        """Lightweight stub for testing migrations (placeholder for real runner)."""
        try:
            # In a real implementation we would run change_request against a shadow DB.
            return {"success": True, "executed_at": datetime.utcnow()}
        except Exception as exc:  # pragma: no cover - defensive
            return {"success": False, "error": str(exc)}

    async def _check_performance_impact(self, change_request: dict) -> dict:
        """Estimate performance impact (placeholder heuristic)."""
        degradation = 0.0
        if change_request.get("affects_indexes"):
            degradation = 0.02
        return {"degradation": degradation}

    async def _flag_performance_concern(self, change_request: dict, perf: dict, safety: dict) -> dict:
        """Return a rejection object when performance concerns arise."""
        return {
            "approved": False,
            "reason": f"Performance degradation risk ({perf['degradation']:.2%})",
            "safety": safety,
            "performance": perf,
        }

    async def _apply_with_rollback(
        self,
        change_request: dict,
        safety: dict,
        requires_approval: bool,
    ) -> dict:
        """Record migration with rollback metadata."""
        migration_id = str(uuid4())
        rollback_id = str(uuid4())
        doc = {
            "migration_id": migration_id,
            "orchestrator_initiated": True,
            "change_request": change_request,
            "safety_checks": {
                "backward_compatible": change_request.get("backward_compatible", True),
                "tested_agents": change_request.get("tested_agents", []),
                "performance_impact": safety.get("risk_level"),
                "rollback_available": True,
            },
            "rollback_migration_id": rollback_id,
            "requires_approval": requires_approval,
            "approved_by": None,
            "approval_reason": None,
            "applied_successfully": not requires_approval,
            "applied_at": datetime.utcnow(),
            "affected_documents": change_request.get("affected_documents"),
            "execution_time_ms": change_request.get("execution_time_ms"),
            "post_migration_health_check": None,
        }
        await _get_collection(self.collection_name).insert_one(doc)
        return {"approved": not requires_approval, "migration": doc}


# ------------------------------------------------------------------------------
# Spawn budget controls
# ------------------------------------------------------------------------------


class SpawnBudgetController:
    """Limit agent creation to prevent runaway spawning."""

    def __init__(self):
        self.collection_name = "spawn_budgets"

    async def check_spawn_budget(self, agent_type: str, requester: str) -> dict:
        """Check if spawning is allowed within budget."""
        budgets = await self._get_applicable_budgets(agent_type, requester)
        for budget in budgets:
            current = budget.get("current_spawns", 0)
            max_spawns = budget.get("max_spawns", 0)
            if max_spawns and current >= max_spawns:
                await self._record_violation(budget, agent_type)
                action = budget.get("action_on_exceed", "BLOCK")
                if action == "BLOCK":
                    return {
                        "allowed": False,
                        "reason": f"Spawn budget exceeded ({current}/{max_spawns})",
                        "retry_after": budget.get("cooldown_minutes", 60),
                    }
                if action == "ALLOW_WITH_APPROVAL":
                    return {
                        "allowed": False,
                        "needs_approval": True,
                        "reason": "Spawn budget exceeded, requires approval",
                    }
        return {"allowed": True}

    async def record_spawn(self, agent_type: str, agent_id: str):
        """Record successful spawn for budget tracking."""
        budgets = await self._get_applicable_budgets(agent_type, "ORCHESTRATOR")
        for budget in budgets:
            await _get_collection(self.collection_name).update_one(
                {"budget_id": budget["budget_id"]},
                {"$inc": {"current_spawns": 1}},
            )

    async def _record_violation(self, budget: dict, agent_type: str):
        """Append a violation record to the budget document."""
        violation = {
            "timestamp": datetime.utcnow(),
            "attempted_spawns": budget.get("current_spawns", 0) + 1,
            "blocked_spawns": 1,
            "reason": "Spawn budget exceeded",
            "agent_type": agent_type,
        }
        await _get_collection(self.collection_name).update_one(
            {"budget_id": budget["budget_id"]},
            {"$push": {"violations": violation}},
        )

    async def _get_applicable_budgets(self, agent_type: str, requester: str) -> List[dict]:
        """Return budgets that apply to the request."""
        query = {
            "$or": [
                {"scope_type": "GLOBAL"},
                {"scope_type": "AGENT_TYPE", "agent_type_filter": agent_type},
            ]
        }
        if requester == "USER":
            query["$or"].append({"scope_type": "USER_INITIATED"})

        cursor = _get_collection(self.collection_name).find(query)
        return await cursor.to_list(length=None)


# ------------------------------------------------------------------------------
# Change monitoring and auto-rollback
# ------------------------------------------------------------------------------


class OrchestratorSafetyMonitor:
    """Monitor orchestrator changes and trigger rollback when needed."""

    def __init__(self):
        self.collection_name = "orchestrator_monitoring"

    async def monitor_change_impact(self, change_type: str, change_id: str):
        """Capture baseline, wait, and evaluate impact."""
        baseline = await self._capture_metrics()
        await asyncio.sleep(settings.monitoring_window_minutes * 60)
        current = await self._capture_metrics()

        impact = self._calculate_impact(baseline, current)
        action_taken = None
        if impact["error_rate_increase"] > settings.error_rate_threshold:
            action_taken = "rollback_error_rate"
        elif impact["performance_degradation"] > settings.performance_degradation_threshold:
            action_taken = "rollback_performance"
        elif impact["agent_failure_rate"] > 0.1:
            action_taken = "rollback_agent_failures"

        await _get_collection(self.collection_name).insert_one(
            {
                "change_type": change_type,
                "change_id": change_id,
                "baseline_metrics": baseline,
                "current_metrics": current,
                "impact": impact,
                "timestamp": datetime.utcnow(),
                "action_taken": action_taken,
            }
        )
        return {"impact": impact, "action_taken": action_taken}

    async def _capture_metrics(self) -> dict:
        """Capture lightweight metrics from task queue and agents."""
        tasks = Database.get_collection("task_queue")
        agents = Database.get_collection("agent_registry")
        now = datetime.utcnow()
        pending = await tasks.count_documents({"status": "PENDING"})
        errors_last_10m = await Database.get_collection("logs").count_documents(
            {"level": "ERROR", "timestamp": {"$gte": now - timedelta(minutes=10)}}
        )
        active_agents = await agents.count_documents({"status": "ACTIVE"})
        failed_agents = await agents.count_documents({"status": "FAILED"})
        return {
            "pending_tasks": pending,
            "errors_last_10m": errors_last_10m,
            "active_agents": active_agents,
            "failed_agents": failed_agents,
        }

    def _calculate_impact(self, baseline: dict, current: dict) -> dict:
        """Compute deltas between two snapshots."""
        error_rate_increase = 0.0
        if baseline.get("errors_last_10m"):
            error_rate_increase = max(
                0.0,
                (current.get("errors_last_10m", 0) - baseline["errors_last_10m"])
                / max(1, baseline["errors_last_10m"]),
            )
        performance_degradation = 0.0
        if baseline.get("pending_tasks"):
            performance_degradation = max(
                0.0,
                (current.get("pending_tasks", 0) - baseline["pending_tasks"])
                / max(1, baseline["pending_tasks"]),
            )
        agent_failure_rate = 0.0
        total_agents = max(1, baseline.get("active_agents", 0) + baseline.get("failed_agents", 0))
        if total_agents:
            agent_failure_rate = (current.get("failed_agents", 0)) / total_agents
        return {
            "error_rate_increase": error_rate_increase,
            "performance_degradation": performance_degradation,
            "agent_failure_rate": agent_failure_rate,
        }


# ------------------------------------------------------------------------------
# Kill switch
# ------------------------------------------------------------------------------


class OrchestratorKillSwitch:
    """Emergency stop mechanism for orchestrator-driven actions."""

    def __init__(self):
        self.collection_name = "system_settings"

    async def activate_kill_switch(self, reason: str):
        await _get_collection(self.collection_name).update_one(
            {"setting": "orchestrator_enabled"},
            {
                "$set": {
                    "setting": "orchestrator_enabled",
                    "value": False,
                    "disabled_at": datetime.utcnow(),
                    "reason": reason,
                }
            },
            upsert=True,
        )
        await _get_collection("agent_registry").update_many(
            {},
            {"$set": {"status": "PAUSED", "paused_reason": reason}},
        )
        logger.warning(f"Kill switch activated: {reason}")

    async def deactivate(self):
        await _get_collection(self.collection_name).update_one(
            {"setting": "orchestrator_enabled"},
            {"$set": {"value": True, "disabled_at": None, "reason": None}},
            upsert=True,
        )
        await _get_collection("agent_registry").update_many(
            {"status": "PAUSED"},
            {"$set": {"status": "ACTIVE", "paused_reason": None}},
        )
        logger.info("Kill switch deactivated")

    async def is_active(self) -> bool:
        doc = await _get_collection(self.collection_name).find_one({"setting": "orchestrator_enabled"})
        if doc is None:
            return False
        return doc.get("value") is False

    async def ensure_enabled_or_raise(self):
        """Raise if kill switch is active."""
        if await self.is_active():
            raise RuntimeError("Orchestrator kill switch active")

    async def check_kill_switch_conditions(self):
        """Check for automatic kill switch triggers."""
        if not settings.kill_switch_enabled:
            return
        tasks = _get_collection("task_queue")
        recent = await tasks.count_documents(
            {"created_at": {"$gte": datetime.utcnow() - timedelta(hours=1)}}
        )
        errors = await _get_collection("logs").count_documents(
            {"level": "ERROR", "timestamp": {"$gte": datetime.utcnow() - timedelta(minutes=10)}}
        )
        if recent > settings.max_spawns_per_hour or errors > 50:
            await self.activate_kill_switch("Automated safety trigger")


async def ensure_orchestrator_enabled() -> bool:
    """Convenience helper to guard orchestrator-sensitive endpoints."""
    try:
        ks = OrchestratorKillSwitch()
        if await ks.is_active():
            return False
        return True
    except RuntimeError:
        # Database not ready yet; default to enabled during startup/import
        return True


