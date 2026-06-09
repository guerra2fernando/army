"""
Task Queue Routes
"""
import json
import hashlib
import re
from datetime import datetime, timedelta
from uuid import uuid4
from typing import Optional, List, Any, Dict
from fastapi import APIRouter, HTTPException, status, Depends, Query, BackgroundTasks, Request
from loguru import logger

from app.db import Database
from app.models.task import (
    TaskCreate, TaskUpdate, TaskResponse, TaskPickupResponse,
    TaskStatus, AgentTarget, TaskPickupRequest
)
from app.models.base import APIResponse
from app.models.user import User
from app.utils.auth import get_current_user
from app.utils.security import require_agent_security
from app.config import get_settings
from app.utils.data_contracts import contract_logger
from app.orchestrator.safety import OrchestratorKillSwitch, ensure_orchestrator_enabled
from app.services.discovery_service import get_discovery_service
from app.services.commercial_ops_service import get_commercial_ops_service

settings = get_settings()
router = APIRouter(prefix="/tasks", tags=["Task Queue"])

TITLE_MAX_LEN = 35
kill_switch = OrchestratorKillSwitch()


async def _guard_kill_switch():
    """Block agent operations when the orchestrator is paused."""
    if not await ensure_orchestrator_enabled():
        raise HTTPException(status_code=503, detail="Orchestrator kill switch active")


def _summarize_title(text: str, agent_target: str) -> str:
    """
    Build a concise, human-friendly title (<35 chars).
    Uses a lightweight summarization heuristic instead of copying the full text.
    """
    if not isinstance(text, str):
        return f"{agent_target.title()} task"
    
    # Extract up to a few meaningful tokens, strip filler, and condense
    tokens = re.findall(r"[A-Za-z0-9@#\+\-&']+", text.strip())
    if not tokens:
        return f"{agent_target.title()} task"
    
    candidate = " ".join(tokens[:8]).title()
    if len(candidate) > TITLE_MAX_LEN:
        candidate = candidate[: TITLE_MAX_LEN - 3].rstrip() + "..."
    return candidate or f"{agent_target.title()} task"


def _derive_task_title(payload: Optional[dict], agent_target: str) -> str:
    """
    Build a concise title from payload/intention, capped at 35 chars.
    """
    payload = payload or {}
    if agent_target == "JOB_HUNTER" and payload.get("action") == "search":
        roles = payload.get("roles") or payload.get("titles") or []
        locations = payload.get("locations") or []
        role_text = ", ".join([role.strip() for role in roles if isinstance(role, str) and role.strip()][:2])
        location_text = ", ".join([location.strip() for location in locations if isinstance(location, str) and location.strip()][:2])
        if role_text or location_text:
            summary = " - ".join([part for part in [role_text, location_text] if part])
            return _summarize_title(summary, agent_target)

    candidates: List[Any] = [
        payload.get("instruction"),
        payload.get("original_command"),
        payload.get("description"),
        payload.get("query"),
    ]
    for candidate in candidates:
        if isinstance(candidate, str) and candidate.strip():
            return _summarize_title(candidate, agent_target)
    
    if isinstance(payload.get("action"), str) and isinstance(payload.get("query"), str):
        return _summarize_title(f"{payload['action']} {payload['query']}", agent_target)
    
    return f"{agent_target.title()} Task"


def _build_idempotency_key(agent_target: str, payload: Optional[dict]) -> str:
    """
    Deterministically derive an idempotency key from the agent target and payload.
    """
    try:
        payload_blob = json.dumps(payload or {}, sort_keys=True, default=str)
    except Exception:
        # As a fallback, stringify the payload to avoid blocking task creation
        payload_blob = str(payload or "")
    digest = hashlib.sha256(payload_blob.encode()).hexdigest()[:16]
    return f"{agent_target}-{digest}"


