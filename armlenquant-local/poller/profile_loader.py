"""
Local operator-data profile loader.
"""
import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from poller.config import get_settings


class LocalOperatorProfile(BaseModel):
    """Operator profile loaded from disk."""

    slug: str = "default"
    display_name: str
    email_identity: Optional[str] = None
    linkedin_url: Optional[str] = None
    preferred_roles: List[str] = Field(default_factory=list)
    preferred_locations: List[str] = Field(default_factory=list)
    preferred_channels: List[str] = Field(default_factory=list)
    resume_path: Optional[str] = None


class LocalBusinessProfile(BaseModel):
    """Business profile loaded from disk."""

    slug: str
    business_name: str
    product_name: str
    tagline: str = ""
    target_personas: List[str] = Field(default_factory=list)
    approved_channels: List[str] = Field(default_factory=list)
    is_active: bool = False


class LocalCommercialPolicy(BaseModel):
    """Commercial policy loaded from disk."""

    slug: str = "default"
    review_required: bool = True
    auto_send_enabled: bool = False
    enrichment_enabled: bool = False
    allowed_channels: List[str] = Field(default_factory=list)
    per_target_cooldown_hours: int = 72
    confidence_threshold: float = 0.75
    active_profile_binding: bool = True


class ResolvedLocalProfiles(BaseModel):
    """Resolved profile state from local folders."""

    operator_profile: Optional[LocalOperatorProfile] = None
    business_profiles: List[LocalBusinessProfile] = Field(default_factory=list)
    commercial_policy: Optional[LocalCommercialPolicy] = None


def _read_json(path: Path) -> Optional[Dict[str, Any]]:
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def _resolve_resume_path(personal_root: Path, raw_path: Optional[str]) -> Optional[Path]:
    if raw_path:
        candidate = Path(raw_path)
        if not candidate.is_absolute():
            candidate = (personal_root / candidate).resolve()
        if candidate.exists():
            return candidate

    cv_root = personal_root / "cv"
    if not cv_root.exists():
        return None

    preferred_names = ["master_cv.md", "master_cv.txt", "resume.md", "resume.txt", "resume.pdf"]
    for name in preferred_names:
        candidate = cv_root / name
        if candidate.exists():
            return candidate

    files = [item for item in cv_root.iterdir() if item.is_file()]
    return sorted(files)[0] if files else None


def load_operator_profile(root: Optional[Path] = None) -> Optional[LocalOperatorProfile]:
    """Load the active operator profile from disk."""
    settings = get_settings()
    root = (root or settings.operator_data_root).resolve()
    personal_root = root / "personal"
    payload = _read_json(personal_root / "profile.json")
    if not payload:
        return None

    profile = LocalOperatorProfile(**payload)
    resume_path = _resolve_resume_path(personal_root, profile.resume_path)
    if resume_path:
        profile.resume_path = str(resume_path)
    return profile


def load_business_profiles(root: Optional[Path] = None, only_active: bool = True) -> List[LocalBusinessProfile]:
    """Load business profiles from disk."""
    settings = get_settings()
    root = (root or settings.operator_data_root).resolve()
    business_root = root / "businesses"
    if not business_root.exists():
        return []

    selected = set(settings.active_business_slugs or [])
    profiles: List[LocalBusinessProfile] = []
    for profile_path in sorted(business_root.glob("*/profile.json")):
        payload = _read_json(profile_path)
        if not payload:
            continue
        profile = LocalBusinessProfile(**payload)
        if selected and profile.slug not in selected:
            continue
        if only_active and not selected and not profile.is_active:
            continue
        profiles.append(profile)
    return profiles


def load_commercial_policy(root: Optional[Path] = None) -> Optional[LocalCommercialPolicy]:
    """Load the shared commercial policy from disk."""
    settings = get_settings()
    root = (root or settings.operator_data_root).resolve()
    payload = _read_json(root / "shared" / "policy.json")
    return LocalCommercialPolicy(**payload) if payload else None


def resolve_active_profiles(root: Optional[Path] = None) -> ResolvedLocalProfiles:
    """Resolve all active local profiles."""
    return ResolvedLocalProfiles(
        operator_profile=load_operator_profile(root=root),
        business_profiles=load_business_profiles(root=root, only_active=True),
        commercial_policy=load_commercial_policy(root=root),
    )
