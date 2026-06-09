"""
Commercial Ops review queue and sending routes.
"""
from typing import List, Optional

from fastapi import APIRouter, Depends, Query

from app.models.base import APIResponse
from app.models.commercial_ops import ReviewActionType, ReviewQueueActionRequest
from app.models.user import User
from app.utils.auth import get_current_user
from app.utils.data_contracts import contract_logger
from app.services.commercial_ops_service import get_commercial_ops_service


router = APIRouter(prefix="/commercial", tags=["Commercial Ops"])


@router.get("/review-items", response_model=List[dict])
async def list_review_items(
    status: Optional[str] = Query(default=None),
    lane: Optional[str] = Query(default=None),
    target_persona: Optional[str] = Query(default=None),
    recommended_channel: Optional[str] = Query(default=None),
    review_kind: Optional[str] = Query(default=None),
    profile_slug: Optional[str] = Query(default=None),
    business_slug: Optional[str] = Query(default=None),
    company: Optional[str] = Query(default=None),
    limit: int = Query(default=100, le=200),
    current_user: User = Depends(get_current_user),
):
    service = get_commercial_ops_service()
    return await service.list_review_items(
        {
            "status": status,
            "lane": lane,
            "target_persona": target_persona,
            "recommended_channel": recommended_channel,
            "review_kind": review_kind,
            "profile_slug": profile_slug,
            "business_slug": business_slug,
            "company": company,
            "limit": limit,
        }
    )


@router.get("/review-items/{review_id}", response_model=dict)
async def get_review_item(review_id: str, current_user: User = Depends(get_current_user)):
    return await get_commercial_ops_service().get_review_item(review_id)


async def _apply_action(review_id: str, action: ReviewActionType, payload: ReviewQueueActionRequest, current_user: User) -> APIResponse:
    service = get_commercial_ops_service()
    item = await service.apply_review_action(review_id, action, payload, current_user.email)
    await contract_logger.emit_event(
        event_type=f"COMMERCIAL_REVIEW_{action.value}",
        title=f"{action.value.title()} review item",
        entity_type="review_item",
        entity_id=review_id,
        payload={"review_id": review_id, "action": action.value, "actor": current_user.email, "status": item.get("status")},
    )
    return APIResponse(success=True, message=f"Review item {action.value.lower()}d", data=item)


@router.patch("/review-items/{review_id}/approve", response_model=APIResponse)
async def approve_review_item(
    review_id: str,
    payload: ReviewQueueActionRequest,
    current_user: User = Depends(get_current_user),
):
    return await _apply_action(review_id, ReviewActionType.APPROVE, payload, current_user)


@router.patch("/review-items/{review_id}/reject", response_model=APIResponse)
async def reject_review_item(
    review_id: str,
    payload: ReviewQueueActionRequest,
    current_user: User = Depends(get_current_user),
):
    return await _apply_action(review_id, ReviewActionType.REJECT, payload, current_user)


@router.patch("/review-items/{review_id}/edit", response_model=APIResponse)
async def edit_review_item(
    review_id: str,
    payload: ReviewQueueActionRequest,
    current_user: User = Depends(get_current_user),
):
    return await _apply_action(review_id, ReviewActionType.EDIT, payload, current_user)


@router.patch("/review-items/{review_id}/reroute", response_model=APIResponse)
async def reroute_review_item(
    review_id: str,
    payload: ReviewQueueActionRequest,
    current_user: User = Depends(get_current_user),
):
    return await _apply_action(review_id, ReviewActionType.REROUTE, payload, current_user)


@router.patch("/review-items/{review_id}/archive", response_model=APIResponse)
async def archive_review_item(
    review_id: str,
    payload: ReviewQueueActionRequest,
    current_user: User = Depends(get_current_user),
):
    return await _apply_action(review_id, ReviewActionType.ARCHIVE, payload, current_user)


