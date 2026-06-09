"""
Job Hunter Data Models
"""
from datetime import datetime
from typing import Optional, List, Dict
from pydantic import BaseModel, Field
from enum import Enum


class JobSource(str, Enum):
    """ATS platforms for job listings."""
    LEVER = "lever"
    GREENHOUSE = "greenhouse"
    ASHBY = "ashby"
    WORKABLE = "workable"
    DIRECT = "direct"


class JobStatus(str, Enum):
    """Job application status."""
    NEW = "NEW"
    DRAFTING = "DRAFTING"
    DRAFT_READY = "DRAFT_READY"
    APPLIED = "APPLIED"
    PHONE_SCREEN = "PHONE_SCREEN"
    INTERVIEW = "INTERVIEW"
    OFFER = "OFFER"
    REJECTED = "REJECTED"
    WITHDRAWN = "WITHDRAWN"


class JobListing(BaseModel):
    """Job listing data."""
    job_id: str
    url: str
    source: JobSource
    company: str
    title: str
    location: str
    description: str = ""
    requirements: List[str] = Field(default_factory=list)
    nice_to_haves: List[str] = Field(default_factory=list)
    salary_range: Optional[Dict[str, int]] = None  # {"min": 100000, "max": 150000}
    posted_at: Optional[datetime] = None
    discovered_at: datetime = Field(default_factory=datetime.utcnow)
    match_score: Optional[float] = None
    status: JobStatus = JobStatus.NEW
    
    class Config:
        use_enum_values = True


class MatchResult(BaseModel):
    """Job matching result."""
    job_id: str
    overall_score: float = Field(ge=0, le=100)
    skill_match: float = Field(ge=0, le=100)
    experience_match: float = Field(ge=0, le=100)
    culture_fit: float = Field(ge=0, le=100)
    compensation_fit: float = Field(ge=0, le=100)
    skill_gaps: List[str] = Field(default_factory=list)
    highlights: List[str] = Field(default_factory=list)
    recommendation: str = ""


class ApplicationDraft(BaseModel):
    """Application materials draft."""
    job_id: str
    company: str
    role: str
    resume_path: str
    cover_letter_path: str
    company_research_path: str = ""
    match_analysis: Optional[MatchResult] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    folder_path: str


class CompanyInfo(BaseModel):
    """Company research data."""
    name: str
    description: str = ""
    employees: Optional[str] = None
    funding: Optional[str] = None
    industry: str = ""
    culture_signals: List[str] = Field(default_factory=list)
    recent_news: List[Dict] = Field(default_factory=list)
    glassdoor_rating: Optional[float] = None
    key_people: List[Dict] = Field(default_factory=list)
    growth_signals: List[str] = Field(default_factory=list)


class SearchCriteria(BaseModel):
    """Job search criteria."""
    roles: List[str] = Field(default_factory=lambda: ["Growth Lead", "Head of Growth"])
    locations: List[str] = Field(default_factory=lambda: ["Remote"])
    sources: List[JobSource] = Field(default_factory=lambda: list(JobSource))
    limit_per_query: int = 10

