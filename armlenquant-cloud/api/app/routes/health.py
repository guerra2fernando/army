"""
System Health Routes
"""
from datetime import datetime
from fastapi import APIRouter, Depends
from loguru import logger

from app.db import Database
from app.models.base import APIResponse
from app.utils.auth import get_current_user

router = APIRouter(prefix="/health", tags=["Health"])


@router.get("")
async def health_check():
    """Basic health check (no auth required)."""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "service": "armlenquant-api"
    }


@router.get("/detailed", response_model=APIResponse)
async def detailed_health(current_user: dict = Depends(get_current_user)):
    """Detailed health check with database status."""
    
    try:
        # Check MongoDB
        await Database.client.admin.command('ping')
        db_status = "connected"
    except Exception as e:
        db_status = f"error: {str(e)}"
    
    # Get agent statuses
    agents = Database.get_collection("agent_registry")
    agent_count = await agents.count_documents({})
    active_agents = await agents.count_documents({"status": "ACTIVE"})
    
    # Get task queue stats
    tasks = Database.get_collection("task_queue")
    pending_tasks = await tasks.count_documents({"status": "PENDING"})
    in_progress_tasks = await tasks.count_documents({"status": "IN_PROGRESS"})
    
    return APIResponse(
        success=True,
        data={
            "status": "healthy" if db_status == "connected" else "degraded",
            "timestamp": datetime.utcnow().isoformat(),
            "database": db_status,
            "agents": {
                "total": agent_count,
                "active": active_agents
            },
            "task_queue": {
                "pending": pending_tasks,
                "in_progress": in_progress_tasks
            }
        }
    )