@router.patch("/review-items/{review_id}/pause-followup", response_model=APIResponse)
async def pause_followup(
    review_id: str,
    payload: ReviewQueueActionRequest,
    current_user: User = Depends(get_current_user),
):
    return await _apply_action(review_id, ReviewActionType.PAUSE_FOLLOWUP, payload, current_user)


@router.patch("/review-items/{review_id}/resume-followup", response_model=APIResponse)
async def resume_followup(
    review_id: str,
    payload: ReviewQueueActionRequest,
    current_user: User = Depends(get_current_user),
):
    return await _apply_action(review_id, ReviewActionType.RESUME_FOLLOWUP, payload, current_user)


@router.patch("/review-items/{review_id}/cancel-followup", response_model=APIResponse)
async def cancel_followup(
    review_id: str,
    payload: ReviewQueueActionRequest,
    current_user: User = Depends(get_current_user),
):
    return await _apply_action(review_id, ReviewActionType.CANCEL_FOLLOWUP, payload, current_user)


@router.patch("/review-items/{review_id}/mark-replied", response_model=APIResponse)
async def mark_replied(
    review_id: str,
    payload: ReviewQueueActionRequest,
    current_user: User = Depends(get_current_user),
):
    return await _apply_action(review_id, ReviewActionType.MARK_REPLIED, payload, current_user)


@router.get("/send-intents", response_model=List[dict])
async def list_send_intents(
    limit: int = Query(default=100, le=200),
    current_user: User = Depends(get_current_user),
):
    return await get_commercial_ops_service().list_send_intents(limit=limit)


@router.get("/followups", response_model=List[dict])
async def list_followup_plans(
    limit: int = Query(default=100, le=200),
    current_user: User = Depends(get_current_user),
):
    return await get_commercial_ops_service().list_followup_plans(limit=limit)


@router.get("/followups/{followup_id}", response_model=dict)
async def get_followup_plan(followup_id: str, current_user: User = Depends(get_current_user)):
    return await get_commercial_ops_service().get_followup_plan(followup_id)


@router.post("/followups/{followup_id}/resume", response_model=APIResponse)
async def resume_followup_plan(
    followup_id: str,
    payload: ReviewQueueActionRequest,
    current_user: User = Depends(get_current_user),
):
    plan = await get_commercial_ops_service().resume_followup(followup_id, current_user.email, payload.note)
    return APIResponse(success=True, message="Follow-up resumed", data=plan)


@router.post("/followups/{followup_id}/cancel", response_model=APIResponse)
async def cancel_followup_plan(
    followup_id: str,
    payload: ReviewQueueActionRequest,
    current_user: User = Depends(get_current_user),
):
    plan = await get_commercial_ops_service().cancel_followup(followup_id, current_user.email, payload.note)
    return APIResponse(success=True, message="Follow-up cancelled", data=plan)


@router.post("/followups/{followup_id}/mark-replied", response_model=APIResponse)
async def mark_followup_plan_replied(
    followup_id: str,
    payload: ReviewQueueActionRequest,
    current_user: User = Depends(get_current_user),
):
    plan = await get_commercial_ops_service().mark_followup_replied(followup_id=followup_id, actor=current_user.email, note=payload.note)
    return APIResponse(success=True, message="Follow-up suppressed after reply", data=plan)


@router.post("/send-intents/{send_intent_id}/dispatch", response_model=APIResponse)
async def dispatch_send_intent(
    send_intent_id: str,
    current_user: User = Depends(get_current_user),
):
    intent = await get_commercial_ops_service().dispatch_send_intent(send_intent_id, current_user.email)
    await contract_logger.emit_event(
        event_type="COMMERCIAL_SEND_DISPATCHED",
        title="Commercial send dispatched",
        entity_type="send_intent",
        entity_id=send_intent_id,
        payload={"send_intent_id": send_intent_id, "actor": current_user.email, "status": intent.get("status")},
    )
    return APIResponse(success=True, message="Send intent dispatched", data=intent)
