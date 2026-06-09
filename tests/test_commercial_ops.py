from datetime import datetime, timedelta
from uuid import uuid4

import pytest

from app.db import Database
from app.main import check_and_execute_scheduled_tasks


async def _seed_profiles_and_policy(*, confidence_threshold: float = 0.75, daily_jobs: int = 10, daily_commercial: int = 20):
    await Database.get_collection("operator_profiles").insert_one(
        {
            "_id": "op-1",
            "profile_id": "op-1",
            "owner_user_id": "user-1",
            "slug": "default",
            "display_name": "Default Operator",
            "preferred_channels": ["EMAIL"],
            "is_active": True,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
        }
    )
    await Database.get_collection("business_profiles").insert_one(
        {
            "_id": "biz-1",
            "profile_id": "biz-1",
            "owner_user_id": "user-1",
            "slug": "lenquant",
            "business_name": "LenQuant",
            "product_name": "LenQuant",
            "approved_channels": ["EMAIL"],
            "is_active": True,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
        }
    )
    await Database.get_collection("commercial_policies").insert_one(
        {
            "_id": "policy-1",
            "policy_id": "policy-1",
            "slug": "default",
            "owner_user_id": "user-1",
            "review_required": True,
            "auto_send_enabled": False,
            "enrichment_enabled": False,
            "allowed_channels": ["EMAIL", "MANUAL"],
            "daily_caps": {"jobs": daily_jobs, "commercial": daily_commercial},
            "per_target_cooldown_hours": 72,
            "confidence_threshold": confidence_threshold,
            "active_profile_binding": True,
            "is_active": True,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
        }
    )


async def _seed_review_item(*, confidence: float = 0.84, status: str = "PENDING", with_followups: bool = True, include_email: bool = True):
    review_id = str(uuid4())
    metadata = {"company": "Acme Capital"}
    if include_email:
        metadata["email"] = "jane@example.com"
    await Database.get_collection("review_queue").insert_one(
        {
            "_id": review_id,
            "review_id": review_id,
            "review_kind": "INITIAL",
            "opportunity_id": "opp-1",
            "route_id": "route-1",
            "source_url": "https://example.com/opportunity/1",
            "kind": "COMMERCIAL",
            "lane": "LENQUANT",
            "specialist": "LENQUANT_SELLER",
            "target_persona": "FOUNDER",
            "status": status,
            "confidence": confidence,
            "profile_binding": {
                "operator_profile_slug": "default",
                "business_profile_slug": "lenquant",
                "policy_slug": "default",
            },
            "recommended_channel": "EMAIL",
            "rationale": ["Looks like a fit for LenQuant."],
            "recommended_next_step": "Review before sending.",
            "primary_draft": {
                "channel": "EMAIL",
                "subject": "Trading ops leverage",
                "body": "Hi Jane,\n\nQuick note.",
                "cta": "Open to a short call?",
            },
            "followups": [{"delay_days": 3, "channel": "EMAIL", "body": "Following up."}] if with_followups else [],
            "draft_metadata": metadata,
            "paused_followup": False,
            "blocked_reasons": [],
            "history": [],
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
        }
    )
    return review_id


@pytest.mark.asyncio
async def test_approve_review_item_creates_send_intent_and_followup_plan(client, auth_headers):
    await _seed_profiles_and_policy()
    review_id = await _seed_review_item()

    response = await client.patch(f"/api/v1/commercial/review-items/{review_id}/approve", json={}, headers=auth_headers)
    assert response.status_code == 200

    review = await Database.get_collection("review_queue").find_one({"review_id": review_id})
    assert review["status"] == "APPROVED"
    assert review["send_intent_id"]

    intents = await Database.get_collection("send_intents").find({"review_id": review_id}).to_list(length=None)
    assert len(intents) == 1
    assert intents[0]["status"] == "READY"
    assert intents[0]["blocked_reasons"] == []

    plan = await Database.get_collection("followup_plans").find_one({"review_id": review_id})
    assert plan is not None
    assert plan["status"] == "SCHEDULED"
    assert plan["next_action_at"] is not None


@pytest.mark.asyncio
async def test_approval_is_blocked_by_policy_and_missing_context(client, auth_headers):
    await _seed_profiles_and_policy(confidence_threshold=0.9)
    review_id = await _seed_review_item(confidence=0.62, include_email=False)

    response = await client.patch(f"/api/v1/commercial/review-items/{review_id}/approve", json={}, headers=auth_headers)
    assert response.status_code == 200

    review = await Database.get_collection("review_queue").find_one({"review_id": review_id})
    assert review["status"] == "BLOCKED"
    assert any("below policy threshold" in reason for reason in review["blocked_reasons"])
    assert any("recipient email" in reason for reason in review["blocked_reasons"])

    intent = await Database.get_collection("send_intents").find_one({"review_id": review_id})
    assert intent is not None
    assert intent["blocked_reasons"] == review["blocked_reasons"]


