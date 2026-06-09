"""
Agent Registry Routes
"""
from datetime import datetime
from uuid import uuid4
from typing import List, Optional
from fastapi import APIRouter, HTTPException, status, Depends, Query
from loguru import logger

from app.db import Database
from app.models.agent import (
    AgentRegister, AgentResponse, AgentHeartbeat,
    AgentStatus, AgentPerformance
)
from app.models.base import APIResponse
from app.models.agent_config import AgentConfigVersion, AgentConfigUpdate, AgentConfigTestResult
from app.utils.auth import get_current_user
from app.utils.security import require_agent_security
from app.orchestrator.safety import SpawnBudgetController, OrchestratorKillSwitch
from app.config import get_settings

settings = get_settings()
budget_controller = SpawnBudgetController()
kill_switch = OrchestratorKillSwitch()

router = APIRouter(prefix="/agents", tags=["Agent Registry"])
DEFAULT_SCHEMA_VERSION = "1.0.0"


def _increment_version(version: str) -> str:
    """Increment semantic version (patch)."""
    try:
        major, minor, patch = [int(x) for x in (version or "0.0.0").split(".")]
        patch += 1
        return f"{major}.{minor}.{patch}"
    except Exception:
        return "1.0.0"


def _get_active_config(agent: dict) -> Optional[dict]:
    """Return the active config version for an agent."""
    versions = agent.get("config_versions") or []
    active = next((v for v in versions if v.get("is_active")), None)
    if active:
        return active
    return versions[0] if versions else None


async def _ensure_orchestrator_enabled():
    """Raise if the orchestrator kill switch is active."""
    if await kill_switch.is_active():
        raise HTTPException(
            status_code=503,
            detail="Orchestrator is paused via kill switch",
        )


async def _ensure_config_structure(agent: dict, agents_collection):
    """Backfill config_version fields for a single agent document."""
    if agent.get("config_versions") and agent.get("config_version"):
        return agent

    legacy_config = {
        "version": agent.get("config_version") or agent.get("version") or "1.0.0",
        "prompt_template": agent.get("prompt_template", ""),
        "config_params": agent.get("config", {}) or {},
        "schema_version": "1.0.0",
        "created_at": agent.get("created_at", datetime.utcnow()),
        "created_by": agent.get("created_by", "SYSTEM"),
        "performance_baseline": agent.get("performance", {}),
        "is_active": True,
    }

    await agents_collection.update_one(
        {"_id": agent["_id"]},
        {
            "$set": {
                "config_version": legacy_config["version"],
                "config_versions": [legacy_config],
                "rollback_versions": agent.get("rollback_versions", []),
                "last_rollback_at": agent.get("last_rollback_at"),
            },
            "$unset": {"prompt_template": "", "config": ""},
        },
    )

    agent["config_version"] = legacy_config["version"]
    agent["config_versions"] = [legacy_config]
    agent["rollback_versions"] = agent.get("rollback_versions", [])
    agent["last_rollback_at"] = agent.get("last_rollback_at")
    return agent


async def _run_config_test(agent_name: str, candidate_config: dict) -> AgentConfigTestResult:
    """
    Lightweight safety test stub for new configs.
    Ensures prompt and params are present and not empty.
    """
    prompt_ok = bool(candidate_config.get("prompt_template", "").strip())
    params_ok = isinstance(candidate_config.get("config_params", {}), dict)

    if not prompt_ok:
        return AgentConfigTestResult(
            safe=False,
            message="Prompt template cannot be empty",
            details={"field": "prompt_template"},
        )
    if not params_ok:
        return AgentConfigTestResult(
            safe=False,
            message="config_params must be an object",
            details={"field": "config_params"},
        )

    return AgentConfigTestResult(
        safe=True,
        message=f"Config for {agent_name} passed basic validation",
        details={"schema_version": candidate_config.get("schema_version", DEFAULT_SCHEMA_VERSION)},
    )


