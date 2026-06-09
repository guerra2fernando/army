"""
Profile routes for operator, business, policy, and uploaded assets.
"""
from base64 import b64encode
from datetime import datetime
from hashlib import sha256
from typing import List

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status

from app.db import Database
from app.models.user import User
from app.models.base import APIResponse
from app.models.profiles import (
    BusinessProfile,
    BusinessProfileCreate,
    CommercialPolicy,
    CommercialPolicyCreate,
    OperatorProfile,
    OperatorProfileCreate,
    ProfileAsset,
    ProfileAssetType,
    ProfileAssetUploadResponse,
    ResolvedProfilesResponse,
    new_profile_id,
)
from app.utils.auth import get_current_user

router = APIRouter(prefix="/profiles", tags=["Profiles"])


async def _deactivate_other_profiles(collection_name: str, owner_user_id: str, current_slug: str):
    collection = Database.get_collection(collection_name)
    await collection.update_many(
        {"owner_user_id": owner_user_id, "slug": {"$ne": current_slug}},
        {"$set": {"is_active": False, "updated_at": datetime.utcnow()}},
    )


@router.post("/assets/upload", response_model=ProfileAssetUploadResponse)
async def upload_profile_asset(
    asset_type: ProfileAssetType,
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
):
    """Upload a profile asset into MongoDB."""
    content = await file.read()
    if not content:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Uploaded file is empty")

    asset_id = new_profile_id()
    asset_doc = ProfileAsset(
        _id=asset_id,
        asset_id=asset_id,
        owner_user_id=current_user.user_id,
        asset_type=asset_type,
        filename=file.filename or "upload.bin",
        content_type=file.content_type or "application/octet-stream",
        size_bytes=len(content),
        sha256=sha256(content).hexdigest(),
        content_base64=b64encode(content).decode("ascii"),
    )
    await Database.get_collection("profile_assets").insert_one(asset_doc.model_dump(by_alias=True))
    return ProfileAssetUploadResponse(
        asset_id=asset_doc.asset_id,
        filename=asset_doc.filename,
        content_type=asset_doc.content_type,
        size_bytes=asset_doc.size_bytes,
        sha256=asset_doc.sha256,
    )


@router.post("/operator", response_model=OperatorProfile)
async def upsert_operator_profile(
    payload: OperatorProfileCreate,
    current_user: User = Depends(get_current_user),
):
    """Create or update an operator profile."""
    collection = Database.get_collection("operator_profiles")
    existing = await collection.find_one({"owner_user_id": current_user.user_id, "slug": payload.slug})
    if payload.is_active:
        await _deactivate_other_profiles("operator_profiles", current_user.user_id, payload.slug)

    doc = {
        "owner_user_id": current_user.user_id,
        "slug": payload.slug,
        "display_name": payload.display_name,
        "email_identity": payload.email_identity,
        "linkedin_url": payload.linkedin_url,
        "preferred_roles": payload.preferred_roles,
        "preferred_locations": payload.preferred_locations,
        "preferred_channels": [channel.value for channel in payload.preferred_channels],
        "salary_target": payload.salary_target.model_dump() if payload.salary_target else None,
        "exclusions": payload.exclusions,
        "metadata": payload.metadata,
        "resume_asset_id": payload.resume_asset_id,
        "resume_path": payload.resume_path,
        "is_active": payload.is_active,
        "updated_at": datetime.utcnow(),
    }

    if existing:
        await collection.update_one({"_id": existing["_id"]}, {"$set": doc})
        stored = await collection.find_one({"_id": existing["_id"]})
    else:
        profile_id = new_profile_id()
        full_doc = {
            "_id": profile_id,
            "profile_id": profile_id,
            "created_at": datetime.utcnow(),
            **doc,
        }
        await collection.insert_one(full_doc)
        stored = full_doc

    return OperatorProfile(**stored)


@router.get("/operator", response_model=List[OperatorProfile])
async def list_operator_profiles(current_user: User = Depends(get_current_user)):
    """List operator profiles for the current user."""
    docs = await Database.get_collection("operator_profiles").find(
        {"owner_user_id": current_user.user_id}
    ).sort("created_at", -1).to_list(length=None)
    return [OperatorProfile(**doc) for doc in docs]


@router.post("/operator/{slug}/activate", response_model=APIResponse)
async def activate_operator_profile(slug: str, current_user: User = Depends(get_current_user)):
    """Mark one operator profile as active."""
    collection = Database.get_collection("operator_profiles")
    existing = await collection.find_one({"owner_user_id": current_user.user_id, "slug": slug})
    if not existing:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Operator profile not found")

    await _deactivate_other_profiles("operator_profiles", current_user.user_id, slug)
    await collection.update_one(
        {"_id": existing["_id"]},
        {"$set": {"is_active": True, "updated_at": datetime.utcnow()}},
    )
    return APIResponse(success=True, message="Operator profile activated")


