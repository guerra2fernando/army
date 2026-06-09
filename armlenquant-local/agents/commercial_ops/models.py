"""
Reusable specialist output schema for local Commercial Ops agents.
"""
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class OutreachChannel(str, Enum):
    EMAIL = "EMAIL"
    LINKEDIN_CONNECT = "LINKEDIN_CONNECT"
    LINKEDIN_DM = "LINKEDIN_DM"
    MANUAL = "MANUAL"


class SpecialistLane(str, Enum):
    JOBS = "JOBS"
    LENQUANT = "LENQUANT"
    LENXYS = "LENXYS"
    SERVICES = "SERVICES"
    TRADING = "TRADING"


class SpecialistName(str, Enum):
    JOB_HUNTER = "JOB_HUNTER"
    LENQUANT_SELLER = "LENQUANT_SELLER"
    LENXYS_SELLER = "LENXYS_SELLER"
    SERVICES_SELLER = "SERVICES_SELLER"
    TRADING_SELLER = "TRADING_SELLER"


class TargetPersona(str, Enum):
    RECRUITER = "RECRUITER"
    HIRING_MANAGER = "HIRING_MANAGER"
    FOUNDER = "FOUNDER"
    CEO = "CEO"
    COO = "COO"
    PORTFOLIO_MANAGER = "PORTFOLIO_MANAGER"
    HEAD_OF_GROWTH = "HEAD_OF_GROWTH"
    GENERIC = "GENERIC"


class ProfileBinding(BaseModel):
    operator_profile_slug: Optional[str] = None
    operator_display_name: Optional[str] = None
    business_profile_slug: Optional[str] = None
    business_name: Optional[str] = None
    product_name: Optional[str] = None
    policy_slug: Optional[str] = None


class DraftMessage(BaseModel):
    channel: OutreachChannel
    subject: Optional[str] = None
    body: str
    cta: str = ""


class FollowupDraft(BaseModel):
    delay_days: int = Field(ge=1, le=30)
    channel: OutreachChannel
    body: str


class SpecialistDraftPackage(BaseModel):
    specialist: SpecialistName
    lane: SpecialistLane
    target_persona: TargetPersona
    profile_binding: ProfileBinding
    created_at: datetime = Field(default_factory=datetime.utcnow)
    opportunity_id: Optional[str] = None
    source_url: str
    title: str = ""
    company: str = ""
    person_name: str = ""
    fit_score: float = Field(default=0.0, ge=0.0, le=1.0)
    rationale: List[str] = Field(default_factory=list)
    recommended_channel: OutreachChannel = OutreachChannel.MANUAL
    recommended_next_step: str
    primary_draft: DraftMessage
    followups: List[FollowupDraft] = Field(default_factory=list, max_length=2)
    metadata: Dict[str, Any] = Field(default_factory=dict)