async def _get_agent_or_404(agent_identifier: str, agents):
    """Find agent by id or name."""
    agent = await agents.find_one({"agent_id": agent_identifier}) or await agents.find_one({"agent_name": agent_identifier})
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    return agent


@router.post("/register", response_model=AgentResponse)
async def register_agent(
    agent_data: AgentRegister,
    _: dict = Depends(require_agent_security(["agent:register"]))
):
    """Register a new agent or update existing."""
    await _ensure_orchestrator_enabled()
    if settings.spawn_budget_enabled:
        budget_check = await budget_controller.check_spawn_budget(agent_data.agent_name, "ORCHESTRATOR")
        if not budget_check.get("allowed", False):
            status_code = status.HTTP_429_TOO_MANY_REQUESTS if not budget_check.get("needs_approval") else status.HTTP_403_FORBIDDEN
            raise HTTPException(status_code=status_code, detail=budget_check.get("reason"))

    agents = Database.get_collection("agent_registry")
    
    # Check if agent exists
    existing = await agents.find_one({"agent_name": agent_data.agent_name})
    
    if existing:
        # Update existing agent
        await agents.update_one(
            {"agent_name": agent_data.agent_name},
            {
                "$set": {
                    "version": agent_data.version,
                    "location": agent_data.location.value,
                    "trigger_type": agent_data.trigger_type.value,
                    "trigger_config": agent_data.trigger_config,
                    "capabilities": agent_data.capabilities,
                    "code_path": agent_data.code_path,
                    "granted_capabilities": [
                        grant.model_dump() for grant in agent_data.granted_capabilities
                    ],
                    "capability_usage": agent_data.capability_usage,
                    "status": AgentStatus.ACTIVE.value,
                    "updated_at": datetime.utcnow()
                }
            }
        )
        
        agent_id = existing["agent_id"]
        logger.info(f"Agent updated: {agent_data.agent_name}")
    else:
        # Create new agent
        agent_id = str(uuid4())
        agent_doc = {
            "_id": agent_id,
            "agent_id": agent_id,
            "agent_name": agent_data.agent_name,
            "version": agent_data.version,
            "location": agent_data.location.value,
            "trigger_type": agent_data.trigger_type.value,
            "trigger_config": agent_data.trigger_config,
            "capabilities": agent_data.capabilities,
            "code_path": agent_data.code_path,
            "granted_capabilities": [grant.model_dump() for grant in agent_data.granted_capabilities],
            "capability_usage": agent_data.capability_usage,
            "status": AgentStatus.ACTIVE.value,
            "performance": AgentPerformance().model_dump(),
            "config_version": agent_data.version,
            "config_versions": [
                AgentConfigVersion(
                    version=agent_data.version,
                    prompt_template="",
                    config_params={},
                    schema_version=DEFAULT_SCHEMA_VERSION,
                    created_by="SYSTEM",
                    performance_baseline={}
                ).model_dump()
            ],
            "rollback_versions": [],
            "last_rollback_at": None,
            "created_by": "SYSTEM",
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        }
        
        await agents.insert_one(agent_doc)
        logger.info(f"Agent registered: {agent_data.agent_name}")
    
    # Get updated agent
    agent = await agents.find_one({"agent_id": agent_id})
    agent = await _ensure_config_structure(agent, agents)

    if settings.spawn_budget_enabled:
        await budget_controller.record_spawn(agent_data.agent_name, agent_id)
    
    return AgentResponse(
        agent_id=agent["agent_id"],
        agent_name=agent["agent_name"],
        version=agent["version"],
        location=agent["location"],
        status=agent["status"],
        trigger_type=agent["trigger_type"],
        performance=AgentPerformance(**agent.get("performance", {})),
        created_at=agent["created_at"],
        config_version=agent.get("config_version"),
        granted_capabilities=agent.get("granted_capabilities", []),
    )


