import io

import pytest

from app.db import Database


@pytest.mark.asyncio
async def test_upload_asset_and_create_operator_profile(client, auth_headers):
    upload = await client.post(
        "/api/v1/profiles/assets/upload?asset_type=RESUME",
        files={"file": ("resume.md", io.BytesIO(b"# Resume\nExperience"), "text/markdown")},
        headers=auth_headers,
    )
    assert upload.status_code == 200
    asset = upload.json()
    assert asset["asset_id"]
    assert asset["filename"] == "resume.md"

    create = await client.post(
        "/api/v1/profiles/operator",
        json={
            "slug": "default",
            "display_name": "Fernando",
            "email_identity": "fern@example.com",
            "preferred_roles": ["Growth Lead"],
            "preferred_locations": ["Remote"],
            "preferred_channels": ["EMAIL", "LINKEDIN_DM"],
            "resume_asset_id": asset["asset_id"],
            "resume_path": "operator_data/personal/cv/master_cv.md",
            "is_active": True,
        },
        headers=auth_headers,
    )
    assert create.status_code == 200
    data = create.json()
    assert data["slug"] == "default"
    assert data["resume_asset_id"] == asset["asset_id"]
    assert data["is_active"] is True

    stored_asset = await Database.get_collection("profile_assets").find_one({"asset_id": asset["asset_id"]})
    assert stored_asset is not None


@pytest.mark.asyncio
async def test_resolved_profiles_returns_active_state(client, auth_headers):
    await client.post(
        "/api/v1/profiles/operator",
        json={
            "slug": "default",
            "display_name": "Fernando",
            "preferred_roles": ["Growth Lead"],
            "preferred_locations": ["Remote"],
            "is_active": True,
        },
        headers=auth_headers,
    )
    await client.post(
        "/api/v1/profiles/business",
        json={
            "slug": "lenquant",
            "business_name": "LenQuant",
            "product_name": "LenQuant",
            "ideal_customer_profile": ["Funds"],
            "target_personas": ["Founder"],
            "approved_channels": ["EMAIL"],
            "is_active": True,
        },
        headers=auth_headers,
    )
    await client.post(
        "/api/v1/profiles/policy",
        json={
            "slug": "default",
            "review_required": True,
            "auto_send_enabled": False,
            "allowed_channels": ["EMAIL", "LINKEDIN_DM"],
            "is_active": True,
        },
        headers=auth_headers,
    )

    resolved = await client.get("/api/v1/profiles/resolved", headers=auth_headers)
    assert resolved.status_code == 200
    data = resolved.json()
    assert data["operator_profile"]["slug"] == "default"
    assert len(data["business_profiles"]) == 1
    assert data["business_profiles"][0]["slug"] == "lenquant"
    assert data["commercial_policy"]["slug"] == "default"


@pytest.mark.asyncio
async def test_activate_operator_profile_deactivates_previous(client, auth_headers):
    await client.post(
        "/api/v1/profiles/operator",
        json={"slug": "default", "display_name": "Fernando", "is_active": True},
        headers=auth_headers,
    )
    await client.post(
        "/api/v1/profiles/operator",
        json={"slug": "secondary", "display_name": "Second Profile", "is_active": False},
        headers=auth_headers,
    )

    activate = await client.post("/api/v1/profiles/operator/secondary/activate", headers=auth_headers)
    assert activate.status_code == 200

    profiles = await client.get("/api/v1/profiles/operator", headers=auth_headers)
    assert profiles.status_code == 200
    data = {item["slug"]: item for item in profiles.json()}
    assert data["secondary"]["is_active"] is True
    assert data["default"]["is_active"] is False
