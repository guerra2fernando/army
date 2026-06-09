"""
Phase Execution API Routes
"""
from fastapi import APIRouter, HTTPException, Depends
from typing import List
from app.models.phase_execution import (
    PhaseExecution, ExecutionControl, ExecutionControlAction,
    PhaseExecutionCreate, ExecutionControlCreate,
    PhaseExecutionResponse, ExecutionControlResponse
)
from app.models.task import TaskStatus
from app.db import get_db
from app.utils.auth import get_current_user
from app.models.user import User
from motor.motor_asyncio import AsyncIOMotorCollection
import uuid
from datetime import datetime

router = APIRouter()


@router.post("/tasks/{task_id}/phases", response_model=PhaseExecutionResponse)
async def create_phase_execution(
    task_id: str,
    execution_data: PhaseExecutionCreate,
    current_user: User = Depends(get_current_user),
    db=Depends(get_db)
):
    """Create a phase execution record."""

    # Verify task exists and is in execution state
    tasks_collection: AsyncIOMotorCollection = db.task_queue
    task = await tasks_collection.find_one({"task_id": task_id})

    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    # Create execution record
    execution_id = str(uuid.uuid4())
    execution = PhaseExecution(
        execution_id=execution_id,
        **execution_data.model_dump()
    )

    executions_collection: AsyncIOMotorCollection = db.task_phase_executions
    await executions_collection.insert_one(execution.model_dump())

    return PhaseExecutionResponse(**execution.model_dump())


@router.get("/tasks/{task_id}/phases", response_model=List[PhaseExecutionResponse])
async def get_phase_executions(
    task_id: str,
    current_user: User = Depends(get_current_user),
    db=Depends(get_db)
):
    """Get all phase executions for a task."""

    executions_collection: AsyncIOMotorCollection = db.task_phase_executions
    executions = await executions_collection.find({"task_id": task_id}).to_list(length=None)

    return [PhaseExecutionResponse(**execution) for execution in executions]


@router.put("/tasks/{task_id}/phases/{execution_id}/status")
async def update_phase_execution_status(
    task_id: str,
    execution_id: str,
    status: str,
    current_user: User = Depends(get_current_user),
    db=Depends(get_db)
):
    """Update phase execution status."""

    executions_collection: AsyncIOMotorCollection = db.task_phase_executions
    execution = await executions_collection.find_one({"execution_id": execution_id, "task_id": task_id})

    if not execution:
        raise HTTPException(status_code=404, detail="Phase execution not found")

    update_data = {"status": status}

    if status == "RUNNING" and not execution.get("started_at"):
        update_data["started_at"] = datetime.utcnow()
    elif status == "COMPLETED" and not execution.get("completed_at"):
        update_data["completed_at"] = datetime.utcnow()

    await executions_collection.update_one(
        {"execution_id": execution_id},
        {"$set": update_data}
    )

    return {"message": f"Phase execution status updated to {status}"}


@router.post("/tasks/{task_id}/controls", response_model=ExecutionControlResponse)
async def create_execution_control(
    task_id: str,
    control_data: ExecutionControlCreate,
    current_user: User = Depends(get_current_user),
    db=Depends(get_db)
):
    """Create an execution control request."""

    # Verify task exists
    tasks_collection: AsyncIOMotorCollection = db.task_queue
    task = await tasks_collection.find_one({"task_id": task_id})

    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    # Create control record
    control_id = str(uuid.uuid4())
    control = ExecutionControl(
        control_id=control_id,
        requested_by=current_user.id,
        **control_data.model_dump()
    )

    controls_collection: AsyncIOMotorCollection = db.task_execution_controls
    await controls_collection.insert_one(control.model_dump())

    # Apply control action to task
    new_status = None
    if control_data.action == ExecutionControlAction.PAUSE:
        new_status = TaskStatus.PHASE_READY
    elif control_data.action == ExecutionControlAction.RESUME:
        new_status = TaskStatus.EXECUTING
    elif control_data.action == ExecutionControlAction.CANCEL:
        new_status = TaskStatus.CANCELLED

    if new_status:
        await tasks_collection.update_one(
            {"task_id": task_id},
            {"$set": {"status": new_status}}
        )

    return ExecutionControlResponse(**control.model_dump())


@router.get("/tasks/{task_id}/controls", response_model=List[ExecutionControlResponse])
async def get_execution_controls(
    task_id: str,
    current_user: User = Depends(get_current_user),
    db=Depends(get_db)
):
    """Get execution controls for a task."""

    controls_collection: AsyncIOMotorCollection = db.task_execution_controls
    controls = await controls_collection.find({"task_id": task_id}).to_list(length=None)

    return [ExecutionControlResponse(**control) for control in controls]


@router.post("/tasks/{task_id}/start-execution")
async def start_task_execution(
    task_id: str,
    current_user: User = Depends(get_current_user),
    db=Depends(get_db)
):
    """Start execution of an approved task."""

    # Verify task exists and is approved
    tasks_collection: AsyncIOMotorCollection = db.task_queue
    task = await tasks_collection.find_one({"task_id": task_id})

    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    if task["status"] != TaskStatus.APPROVED:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot start execution for task in {task['status']} status. Task must be approved first."
        )

    # Update task status to EXECUTING
    await tasks_collection.update_one(
        {"task_id": task_id},
        {"$set": {"status": TaskStatus.EXECUTING}}
    )

    return {"message": "Task execution started", "status": TaskStatus.EXECUTING}


@router.get("/tasks/{task_id}/execution-status")
async def get_execution_status(
    task_id: str,
    current_user: User = Depends(get_current_user),
    db=Depends(get_db)
):
    """Get comprehensive execution status for a task."""

    # Get task
    tasks_collection: AsyncIOMotorCollection = db.task_queue
    task = await tasks_collection.find_one({"task_id": task_id})

    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    # Get master plan
    plans_collection: AsyncIOMotorCollection = db.task_master_plans
    plan = await plans_collection.find_one({"task_id": task_id})

    # Get phase executions
    executions_collection: AsyncIOMotorCollection = db.task_phase_executions
    executions = await executions_collection.find({"task_id": task_id}).to_list(length=None)

    # Get execution controls
    controls_collection: AsyncIOMotorCollection = db.task_execution_controls
    controls = await controls_collection.find({"task_id": task_id}).to_list(length=None)

    return {
        "task": task,
        "master_plan": plan,
        "phase_executions": executions,
        "execution_controls": controls,
        "can_start_execution": task["status"] == TaskStatus.APPROVED,
        "can_pause_execution": task["status"] == TaskStatus.EXECUTING,
        "can_resume_execution": task["status"] in [TaskStatus.PHASE_READY, TaskStatus.PHASE_REVIEW]
    }