def _build_task_response(task_doc: dict) -> TaskResponse:
    """Normalize task document into response model."""
    return TaskResponse(
        task_id=task_doc["task_id"],
        idempotency_key=task_doc.get("idempotency_key"),
        agent_target=task_doc["agent_target"],
        title=task_doc.get("title") or _derive_task_title(task_doc.get("payload"), task_doc.get("agent_target", "Task")),
        status=task_doc["status"],
        priority=task_doc["priority"],
        created_at=task_doc["created_at"],
        updated_at=task_doc.get("updated_at"),
        worker_id=task_doc.get("worker_id"),
        picked_up_by=task_doc.get("picked_up_by"),
        lease_until=task_doc.get("lease_until"),
        last_execution_started=task_doc.get("last_execution_started"),
        execution_count=task_doc.get("execution_count", 0),
        payload=task_doc.get("payload"),
        error_log=task_doc.get("error_log", []),
        completed_at=task_doc.get("completed_at"),
        result=task_doc.get("result"),
        recurring=task_doc.get("recurring", False)
    )


@router.post("", response_model=TaskResponse)
async def create_task(
    task_data: TaskCreate,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user)
):
    """Create a new task in the queue."""
    
    tasks = Database.get_collection("task_queue")
    
    task_id = str(uuid4())
    derived_title = _derive_task_title(task_data.payload, task_data.agent_target.value)

    # Generate idempotency key and perform deduplication within the configured window
    idempotency_key = _build_idempotency_key(task_data.agent_target.value, task_data.payload)
    dedupe_cutoff = datetime.utcnow() - timedelta(hours=settings.idempotency_window_hours)
    existing_task = await tasks.find_one({
        "idempotency_key": idempotency_key,
        "created_at": {"$gte": dedupe_cutoff},
        "status": {"$nin": [TaskStatus.FAILED.value, TaskStatus.CANCELLED.value]}
    })

    if existing_task:
        logger.info(f"Idempotency hit for {idempotency_key}, returning task {existing_task.get('task_id')}")
        return _build_task_response(existing_task)
    
    # Special handling for ORCHESTRATOR tasks - process immediately
    if task_data.agent_target.value == "ORCHESTRATOR":
        instruction = task_data.payload.get("instruction", "")
        if instruction:
            # Process through orchestrator
            from app.orchestrator.agent_00 import get_orchestrator
            orchestrator = get_orchestrator()
            
            response = await orchestrator.process_command(
                command=instruction,
                user_id=current_user.user_id,
                context=task_data.payload.get("context")
            )
            
            # If the orchestrator created a workflow, return a placeholder task
            if getattr(response, "workflow_created", False) and response.workflow_id:
                task_doc = {
                    "_id": task_id,
                    "task_id": task_id,
                    "idempotency_key": idempotency_key,
                    "agent_target": "ORCHESTRATOR",
                    "payload": task_data.payload,
                    "title": derived_title,
                    "status": TaskStatus.COMPLETED.value,
                    "priority": task_data.priority,
                    "worker_id": None,
                    "picked_up_by": None,
                    "picked_up_at": None,
                    "lease_until": None,
                    "last_execution_started": None,
                    "execution_count": 0,
                    "completed_at": datetime.utcnow(),
                    "retry_count": 0,
                    "max_retries": 0,
                    "error_log": [],
                    "result": {
                        "message": response.message,
                        "workflow_id": response.workflow_id,
                        "routed_to": response.agent_target,
                        "requires_clarification": response.requires_clarification,
                        "clarification_question": response.clarification_question,
                    },
                    "created_by": current_user.user_id,
                    "recurring": task_data.recurring,
                    "created_at": datetime.utcnow(),
                    "updated_at": datetime.utcnow(),
                }

                await tasks.insert_one(task_doc)
                logger.info(f"Workflow created by orchestrator: {response.workflow_id}")
                return _build_task_response(task_doc)

            # If orchestrator created a task, return that info
            if response.task_created and response.task_id:
                # Get the actual task created by orchestrator
                actual_task = await tasks.find_one({"task_id": response.task_id})
                if actual_task:
                    return _build_task_response({
                        **actual_task,
                        "result": actual_task.get("result") or {"orchestrator_message": response.message},
                    })
            
            # If no task was created (e.g., system query or clarification needed)
            # Create a placeholder task with the orchestrator's response
            placeholder_status = (
                TaskStatus.PENDING.value
                if response.requires_clarification
                else TaskStatus.FAILED.value if not response.success
                else TaskStatus.COMPLETED.value
            )
            completed_at = datetime.utcnow() if placeholder_status == TaskStatus.COMPLETED.value else None
            task_doc = {
                "_id": task_id,
                "task_id": task_id,
                "idempotency_key": idempotency_key,
                "agent_target": "ORCHESTRATOR",
                "payload": task_data.payload,
                "title": derived_title,
                "status": placeholder_status,
                "priority": task_data.priority,
                "worker_id": None,
                "picked_up_by": None,
                "picked_up_at": None,  # ORCHESTRATOR tasks are processed immediately, not picked up by workers
                "lease_until": None,
                "last_execution_started": None,
                "execution_count": 0,
                "completed_at": completed_at,
                "retry_count": 0,
                "max_retries": 0,
                "error_log": [],
                "result": {
                    "message": response.message,
                    "routed_to": response.agent_target,
                    "requires_clarification": response.requires_clarification,
                    "clarification_question": response.clarification_question,
                    "error": None if response.success else response.message,
                },
                "created_by": current_user.user_id,
                "recurring": task_data.recurring,
                "created_at": datetime.utcnow(),
                "updated_at": datetime.utcnow(),
            }
            
            await tasks.insert_one(task_doc)
            
            logger.info(f"Orchestrator processed command: {task_id}")
            
            return _build_task_response(task_doc)
    
    # Normal task creation for other agents
    task_doc = {
        "_id": task_id,
        "task_id": task_id,
        "idempotency_key": idempotency_key,
        "agent_target": task_data.agent_target.value,
        "payload": task_data.payload,
        "title": derived_title,
        "status": TaskStatus.PENDING.value,
        "priority": task_data.priority,
        "worker_id": None,
        "picked_up_by": None,
        "lease_until": None,
        "last_execution_started": None,
        "execution_count": 0,
        "retry_count": 0,
        "max_retries": settings.max_task_retries,
        "error_log": [],
        "result": None,
        "created_by": current_user.user_id,
        "recurring": task_data.recurring,
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow(),
    }
    
    await tasks.insert_one(task_doc)
    
    # Log event
    await _log_event("TASK_CREATED", {
        "task_id": task_id,
        "agent_target": task_data.agent_target.value,
        "created_by": current_user.user_id
    })
    
    logger.info(f"Task created: {task_id} for {task_data.agent_target.value}")
    
    return _build_task_response(task_doc)


