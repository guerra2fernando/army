"""
Orchestrator API Routes
"""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional, Dict, Any, List

from app.utils.auth import get_current_user
from app.orchestrator.agent_00 import get_orchestrator, OrchestratorResponse
from app.models.user import User
from app.orchestrator.task_router import TaskRouter

router = APIRouter(prefix="/orchestrator", tags=["Orchestrator"])


class CommandRequest(BaseModel):
    """User command request."""
    command: str
    context: Optional[Dict[str, Any]] = None


class CommandResponse(BaseModel):
    """Command response."""
    success: bool
    message: str
    task_created: bool = False
    task_id: Optional[str] = None
    agent_target: Optional[str] = None
    requires_clarification: bool = False
    clarification_question: Optional[str] = None
    data: Optional[Dict[str, Any]] = None


class CapabilitiesResponse(BaseModel):
    """Capabilities response."""
    agents: Dict[str, List[str]]
    categories: List[str]


class StatusResponse(BaseModel):
    """Status response."""
    status: str
    agents: Optional[Dict[str, int]] = None
    tasks: Optional[Dict[str, int]] = None
    timestamp: Optional[str] = None
    error: Optional[str] = None


@router.post("/command", response_model=CommandResponse)
async def execute_command(
    request: CommandRequest,
    current_user: User = Depends(get_current_user)
):
    """
    Execute a natural language command.
    
    The Orchestrator will:
    1. Parse the command intent
    2. Route to the appropriate agent
    3. Create a task if needed
    4. Return status and any immediate results
    """
    orchestrator = get_orchestrator()
    
    response = await orchestrator.process_command(
        command=request.command,
        user_id=current_user.user_id,
        context=request.context
    )
    
    return CommandResponse(**response.to_dict())


@router.get("/capabilities", response_model=CapabilitiesResponse)
async def get_capabilities(current_user: dict = Depends(get_current_user)):
    """Get available capabilities and agents."""
    task_router = TaskRouter()
    
    return CapabilitiesResponse(
        agents=task_router.AGENT_ACTIONS,
        categories=list(task_router.INTENT_TO_AGENT.keys())
    )


@router.get("/status", response_model=StatusResponse)
async def get_status(current_user: dict = Depends(get_current_user)):
    """Get orchestrator and system status."""
    orchestrator = get_orchestrator()
    status = await orchestrator._get_system_status()
    return StatusResponse(**status)