@router.get("", response_model=List[AgentResponse])
async def list_agents(current_user: dict = Depends(get_current_user)):
    """List all registered agents."""
    
    agents = Database.get_collection("agent_registry")
    cursor = agents.find().sort("agent_name", 1)
    results = await cursor.to_list(length=100)
    
    return [
        AgentResponse(
            agent_id=a["agent_id"],
            agent_name=a["agent_name"],
            version=a["version"],
            location=a["location"],
            status=a["status"],
            trigger_type=a["trigger_type"],
            performance=AgentPerformance(**a.get("performance", {})),
            created_at=a["created_at"],
            config_version=a.get("config_version")
        )
        for a in results
    ]


@router.get("/{agent_id}/config/active")
async def get_active_agent_config(
    agent_id: str,
    _: dict = Depends(require_agent_security(["agent:read"])),
):
    """Return the currently active config version for the agent."""
    agents = Database.get_collection("agent_registry")
    agent = await _get_agent_or_404(agent_id, agents)
    agent = await _ensure_config_structure(agent, agents)
    active_config = _get_active_config(agent)

    if not active_config:
        raise HTTPException(status_code=404, detail="Active config not found")

    return active_config


@router.get("/{agent_id}/config/versions", response_model=List[AgentConfigVersion])
async def list_agent_config_versions(
    agent_id: str,
    user=Depends(get_current_user)
):
    """List all config versions for an agent."""
    agents = Database.get_collection("agent_registry")
    agent = await _get_agent_or_404(agent_id, agents)
    agent = await _ensure_config_structure(agent, agents)

    versions = agent.get("config_versions", [])
    # Sort by created_at descending, active first
    versions_sorted = sorted(
        versions,
        key=lambda v: (not v.get("is_active", False), v.get("created_at", datetime.min)),
    )
    return [AgentConfigVersion(**v) for v in versions_sorted]


@router.post("/{agent_id}/config", response_model=APIResponse)
async def update_agent_config(
    agent_id: str,
    config_update: AgentConfigUpdate,
    user=Depends(get_current_user)
):
    """Create a new configuration version and activate it."""
    agents = Database.get_collection("agent_registry")
    agent = await _get_agent_or_404(agent_id, agents)
    agent = await _ensure_config_structure(agent, agents)

    active_config = _get_active_config(agent) or {}
    new_version = _increment_version(agent.get("config_version") or active_config.get("version") or "0.0.0")
    created_by = user.get("email") if isinstance(user, dict) else "SYSTEM"

    candidate_config = {
        "version": new_version,
        "prompt_template": config_update.prompt_template or active_config.get("prompt_template", ""),
        "config_params": config_update.config_params or active_config.get("config_params", {}),
        "schema_version": active_config.get("schema_version", DEFAULT_SCHEMA_VERSION),
        "created_at": datetime.utcnow(),
        "created_by": created_by,
        "performance_baseline": active_config.get("performance_baseline", {}),
        "is_active": True,
        "notes": config_update.reason,
    }

    test_result = await _run_config_test(agent["agent_name"], candidate_config)
    if not test_result.safe:
        raise HTTPException(status_code=400, detail=test_result.message)

    updated_versions = []
    for version in agent.get("config_versions", []):
        version["is_active"] = False
        updated_versions.append(version)
    updated_versions.append(candidate_config)

    await agents.update_one(
        {"_id": agent["_id"]},
        {
            "$set": {
                "config_versions": updated_versions,
                "config_version": new_version,
                "updated_at": datetime.utcnow(),
            }
        },
    )

    return APIResponse(
        success=True,
        message="Config version created and activated",
        data={"version": new_version, "test_result": test_result.model_dump()},
    )