@router.get("", response_model=List[TaskResponse])
async def list_tasks(
    status: Optional[TaskStatus] = None,
    agent_target: Optional[AgentTarget] = None,
    limit: int = Query(default=50, le=100),
    current_user: User = Depends(get_current_user)
):
    """List tasks with optional filters."""
    
    tasks = Database.get_collection("task_queue")
    
    query = {}
    if status:
        query["status"] = status.value
    if agent_target:
        query["agent_target"] = agent_target.value
    
    cursor = tasks.find(query).sort("created_at", -1).limit(limit)
    results = await cursor.to_list(length=limit)
    
    return [_build_task_response(t) for t in results]


@router.get("/{task_id}", response_model=TaskResponse)
async def get_task(
    task_id: str,
    current_user: User = Depends(get_current_user)
):
    """Get a specific task by ID."""

    tasks = Database.get_collection("task_queue")
    task = await tasks.find_one({"task_id": task_id})

    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found"
        )

    return _build_task_response(task)


@router.get("/{task_id}/details", response_model=dict)
async def get_task_details(
    task_id: str,
    current_user: User = Depends(get_current_user)
):
    """Get detailed information about a task including history and metrics."""

    tasks = Database.get_collection("task_queue")
    task = await tasks.find_one({"task_id": task_id})

    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found"
        )

    # Get task execution history (events related to this task)
    events = Database.get_collection("event_stream")
    task_events = await events.find(
        {"payload.task_id": task_id}
    ).sort("timestamp", -1).to_list(length=50)

    # Get agent performance metrics if applicable
    agent_metrics = None
    if task.get("agent_target") == "CRYPTO_SENTINEL":
        # Get recent crypto briefs or signals for this task type
        briefs_col = Database.get_collection("daily_brief")
        recent_briefs = await briefs_col.find(
            {"generated_at": {"$gte": task.get("created_at")}}
        ).sort("generated_at", -1).limit(5).to_list(length=5)

        agent_metrics = {
            "recent_briefs_count": len(recent_briefs),
            "briefs": recent_briefs,
            "api_usage": {
                "coingecko_used": True,  # Assuming the task used it
                "cryptopanic_used": True,  # Assuming the task used it
            }
        }

    # Calculate execution metrics
    execution_time = None
    if task.get("completed_at") and task.get("picked_up_at"):
        execution_time = (task["completed_at"] - task["picked_up_at"]).total_seconds()
    elif task.get("completed_at") and task.get("created_at"):
        execution_time = (task["completed_at"] - task["created_at"]).total_seconds()

    # Get similar tasks for comparison
    similar_tasks = await tasks.find({
        "agent_target": task.get("agent_target"),
        "status": "COMPLETED"
    }).sort("completed_at", -1).limit(3).to_list(length=3)

    # Build detailed response
    details = {
        "task": _build_task_response(task),
        "execution_metrics": {
            "execution_time_seconds": execution_time,
            "retry_count": task.get("retry_count", 0),
            "error_count": len(task.get("error_log", [])),
            "has_result": task.get("result") is not None,
        },
        "history": {
            "events": [
                {
                    "event_type": event.get("event_type"),
                    "timestamp": event.get("timestamp"),
                    "details": event.get("payload", {})
                }
                for event in task_events
            ],
            "total_events": len(task_events)
        },
        "agent_specific": agent_metrics,
        "comparison": {
            "similar_tasks_count": len(similar_tasks),
            "similar_tasks": [_build_task_response(t) for t in similar_tasks]
        },
        "metadata": {
            "created_by_user": task.get("created_by") != "SYSTEM",
            "has_worker": task.get("worker_id") is not None,
            "is_recurring": task.get("payload", {}).get("recurring", False),
            "priority_level": "high" if task.get("priority", 5) >= 8 else "normal" if task.get("priority", 5) >= 5 else "low"
        }
    }

    return details


