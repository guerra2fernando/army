import json
from pathlib import Path

from poller.profile_loader import (
    load_business_profiles,
    load_commercial_policy,
    load_operator_profile,
    resolve_active_profiles,
)


def _write_json(path: Path, payload: dict):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")


def test_load_operator_profile_resolves_resume(tmp_path):
    root = tmp_path / "operator_data"
    _write_json(
        root / "personal" / "profile.json",
        {
            "slug": "default",
            "display_name": "Fernando",
            "preferred_roles": ["Growth Lead"],
            "resume_path": "cv/master_cv.md",
        },
    )
    resume = root / "personal" / "cv" / "master_cv.md"
    resume.parent.mkdir(parents=True, exist_ok=True)
    resume.write_text("# CV", encoding="utf-8")

    profile = load_operator_profile(root=root)
    assert profile is not None
    assert profile.resume_path == str(resume.resolve())


def test_load_business_profiles_only_active(tmp_path):
    root = tmp_path / "operator_data"
    _write_json(
        root / "businesses" / "lenquant" / "profile.json",
        {
            "slug": "lenquant",
            "business_name": "LenQuant",
            "product_name": "LenQuant",
            "is_active": True,
        },
    )
    _write_json(
        root / "businesses" / "lenxys" / "profile.json",
        {
            "slug": "lenxys",
            "business_name": "Lenxys",
            "product_name": "Lenxys",
            "is_active": False,
        },
    )

    profiles = load_business_profiles(root=root, only_active=True)
    assert [item.slug for item in profiles] == ["lenquant"]


def test_resolve_active_profiles_bundle(tmp_path):
    root = tmp_path / "operator_data"
    _write_json(
        root / "personal" / "profile.json",
        {
            "slug": "default",
            "display_name": "Fernando",
        },
    )
    _write_json(
        root / "businesses" / "lenquant" / "profile.json",
        {
            "slug": "lenquant",
            "business_name": "LenQuant",
            "product_name": "LenQuant",
            "is_active": True,
        },
    )
    _write_json(
        root / "shared" / "policy.json",
        {
            "slug": "default",
            "review_required": True,
            "allowed_channels": ["EMAIL"],
        },
    )

    resolved = resolve_active_profiles(root=root)
    assert resolved.operator_profile is not None
    assert resolved.business_profiles[0].slug == "lenquant"
    assert resolved.commercial_policy is not None
    assert resolved.commercial_policy.review_required is True


def test_load_commercial_policy(tmp_path):
    root = tmp_path / "operator_data"
    _write_json(
        root / "shared" / "policy.json",
        {
            "slug": "default",
            "auto_send_enabled": False,
            "confidence_threshold": 0.8,
        },
    )
    policy = load_commercial_policy(root=root)
    assert policy is not None
    assert policy.confidence_threshold == 0.8