@router.post("/business", response_model=BusinessProfile)
async def upsert_business_profile(
    payload: BusinessProfileCreate,
    current_user: User = Depends(get_current_user),
):
    """Create or update a business profile."""
    collection = Database.get_collection("business_profiles")
    existing = await collection.find_one({"owner_user_id": current_user.user_id, "slug": payload.slug})

    doc = {
        "owner_user_id": current_user.user_id,
        "slug": payload.slug,
        "business_name": payload.business_name,
        "product_name": payload.product_name,
        "tagline": payload.tagline,
        "ideal_customer_profile": payload.ideal_customer_profile,
        "proof_points": payload.proof_points,
        "disallowed_claims": payload.disallowed_claims,
        "target_personas": payload.target_personas,
        "approved_channels": [channel.value for channel in payload.approved_channels],
        "website_url": payload.website_url,
        "linkedin_url": payload.linkedin_url,
        "metadata": payload.metadata,
        "is_active": payload.is_active,
        "updated_at": datetime.utcnow(),
    }

    if existing:
        await collection.update_one({"_id": existing["_id"]}, {"$set": doc})
        stored = await collection.find_one({"_id": existing["_id"]})
    else:
        profile_id = new_profile_id()
        full_doc = {
            "_id": profile_id,
            "profile_id": profile_id,
            "created_at": datetime.utcnow(),
            **doc,
        }
        await collection.insert_one(full_doc)
        stored = full_doc

    return BusinessProfile(**stored)


@router.get("/business", response_model=List[BusinessProfile])
async def list_business_profiles(current_user: User = Depends(get_current_user)):
    """List business profiles for the current user."""
    docs = await Database.get_collection("business_profiles").find(
        {"owner_user_id": current_user.user_id}
    ).sort("created_at", -1).to_list(length=None)
    return [BusinessProfile(**doc) for doc in docs]


@router.post("/policy", response_model=CommercialPolicy)
async def upsert_commercial_policy(
    payload: CommercialPolicyCreate,
    current_user: User = Depends(get_current_user),
):
    """Create or update a commercial policy."""
    collection = Database.get_collection("commercial_policies")
    existing = await collection.find_one({"owner_user_id": current_user.user_id, "slug": payload.slug})
    if payload.is_active:
        await collection.update_many(
            {"owner_user_id": current_user.user_id},
            {"$set": {"is_active": False, "updated_at": datetime.utcnow()}},
        )

    doc = {
        "owner_user_id": current_user.user_id,
        "slug": payload.slug,
        "review_required": payload.review_required,
        "auto_send_enabled": payload.auto_send_enabled,
        "enrichment_enabled": payload.enrichment_enabled,
        "allowed_channels": [channel.value for channel in payload.allowed_channels],
        "daily_caps": payload.daily_caps.model_dump(),
        "per_target_cooldown_hours": payload.per_target_cooldown_hours,
        "confidence_threshold": payload.confidence_threshold,
        "active_profile_binding": payload.active_profile_binding,
        "is_active": payload.is_active,
        "updated_at": datetime.utcnow(),
    }

    if existing:
        await collection.update_one({"_id": existing["_id"]}, {"$set": doc})
        stored = await collection.find_one({"_id": existing["_id"]})
    else:
        policy_id = new_profile_id()
        full_doc = {
            "_id": policy_id,
            "policy_id": policy_id,
            "created_at": datetime.utcnow(),
            **doc,
        }
        await collection.insert_one(full_doc)
        stored = full_doc

    return CommercialPolicy(**stored)


@router.get("/resolved", response_model=ResolvedProfilesResponse)
async def get_resolved_profiles(current_user: User = Depends(get_current_user)):
    """Resolve the currently active operator, businesses, and policy."""
    operator_doc = await Database.get_collection("operator_profiles").find_one(
        {"owner_user_id": current_user.user_id, "is_active": True}
    )
    business_docs = await Database.get_collection("business_profiles").find(
        {"owner_user_id": current_user.user_id, "is_active": True}
    ).sort("slug", 1).to_list(length=None)
    policy_doc = await Database.get_collection("commercial_policies").find_one(
        {"owner_user_id": current_user.user_id, "is_active": True}
    )

    return ResolvedProfilesResponse(
        operator_profile=OperatorProfile(**operator_doc) if operator_doc else None,
        business_profiles=[BusinessProfile(**doc) for doc in business_docs],
        commercial_policy=CommercialPolicy(**policy_doc) if policy_doc else None,
    )
