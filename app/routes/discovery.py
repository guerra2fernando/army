"""
Discovery routes for job and commercial opportunity intake.
"""
from datetime import datetime
from uuid import uuid4
from typing import List, Optional

from fastapi import APIRouter, Depends, Query

from app.db import Database
from app.models.task import TaskStatus
from app.models.user import User
from app.models.opportunity import (
    CommercialDiscoveryRunCreate,
    CommercialDiscoveryScheduleCreate,
    DiscoveryRun,
    DiscoveryTriggerResponse,
    JobDiscoveryRunCreate,
    JobDiscoveryScheduleCreate,
    OpportunityImportRequest,
    OpportunityKind,
    OpportunityLane,
    OpportunityRecord,
    OpportunityStatus,
)
from app.utils.auth import get_current_user
from app.services.discovery_service import get_discovery_service

router = APIRouter(prefix="/discovery", tags=["Discovery"])


def _job_discovery_payload(request: JobDiscoveryRunCreate, run_id: str) -> dict:
    return {
        "action": "search",
        "roles": request.roles,
        "locations": request.locations,
        "sources": request.sources,
        "limit": request.limit,
        "profile_slug": request.profile_slug,
        "discovery_run_id": run_id,
    }


def _commercial_lane(slug: str) -> OpportunityLane:
    normalized = (slug or "").strip().upper()
    if normalized == "LENQUANT":
        return OpportunityLane.LENQUANT
    if normalized == "LENXYS":
        return OpportunityLane.LENXYS
    if normalized == "SERVICES":
        return OpportunityLane.SERVICES
    if normalized == "TRADING":
        return OpportunityLane.TRADING
    return OpportunityLane.COMMERCIAL


def _commercial_discovery_payload(request: CommercialDiscoveryRunCreate, run_id: str) -> dict:
    return {
        "action": "discover_leads",
        "business_slug": request.business_slug,
        "personas": request.personas,
        "keywords": request.keywords,
        "locations": request.locations,
        "limit": request.limit,
        "lane": _commercial_lane(request.business_slug).value,
        "discovery_run_id": run_id,
    }


@router.post("/jobs/run", response_model=DiscoveryTriggerResponse)
async def run_job_discovery(request: JobDiscoveryRunCreate, current_user: User = Depends(get_current_user)):
    """Create an immediate job discovery task."""
    service = get_discovery_service()
    run_id = await service.create_run(
        kind=OpportunityKind.JOB,
        lane=OpportunityLane.JOBS,
        created_by=current_user.user_id,
        payload=request.model_dump(),
        profile_slug=request.profile_slug,
    )

    task_id = str(uuid4())
    payload = _job_discovery_payload(request, run_id)
    await Database.get_collection("task_queue").insert_one(
        {
            "_id": task_id,
            "task_id": task_id,
            "idempotency_key": f"job-discovery-{run_id}",
            "agent_target": "JOB_HUNTER",
            "payload": payload,
            "title": "Job discovery run",
            "status": TaskStatus.PENDING.value,
            "priority": request.priority,
            "worker_id": None,
            "picked_up_by": None,
            "lease_until": None,
            "last_execution_started": None,
            "execution_count": 0,
            "retry_count": 0,
            "max_retries": 3,
            "error_log": [],
            "result": None,
            "created_by": current_user.user_id,
            "recurring": False,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
        }
    )
    await service.attach_run_task(run_id, task_id=task_id)
    return DiscoveryTriggerResponse(run_id=run_id, task_id=task_id, status="RUNNING")


@router.post("/jobs/schedule", response_model=DiscoveryTriggerResponse)
async def schedule_job_discovery(
    request: JobDiscoveryScheduleCreate,
    current_user: User = Depends(get_current_user),
):
    """Create a scheduled job discovery task."""
    service = get_discovery_service()
    run_id = await service.create_run(
        kind=OpportunityKind.JOB,
        lane=OpportunityLane.JOBS,
        created_by=current_user.user_id,
        payload=request.model_dump(),
        profile_slug=request.profile_slug,
        status="SCHEDULED",
        scheduled_time=request.scheduled_time,
    )
    scheduled_task_id = str(uuid4())
    await Database.get_collection("scheduled_tasks").insert_one(
        {
            "_id": scheduled_task_id,
            "task_id": scheduled_task_id,
            "agent_target": "JOB_HUNTER",
            "payload": _job_discovery_payload(request, run_id),
            "scheduled_time": request.scheduled_time,
            "title": "Scheduled job discovery",
            "original_command": "Scheduled job discovery run",
            "created_by": current_user.user_id,
            "created_at": datetime.utcnow(),
            "executed": False,
            "cancelled": False,
            "executed_at": None,
            "priority": request.priority,
            "recurring": request.recurring,
            "last_scheduled": None,
        }
    )
    await service.attach_run_task(run_id, scheduled_task_id=scheduled_task_id)
    return DiscoveryTriggerResponse(run_id=run_id, scheduled_task_id=scheduled_task_id, status="SCHEDULED")


