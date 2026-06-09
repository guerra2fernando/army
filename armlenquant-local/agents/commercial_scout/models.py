"""
Commercial scout data models.
"""
from datetime import datetime
from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field


class LeadSource(str, Enum):
    LINKEDIN = "linkedin"
    COMPANY_WEBSITE = "company_website"
    DIRECT = "direct"


class LeadCandidate(BaseModel):
    lead_id: str
    url: str
    source: LeadSource
    title: str = ""
    person_name: str = ""
    company: str = ""
    location: str = ""
    discovered_at: datetime = Field(default_factory=datetime.utcnow)


class LeadSearchCriteria(BaseModel):
    personas: List[str] = Field(default_factory=lambda: ["Founder", "CEO"])
    keywords: List[str] = Field(default_factory=list)
    locations: List[str] = Field(default_factory=lambda: ["Remote"])
    limit_per_query: int = 10