@router.delete("/{task_id}", response_model=APIResponse)
async def delete_task(
    task_id: str,
    current_user: User = Depends(get_current_user)
):
    """Delete a task regardless of status."""
    tasks = Database.get_collection("task_queue")

    result = await tasks.delete_one({"task_id": task_id})
    if result.deleted_count == 0:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found"
        )

    await _log_event("TASK_DELETED", {
        "task_id": task_id,
        "deleted_by": current_user.user_id,
    })

    return APIResponse(success=True, message="Task deleted")


# ============================================================================
# AGENT-FACING ENDPOINTS (Protected by Agent Secret)
# ============================================================================

@router.post("/pickup", response_model=Optional[TaskPickupResponse])
async def pickup_task(
    pickup_request: TaskPickupRequest,
    _: dict = Depends(require_agent_security(["task:read"]))
):
    """
    Pick up the next available task for specified agent types.
    Called by local poller.
    """
    await _guard_kill_switch()
    
    tasks = Database.get_collection("task_queue")
    
    # Find and atomically update with leasing
    target_values = [t.value for t in pickup_request.agent_targets]
    lease_duration = timedelta(minutes=settings.task_lease_duration_minutes)
    now = datetime.utcnow()
    
    task = await tasks.find_one_and_update(
        {
            "status": {"$in": [
                TaskStatus.PENDING.value,
                TaskStatus.PICKED_UP.value,
                TaskStatus.IN_PROGRESS.value,
                TaskStatus.EXECUTING.value,
            ]},
            "agent_target": {"$in": target_values},
            "$or": [
                {"lease_until": {"$lt": now}},
                {"lease_until": None}
            ]
        },
        {
            "$set": {
                "status": TaskStatus.PICKED_UP.value,
                "worker_id": pickup_request.worker_id,
                "picked_up_by": pickup_request.worker_id,
                "picked_up_at": datetime.utcnow(),
                "lease_until": now + lease_duration,
                "last_execution_started": now,
                "updated_at": now
            },
            "$inc": {"execution_count": 1}
        },
        sort=[("priority", -1), ("created_at", 1)],
        return_document=True
    )
    
    if not task:
        return None
    
    logger.info(f"Task picked up: {task['task_id']} by {pickup_request.worker_id}")
    
    return TaskPickupResponse(
        task_id=task["task_id"],
        agent_target=task["agent_target"],
        payload=task["payload"],
        priority=task["priority"],
        lease_until=task.get("lease_until")
    )