@pytest.mark.asyncio
async def test_dispatch_send_intent_is_idempotent_and_creates_task(client, auth_headers):
    await _seed_profiles_and_policy()
    review_id = await _seed_review_item()
    await client.patch(f"/api/v1/commercial/review-items/{review_id}/approve", json={}, headers=auth_headers)
    intent = await Database.get_collection("send_intents").find_one({"review_id": review_id})

    first = await client.post(f"/api/v1/commercial/send-intents/{intent['send_intent_id']}/dispatch", headers=auth_headers)
    second = await client.post(f"/api/v1/commercial/send-intents/{intent['send_intent_id']}/dispatch", headers=auth_headers)

    assert first.status_code == 200
    assert second.status_code == 200

    tasks = await Database.get_collection("task_queue").find({"agent_target": "OUTREACH_EXECUTOR"}).to_list(length=None)
    assert len(tasks) == 1
    refreshed = await Database.get_collection("send_intents").find_one({"send_intent_id": intent["send_intent_id"]})
    assert refreshed["status"] == "DISPATCHED"


@pytest.mark.asyncio
async def test_send_result_is_idempotent_and_scheduler_creates_due_followup_review(client, auth_headers, agent_headers):
    await _seed_profiles_and_policy()
    review_id = await _seed_review_item()
    await client.patch(f"/api/v1/commercial/review-items/{review_id}/approve", json={}, headers=auth_headers)
    intent = await Database.get_collection("send_intents").find_one({"review_id": review_id})

    send_task_id = str(uuid4())
    await Database.get_collection("task_queue").insert_one(
        {
            "_id": send_task_id,
            "task_id": send_task_id,
            "agent_target": "OUTREACH_EXECUTOR",
            "payload": {
                "send_intent_id": intent["send_intent_id"],
                "channel": "EMAIL",
                "followup_plan_id": intent["followup_plan_id"],
                "is_followup": False,
            },
            "title": "Send email",
            "status": "PICKED_UP",
            "priority": 5,
            "worker_id": "worker-1",
            "created_by": "SYSTEM",
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
        }
    )
    send_complete = {
        "status": "COMPLETED",
        "result": {
            "success": True,
            "data": {
                "send_result": {
                    "status": "MANUAL",
                    "channel": "EMAIL",
                    "provider": "local_export",
                    "artifact_path": "C:/temp/export.json",
                    "detail": {"reason": "SMTP not configured"},
                }
            },
        },
    }
    path = f"/api/v1/tasks/{send_task_id}/status"
    response = await client.patch(path, json=send_complete, headers=agent_headers("PATCH", path, send_complete))
    assert response.status_code == 200
    response = await client.patch(path, json=send_complete, headers=agent_headers("PATCH", path, send_complete))
    assert response.status_code == 200

    send_results = await Database.get_collection("send_results").find({"send_intent_id": intent["send_intent_id"]}).to_list(length=None)
    assert len(send_results) == 1

    plan = await Database.get_collection("followup_plans").find_one({"followup_id": intent["followup_plan_id"]})
    assert plan["status"] == "SCHEDULED"
    await Database.get_collection("followup_plans").update_one(
        {"followup_id": intent["followup_plan_id"]},
        {"$set": {"next_action_at": datetime.utcnow() - timedelta(minutes=1)}},
    )

    await check_and_execute_scheduled_tasks()

    followup_reviews = await Database.get_collection("review_queue").find({"review_kind": "FOLLOWUP"}).to_list(length=None)
    assert len(followup_reviews) == 1
    assert followup_reviews[0]["followup_step"] == 1


