"""
Workflow routes for creation, retrieval, and step execution.
"""
from datetime import datetime
from typing import List, Optional
from uuid import uuid4
from fastapi import APIRouter, Depends, HTTPException, Query, status
from loguru import logger

from app.db import Database
from app.models.base import APIResponse
from app.models.user import User
from app.models.workflow import (
    ApprovalState,
    Workflow,
    WorkflowCreate,
    WorkflowStatus,
    WorkflowStatusUpdate,
    WorkflowStep,
    WorkflowStepPickupRequest,
    WorkflowStepPickupResponse,
    WorkflowStepStatus,
    WorkflowStepUpdate,
)
from app.utils.auth import get_current_user
from app.utils.security import require_agent_security
from app.utils.data_contracts import contract_logger
from app.orchestrator.safety import OrchestratorKillSwitch, ensure_orchestrator_enabled

router = APIRouter(prefix="/workflows", tags=["Workflows"])
kill_switch = OrchestratorKillSwitch()


async def _guard_kill_switch():
    """Block agent workflow pickup/update when kill switch is active."""
    if not await ensure_orchestrator_enabled():
        raise HTTPException(status_code=503, detail="Orchestrator kill switch active")


def _build_workflow_response(doc: dict) -> Workflow:
    """Normalize workflow document into response model."""
    return Workflow(**doc)


async def _log_workflow_event(event_type: str, payload: dict):
    """Log workflow event to event_stream."""
    try:
        await contract_logger.emit_event(
            event_type=event_type,
            title=payload.get("title") if isinstance(payload, dict) else event_type.replace("_", " ").title(),
            description=payload.get("description") if isinstance(payload, dict) else None,
            priority=payload.get("priority", "NORMAL") if isinstance(payload, dict) else "NORMAL",
            agent_name=payload.get("agent_target") if isinstance(payload, dict) else None,
            entity_type="workflow",
            entity_id=payload.get("workflow_id") if isinstance(payload, dict) else None,
            payload=payload if isinstance(payload, dict) else {"data": payload},
        )
    except Exception as exc:  # pragma: no cover - best effort logging
        logger.warning(f"Failed to log workflow event: {exc}")


@router.post("", response_model=Workflow)
async def create_workflow(
    workflow: WorkflowCreate,
    current_user: User = Depends(get_current_user),
):
    """Create a new workflow with steps."""
    if not workflow.steps:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Workflow must contain at least one step",
        )

    workflows = Database.get_collection("workflows")

    workflow_id = str(uuid4())
    approval_token: Optional[str] = None
    approval_config = workflow.approval_config or {
        "approval_type": "HUMAN",
        "approver_roles": ["user"],
        "timeout_hours": 24,
        "approval_message": "Please review this workflow",
        "approval_context": workflow.metadata or {},
    }

    if workflow.approval_required or any(s.approval_required for s in workflow.steps):
        approval_token = str(uuid4())

    step_docs: List[dict] = []
    for index, step in enumerate(workflow.steps):
        step_docs.append(
            WorkflowStep(
                step_id=str(uuid4()),
                name=step.name,
                agent_target=step.agent_target,
                status=WorkflowStepStatus.PENDING,
                task_id=step.task_id,
                inputs=step.inputs,
                outputs=None,
                started_at=None,
                completed_at=None,
                error=None,
                worker_id=None,
                approval_required=step.approval_required,
                approval_state=ApprovalState.PENDING if step.approval_required else ApprovalState.APPROVED,
                approval_context=step.inputs,
            ).model_dump()
        )

    approval_state = (
        ApprovalState.PENDING.value
        if approval_token
        else ApprovalState.APPROVED.value
    )

    workflow_doc = {
        "_id": workflow_id,
        "workflow_id": workflow_id,
        "type": workflow.type,
        "status": WorkflowStatus.PENDING.value,
        "current_step": 0,
        "steps": step_docs,
        "approval_required": workflow.approval_required,
        "approved_by": None,
        "approval_state": approval_state,
        "approval_token": approval_token,
        "approval_config": approval_config,
        "approval_requested_at": datetime.utcnow() if approval_token else None,
        "resume_token": None,
        "created_by": current_user.user_id,
        "priority": workflow.priority,
        "related_tasks": [],
        "parent_workflow": None,
        "metadata": workflow.metadata,
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow(),
    }

    await workflows.insert_one(workflow_doc)
    await _log_workflow_event(
        "WORKFLOW_CREATED",
        {"workflow_id": workflow_id, "type": workflow.type, "created_by": current_user.user_id},
    )

    return _build_workflow_response(workflow_doc)


@router.get("/{workflow_id}", response_model=Workflow)
async def get_workflow(workflow_id: str, current_user: User = Depends(get_current_user)):
    """Get a workflow and its steps."""
    workflows = Database.get_collection("workflows")
    doc = await workflows.find_one({"workflow_id": workflow_id})

    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workflow not found")

    return _build_workflow_response(doc)