@router.post("/commercial/run", response_model=DiscoveryTriggerResponse)
async def run_commercial_discovery(request: CommercialDiscoveryRunCreate, current_user: User = Depends(get_current_user)):
    """Create an immediate commercial discovery task."""
    service = get_discovery_service()
    lane = _commercial_lane(request.business_slug)
    run_id = await service.create_run(
        kind=OpportunityKind.COMMERCIAL,
        lane=lane,
        created_by=current_user.user_id,
        payload=request.model_dump(),
        business_slug=request.business_slug,
    )
    task_id = str(uuid4())
    payload = _commercial_discovery_payload(request, run_id)
    await Database.get_collection("task_queue").insert_one(
        {
            "_id": task_id,
            "task_id": task_id,
            "idempotency_key": f"commercial-discovery-{run_id}",
            "agent_target": "COMMERCIAL_SCOUT",
            "payload": payload,
            "title": f"Commercial discovery {request.business_slug}",
            "status": TaskStatus.PENDING.value,
            "priority": request.priority,
            "worker_id": None,
            "picked_up_by": None,
            "lease_until": None,
            "last_execution_started": None,
            "execution_count": 0,
            "retry_count": 0,
            "max_retries": 3,
            "error_log": [],
            "result": None,
            "created_by": current_user.user_id,
            "recurring": False,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
        }
    )
    await service.attach_run_task(run_id, task_id=task_id)
    return DiscoveryTriggerResponse(run_id=run_id, task_id=task_id, status="RUNNING")


@router.post("/commercial/schedule", response_model=DiscoveryTriggerResponse)
async def schedule_commercial_discovery(
    request: CommercialDiscoveryScheduleCreate,
    current_user: User = Depends(get_current_user),
):
    """Create a scheduled commercial discovery task."""
    service = get_discovery_service()
    lane = _commercial_lane(request.business_slug)
    run_id = await service.create_run(
        kind=OpportunityKind.COMMERCIAL,
        lane=lane,
        created_by=current_user.user_id,
        payload=request.model_dump(),
        business_slug=request.business_slug,
        status="SCHEDULED",
        scheduled_time=request.scheduled_time,
    )
    scheduled_task_id = str(uuid4())
    await Database.get_collection("scheduled_tasks").insert_one(
        {
            "_id": scheduled_task_id,
            "task_id": scheduled_task_id,
            "agent_target": "COMMERCIAL_SCOUT",
            "payload": _commercial_discovery_payload(request, run_id),
            "scheduled_time": request.scheduled_time,
            "title": f"Scheduled commercial discovery {request.business_slug}",
            "original_command": "Scheduled commercial discovery run",
            "created_by": current_user.user_id,
            "created_at": datetime.utcnow(),
            "executed": False,
            "cancelled": False,
            "executed_at": None,
            "priority": request.priority,
            "recurring": request.recurring,
            "last_scheduled": None,
        }
    )
    await service.attach_run_task(run_id, scheduled_task_id=scheduled_task_id)
    return DiscoveryTriggerResponse(run_id=run_id, scheduled_task_id=scheduled_task_id, status="SCHEDULED")


@router.post("/opportunities/import", response_model=DiscoveryTriggerResponse)
async def import_opportunities(request: OpportunityImportRequest, current_user: User = Depends(get_current_user)):
    """Import discovered opportunities directly into the cloud source of truth."""
    service = get_discovery_service()
    if not request.items:
        raise ValueError("Import requires at least one item")
    first = request.items[0]
    run_id = await service.create_run(
        kind=first.kind,
        lane=first.lane,
        created_by=current_user.user_id,
        payload={"count": len(request.items)},
        profile_slug=first.profile_slug,
        business_slug=first.business_slug,
    )
    await service.ingest_items(
        kind=first.kind,
        lane=first.lane,
        items=[item.model_dump() for item in request.items],
        profile_slug=first.profile_slug,
        business_slug=first.business_slug,
        discovery_run_id=run_id,
    )
    return DiscoveryTriggerResponse(run_id=run_id, status="COMPLETED")


@router.get("/opportunities", response_model=List[OpportunityRecord])
async def list_opportunities(
    kind: Optional[OpportunityKind] = None,
    lane: Optional[OpportunityLane] = None,
    status: Optional[OpportunityStatus] = Query(default=None),
    business_slug: Optional[str] = None,
    profile_slug: Optional[str] = None,
    limit: int = Query(default=50, le=200),
    current_user: User = Depends(get_current_user),
):
    """List persisted opportunities."""
    query = {}
    if kind:
        query["kind"] = kind.value
    if lane:
        query["lane"] = lane.value
    if status:
        query["status"] = status.value
    if business_slug:
        query["business_slug"] = business_slug
    if profile_slug:
        query["profile_slug"] = profile_slug
    docs = await Database.get_collection("opportunities").find(query).sort("last_seen_at", -1).limit(limit).to_list(length=limit)
    return [OpportunityRecord(**doc) for doc in docs]


@router.get("/runs", response_model=List[DiscoveryRun])
async def list_discovery_runs(
    limit: int = Query(default=50, le=200),
    current_user: User = Depends(get_current_user),
):
    """List discovery runs."""
    docs = await Database.get_collection("discovery_runs").find({}).sort("created_at", -1).limit(limit).to_list(length=limit)
    return [DiscoveryRun(**doc) for doc in docs]