@pytest.mark.asyncio
async def test_pause_resume_cancel_and_reply_suppression(client, auth_headers):
    await _seed_profiles_and_policy()
    review_id = await _seed_review_item()
    await client.patch(f"/api/v1/commercial/review-items/{review_id}/approve", json={}, headers=auth_headers)

    pause_response = await client.patch(
        f"/api/v1/commercial/review-items/{review_id}/pause-followup",
        json={"note": "Operator pause"},
        headers=auth_headers,
    )
    assert pause_response.status_code == 200
    paused = await Database.get_collection("followup_plans").find_one({"review_id": review_id})
    assert paused["status"] == "PAUSED"

    resume_response = await client.patch(
        f"/api/v1/commercial/review-items/{review_id}/resume-followup",
        json={"note": "Resume"},
        headers=auth_headers,
    )
    assert resume_response.status_code == 200
    resumed = await Database.get_collection("followup_plans").find_one({"review_id": review_id})
    assert resumed["status"] == "SCHEDULED"

    replied_response = await client.patch(
        f"/api/v1/commercial/review-items/{review_id}/mark-replied",
        json={"note": "Lead replied"},
        headers=auth_headers,
    )
    assert replied_response.status_code == 200
    suppressed = await Database.get_collection("followup_plans").find_one({"review_id": review_id})
    assert suppressed["status"] == "SUPPRESSED"
    assert suppressed["next_action_at"] is None

    cancel_response = await client.patch(
        f"/api/v1/commercial/review-items/{review_id}/cancel-followup",
        json={"note": "Closed lost"},
        headers=auth_headers,
    )
    assert cancel_response.status_code == 200
    cancelled = await Database.get_collection("followup_plans").find_one({"review_id": review_id})
    assert cancelled["status"] == "CANCELLED"


@pytest.mark.asyncio
async def test_task_completion_creates_review_item_and_send_result(client, auth_headers, agent_headers):
    await _seed_profiles_and_policy()
    task_id = str(uuid4())
    await Database.get_collection("task_queue").insert_one(
        {
            "_id": task_id,
            "task_id": task_id,
            "agent_target": "JOB_HUNTER",
            "payload": {"action": "draft_outreach"},
            "title": "Draft outreach",
            "status": "PICKED_UP",
            "priority": 5,
            "worker_id": "worker-1",
            "created_by": "SYSTEM",
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
        }
    )

    complete_body = {
        "status": "COMPLETED",
        "result": {
            "success": True,
            "data": {
                "draft_package": {
                    "specialist": "JOB_HUNTER",
                    "lane": "JOBS",
                    "target_persona": "RECRUITER",
                    "profile_binding": {"operator_profile_slug": "default", "policy_slug": "default"},
                    "opportunity_id": "job-123",
                    "source_url": "https://jobs.example.com/123",
                    "title": "Growth Lead",
                    "company": "Example",
                    "person_name": "",
                    "fit_score": 0.88,
                    "rationale": ["Strong fit."],
                    "recommended_channel": "EMAIL",
                    "recommended_next_step": "Review and approve.",
                    "primary_draft": {"channel": "EMAIL", "subject": "Growth Lead fit", "body": "Hi there", "cta": "Open to a chat?"},
                    "followups": [{"delay_days": 4, "channel": "EMAIL", "body": "Following up."}],
                    "metadata": {"email": "lead@example.com", "company": "Example"},
                }
            },
        },
    }
    path = f"/api/v1/tasks/{task_id}/status"
    response = await client.patch(path, json=complete_body, headers=agent_headers("PATCH", path, complete_body))
    assert response.status_code == 200
    review = await Database.get_collection("review_queue").find_one({"opportunity_id": "job-123"})
    assert review is not None
    assert review["target_persona"] == "RECRUITER"

    send_task_id = str(uuid4())
    await Database.get_collection("task_queue").insert_one(
        {
            "_id": send_task_id,
            "task_id": send_task_id,
            "agent_target": "OUTREACH_EXECUTOR",
            "payload": {"send_intent_id": "intent-1", "channel": "EMAIL"},
            "title": "Send email",
            "status": "PICKED_UP",
            "priority": 5,
            "worker_id": "worker-1",
            "created_by": "SYSTEM",
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
        }
    )
    await Database.get_collection("send_intents").insert_one(
        {
            "_id": "intent-1",
            "send_intent_id": "intent-1",
            "review_id": review["review_id"],
            "opportunity_id": "job-123",
            "status": "DISPATCHED",
            "channel": "EMAIL",
            "profile_binding": {"operator_profile_slug": "default"},
            "idempotency_key": "idem-1",
            "cooldown_key": "cooldown-1",
            "provider": "local_worker",
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
        }
    )
    send_complete = {
        "status": "COMPLETED",
        "result": {
            "success": True,
            "data": {
                "send_result": {
                    "status": "MANUAL",
                    "channel": "EMAIL",
                    "provider": "local_export",
                    "artifact_path": "C:/temp/export.json",
                    "detail": {"reason": "SMTP not configured"},
                }
            },
        },
    }
    path = f"/api/v1/tasks/{send_task_id}/status"
    response = await client.patch(path, json=send_complete, headers=agent_headers("PATCH", path, send_complete))
    assert response.status_code == 200
    send_result = await Database.get_collection("send_results").find_one({"send_intent_id": "intent-1"})
    assert send_result is not None
    updated_intent = await Database.get_collection("send_intents").find_one({"send_intent_id": "intent-1"})
    assert updated_intent["status"] == "MANUAL"
