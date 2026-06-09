"""
Master Plan API Routes
"""
from fastapi import APIRouter, HTTPException, Depends
from typing import List
from app.models.master_plan import MasterPlan, MasterPlanCreate, MasterPlanResponse
from app.models.task import TaskStatus
from app.db import get_db
from app.utils.auth import get_current_user
from app.models.user import User
from motor.motor_asyncio import AsyncIOMotorCollection
import uuid
from datetime import datetime

router = APIRouter()


@router.post("/tasks/{task_id}/plans", response_model=MasterPlanResponse)
async def create_master_plan(
    task_id: str,
    plan_data: MasterPlanCreate,
    current_user: User = Depends(get_current_user),
    db=Depends(get_db)
):
    """Create a master plan for a task."""

    # Verify task exists and is in planning state
    tasks_collection: AsyncIOMotorCollection = db.task_queue
    task = await tasks_collection.find_one({"task_id": task_id})

    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    if task["status"] not in [TaskStatus.PENDING, TaskStatus.PLANNING]:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot create plan for task in {task['status']} status"
        )

    # Check if plan already exists
    plans_collection: AsyncIOMotorCollection = db.task_master_plans
    existing_plan = await plans_collection.find_one({"task_id": task_id})
    if existing_plan:
        raise HTTPException(status_code=400, detail="Plan already exists for this task")

    # Create plan
    plan_id = str(uuid.uuid4())
    plan = MasterPlan(
        plan_id=plan_id,
        **plan_data.model_dump()
    )

    await plans_collection.insert_one(plan.model_dump())

    # Update task status to PLAN_READY
    await tasks_collection.update_one(
        {"task_id": task_id},
        {"$set": {"status": TaskStatus.PLAN_READY}}
    )

    return MasterPlanResponse(**plan.model_dump())


@router.get("/tasks/{task_id}/plan", response_model=MasterPlanResponse)
async def get_master_plan(
    task_id: str,
    current_user: User = Depends(get_current_user),
    db=Depends(get_db)
):
    """Get master plan for a task."""

    plans_collection: AsyncIOMotorCollection = db.task_master_plans
    plan = await plans_collection.find_one({"task_id": task_id})

    if not plan:
        raise HTTPException(status_code=404, detail="Master plan not found")

    return MasterPlanResponse(**plan)


@router.post("/tasks/{task_id}/plans/{plan_id}/approve")
async def approve_master_plan(
    task_id: str,
    plan_id: str,
    current_user: User = Depends(get_current_user),
    db=Depends(get_db)
):
    """Approve a master plan and start execution."""

    # Verify plan exists
    plans_collection: AsyncIOMotorCollection = db.task_master_plans
    plan = await plans_collection.find_one({"plan_id": plan_id, "task_id": task_id})

    if not plan:
        raise HTTPException(status_code=404, detail="Master plan not found")

    if plan.get("approved_at"):
        raise HTTPException(status_code=400, detail="Plan already approved")

    # Update plan with approval
    await plans_collection.update_one(
        {"plan_id": plan_id},
        {
            "$set": {
                "approved_at": datetime.utcnow(),
                "approved_by": current_user.user_id
            }
        }
    )

    # Update task status to APPROVED
    tasks_collection: AsyncIOMotorCollection = db.task_queue
    await tasks_collection.update_one(
        {"task_id": task_id},
        {"$set": {"status": TaskStatus.APPROVED}}
    )

    return {"message": "Plan approved successfully", "next_action": "start_execution"}


@router.post("/tasks/{task_id}/plans/{plan_id}/reject")
async def reject_master_plan(
    task_id: str,
    plan_id: str,
    rejection_reason: str = None,
    current_user: User = Depends(get_current_user),
    db=Depends(get_db)
):
    """Reject a master plan."""

    # Verify plan exists
    plans_collection: AsyncIOMotorCollection = db.task_master_plans
    plan = await plans_collection.find_one({"plan_id": plan_id, "task_id": task_id})

    if not plan:
        raise HTTPException(status_code=404, detail="Master plan not found")

    if plan.get("approved_at"):
        raise HTTPException(status_code=400, detail="Cannot reject an approved plan")

    # Delete the plan
    await plans_collection.delete_one({"plan_id": plan_id})

    # Update task status back to PENDING
    tasks_collection: AsyncIOMotorCollection = db.task_queue
    await tasks_collection.update_one(
        {"task_id": task_id},
        {
            "$set": {"status": TaskStatus.PENDING},
            "$push": {"error_log": f"Plan rejected by {current_user.email}: {rejection_reason or 'No reason provided'}"}
        }
    )

    return {"message": "Plan rejected and task reset to pending"}


@router.put("/tasks/{task_id}/plans/{plan_id}/modify")
async def modify_master_plan(
    task_id: str,
    plan_id: str,
    modifications: dict,
    current_user: User = Depends(get_current_user),
    db=Depends(get_db)
):
    """Modify a master plan."""

    # Verify plan exists
    plans_collection: AsyncIOMotorCollection = db.task_master_plans
    plan = await plans_collection.find_one({"plan_id": plan_id, "task_id": task_id})

    if not plan:
        raise HTTPException(status_code=404, detail="Master plan not found")

    if plan.get("approved_at"):
        raise HTTPException(status_code=400, detail="Cannot modify an approved plan")

    # Update plan with modifications
    await plans_collection.update_one(
        {"plan_id": plan_id},
        {"$set": modifications}
    )

    return {"message": "Plan modified successfully"}
