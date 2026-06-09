"""
Safety and orchestrator guardrails endpoints.
"""
from datetime import datetime
from typing import Optional, List

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from app.config import get_settings
from app.db import Database
from app.models.user import User
from app.orchestrator.safety import (
    OrchestratorKillSwitch,
    SpawnBudgetController,
    ensure_orchestrator_enabled,
)
from app.utils.auth import get_current_user

settings = get_settings()
router = APIRouter(prefix="/safety", tags=["Safety"])
kill_switch = OrchestratorKillSwitch()
budget_controller = SpawnBudgetController()


class KillSwitchRequest(BaseModel):
    reason: str = Field(default="Manual activation", min_length=3)


class SpawnBudgetConfig(BaseModel):
    budget_id: Optional[str] = None
    scope_type: str = Field(description="GLOBAL | AGENT_TYPE | USER_INITIATED")
    agent_type_filter: Optional[str] = None
    max_spawns: int = Field(gt=0)
    time_window: str = Field(default="DAILY")
    action_on_exceed: str = Field(default="BLOCK")
    cooldown_minutes: int = Field(default=60, ge=0)


async def _require_admin(user: User):
    if not user.is_admin:
        raise HTTPException(status_code=403, detail="Admin privileges required")


@router.get("/status")
async def safety_status(current_user: User = Depends(get_current_user)):
    """Return orchestrator safety state."""
    await _require_admin(current_user)
    active = await kill_switch.is_active()
    budgets = await Database.get_collection("spawn_budgets").find().to_list(length=None)
    return {
        "kill_switch_active": active,
        "budgets": budgets,
        "orchestrator_enabled": await ensure_orchestrator_enabled(),
    }


@router.post("/kill-switch")
async def activate_kill_switch(
    payload: KillSwitchRequest,
    current_user: User = Depends(get_current_user),
):
    """Activate kill switch (admin only)."""
    await _require_admin(current_user)
    await kill_switch.activate_kill_switch(payload.reason)
    return {"success": True, "message": "Kill switch activated", "reason": payload.reason}


@router.post("/kill-switch/reset")
async def reset_kill_switch(current_user: User = Depends(get_current_user)):
    """Deactivate kill switch (admin only)."""
    await _require_admin(current_user)
    await kill_switch.deactivate()
    return {"success": True, "message": "Kill switch deactivated"}


@router.post("/spawn-budgets")
async def upsert_spawn_budget(
    config: SpawnBudgetConfig,
    current_user: User = Depends(get_current_user),
):
    """Create or update a spawn budget configuration."""
    await _require_admin(current_user)
    budgets = Database.get_collection("spawn_budgets")
    budget_id = config.budget_id or str(datetime.utcnow().timestamp()).replace(".", "")
    doc = {
        "budget_id": budget_id,
        "scope_type": config.scope_type,
        "agent_type_filter": config.agent_type_filter,
        "max_spawns": config.max_spawns,
        "current_spawns": 0,
        "time_window": config.time_window,
        "action_on_exceed": config.action_on_exceed,
        "cooldown_minutes": config.cooldown_minutes,
        "window_start": datetime.utcnow(),
        "violations": [],
    }
    await budgets.update_one(
        {"budget_id": budget_id},
        {"$set": doc},
        upsert=True,
    )
    return {"success": True, "budget": doc}










