"""
Commercial Ops review queue, guardrail, and follow-up lifecycle service.
"""
import hashlib
import json
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
from uuid import uuid4

from fastapi import HTTPException, status

from app.db import Database
from app.models.commercial_ops import (
    DraftMessage,
    FollowupDraft,
    FollowupPlan,
    FollowupStatus,
    ReviewActionType,
    ReviewHistoryEntry,
    ReviewItemKind,
    ReviewQueueActionRequest,
    ReviewQueueItem,
    ReviewQueueStatus,
    SendIntent,
    SendIntentStatus,
    SendResult,
    SpecialistProfileBinding,
)
from app.models.opportunity import OpportunityKind, OpportunityLane
from app.models.profiles import CommercialPolicy, OutreachChannel
from app.models.task import TaskStatus


class CommercialOpsService:
    """Persistence and lifecycle helpers for Commercial Ops."""

    ACTIVE_SEND_STATUSES = [
        SendIntentStatus.READY.value,
        SendIntentStatus.DISPATCHED.value,
        SendIntentStatus.SENT.value,
        SendIntentStatus.MANUAL.value,
    ]

    def __init__(self):
        self.review_queue = Database.get_collection("review_queue")
        self.routes = Database.get_collection("opportunity_routes")
        self.send_intents = Database.get_collection("send_intents")
        self.send_results = Database.get_collection("send_results")
        self.followup_plans = Database.get_collection("followup_plans")
        self.task_queue = Database.get_collection("task_queue")
        self.commercial_policies = Database.get_collection("commercial_policies")
        self.operator_profiles = Database.get_collection("operator_profiles")
        self.business_profiles = Database.get_collection("business_profiles")

    async def create_review_item_from_task_result(self, task_doc: Dict[str, Any], task_result: Dict[str, Any]) -> Optional[str]:
        """Persist a review item if a specialist draft package was produced."""
        package = ((task_result or {}).get("data") or {}).get("draft_package")
        if not isinstance(package, dict):
            return None

        review_id = str(uuid4())
        opportunity_id = package.get("opportunity_id")
        route_doc = await self.routes.find_one({"opportunity_id": opportunity_id}) if opportunity_id else None

        history = [
            ReviewHistoryEntry(
                action=ReviewActionType.EDIT,
                acted_by=task_doc.get("agent_target", "SYSTEM"),
                note="Draft package created by specialist task.",
            ).model_dump(mode="json")
        ]
        item = ReviewQueueItem(
            review_id=review_id,
            opportunity_id=opportunity_id,
            route_id=route_doc.get("route_id") if route_doc else None,
            source_url=package["source_url"],
            kind=OpportunityKind.JOB if package.get("lane") == OpportunityLane.JOBS.value else OpportunityKind.COMMERCIAL,
            lane=OpportunityLane(package["lane"]),
            specialist=package["specialist"],
            target_persona=package["target_persona"],
            status=ReviewQueueStatus.PENDING,
            confidence=float(package.get("fit_score", 0.0)),
            profile_binding=SpecialistProfileBinding(**package.get("profile_binding", {})),
            recommended_channel=package.get("recommended_channel", OutreachChannel.MANUAL.value),
            rationale=package.get("rationale", []),
            recommended_next_step=package.get("recommended_next_step", "Review before sending."),
            primary_draft=DraftMessage(**package["primary_draft"]),
            followups=[FollowupDraft(**entry) for entry in package.get("followups", [])],
            draft_metadata=package.get("metadata", {}),
            workflow_id=task_doc.get("workflow_id"),
            task_id=task_doc.get("task_id"),
            history=history,
        )

        pending_states = [
            ReviewQueueStatus.PENDING.value,
            ReviewQueueStatus.PAUSED.value,
            ReviewQueueStatus.BLOCKED.value,
        ]
        await self.review_queue.update_one(
            {
                "opportunity_id": item.opportunity_id,
                "review_kind": ReviewItemKind.INITIAL.value,
                "status": {"$in": pending_states},
            },
            {"$setOnInsert": {"_id": review_id, **item.model_dump(mode="json")}},
            upsert=True,
        )
        existing = await self.review_queue.find_one(
            {
                "opportunity_id": item.opportunity_id,
                "review_kind": ReviewItemKind.INITIAL.value,
                "status": {"$in": pending_states},
            }
        )
        return existing.get("review_id") if existing else review_id

    async def list_review_items(self, filters: Dict[str, Any]) -> List[Dict[str, Any]]:
        """List review queue items with optional filters."""
        query: Dict[str, Any] = {}
        for key in ["status", "lane", "target_persona", "recommended_channel", "review_kind"]:
            if filters.get(key):
                value = filters[key]
                query[key] = value.value if hasattr(value, "value") else value
        if filters.get("profile_slug"):
            query["profile_binding.operator_profile_slug"] = filters["profile_slug"]
        if filters.get("business_slug"):
            query["profile_binding.business_profile_slug"] = filters["business_slug"]
        if filters.get("company"):
            query["draft_metadata.company"] = filters["company"]
        cursor = self.review_queue.find(query).sort("created_at", -1).limit(filters.get("limit", 100))
        return await cursor.to_list(length=filters.get("limit", 100))

    async def get_review_item(self, review_id: str) -> Dict[str, Any]:
        item = await self.review_queue.find_one({"review_id": review_id})
        if not item:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Review item not found")
        return item

    async def apply_review_action(self, review_id: str, action: ReviewActionType, payload: ReviewQueueActionRequest, actor: str) -> Dict[str, Any]:
        """Apply review-state transitions."""
        item = await self.get_review_item(review_id)
        update: Dict[str, Any] = {"updated_at": datetime.utcnow(), "latest_note": payload.note}
        note = payload.note
        changes: Dict[str, Any] = {}

        if action == ReviewActionType.APPROVE:
            send_intent = await self.ensure_send_intent(item, actor)
            update["send_intent_id"] = send_intent["send_intent_id"]
            update["blocked_reasons"] = send_intent.get("blocked_reasons", [])
            update["status"] = ReviewQueueStatus.BLOCKED.value if send_intent.get("blocked_reasons") else ReviewQueueStatus.APPROVED.value
            changes["send_intent_id"] = send_intent["send_intent_id"]
            if send_intent.get("blocked_reasons"):
                changes["blocked_reasons"] = send_intent["blocked_reasons"]
        elif action == ReviewActionType.REJECT:
            update["status"] = ReviewQueueStatus.REJECTED.value
        elif action == ReviewActionType.ARCHIVE:
            update["status"] = ReviewQueueStatus.ARCHIVED.value
            update["archived_reason"] = note
        elif action == ReviewActionType.PAUSE_FOLLOWUP:
            update["status"] = ReviewQueueStatus.PAUSED.value
            update["paused_followup"] = True
            plan = await self._upsert_followup_plan(item, paused=True, note=note)
            self._apply_followup_summary(update, plan)
        elif action == ReviewActionType.RESUME_FOLLOWUP:
            update["paused_followup"] = False
            if item.get("status") == ReviewQueueStatus.PAUSED.value:
                update["status"] = ReviewQueueStatus.PENDING.value
            plan = await self.resume_followup_for_review(review_id, actor=actor, note=note)
            self._apply_followup_summary(update, plan)
        elif action == ReviewActionType.CANCEL_FOLLOWUP:
            plan = await self.cancel_followup_for_review(review_id, actor=actor, reason=note)
            self._apply_followup_summary(update, plan)
        elif action == ReviewActionType.MARK_REPLIED:
            plan = await self.mark_followup_replied(review_id=review_id, actor=actor, note=note)
            self._apply_followup_summary(update, plan)
        elif action == ReviewActionType.EDIT:
            if payload.updated_draft:
                update["primary_draft"] = payload.updated_draft.model_dump(mode="json")
                changes["primary_draft"] = update["primary_draft"]
            if payload.updated_followups is not None:
                update["followups"] = [entry.model_dump(mode="json") for entry in payload.updated_followups]
                changes["followups"] = update["followups"]
                plan = await self._upsert_followup_plan({**item, "followups": update["followups"]}, paused=bool(item.get("paused_followup")))
                self._apply_followup_summary(update, plan)
            guardrails = await self.evaluate_guardrails({**item, **update}, update.get("primary_draft"))
            update["blocked_reasons"] = guardrails
            if guardrails and item.get("status") == ReviewQueueStatus.APPROVED.value:
                update["status"] = ReviewQueueStatus.BLOCKED.value
        elif action == ReviewActionType.REROUTE:
            update["status"] = ReviewQueueStatus.REROUTED.value
            for field in ["lane", "specialist", "target_persona", "recommended_channel"]:
                value = getattr(payload, field)
                if value is not None:
                    update[field] = value.value if hasattr(value, "value") else value
                    changes[field] = update[field]

        history_entry = ReviewHistoryEntry(
            action=action,
            acted_by=actor,
            note=note,
            changes=changes,
        ).model_dump(mode="json")

        await self.review_queue.update_one(
            {"review_id": review_id},
            {"$set": update, "$push": {"history": history_entry}},
        )
        return await self.get_review_item(review_id)

    async def ensure_send_intent(self, review_item: Dict[str, Any], approved_by: str) -> Dict[str, Any]:
        """Create or return an idempotent send intent for a review item."""
        draft = review_item["primary_draft"]
        channel = draft.get("channel", review_item.get("recommended_channel", OutreachChannel.MANUAL.value))
        idempotency_key = self._build_send_idempotency_key(review_item, draft)
        guardrails = await self.evaluate_guardrails(review_item, draft)
        existing = await self.send_intents.find_one({"idempotency_key": idempotency_key})
        if existing:
            if existing.get("blocked_reasons") != guardrails:
                await self.send_intents.update_one(
                    {"send_intent_id": existing["send_intent_id"]},
                    {"$set": {"blocked_reasons": guardrails, "updated_at": datetime.utcnow()}},
                )
                existing = await self.send_intents.find_one({"send_intent_id": existing["send_intent_id"]})
            await self.review_queue.update_one(
                {"review_id": review_item["review_id"]},
                {
                    "$set": {
                        "send_intent_id": existing["send_intent_id"],
                        "blocked_reasons": guardrails,
                        "status": ReviewQueueStatus.BLOCKED.value if guardrails else ReviewQueueStatus.APPROVED.value,
                        "updated_at": datetime.utcnow(),
                    }
                },
            )
            return existing

        followup_plan = await self._upsert_followup_plan(review_item, paused=bool(review_item.get("paused_followup")))
        followup_plan_id = followup_plan.get("followup_id") if followup_plan else review_item.get("followup_plan_id")
        send_intent_id = str(uuid4())
        is_followup = review_item.get("review_kind") == ReviewItemKind.FOLLOWUP.value
        intent = SendIntent(
            send_intent_id=send_intent_id,
            review_id=review_item["review_id"],
            opportunity_id=review_item.get("opportunity_id"),
            status=SendIntentStatus.READY,
            channel=channel,
            profile_binding=SpecialistProfileBinding(**review_item.get("profile_binding", {})),
            idempotency_key=idempotency_key,
            cooldown_key=self._build_cooldown_key(review_item, channel),
            blocked_reasons=guardrails,
            followup_plan_id=followup_plan_id,
            followup_step=review_item.get("followup_step"),
            is_followup=is_followup,
            approved_by=approved_by,
            approved_at=datetime.utcnow(),
            payload={
                "review_id": review_item["review_id"],
                "opportunity_id": review_item.get("opportunity_id"),
                "channel": channel,
                "source_url": review_item.get("source_url"),
                "lane": review_item.get("lane"),
                "target_persona": review_item.get("target_persona"),
                "profile_binding": review_item.get("profile_binding", {}),
                "draft": draft,
                "followups": review_item.get("followups", []),
                "draft_metadata": review_item.get("draft_metadata", {}),
                "is_followup": is_followup,
                "followup_plan_id": followup_plan_id,
                "followup_step": review_item.get("followup_step"),
            },
        )
        await self.send_intents.insert_one({"_id": send_intent_id, **intent.model_dump(mode="json")})
        await self.review_queue.update_one(
            {"review_id": review_item["review_id"]},
            {
                "$set": {
                    "send_intent_id": send_intent_id,
                    "blocked_reasons": guardrails,
                    "status": ReviewQueueStatus.BLOCKED.value if guardrails else ReviewQueueStatus.APPROVED.value,
                    "followup_plan_id": followup_plan_id,
                    "updated_at": datetime.utcnow(),
                }
            },
        )
        return await self.send_intents.find_one({"send_intent_id": send_intent_id})

    async def list_send_intents(self, limit: int = 100) -> List[Dict[str, Any]]:
        return await self.send_intents.find({}).sort("created_at", -1).limit(limit).to_list(length=limit)

    async def list_followup_plans(self, limit: int = 100) -> List[Dict[str, Any]]:
        return await self.followup_plans.find({}).sort("updated_at", -1).limit(limit).to_list(length=limit)

    async def get_followup_plan(self, followup_id: str) -> Dict[str, Any]:
        plan = await self.followup_plans.find_one({"followup_id": followup_id})
        if not plan:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Follow-up plan not found")
        return plan

    async def dispatch_send_intent(self, send_intent_id: str, actor: str) -> Dict[str, Any]:
        """Queue a send intent onto the local worker."""
        intent = await self.send_intents.find_one({"send_intent_id": send_intent_id})
        if not intent:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Send intent not found")
        if intent["status"] not in [SendIntentStatus.READY.value, SendIntentStatus.FAILED.value]:
            return intent

        blocked_reasons = await self.evaluate_guardrails_for_send_intent(intent)
        if blocked_reasons:
            await self.send_intents.update_one(
                {"send_intent_id": send_intent_id},
                {"$set": {"blocked_reasons": blocked_reasons, "updated_at": datetime.utcnow()}},
            )
            await self.review_queue.update_one(
                {"review_id": intent["review_id"]},
                {
                    "$set": {
                        "status": ReviewQueueStatus.BLOCKED.value,
                        "blocked_reasons": blocked_reasons,
                        "updated_at": datetime.utcnow(),
                    }
                },
            )
            return await self.send_intents.find_one({"send_intent_id": send_intent_id})

        task_id = str(uuid4())
        channel = intent["channel"]
        action = {
            OutreachChannel.EMAIL.value: "send_email",
            OutreachChannel.LINKEDIN_CONNECT.value: "linkedin_connect",
            OutreachChannel.LINKEDIN_DM.value: "linkedin_dm",
            OutreachChannel.MANUAL.value: "manual_export",
        }.get(channel, "manual_export")

        await self.task_queue.insert_one(
            {
                "_id": task_id,
                "task_id": task_id,
                "agent_target": "OUTREACH_EXECUTOR",
                "payload": {"action": action, "send_intent_id": send_intent_id, **intent["payload"]},
                "title": f"Send {channel.lower()}",
                "status": TaskStatus.PENDING.value,
                "priority": 7,
                "worker_id": None,
                "picked_up_by": None,
                "lease_until": None,
                "last_execution_started": None,
                "execution_count": 0,
                "retry_count": intent.get("retry_count", 0),
                "max_retries": intent.get("max_retries", 3),
                "error_log": [],
                "result": None,
                "created_by": actor,
                "created_at": datetime.utcnow(),
                "updated_at": datetime.utcnow(),
            }
        )
        await self.send_intents.update_one(
            {"send_intent_id": send_intent_id},
            {
                "$set": {
                    "status": SendIntentStatus.DISPATCHED.value,
                    "dispatch_task_id": task_id,
                    "dispatched_at": datetime.utcnow(),
                    "blocked_reasons": [],
                    "updated_at": datetime.utcnow(),
                }
            },
        )
        return await self.send_intents.find_one({"send_intent_id": send_intent_id})

    async def persist_send_result_from_task(self, task_doc: Dict[str, Any], task_result: Dict[str, Any]) -> Optional[str]:
        """Persist send result emitted by the local outreach executor."""
        payload = task_doc.get("payload", {})
        send_intent_id = payload.get("send_intent_id")
        result_payload = ((task_result or {}).get("data") or {}).get("send_result")
        if not send_intent_id or not isinstance(result_payload, dict):
            return None

        existing = await self.send_results.find_one({"send_intent_id": send_intent_id})
        result_id = existing.get("send_result_id") if existing else str(uuid4())
        send_result = SendResult(
            send_result_id=result_id,
            send_intent_id=send_intent_id,
            status=result_payload.get("status", SendIntentStatus.FAILED.value),
            channel=result_payload.get("channel", payload.get("channel", OutreachChannel.MANUAL.value)),
            provider=result_payload.get("provider", "local_worker"),
            executed_by=task_doc.get("agent_target"),
            external_id=result_payload.get("external_id"),
            artifact_path=result_payload.get("artifact_path"),
            detail=result_payload.get("detail", {}),
            error=result_payload.get("error"),
            delivered_at=datetime.utcnow() if result_payload.get("status") in [SendIntentStatus.SENT.value, SendIntentStatus.MANUAL.value] else None,
        )
        if existing:
            await self.send_results.update_one({"send_result_id": result_id}, {"$set": send_result.model_dump(mode="json")})
        else:
            await self.send_results.insert_one({"_id": result_id, **send_result.model_dump(mode="json")})

        intent_status = result_payload.get("status", SendIntentStatus.FAILED.value)
        await self.send_intents.update_one(
            {"send_intent_id": send_intent_id},
            {
                "$set": {
                    "status": intent_status,
                    "send_result_id": result_id,
                    "completed_at": datetime.utcnow(),
                    "last_error": result_payload.get("error"),
                    "updated_at": datetime.utcnow(),
                },
                "$inc": {"retry_count": 0 if intent_status in [SendIntentStatus.SENT.value, SendIntentStatus.MANUAL.value] else 1},
            },
        )

        intent = await self.send_intents.find_one({"send_intent_id": send_intent_id})
        if intent:
            await self.review_queue.update_one(
                {"review_id": intent["review_id"]},
                {
                    "$set": {
                        "blocked_reasons": [],
                        "status": ReviewQueueStatus.APPROVED.value,
                        "updated_at": datetime.utcnow(),
                    }
                },
            )
            await self._advance_followup_plan_after_send(intent, send_result.model_dump(mode="json"), task_doc)
        return result_id

    async def mark_send_failed(self, send_intent_id: str, error_message: str):
        await self.send_intents.update_one(
            {"send_intent_id": send_intent_id},
            {
                "$set": {
                    "status": SendIntentStatus.FAILED.value,
                    "last_error": error_message,
                    "updated_at": datetime.utcnow(),
                },
                "$inc": {"retry_count": 1},
            },
        )

    async def process_due_followups(self) -> int:
        """Create review items for follow-ups that are due and not suppressed."""
        now = datetime.utcnow()
        due_plans = await self.followup_plans.find(
            {
                "status": FollowupStatus.SCHEDULED.value,
                "next_action_at": {"$lte": now},
                "reply_detected_at": None,
            }
        ).to_list(length=None)
        created = 0
        for plan in due_plans:
            created += await self._create_due_followup_review(plan)
        return created

    async def resume_followup(self, followup_id: str, actor: str, note: Optional[str] = None) -> Dict[str, Any]:
        plan = await self.get_followup_plan(followup_id)
        if plan.get("status") == FollowupStatus.COMPLETED.value:
            return plan
        update = {
            "status": FollowupStatus.SCHEDULED.value,
            "paused_reason": None,
            "suppression_reason": None,
            "last_transition_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
        }
        if not plan.get("next_action_at") and plan.get("current_step", 0) < len(plan.get("drafts", [])):
            update["next_action_at"] = datetime.utcnow()
        await self.followup_plans.update_one({"followup_id": followup_id}, {"$set": update})
        await self._append_followup_history(plan["review_id"], ReviewActionType.RESUME_FOLLOWUP, actor, note)
        refreshed = await self.get_followup_plan(followup_id)
        await self._sync_review_followup_summary(refreshed["review_id"], refreshed)
        return refreshed

    async def resume_followup_for_review(self, review_id: str, actor: str, note: Optional[str] = None) -> Dict[str, Any]:
        plan = await self.followup_plans.find_one({"review_id": review_id})
        if not plan:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Follow-up plan not found")
        return await self.resume_followup(plan["followup_id"], actor=actor, note=note)

    async def cancel_followup(self, followup_id: str, actor: str, reason: Optional[str] = None) -> Dict[str, Any]:
        plan = await self.get_followup_plan(followup_id)
        await self.followup_plans.update_one(
            {"followup_id": followup_id},
            {
                "$set": {
                    "status": FollowupStatus.CANCELLED.value,
                    "cancelled_reason": reason,
                    "next_action_at": None,
                    "last_transition_at": datetime.utcnow(),
                    "updated_at": datetime.utcnow(),
                }
            },
        )
        await self._append_followup_history(plan["review_id"], ReviewActionType.CANCEL_FOLLOWUP, actor, reason)
        refreshed = await self.get_followup_plan(followup_id)
        await self._sync_review_followup_summary(refreshed["review_id"], refreshed)
        return refreshed

    async def cancel_followup_for_review(self, review_id: str, actor: str, reason: Optional[str] = None) -> Dict[str, Any]:
        plan = await self.followup_plans.find_one({"review_id": review_id})
        if not plan:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Follow-up plan not found")
        return await self.cancel_followup(plan["followup_id"], actor=actor, reason=reason)

    async def mark_followup_replied(self, *, review_id: Optional[str] = None, followup_id: Optional[str] = None, actor: str, note: Optional[str] = None) -> Dict[str, Any]:
        if followup_id:
            plan = await self.get_followup_plan(followup_id)
        elif review_id:
            plan = await self.followup_plans.find_one({"review_id": review_id})
            if not plan:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Follow-up plan not found")
        else:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="review_id or followup_id is required")

        await self.followup_plans.update_one(
            {"followup_id": plan["followup_id"]},
            {
                "$set": {
                    "status": FollowupStatus.SUPPRESSED.value,
                    "reply_detected_at": datetime.utcnow(),
                    "suppression_reason": note or "Reply detected",
                    "next_action_at": None,
                    "last_transition_at": datetime.utcnow(),
                    "updated_at": datetime.utcnow(),
                }
            },
        )
        await self._append_followup_history(plan["review_id"], ReviewActionType.MARK_REPLIED, actor, note or "Reply detected")
        refreshed = await self.get_followup_plan(plan["followup_id"])
        await self._sync_review_followup_summary(refreshed["review_id"], refreshed)
        return refreshed

    async def evaluate_guardrails(self, review_item: Dict[str, Any], draft: Optional[Dict[str, Any]] = None) -> List[str]:
        policy = await self._resolve_policy(review_item.get("profile_binding", {}))
        reasons: List[str] = []
        draft = draft or review_item.get("primary_draft") or {}
        channel = draft.get("channel") or review_item.get("recommended_channel")

        if policy:
            allowed_channels = {value.value if hasattr(value, "value") else value for value in policy.allowed_channels}
            if channel and allowed_channels and channel not in allowed_channels:
                reasons.append(f"Channel {channel} is not allowed by policy {policy.slug}.")
            if review_item.get("confidence", 0.0) < float(policy.confidence_threshold):
                reasons.append(
                    f"Confidence {float(review_item.get('confidence', 0.0)):.2f} is below policy threshold {float(policy.confidence_threshold):.2f}."
                )
            if policy.active_profile_binding:
                reasons.extend(await self._validate_active_profile_binding(review_item))
            reasons.extend(await self._validate_caps(review_item, policy))
        else:
            reasons.append("No active commercial policy is configured.")

        reasons.extend(self._validate_required_context(review_item, draft))
        reasons.extend(await self._validate_cooldown(review_item, channel))
        return reasons

    async def evaluate_guardrails_for_send_intent(self, send_intent: Dict[str, Any]) -> List[str]:
        review_item = await self.get_review_item(send_intent["review_id"])
        return await self.evaluate_guardrails(review_item, send_intent.get("payload", {}).get("draft"))

    async def _upsert_followup_plan(self, review_item: Dict[str, Any], paused: bool = False, note: Optional[str] = None) -> Optional[Dict[str, Any]]:
        followups = [FollowupDraft(**draft) for draft in review_item.get("followups", [])]
        if not followups:
            await self.followup_plans.delete_many({"review_id": review_item["review_id"]})
            await self._sync_review_followup_summary(review_item["review_id"], None)
            return None

        existing = await self.followup_plans.find_one({"review_id": review_item["review_id"]})
        current_step = int(existing.get("current_step", 0)) if existing else 0
        status_value = (
            FollowupStatus.PAUSED.value
            if paused
            else existing.get("status", FollowupStatus.SCHEDULED.value)
            if existing
            else FollowupStatus.SCHEDULED.value
        )
        next_action_at = existing.get("next_action_at") if existing else None
        if paused:
            next_action_at = None
        elif current_step < len(followups) and next_action_at is None and status_value == FollowupStatus.SCHEDULED.value:
            next_action_at = self._compute_followup_time(existing.get("last_sent_at") if existing else None, followups[current_step].delay_days)

        await self.followup_plans.update_one(
            {"review_id": review_item["review_id"]},
            {
                "$set": {
                    "review_id": review_item["review_id"],
                    "root_review_id": review_item.get("parent_review_id") or review_item["review_id"],
                    "opportunity_id": review_item.get("opportunity_id"),
                    "status": status_value,
                    "profile_binding": review_item.get("profile_binding", {}),
                    "current_step": current_step,
                    "next_action_at": next_action_at,
                    "drafts": [draft.model_dump(mode="json") for draft in followups],
                    "paused_reason": note if paused else None,
                    "last_transition_at": datetime.utcnow(),
                    "updated_at": datetime.utcnow(),
                },
                "$setOnInsert": {
                    "_id": str(uuid4()),
                    "followup_id": str(uuid4()),
                    "created_at": datetime.utcnow(),
                    "reply_detected_at": None,
                    "suppression_reason": None,
                    "cancelled_reason": None,
                    "closed_lost_at": None,
                    "last_sent_at": None,
                    "last_review_id": None,
                    "last_task_id": None,
                },
            },
            upsert=True,
        )
        plan = await self.followup_plans.find_one({"review_id": review_item["review_id"]})
        await self._sync_review_followup_summary(review_item["review_id"], plan)
        return plan

    async def _advance_followup_plan_after_send(self, intent: Dict[str, Any], send_result: Dict[str, Any], task_doc: Dict[str, Any]):
        followup_id = intent.get("followup_plan_id")
        if not followup_id:
            return
        plan = await self.followup_plans.find_one({"followup_id": followup_id})
        if not plan:
            return

        delivered = send_result.get("status") in [SendIntentStatus.SENT.value, SendIntentStatus.MANUAL.value]
        if not delivered:
            return

        current_step = int(plan.get("current_step", 0))
        next_step = current_step + 1 if intent.get("is_followup") else current_step
        total_drafts = len(plan.get("drafts", []))
        if not intent.get("is_followup") and total_drafts > 0:
            next_action_at = self._compute_followup_time(datetime.utcnow(), plan["drafts"][0]["delay_days"])
            next_status = FollowupStatus.SCHEDULED.value
        elif next_step >= total_drafts:
            next_action_at = None
            next_status = FollowupStatus.COMPLETED.value
        else:
            next_action_at = self._compute_followup_time(datetime.utcnow(), plan["drafts"][next_step]["delay_days"])
            next_status = FollowupStatus.SCHEDULED.value

        await self.followup_plans.update_one(
            {"followup_id": followup_id},
            {
                "$set": {
                    "status": next_status,
                    "current_step": next_step,
                    "next_action_at": next_action_at,
                    "last_sent_at": datetime.utcnow(),
                    "last_task_id": task_doc.get("task_id"),
                    "last_transition_at": datetime.utcnow(),
                    "updated_at": datetime.utcnow(),
                }
            },
        )
        refreshed = await self.followup_plans.find_one({"followup_id": followup_id})
        if refreshed:
            await self._sync_review_followup_summary(refreshed["review_id"], refreshed)

    async def _create_due_followup_review(self, plan: Dict[str, Any]) -> int:
        current_step = int(plan.get("current_step", 0))
        drafts = plan.get("drafts", [])
        if current_step >= len(drafts):
            await self.followup_plans.update_one(
                {"followup_id": plan["followup_id"]},
                {"$set": {"status": FollowupStatus.COMPLETED.value, "next_action_at": None, "updated_at": datetime.utcnow()}},
            )
            return 0

        existing = await self.review_queue.find_one(
            {
                "followup_plan_id": plan["followup_id"],
                "followup_step": current_step + 1,
                "status": {"$in": [
                    ReviewQueueStatus.PENDING.value,
                    ReviewQueueStatus.PAUSED.value,
                    ReviewQueueStatus.BLOCKED.value,
                    ReviewQueueStatus.APPROVED.value,
                ]},
            }
        )
        if existing:
            await self.followup_plans.update_one(
                {"followup_id": plan["followup_id"]},
                {
                    "$set": {
                        "status": FollowupStatus.PENDING_REVIEW.value,
                        "last_review_id": existing["review_id"],
                        "next_action_at": None,
                        "updated_at": datetime.utcnow(),
                    }
                },
            )
            return 0

        root_review = await self.get_review_item(plan["review_id"])
        followup_draft = drafts[current_step]
        review_id = str(uuid4())
        item = ReviewQueueItem(
            review_id=review_id,
            review_kind=ReviewItemKind.FOLLOWUP,
            parent_review_id=plan["review_id"],
            followup_plan_id=plan["followup_id"],
            followup_step=current_step + 1,
            opportunity_id=root_review.get("opportunity_id"),
            route_id=root_review.get("route_id"),
            source_url=root_review["source_url"],
            kind=root_review["kind"],
            lane=root_review["lane"],
            specialist=root_review["specialist"],
            target_persona=root_review["target_persona"],
            status=ReviewQueueStatus.PENDING,
            confidence=float(root_review.get("confidence", 0.0)),
            profile_binding=SpecialistProfileBinding(**root_review.get("profile_binding", {})),
            recommended_channel=followup_draft["channel"],
            rationale=list(root_review.get("rationale", [])) + [f"Scheduled follow-up #{current_step + 1}"],
            recommended_next_step=f"Review follow-up #{current_step + 1} before sending.",
            primary_draft=DraftMessage(
                channel=followup_draft["channel"],
                subject=root_review.get("primary_draft", {}).get("subject"),
                body=followup_draft["body"],
                cta=root_review.get("primary_draft", {}).get("cta", ""),
            ),
            followups=root_review.get("followups", []),
            draft_metadata=root_review.get("draft_metadata", {}),
            blocked_reasons=[],
            followup_status=FollowupStatus.PENDING_REVIEW,
            next_action_at=None,
            history=[
                ReviewHistoryEntry(
                    action=ReviewActionType.EDIT,
                    acted_by="SYSTEM",
                    note=f"Follow-up #{current_step + 1} entered review queue.",
                ).model_dump(mode="json")
            ],
        )
        await self.review_queue.insert_one({"_id": review_id, **item.model_dump(mode="json")})
        await self.followup_plans.update_one(
            {"followup_id": plan["followup_id"]},
            {
                "$set": {
                    "status": FollowupStatus.PENDING_REVIEW.value,
                    "last_review_id": review_id,
                    "next_action_at": None,
                    "last_transition_at": datetime.utcnow(),
                    "updated_at": datetime.utcnow(),
                }
            },
        )
        refreshed = await self.followup_plans.find_one({"followup_id": plan["followup_id"]})
        await self._sync_review_followup_summary(plan["review_id"], refreshed)
        return 1

    async def _resolve_policy(self, profile_binding: Dict[str, Any]) -> Optional[CommercialPolicy]:
        policy_slug = profile_binding.get("policy_slug")
        policy_doc = await self.commercial_policies.find_one({"slug": policy_slug}) if policy_slug else None
        if not policy_doc:
            policy_doc = await self.commercial_policies.find_one({"is_active": True})
        return CommercialPolicy(**policy_doc) if policy_doc else None

    async def _validate_active_profile_binding(self, review_item: Dict[str, Any]) -> List[str]:
        reasons: List[str] = []
        binding = review_item.get("profile_binding", {})
        operator_slug = binding.get("operator_profile_slug")
        business_slug = binding.get("business_profile_slug")

        if operator_slug:
            operator = await self.operator_profiles.find_one({"slug": operator_slug, "is_active": True})
            if not operator:
                reasons.append(f"Operator profile {operator_slug} is not active.")

        if review_item.get("kind") == OpportunityKind.COMMERCIAL.value or business_slug:
            if not business_slug:
                reasons.append("Commercial outreach is missing a bound business profile.")
            else:
                business = await self.business_profiles.find_one({"slug": business_slug, "is_active": True})
                if not business:
                    reasons.append(f"Business profile {business_slug} is not active.")
        return reasons

    async def _validate_caps(self, review_item: Dict[str, Any], policy: CommercialPolicy) -> List[str]:
        now = datetime.utcnow()
        lane = review_item.get("lane")
        lane_cap = int(policy.daily_caps.jobs if lane == OpportunityLane.JOBS.value else policy.daily_caps.commercial)
        daily_count = await self.send_intents.count_documents(
            {"approved_at": {"$gte": now - timedelta(hours=24)}, "status": {"$in": self.ACTIVE_SEND_STATUSES}}
        )
        hourly_count = await self.send_intents.count_documents(
            {"approved_at": {"$gte": now - timedelta(hours=1)}, "status": {"$in": self.ACTIVE_SEND_STATUSES}}
        )
        reasons: List[str] = []
        if daily_count >= lane_cap:
            reasons.append(f"Daily outreach cap reached for lane {lane}: {daily_count}/{lane_cap}.")
        hourly_cap = max(1, lane_cap // 4)
        if hourly_count >= hourly_cap:
            reasons.append(f"Hourly outreach cap reached for lane {lane}: {hourly_count}/{hourly_cap}.")
        return reasons

    def _validate_required_context(self, review_item: Dict[str, Any], draft: Dict[str, Any]) -> List[str]:
        reasons: List[str] = []
        if not draft.get("body"):
            reasons.append("Draft body is required.")
        channel = draft.get("channel") or review_item.get("recommended_channel")
        metadata = review_item.get("draft_metadata", {})
        if channel == OutreachChannel.EMAIL.value:
            if not draft.get("subject"):
                reasons.append("Email draft is missing a subject.")
            if not (metadata.get("email") or metadata.get("contact_email") or review_item.get("to_email")):
                reasons.append("Email send is missing a recipient email.")
        if channel in [OutreachChannel.LINKEDIN_DM.value, OutreachChannel.LINKEDIN_CONNECT.value] and not review_item.get("source_url"):
            reasons.append(f"{channel} send is missing a source URL.")
        if review_item.get("kind") == OpportunityKind.COMMERCIAL.value and not metadata.get("company"):
            reasons.append("Commercial send is missing company context.")
        return reasons

    async def _validate_cooldown(self, review_item: Dict[str, Any], channel: Optional[str]) -> List[str]:
        if not channel:
            return []
        cutoff = datetime.utcnow() - timedelta(hours=await self._resolve_cooldown_hours(review_item.get("profile_binding", {})))
        cooldown_hit = await self.send_intents.find_one(
            {
                "cooldown_key": self._build_cooldown_key(review_item, channel),
                "created_at": {"$gte": cutoff},
                "status": {"$in": self.ACTIVE_SEND_STATUSES},
                "review_id": {"$ne": review_item["review_id"]},
            }
        )
        if cooldown_hit:
            return [f"Per-target cooldown is active until {cooldown_hit.get('created_at')}."]
        return []

    async def _resolve_cooldown_hours(self, profile_binding: Dict[str, Any]) -> int:
        policy = await self._resolve_policy(profile_binding)
        return int(policy.per_target_cooldown_hours) if policy else 72

    async def _sync_review_followup_summary(self, review_id: str, plan: Optional[Dict[str, Any]]):
        await self.review_queue.update_one(
            {"review_id": review_id},
            {
                "$set": {
                    "followup_plan_id": plan.get("followup_id") if plan else None,
                    "followup_status": plan.get("status") if plan else None,
                    "next_action_at": plan.get("next_action_at") if plan else None,
                    "updated_at": datetime.utcnow(),
                }
            },
        )

    def _apply_followup_summary(self, update: Dict[str, Any], plan: Optional[Dict[str, Any]]):
        update["followup_plan_id"] = plan.get("followup_id") if plan else None
        update["followup_status"] = plan.get("status") if plan else None
        update["next_action_at"] = plan.get("next_action_at") if plan else None

    async def _append_followup_history(self, review_id: str, action: ReviewActionType, actor: str, note: Optional[str]):
        await self.review_queue.update_one(
            {"review_id": review_id},
            {
                "$push": {"history": ReviewHistoryEntry(action=action, acted_by=actor, note=note).model_dump(mode="json")},
                "$set": {"updated_at": datetime.utcnow(), "latest_note": note},
            },
        )

    @staticmethod
    def _compute_followup_time(base_time: Optional[datetime], delay_days: int) -> datetime:
        return (base_time or datetime.utcnow()) + timedelta(days=delay_days)

    def _build_send_idempotency_key(self, review_item: Dict[str, Any], draft: Dict[str, Any]) -> str:
        blob = json.dumps(
            {
                "review_id": review_item["review_id"],
                "followup_plan_id": review_item.get("followup_plan_id"),
                "followup_step": review_item.get("followup_step"),
                "channel": draft.get("channel"),
                "subject": draft.get("subject"),
                "body": draft.get("body"),
                "cta": draft.get("cta"),
            },
            sort_keys=True,
        )
        return hashlib.sha256(blob.encode("utf-8")).hexdigest()

    def _build_cooldown_key(self, review_item: Dict[str, Any], channel: str) -> str:
        parts = [
            review_item.get("opportunity_id") or "",
            review_item.get("source_url") or "",
            review_item.get("draft_metadata", {}).get("email") or review_item.get("draft_metadata", {}).get("contact_email") or "",
            review_item.get("profile_binding", {}).get("business_profile_slug") or review_item.get("profile_binding", {}).get("operator_profile_slug") or "",
            channel,
        ]
        return hashlib.sha256("|".join(parts).encode("utf-8")).hexdigest()


def get_commercial_ops_service() -> CommercialOpsService:
    """Return the commercial ops service."""

    return CommercialOpsService()