@router.post("/{agent_id}/config/rollback", response_model=APIResponse)
async def rollback_agent_config(
    agent_id: str,
    target_version: str,
    user=Depends(get_current_user)
):
    """Rollback to a previous config version."""
    agents = Database.get_collection("agent_registry")
    agent = await _get_agent_or_404(agent_id, agents)
    agent = await _ensure_config_structure(agent, agents)

    versions = agent.get("config_versions", [])
    target = next((v for v in versions if v.get("version") == target_version), None)
    if not target:
        raise HTTPException(status_code=404, detail="Target version not found")

    updated_versions = []
    for version in versions:
        version["is_active"] = version.get("version") == target_version
        updated_versions.append(version)

    rollback_versions = agent.get("rollback_versions", [])
    active_version = agent.get("config_version")
    if active_version and active_version != target_version:
        rollback_versions = [active_version] + rollback_versions[:4]

    await agents.update_one(
        {"_id": agent["_id"]},
        {
            "$set": {
                "config_versions": updated_versions,
                "config_version": target_version,
                "rollback_versions": rollback_versions,
                "last_rollback_at": datetime.utcnow(),
                "updated_at": datetime.utcnow(),
            }
        },
    )

    return APIResponse(
        success=True,
        message=f"Rolled back to version {target_version}",
        data={"config_version": target_version},
    )


@router.post("/{agent_id}/config/test", response_model=AgentConfigTestResult)
async def test_agent_config(
    agent_id: str,
    config_update: AgentConfigUpdate,
    user=Depends(get_current_user)
):
    """Test a new config without saving it."""
    agents = Database.get_collection("agent_registry")
    agent = await _get_agent_or_404(agent_id, agents)
    agent = await _ensure_config_structure(agent, agents)

    active_config = _get_active_config(agent) or {}
    candidate_config = {
        "version": _increment_version(agent.get("config_version") or active_config.get("version") or "0.0.0"),
        "prompt_template": config_update.prompt_template or active_config.get("prompt_template", ""),
        "config_params": config_update.config_params or active_config.get("config_params", {}),
        "schema_version": active_config.get("schema_version", DEFAULT_SCHEMA_VERSION),
        "created_at": datetime.utcnow(),
        "created_by": user.get("email") if isinstance(user, dict) else "SYSTEM",
        "performance_baseline": active_config.get("performance_baseline", {}),
        "is_active": True,
        "notes": config_update.reason,
    }

    return await _run_config_test(agent["agent_name"], candidate_config)


@router.post("/heartbeat", response_model=APIResponse)
async def agent_heartbeat(
    heartbeat: AgentHeartbeat,
    _: dict = Depends(require_agent_security(["agent:heartbeat"]))
):
    """
    Receive heartbeat from agent.
    Updates last_seen and health status.
    """
    await _ensure_orchestrator_enabled()
    
    agents = Database.get_collection("agent_registry")
    health = Database.get_collection("system_health")
    
    # Update agent status
    await agents.update_one(
        {"agent_name": heartbeat.agent_name},
        {
            "$set": {
                "status": AgentStatus.ACTIVE.value if heartbeat.status == "HEALTHY" else AgentStatus.FAILED.value,
                "performance.last_run_at": datetime.utcnow(),
                "updated_at": datetime.utcnow()
            }
        }
    )
    
    # Store heartbeat in system_health
    await health.update_one(
        {"type": "agent_heartbeat", "agent_name": heartbeat.agent_name},
        {
            "$set": {
                "worker_id": heartbeat.worker_id,
                "status": heartbeat.status,
                "current_task": heartbeat.current_task,
                "metrics": heartbeat.metrics,
                "last_seen": datetime.utcnow()
            }
        },
        upsert=True
    )
    
    return APIResponse(
        success=True,
        message="Heartbeat received"
    )


@router.patch("/{agent_name}/status", response_model=APIResponse)
async def update_agent_status(
    agent_name: str,
    status: AgentStatus = Query(...),
    current_user: dict = Depends(get_current_user)
):
    """Update agent status (pause, resume, etc.)."""
    
    agents = Database.get_collection("agent_registry")
    
    result = await agents.update_one(
        {"agent_name": agent_name},
        {
            "$set": {
                "status": status.value,
                "updated_at": datetime.utcnow()
            }
        }
    )
    
    if result.matched_count == 0:
        raise HTTPException(
            status_code=404,
            detail="Agent not found"
        )
    
    logger.info(f"Agent {agent_name} status changed to {status.value}")
    
    return APIResponse(
        success=True,
        message=f"Agent status updated to {status.value}"
    )