@router.patch("/{task_id}/lease", response_model=APIResponse)
async def renew_task_lease(
    task_id: str,
    request: Request,
    _: dict = Depends(require_agent_security(["task:lease"]))
):
    """
    Renew a task lease while it is in progress.
    """
    await _guard_kill_switch()
    tasks = Database.get_collection("task_queue")
    task = await tasks.find_one({"task_id": task_id})

    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found"
        )

    worker_id = request.headers.get("x-worker-id") or request.headers.get("X-Worker-ID")
    if task.get("picked_up_by") and worker_id and task.get("picked_up_by") != worker_id:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Lease owned by a different worker"
        )

    new_lease_until = datetime.utcnow() + timedelta(minutes=settings.task_lease_duration_minutes)
    await tasks.update_one(
        {"task_id": task_id},
        {
            "$set": {
                "lease_until": new_lease_until,
                "updated_at": datetime.utcnow()
            }
        }
    )

    return APIResponse(
        success=True,
        message="Lease renewed",
        data={"lease_until": new_lease_until.isoformat()}
    )


@router.post("/recover_leases", response_model=APIResponse)
async def recover_expired_leases(
    _: dict = Depends(require_agent_security(["task:lease"]))
):
    """
    Reclaim tasks whose leases have expired.
    """
    await _guard_kill_switch()
    tasks = Database.get_collection("task_queue")
    now = datetime.utcnow()
    result = await tasks.update_many(
        {
            "status": {"$in": [
                TaskStatus.PICKED_UP.value,
                TaskStatus.IN_PROGRESS.value,
                TaskStatus.EXECUTING.value,
            ]},
            "lease_until": {"$lt": now}
        },
        {
            "$set": {
                "status": TaskStatus.PENDING.value,
                "lease_until": None,
                "picked_up_by": None,
                "worker_id": None,
                "picked_up_at": None,
                "last_execution_started": None,
                "updated_at": now
            },
            "$inc": {"retry_count": 1},
            "$push": {"error_log": f"Lease expired and task recovered at {now.isoformat()}"}
        }
    )

    return APIResponse(
        success=True,
        message="Recovered expired tasks",
        data={"recovered": result.modified_count}
    )