@router.get("", response_model=List[Workflow])
async def list_workflows(
    status: Optional[WorkflowStatus] = Query(default=None),
    limit: int = Query(default=50, le=100),
    current_user: User = Depends(get_current_user),
):
    """List workflows with optional filtering."""
    workflows = Database.get_collection("workflows")
    query = {}
    if status:
        query["status"] = status.value

    cursor = workflows.find(query).sort("created_at", -1).limit(limit)
    docs = await cursor.to_list(length=limit)
    return [_build_workflow_response(doc) for doc in docs]


@router.patch("/{workflow_id}/status", response_model=APIResponse)
async def update_workflow_status(
    workflow_id: str,
    status_update: WorkflowStatusUpdate,
    current_user: User = Depends(get_current_user),
):
    """Update workflow status (pause, resume, cancel)."""
    workflows = Database.get_collection("workflows")
    workflow = await workflows.find_one({"workflow_id": workflow_id})

    if not workflow:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workflow not found")

    new_status = status_update.status.value
    update_doc = {
        "status": new_status,
        "updated_at": datetime.utcnow(),
    }

    # Cancel all pending steps if workflow is cancelled
    if status_update.status == WorkflowStatus.CANCELLED:
        steps = workflow.get("steps", [])
        for idx, step in enumerate(steps):
            if step.get("status") == WorkflowStepStatus.PENDING.value:
                steps[idx]["status"] = WorkflowStepStatus.CANCELLED.value
                steps[idx]["completed_at"] = datetime.utcnow()
        update_doc["steps"] = steps

    await workflows.update_one({"workflow_id": workflow_id}, {"$set": update_doc})
    await _log_workflow_event(
        "WORKFLOW_STATUS_UPDATED",
        {"workflow_id": workflow_id, "status": new_status, "by": current_user.user_id},
    )

    return APIResponse(success=True, message=f"Workflow status updated to {new_status}")


@router.post("/{workflow_id}/approve", response_model=APIResponse)
async def approve_workflow(
    workflow_id: str,
    token: Optional[str] = None,
    current_user: User = Depends(get_current_user),
):
    """Approve a workflow."""
    workflows = Database.get_collection("workflows")
    query = {"workflow_id": workflow_id}
    if token:
        query["approval_token"] = token

    workflow = await workflows.find_one(query)
    if not workflow:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workflow not found")

    steps = workflow.get("steps", [])
    for idx, step in enumerate(steps):
        if step.get("approval_required"):
            steps[idx]["approval_state"] = ApprovalState.APPROVED.value

    await workflows.update_one(
        {"workflow_id": workflow_id},
        {
            "$set": {
                "approval_state": ApprovalState.APPROVED.value,
                "approved_by": current_user.email,
                "status": WorkflowStatus.RUNNING.value,
                "approved_at": datetime.utcnow(),
                "updated_at": datetime.utcnow(),
                "steps": steps,
            }
        },
    )

    await _log_workflow_event(
        "WORKFLOW_APPROVED",
        {"workflow_id": workflow_id, "approved_by": current_user.email},
    )

    return APIResponse(success=True, message="Workflow approved")


@router.post("/{workflow_id}/reject", response_model=APIResponse)
async def reject_workflow(
    workflow_id: str,
    reason: Optional[str] = None,
    current_user: User = Depends(get_current_user),
):
    """Reject a workflow request."""
    workflows = Database.get_collection("workflows")
    result = await workflows.update_one(
        {"workflow_id": workflow_id},
        {
            "$set": {
                "approval_state": ApprovalState.REJECTED.value,
                "approved_by": current_user.email,
                "approval_reason": reason,
                "status": WorkflowStatus.CANCELLED.value,
                "updated_at": datetime.utcnow(),
            }
        },
    )

    if result.modified_count == 0:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workflow not found")

    await _log_workflow_event(
        "WORKFLOW_REJECTED",
        {"workflow_id": workflow_id, "rejected_by": current_user.email, "reason": reason},
    )

    return APIResponse(success=True, message="Workflow rejected")


@router.post("/{workflow_id}/resume", response_model=APIResponse)
async def resume_workflow(
    workflow_id: str,
    current_user: User = Depends(get_current_user),
):
    """Resume a paused workflow."""
    workflows = Database.get_collection("workflows")
    result = await workflows.update_one(
        {"workflow_id": workflow_id},
        {"$set": {"status": WorkflowStatus.RUNNING.value, "updated_at": datetime.utcnow()}},
    )

    if result.modified_count == 0:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workflow not found")

    await _log_workflow_event(
        "WORKFLOW_RESUMED",
        {"workflow_id": workflow_id, "resumed_by": current_user.user_id},
    )

    return APIResponse(success=True, message="Workflow resumed")


