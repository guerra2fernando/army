"""
Discovery persistence and deduplication service.
"""
from datetime import datetime, timedelta
import hashlib
from typing import Any, Dict, Iterable, List, Optional, Tuple
from urllib.parse import urlparse

from app.db import Database
from app.models.opportunity import (
    DiscoveryRunStatus,
    OpportunityKind,
    OpportunityLane,
    OpportunityRecord,
    OpportunityStatus,
    SourcePlatform,
    new_opportunity_id,
)
from app.services.opportunity_router import get_opportunity_router


class DiscoveryService:
    """Service for discovery runs and opportunity ingestion."""

    def __init__(self):
        self.opportunities = Database.get_collection("opportunities")
        self.discovery_runs = Database.get_collection("discovery_runs")

    @staticmethod
    def normalize_url(url: str) -> str:
        """Normalize source URL for deduplication."""
        parsed = urlparse((url or "").strip())
        path = parsed.path.rstrip("/")
        return f"{parsed.scheme.lower()}://{parsed.netloc.lower()}{path}"

    @classmethod
    def build_dedupe_key(cls, kind: OpportunityKind, url: str) -> str:
        normalized = cls.normalize_url(url)
        return hashlib.sha256(f"{kind.value}|{normalized}".encode("utf-8")).hexdigest()

    @staticmethod
    def detect_source_platform(url: str, fallback: Optional[str] = None) -> SourcePlatform:
        """Infer source platform from URL or source string."""
        raw = (fallback or "").strip().lower()
        normalized = url.lower()
        if "linkedin.com" in normalized or raw == "linkedin":
            return SourcePlatform.LINKEDIN
        if "lever.co" in normalized or raw == "lever":
            return SourcePlatform.LEVER
        if "greenhouse.io" in normalized or raw == "greenhouse":
            return SourcePlatform.GREENHOUSE
        if "ashbyhq.com" in normalized or raw == "ashby":
            return SourcePlatform.ASHBY
        if "workable.com" in normalized or raw == "workable":
            return SourcePlatform.WORKABLE
        if raw == "google":
            return SourcePlatform.GOOGLE
        if raw == "company_website":
            return SourcePlatform.COMPANY_WEBSITE
        return SourcePlatform.OTHER

    @staticmethod
    def _freshness_window(kind: OpportunityKind) -> timedelta:
        return timedelta(days=3 if kind == OpportunityKind.JOB else 7)

    async def create_run(
        self,
        *,
        kind: OpportunityKind,
        lane: OpportunityLane,
        created_by: str,
        payload: Dict[str, Any],
        profile_slug: Optional[str] = None,
        business_slug: Optional[str] = None,
        status: DiscoveryRunStatus = DiscoveryRunStatus.PENDING,
        scheduled_time: Optional[datetime] = None,
    ) -> str:
        run_id = new_opportunity_id()
        status_value = status.value if hasattr(status, "value") else str(status)
        await self.discovery_runs.insert_one(
            {
                "_id": run_id,
                "run_id": run_id,
                "kind": kind.value,
                "lane": lane.value,
                "status": status_value,
                "created_by": created_by,
                "payload": payload,
                "profile_slug": profile_slug,
                "business_slug": business_slug,
                "scheduled_time": scheduled_time,
                "persisted_count": 0,
                "deduped_count": 0,
                "created_at": datetime.utcnow(),
                "updated_at": datetime.utcnow(),
                "completed_at": None,
                "error": None,
            }
        )
        return run_id

    async def attach_run_task(self, run_id: str, *, task_id: Optional[str] = None, scheduled_task_id: Optional[str] = None):
        await self.discovery_runs.update_one(
            {"run_id": run_id},
            {
                "$set": {
                    "task_id": task_id,
                    "scheduled_task_id": scheduled_task_id,
                    "status": DiscoveryRunStatus.SCHEDULED.value if scheduled_task_id else DiscoveryRunStatus.RUNNING.value,
                    "updated_at": datetime.utcnow(),
                }
            },
        )

    async def mark_run_failed(self, run_id: str, error: str):
        await self.discovery_runs.update_one(
            {"run_id": run_id},
            {
                "$set": {
                    "status": DiscoveryRunStatus.FAILED.value,
                    "error": error,
                    "completed_at": datetime.utcnow(),
                    "updated_at": datetime.utcnow(),
                }
            },
        )

    async def ingest_items(
        self,
        *,
        kind: OpportunityKind,
        lane: OpportunityLane,
        items: Iterable[Dict[str, Any]],
        profile_slug: Optional[str] = None,
        business_slug: Optional[str] = None,
        discovery_run_id: Optional[str] = None,
    ) -> Tuple[int, int]:
        persisted = 0
        deduped = 0
        now = datetime.utcnow()
        freshness_window = self._freshness_window(kind)

        for item in items:
            url = item.get("source_url") or item.get("url")
            if not url:
                continue

            dedupe_key = self.build_dedupe_key(kind, url)
            existing = await self.opportunities.find_one({"dedupe_key": dedupe_key})
            source_platform = self.detect_source_platform(url, item.get("source_platform") or item.get("source"))
            doc = {
                "kind": kind.value,
                "lane": lane.value,
                "status": OpportunityStatus.FRESH.value,
                "title": item.get("title", ""),
                "company": item.get("company", ""),
                "person_name": item.get("person_name", ""),
                "location": item.get("location", ""),
                "source_platform": source_platform.value,
                "source_url": self.normalize_url(url),
                "profile_slug": profile_slug or item.get("profile_slug"),
                "business_slug": business_slug or item.get("business_slug"),
                "discovery_run_id": discovery_run_id,
                "source_data": item.get("source_data", item),
                "reasons": item.get("reasons", []),
                "confidence": item.get("confidence", 0.5),
                "last_seen_at": now,
                "freshness_expires_at": now + freshness_window,
                "recrawl_after": now + freshness_window,
                "updated_at": now,
            }

            if existing:
                deduped += 1
                await self.opportunities.update_one(
                    {"_id": existing["_id"]},
                    {
                        "$set": doc,
                        "$inc": {"seen_count": 1},
                    },
                )
                persisted_doc = await self.opportunities.find_one({"_id": existing["_id"]})
            else:
                persisted += 1
                opportunity_id = new_opportunity_id()
                await self.opportunities.insert_one(
                    {
                        "_id": opportunity_id,
                        "opportunity_id": opportunity_id,
                        "dedupe_key": dedupe_key,
                        "first_seen_at": now,
                        "seen_count": 1,
                        "created_at": now,
                        **doc,
                    }
                )
                persisted_doc = await self.opportunities.find_one({"_id": opportunity_id})

            if persisted_doc:
                await get_opportunity_router().route_and_persist(persisted_doc)

        if discovery_run_id:
            await self.discovery_runs.update_one(
                {"run_id": discovery_run_id},
                {
                    "$set": {
                        "status": DiscoveryRunStatus.COMPLETED.value,
                        "persisted_count": persisted,
                        "deduped_count": deduped,
                        "completed_at": now,
                        "updated_at": now,
                    }
                },
            )

        return persisted, deduped

    async def ingest_task_result(self, task_doc: Dict[str, Any], task_result: Dict[str, Any]) -> Tuple[int, int]:
        """Ingest discovery results from completed tasks."""
        payload = task_doc.get("payload", {})
        result_data = (task_result or {}).get("data", {})
        discovery_run_id = payload.get("discovery_run_id")

        if task_doc.get("agent_target") == "JOB_HUNTER" and payload.get("action") == "search":
            jobs = result_data.get("jobs", [])
            return await self.ingest_items(
                kind=OpportunityKind.JOB,
                lane=OpportunityLane.JOBS,
                items=[
                    {
                        "title": item.get("title", ""),
                        "company": item.get("company", ""),
                        "location": item.get("location", ""),
                        "source_platform": item.get("source"),
                        "source_url": item.get("url"),
                        "profile_slug": payload.get("profile_slug"),
                        "source_data": item,
                        "reasons": ["job_search_discovery"],
                        "confidence": 0.7,
                    }
                    for item in jobs
                ],
                profile_slug=payload.get("profile_slug"),
                discovery_run_id=discovery_run_id,
            )

        if task_doc.get("agent_target") == "COMMERCIAL_SCOUT" and payload.get("action") == "discover_leads":
            leads = result_data.get("leads", [])
            lane = OpportunityLane(payload.get("lane", "COMMERCIAL"))
            return await self.ingest_items(
                kind=OpportunityKind.COMMERCIAL,
                lane=lane,
                items=[
                    {
                        "title": item.get("title", ""),
                        "company": item.get("company", ""),
                        "person_name": item.get("person_name", ""),
                        "location": item.get("location", ""),
                        "source_platform": item.get("source"),
                        "source_url": item.get("url"),
                        "business_slug": payload.get("business_slug"),
                        "source_data": item,
                        "reasons": ["commercial_discovery"],
                        "confidence": 0.65,
                    }
                    for item in leads
                ],
                business_slug=payload.get("business_slug"),
                discovery_run_id=discovery_run_id,
            )

        return 0, 0


def get_discovery_service() -> DiscoveryService:
    """Return discovery service."""

    return DiscoveryService()