@router.patch("/{task_id}/status", response_model=APIResponse)
async def update_task_status(
    task_id: str,
    update: TaskUpdate,
    background_tasks: BackgroundTasks,
    request: Request,
    _: dict = Depends(require_agent_security(["task:update"]))
):
    """
    Update task status. Called by agents after execution.
    """
    await _guard_kill_switch()
    
    tasks = Database.get_collection("task_queue")
    
    # Get current task first
    existing_task = await tasks.find_one({"task_id": task_id})
    if not existing_task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found"
        )

    # Only the worker that holds the lease may update the task
    requesting_worker = request.headers.get("x-worker-id") or request.headers.get("X-Worker-ID")
    if existing_task.get("picked_up_by") and requesting_worker and existing_task.get("picked_up_by") != requesting_worker:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Lease owned by a different worker"
        )
    
    update_doc = {
        "status": update.status.value,
        "updated_at": datetime.utcnow()
    }
    
    should_notify_complete = False
    should_notify_failed = False
    should_recreate_recurring = False

    if update.status == TaskStatus.IN_PROGRESS:
        update_doc["last_execution_started"] = datetime.utcnow()
    if update.status == TaskStatus.CANCELLED:
        update_doc["lease_until"] = None
        update_doc["picked_up_by"] = None
        update_doc["worker_id"] = None

    if update.status == TaskStatus.COMPLETED:
        update_doc["completed_at"] = datetime.utcnow()
        update_doc["result"] = update.result
        update_doc["lease_until"] = None
        should_notify_complete = True

        # Check if this is a recurring task that should be recreated
        if existing_task.get("recurring", False):
            should_recreate_recurring = True
    
    # Handle retry logic for failures
    if update.status == TaskStatus.FAILED:
        if existing_task.get("retry_count", 0) < existing_task.get("max_retries", 3):
            # Reset to PENDING for retry
            update_doc["status"] = TaskStatus.PENDING.value
            update_doc["worker_id"] = None
            update_doc["picked_up_by"] = None
            update_doc["lease_until"] = None
            update_doc["picked_up_at"] = None
            update_doc["last_execution_started"] = None
            
            # Update with retry increment
            result = await tasks.update_one(
                {"task_id": task_id},
                {
                    "$set": update_doc,
                    "$inc": {"retry_count": 1},
                    "$push": {"error_log": update.error_message or "Unknown error"}
                }
            )
        else:
            # Max retries reached, keep as FAILED
            result = await tasks.update_one(
                {"task_id": task_id},
                {
                    "$set": {**update_doc, "lease_until": None},
                    "$push": {"error_log": update.error_message or "Unknown error"}
                }
            )
            should_notify_failed = True
    else:
        result = await tasks.update_one(
            {"task_id": task_id},
            {"$set": update_doc}
        )
    
    # Log event
    await _log_event("TASK_STATUS_UPDATED", {
        "task_id": task_id,
        "new_status": update.status.value
    })
    
    logger.info(f"Task status updated: {task_id} -> {update.status.value}")

    # Persist discovered opportunities for discovery tasks
    discovery_run_id = existing_task.get("payload", {}).get("discovery_run_id")
    if update.status == TaskStatus.COMPLETED and update.result and discovery_run_id:
        await get_discovery_service().ingest_task_result(existing_task, update.result)
    elif update.status == TaskStatus.FAILED and discovery_run_id and update.error_message:
        await get_discovery_service().mark_run_failed(discovery_run_id, update.error_message)

    # Persist commercial review items and send results
    if update.status == TaskStatus.COMPLETED and update.result:
        await get_commercial_ops_service().create_review_item_from_task_result(existing_task, update.result)
        if existing_task.get("agent_target") == "OUTREACH_EXECUTOR":
            await get_commercial_ops_service().persist_send_result_from_task(existing_task, update.result)
    elif update.status == TaskStatus.FAILED and existing_task.get("agent_target") == "OUTREACH_EXECUTOR":
        send_intent_id = existing_task.get("payload", {}).get("send_intent_id")
        if send_intent_id and update.error_message:
            await get_commercial_ops_service().mark_send_failed(send_intent_id, update.error_message)
    
    # Send notifications in background
    if settings.notifications_enabled:
        if should_notify_complete:
            # Calculate execution time if available
            execution_time_ms = None
            if existing_task.get("picked_up_at") and existing_task.get("completed_at"):
                picked_up = existing_task["picked_up_at"]
                completed = existing_task["completed_at"]
                if isinstance(picked_up, datetime) and isinstance(completed, datetime):
                    execution_time_ms = int((completed - picked_up).total_seconds() * 1000)

            background_tasks.add_task(
                _send_task_notification,
                task_id,
                existing_task.get("agent_target", "Unknown"),
                "COMPLETED",
                update.result,
                execution_time_ms
            )
        elif should_notify_failed:
            background_tasks.add_task(
                _send_task_notification,
                task_id,
                existing_task.get("agent_target", "Unknown"),
                "FAILED",
                None,
                update.error_message
            )

    # Recreate recurring task if needed
    if should_recreate_recurring:
        background_tasks.add_task(
            _recreate_recurring_task,
            existing_task
        )

    return APIResponse(
        success=True,
        message=f"Task status updated to {update.status.value}"
    )