@router.post("/steps/pickup", response_model=Optional[WorkflowStepPickupResponse])
async def pickup_workflow_step(
    request: WorkflowStepPickupRequest,
    _: dict = Depends(require_agent_security(["workflow:read"])),
):
    """
    Agents pick up the next available workflow step.
    """
    await _guard_kill_switch()
    workflows = Database.get_collection("workflows")
    # Find a workflow that has a pending step for the provided agent targets
    workflow = await workflows.find_one(
        {
            "status": {"$in": [WorkflowStatus.PENDING.value, WorkflowStatus.RUNNING.value]},
            "approval_state": {"$in": [ApprovalState.APPROVED.value, None]},
            "steps": {
                "$elemMatch": {
                    "status": WorkflowStepStatus.PENDING.value,
                    "agent_target": {"$in": request.agent_targets},
                    "$or": [
                        {"approval_required": False},
                        {"approval_state": {"$in": [ApprovalState.APPROVED.value, None]}},
                    ],
                }
            },
        },
        sort=[("priority", -1), ("created_at", 1)],
    )

    if not workflow:
        return None

    steps = workflow.get("steps", [])
    step_index = next(
        (idx for idx, step in enumerate(steps) if step["status"] == WorkflowStepStatus.PENDING.value
         and step.get("agent_target") in request.agent_targets),
        None,
    )

    if step_index is None:
        return None

    step = steps[step_index]
    # Do not hand out steps still awaiting approval
    if step.get("approval_required") and step.get("approval_state") not in (
        ApprovalState.APPROVED.value,
        ApprovalState.APPROVED,
    ):
        return None

    # Attempt to claim this step atomically
    claim_result = await workflows.update_one(
        {
            "workflow_id": workflow["workflow_id"],
            f"steps.{step_index}.step_id": step["step_id"],
            f"steps.{step_index}.status": WorkflowStepStatus.PENDING.value,
        },
        {
            "$set": {
                f"steps.{step_index}.status": WorkflowStepStatus.RUNNING.value,
                f"steps.{step_index}.started_at": datetime.utcnow(),
                f"steps.{step_index}.worker_id": request.worker_id,
                "status": WorkflowStatus.RUNNING.value,
                "current_step": step_index,
                "updated_at": datetime.utcnow(),
            }
        },
    )

    if claim_result.modified_count == 0:
        return None

    return WorkflowStepPickupResponse(
        workflow_id=workflow["workflow_id"],
        step_id=step["step_id"],
        step_name=step.get("name", ""),
        agent_target=step["agent_target"],
        inputs=step.get("inputs", {}),
        step_index=step_index,
        priority=workflow.get("priority", 5),
    )


@router.patch("/{workflow_id}/steps/{step_id}", response_model=APIResponse)
async def update_workflow_step(
    workflow_id: str,
    step_id: str,
    update: WorkflowStepUpdate,
    _: dict = Depends(require_agent_security(["workflow:update"])),
):
    """Update workflow step status and propagate workflow status."""
    await _guard_kill_switch()
    workflows = Database.get_collection("workflows")
    workflow = await workflows.find_one({"workflow_id": workflow_id})

    if not workflow:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workflow not found")

    steps = workflow.get("steps", [])
    step_index = next((idx for idx, s in enumerate(steps) if s["step_id"] == step_id), None)
    if step_index is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Step not found")

    step = steps[step_index]
    step["status"] = update.status.value
    step["updated_at"] = datetime.utcnow()

    if update.status == WorkflowStepStatus.RUNNING:
        step["started_at"] = step.get("started_at") or datetime.utcnow()
    elif update.status == WorkflowStepStatus.COMPLETED:
        step["completed_at"] = datetime.utcnow()
        step["outputs"] = update.outputs
        step["error"] = None
    elif update.status == WorkflowStepStatus.FAILED:
        step["completed_at"] = datetime.utcnow()
        step["error"] = update.error

    steps[step_index] = step

    # Determine new workflow status
    new_workflow_status = workflow.get("status", WorkflowStatus.PENDING.value)
    if update.status == WorkflowStepStatus.FAILED:
        new_workflow_status = WorkflowStatus.FAILED.value
    else:
        all_completed = all(
            s.get("status") == WorkflowStepStatus.COMPLETED.value for s in steps
        )
        if all_completed:
            new_workflow_status = WorkflowStatus.COMPLETED.value
        else:
            new_workflow_status = WorkflowStatus.RUNNING.value

    await workflows.update_one(
        {"workflow_id": workflow_id},
        {
            "$set": {
                "steps": steps,
                "status": new_workflow_status,
                "current_step": step_index,
                "updated_at": datetime.utcnow(),
            }
        },
    )

    await _log_workflow_event(
        "WORKFLOW_STEP_UPDATED",
        {
            "workflow_id": workflow_id,
            "step_id": step_id,
            "status": update.status.value,
            "error": update.error,
        },
    )

    return APIResponse(success=True, message=f"Step updated to {update.status.value}")