async def _send_task_notification(
    task_id: str,
    agent: str,
    status: str,
    result: Optional[dict] = None,
    error: Optional[str] = None,
    execution_time_ms: Optional[int] = None
):
    """Send task notification in background."""
    try:
        from app.notifications.service import get_notification_service
        from app.db import Database
        service = get_notification_service()

        if status == "COMPLETED":
            # Special handling for CRYPTO_SENTINEL morning brief tasks
            if agent == "CRYPTO_SENTINEL" and result and isinstance(result, dict):
                # Check if this is a morning brief by looking at the payload or result
                # Ensure database is connected
                if Database.db is None:
                    await Database.connect()

                tasks = Database.get_collection("task_queue")
                task_doc = await tasks.find_one({"task_id": task_id})

                if task_doc and task_doc.get("payload", {}).get("action") == "morning_brief":
                    # Send the full morning brief content
                    brief_content = result.get("data", {}).get("message", "")
                    if brief_content:
                        await service.send_morning_brief_notification(brief_content)
                        return  # Don't send the generic task completion notification

            # Format result summary if available
            result_summary = None
            if result:
                if isinstance(result, dict):
                    # Try to extract a meaningful summary
                    result_summary = result.get("summary") or result.get("message")
                    if not result_summary and "data" in result:
                        result_summary = f"Data received: {len(result.get('data', []))} items"

            # Send enhanced notification with full result data and execution time for better summaries
            await service.notify_task_completed(task_id, agent, result_summary, result, execution_time_ms)
        elif status == "FAILED":
            await service.notify_task_failed(task_id, agent, error or "Unknown error")
    except Exception as e:
        logger.error(f"Failed to send task notification: {e}")


async def _recreate_recurring_task(completed_task: dict):
    """Recreate a recurring task after completion."""
    try:
        # Ensure database is connected
        if Database.db is None:
            await Database.connect()

        tasks = Database.get_collection("task_queue")

        # Create a new task with the same parameters
        new_task_id = str(uuid4())
        new_task_doc = {
            "_id": new_task_id,
            "task_id": new_task_id,
            "agent_target": completed_task["agent_target"],
            "payload": completed_task["payload"],
            "title": completed_task.get("title", "Recurring Task"),
            "status": TaskStatus.PENDING.value,
            "priority": completed_task["priority"],
            "worker_id": None,
            "picked_up_at": None,
            "completed_at": None,
            "retry_count": 0,
            "max_retries": 3,
            "error_log": [],
            "result": None,
            "created_by": completed_task.get("created_by"),
            "recurring": True,  # Keep it recurring
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
        }

        await tasks.insert_one(new_task_doc)

        # Log the recreation event
        await _log_event("RECURRING_TASK_RECREATED", {
            "original_task_id": completed_task["task_id"],
            "new_task_id": new_task_id,
            "agent_target": completed_task["agent_target"]
        })

        logger.info(f"Recreated recurring task: {new_task_id} (from {completed_task['task_id']})")

    except Exception as e:
        logger.error(f"Failed to recreate recurring task {completed_task['task_id']}: {e}")


async def _log_event(event_type: str, payload: dict):
    """Log an event to the event stream."""
    # Ensure database is connected
    if Database.db is None:
        await Database.connect()

    await contract_logger.emit_event(
        event_type=event_type,
        title=payload.get("title") if isinstance(payload, dict) else event_type.replace("_", " ").title(),
        description=payload.get("description") if isinstance(payload, dict) else None,
        priority=payload.get("priority", "NORMAL") if isinstance(payload, dict) else "NORMAL",
        agent_name=payload.get("agent_target") if isinstance(payload, dict) else None,
        entity_type=payload.get("entity_type") if isinstance(payload, dict) else None,
        entity_id=payload.get("task_id") if isinstance(payload, dict) else None,
        payload=payload if isinstance(payload, dict) else {"data": payload},
    )
