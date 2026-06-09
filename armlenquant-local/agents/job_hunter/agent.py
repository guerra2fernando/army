"""
Job Hunter Agent
Full implementation for autonomous job searching.
"""
from typing import Dict, Any, List, Optional
from pathlib import Path
from datetime import datetime

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from agents.base_agent import BaseAgent, AgentResult
from agents.capability_manager import CapabilityError
from models.capability import CapabilityGrant, CapabilityPolicy
from poller.config import get_settings
from poller.profile_loader import load_commercial_policy, load_operator_profile
from agents.commercial_ops.models import (
    DraftMessage,
    FollowupDraft,
    OutreachChannel,
    ProfileBinding,
    SpecialistDraftPackage,
    SpecialistLane,
    SpecialistName,
    TargetPersona,
)
from .searcher import JobSearcher
from .job_parser import JobParser
from .matcher import JobMatcher
from .drafter import DocumentDrafter
from .models import JobListing, JobSource, JobStatus, MatchResult

settings = get_settings()


class JobHunterAgent(BaseAgent):
    """
    Job Hunter - Autonomous Career Intelligence Agent
    
    Capabilities:
    - Search for jobs using Google Dorks across ATS platforms
    - Parse and extract job details from listings
    - Match jobs against user CV and preferences
    - Generate tailored resumes and cover letters
    - Create organized application packages
    """
    
    def __init__(self):
        super().__init__("JOB_HUNTER", version="2.0.0")
        self.searcher = JobSearcher()
        self.matcher = JobMatcher()
        self.drafter = DocumentDrafter()
        self.parser: Optional[JobParser] = None
        self._cv_content: Optional[str] = None

    def get_capability_grants(self) -> list[CapabilityGrant]:
        """Define sandbox grants for Job Hunter."""
        allowed_path = str(settings.job_drafts_path)
        operator_data_path = str(settings.operator_data_root.resolve())
        return [
            CapabilityGrant(
                capability_id="web_scraping",
                policy_override=CapabilityPolicy(
                    allowed_domains=[
                        "*.google.com",
                        "*.linkedin.com",
                        "*.indeed.com",
                        "*.glassdoor.com",
                        "*.ashbyhq.com",
                        "*.workable.com",
                        "*.greenhouse.io",
                    ],
                ),
            ),
            CapabilityGrant(
                capability_id="file_read",
                policy_override=CapabilityPolicy(
                    allowed_paths=[
                        str(settings.cv_path),
                        operator_data_path,
                        str(settings.operator_data_root / "**"),
                    ]
                ),
            ),
            CapabilityGrant(
                capability_id="file_write",
                policy_override=CapabilityPolicy(
                    allowed_paths=[allowed_path, str(settings.job_drafts_path / "**")],
                    blocked_paths=[],
                    max_file_size_mb=100,
                ),
            ),
            CapabilityGrant(
                capability_id="browser_navigate",
                policy_override=CapabilityPolicy(
                    allowed_domains=["*.google.com", "*.linkedin.com", "*.indeed.com"]
                ),
            ),
        ]
    
    async def execute(self, payload: Dict[str, Any]) -> AgentResult:
        """Execute job hunting task."""
        action = self._normalize_action(payload.get("action", "search"))
        
        self.logger.info(f"Executing action: {action}")
        
        try:
            if action == "search":
                return await self._action_search(payload)
            elif action == "generate_materials":
                return await self._action_generate_materials(payload)
            elif action == "match_job":
                return await self._action_match_job(payload)
            elif action == "parse_job":
                return await self._action_parse_job(payload)
            elif action == "draft_outreach":
                return await self._action_draft_outreach(payload)
            else:
                return AgentResult(
                    success=False,
                    error=f"Unknown action: {action}"
                )
        except Exception as e:
            self.logger.error(f"Action {action} failed: {e}")
            return AgentResult(success=False, error=str(e))
    
    async def _action_search(self, payload: Dict[str, Any]) -> AgentResult:
        """Search for jobs based on criteria."""
        roles = payload.get("roles") or payload.get("titles") or ["Growth Lead", "Head of Growth"]
        locations = payload.get("locations", ["Remote"])
        sources = payload.get("sources")  # Optional list of source strings
        limit = payload.get("limit", 20)
        
        # Convert source strings to enums if provided
        source_enums = None
        if sources:
            source_enums = [JobSource(s) if isinstance(s, str) else s for s in sources]
        
        # Initialize browser
        await self.searcher.initialize()
        
        try:
            # Search for jobs
            try:
                jobs = await self.execute_with_capability(
                    "web_scraping",
                    self.searcher.search_jobs,
                    roles=roles,
                    locations=locations,
                    sources=source_enums,
                    limit_per_query=10,
                )
            except CapabilityError as exc:
                return AgentResult(success=False, error=str(exc))
            
            if not jobs:
                return AgentResult(
                    success=True,
                    data={"jobs_found": 0, "message": "No new jobs found"}
                )
            
            # Parse job details
            self.parser = JobParser(self.searcher.browser)
            
            parsed_jobs = []
            for job in jobs[:limit]:
                if job.source == JobSource.DIRECT and job.description:
                    parsed_jobs.append(job)
                    continue
                try:
                    parsed = await self.parser.parse_job(job)
                    parsed_jobs.append(parsed)
                except Exception as e:
                    self.logger.warning(f"Failed to parse {job.url}: {e}")
                    parsed_jobs.append(job)  # Keep unparsed job
            
            # Load CV for matching
            await self._load_cv()
            
            if self._cv_content:
                # Match jobs against CV
                for job in parsed_jobs:
                    try:
                        match = await self.matcher.match_job(job, self._cv_content)
                        job.match_score = match.overall_score
                    except Exception as e:
                        self.logger.warning(f"Matching failed for {job.job_id}: {e}")
            
            # Sort by match score (highest first)
            parsed_jobs.sort(key=lambda j: j.match_score or 0, reverse=True)
            
            # Identify high matches
            high_matches = [j for j in parsed_jobs if (j.match_score or 0) >= 75]
            
            return AgentResult(
                success=True,
                data={
                    "jobs_found": len(parsed_jobs),
                    "high_matches": len(high_matches),
                    "jobs": [j.model_dump() for j in parsed_jobs[:10]],
                    "all_job_ids": [j.job_id for j in parsed_jobs]
                }
            )
            
        finally:
            await self.searcher.close()
    
    async def _action_generate_materials(
        self,
        payload: Dict[str, Any]
    ) -> AgentResult:
        """Generate application materials for a job."""
        job_data = payload.get("job")
        
        if not job_data:
            return AgentResult(
                success=False,
                error="No job data provided"
            )
        
        # Create job listing from data
        try:
            job = JobListing(**job_data)
        except Exception as e:
            return AgentResult(
                success=False,
                error=f"Invalid job data: {e}"
            )
        
        # Load CV
        await self._load_cv()
        
        if not self._cv_content:
            return AgentResult(
                success=False,
                error="CV not found. Please ensure CV file exists at configured path."
            )
        
        # Match job to get analysis
        match_result = await self.matcher.match_job(job, self._cv_content)
        
        # Generate application package inside sandbox
        try:
            # Ensure read access to CV is allowed
            await self.capability_manager.check_permission(
                self.name,
                "file_read",
                policy_params={"path": str(settings.cv_path)},
            )
            draft = await self.execute_with_capability(
                "file_write",
                self.drafter.generate_application,
                policy_params={"path": str(settings.job_drafts_path)},
                job=job,
                match_result=match_result,
                cv_content=self._cv_content,
            )
        except CapabilityError as exc:
            return AgentResult(success=False, error=str(exc))
        
        return AgentResult(
            success=True,
            data={
                "draft": draft.model_dump(),
                "folder_path": draft.folder_path,
                "match_score": match_result.overall_score,
                "recommendation": match_result.recommendation
            }
        )
    
    async def _action_match_job(self, payload: Dict[str, Any]) -> AgentResult:
        """Match a specific job against CV."""
        job_data = payload.get("job")
        
        if not job_data:
            return AgentResult(
                success=False,
                error="No job data provided"
            )
        
        try:
            job = JobListing(**job_data)
        except Exception as e:
            return AgentResult(
                success=False,
                error=f"Invalid job data: {e}"
            )
        
        await self._load_cv()
        
        if not self._cv_content:
            return AgentResult(
                success=False,
                error="CV not found"
            )
        
        match_result = await self.matcher.match_job(job, self._cv_content)
        
        return AgentResult(
            success=True,
            data={"match": match_result.model_dump()}
        )
    
    async def _action_parse_job(self, payload: Dict[str, Any]) -> AgentResult:
        """Parse a single job URL to extract details."""
        url = payload.get("url")
        
        if not url:
            return AgentResult(
                success=False,
                error="No URL provided"
            )
        
        # Initialize browser if needed
        await self.searcher.initialize()
        
        try:
            # Create basic job listing
            job = JobListing(
                job_id=self.searcher._generate_job_id(url),
                url=url,
                source=self.searcher._detect_source(url),
                company="",
                title="",
                location="",
                discovered_at=datetime.utcnow()
            )
            
            # Parse
            self.parser = JobParser(self.searcher.browser)
            try:
                parsed_job = await self.execute_with_capability(
                    "web_scraping",
                    self.parser.parse_job,
                    policy_params={"url": url},
                    job=job,
                )
            except CapabilityError as exc:
                return AgentResult(success=False, error=str(exc))
            
            return AgentResult(
                success=True,
                data={"job": parsed_job.model_dump()}
            )
            
        finally:
            await self.searcher.close()

    async def _action_draft_outreach(self, payload: Dict[str, Any]) -> AgentResult:
        """Generate structured outreach drafts for a job opportunity."""
        job = self._coerce_job(payload)
        if not job:
            return AgentResult(success=False, error="No job data provided")

        operator_profile = load_operator_profile()
        policy = load_commercial_policy()
        await self._load_cv()

        match_result = await self._score_job_fit(job)
        target_persona = self._infer_job_persona(payload, job)
        recommended_channel = self._pick_job_channel(operator_profile, policy, target_persona)

        rationale = [
            f"Role fit scored at {int(match_result.overall_score)} out of 100.",
            f"Messaging is tailored for a {target_persona.value.lower().replace('_', ' ')} contact path.",
        ]
        if operator_profile and operator_profile.preferred_roles:
            rationale.append(f"Active operator profile prefers roles like {', '.join(operator_profile.preferred_roles[:2])}.")

        draft = SpecialistDraftPackage(
            specialist=SpecialistName.JOB_HUNTER,
            lane=SpecialistLane.JOBS,
            target_persona=target_persona,
            profile_binding=ProfileBinding(
                operator_profile_slug=operator_profile.slug if operator_profile else None,
                operator_display_name=operator_profile.display_name if operator_profile else None,
                policy_slug=policy.slug if policy else None,
            ),
            opportunity_id=payload.get("opportunity_id") or job.job_id,
            source_url=job.url,
            title=job.title,
            company=job.company,
            person_name=payload.get("person_name", ""),
            fit_score=round((match_result.overall_score or 0) / 100.0, 3),
            rationale=rationale + list(match_result.highlights[:2]),
            recommended_channel=recommended_channel,
            recommended_next_step="Review and approve the primary outreach draft before sending.",
            primary_draft=DraftMessage(
                channel=recommended_channel,
                subject=self._build_job_subject(job, target_persona),
                body=self._build_job_message(job, operator_profile, target_persona, match_result),
                cta=self._build_job_cta(target_persona),
            ),
            followups=[
                FollowupDraft(
                    delay_days=4,
                    channel=recommended_channel,
                    body=self._build_job_followup(job, operator_profile, target_persona, followup_number=1),
                ),
                FollowupDraft(
                    delay_days=8,
                    channel=recommended_channel,
                    body=self._build_job_followup(job, operator_profile, target_persona, followup_number=2),
                ),
            ],
            metadata={
                "job_id": job.job_id,
                "match_summary": match_result.recommendation,
                "contact_hint": payload.get("contact_title") or payload.get("contact_role"),
            },
        )

        return AgentResult(success=True, data={"draft_package": draft.model_dump(mode="json")})
    
    async def _load_cv(self):
        """Load CV content from file."""
        if self._cv_content:
            return

        operator_profile = load_operator_profile()
        cv_path = Path(operator_profile.resume_path) if operator_profile and operator_profile.resume_path else Path(settings.cv_path)
        
        if cv_path.exists():
            try:
                await self.capability_manager.check_permission(
                    self.name,
                    "file_read",
                    policy_params={"path": str(cv_path)},
                )
                self._cv_content = cv_path.read_text(encoding="utf-8")
                self.logger.info(f"CV loaded from file: {cv_path}")
            except Exception as e:
                self.logger.error(f"Failed to read CV file: {e}")
        else:
            self.logger.warning(f"CV file not found at: {cv_path}")

    def _normalize_action(self, action: str) -> str:
        """Map legacy cloud verbs to local execution verbs."""
        normalized = (action or "").strip().lower()
        aliases = {
            "search_jobs": "search",
            "generate_resume": "generate_materials",
            "generate_cover_letter": "generate_materials",
            "research_company": "parse_job",
            "track_application": "draft_outreach",
        }
        return aliases.get(normalized, normalized)

    def _coerce_job(self, payload: Dict[str, Any]) -> Optional[JobListing]:
        """Coerce payload data into a job listing."""
        job_data = payload.get("job")
        if isinstance(job_data, dict):
            return JobListing(**job_data)
        if payload.get("url"):
            return JobListing(
                job_id=payload.get("job_id") or self.searcher._generate_job_id(payload["url"]),
                url=payload["url"],
                source=self.searcher._detect_source(payload["url"]),
                company=payload.get("company", ""),
                title=payload.get("title", ""),
                location=payload.get("location", ""),
                description=payload.get("description", ""),
                requirements=payload.get("requirements", []),
                discovered_at=datetime.utcnow(),
            )
        return None

    async def _score_job_fit(self, job: JobListing) -> MatchResult:
        """Score job fit using the matcher when possible, with heuristic fallback."""
        if self._cv_content:
            try:
                return await self.matcher.match_job(job, self._cv_content)
            except Exception as exc:
                self.logger.warning(f"Matcher failed for draft generation: {exc}")

        profile = load_operator_profile()
        score = 50.0
        highlights: List[str] = []
        title_lower = job.title.lower()
        location_lower = job.location.lower()
        if profile:
            if any(role.lower() in title_lower for role in profile.preferred_roles):
                score += 20
                highlights.append("Role title matches active profile preferences.")
            if any(location.lower() in location_lower for location in profile.preferred_locations):
                score += 10
                highlights.append("Location aligns with active profile preferences.")
        if job.description:
            score += 5
        score = max(0.0, min(95.0, score))
        return MatchResult(
            job_id=job.job_id,
            overall_score=score,
            skill_match=score,
            experience_match=max(0.0, score - 5),
            culture_fit=max(0.0, score - 10),
            compensation_fit=max(0.0, score - 8),
            highlights=highlights,
            recommendation="Heuristic match used because CV-based matching was unavailable.",
        )

    def _infer_job_persona(self, payload: Dict[str, Any], job: JobListing) -> TargetPersona:
        """Infer who the outreach is for."""
        haystack = " ".join(
            [
                payload.get("contact_title", ""),
                payload.get("contact_role", ""),
                payload.get("person_name", ""),
                job.title,
                job.description[:250],
            ]
        ).lower()
        if any(term in haystack for term in ["recruiter", "talent", "sourcer", "people partner"]):
            return TargetPersona.RECRUITER
        if any(term in haystack for term in ["founder", "cofounder"]):
            return TargetPersona.FOUNDER
        return TargetPersona.HIRING_MANAGER

    def _pick_job_channel(self, operator_profile, policy, target_persona: TargetPersona) -> OutreachChannel:
        channels = []
        if operator_profile:
            channels.extend(operator_profile.preferred_channels)
        if policy:
            channels.extend(policy.allowed_channels)
        normalized = [str(channel).upper() for channel in channels]
        if target_persona == TargetPersona.RECRUITER and "EMAIL" in normalized:
            return OutreachChannel.EMAIL
        if "LINKEDIN_DM" in normalized:
            return OutreachChannel.LINKEDIN_DM
        if "EMAIL" in normalized:
            return OutreachChannel.EMAIL
        return OutreachChannel.MANUAL

    def _build_job_subject(self, job: JobListing, target_persona: TargetPersona) -> str:
        if target_persona == TargetPersona.RECRUITER:
            return f"{job.title} fit for {job.company}"
        return f"Interest in {job.title} at {job.company}"

    def _build_job_message(self, job: JobListing, operator_profile, target_persona: TargetPersona, match_result: MatchResult) -> str:
        display_name = operator_profile.display_name if operator_profile else "I"
        opener = {
            TargetPersona.RECRUITER: f"Hi, I'm {display_name} and I saw the {job.title} opening at {job.company}.",
            TargetPersona.FOUNDER: f"Hi, I'm {display_name}. Your {job.title} role at {job.company} stood out because I can bring immediate operator leverage.",
            TargetPersona.HIRING_MANAGER: f"Hi, I'm {display_name}. I'm reaching out directly about the {job.title} role at {job.company}.",
        }[target_persona]
        proof = match_result.highlights[0] if match_result.highlights else "My background aligns with the role's core scope."
        closing = {
            TargetPersona.RECRUITER: "If the team is still hiring, I'd be glad to share tailored materials and availability.",
            TargetPersona.FOUNDER: "If useful, I can send a brief plan for how I'd approach the role in the first 30 days.",
            TargetPersona.HIRING_MANAGER: "If helpful, I can send a concise outline of how I'd contribute in the first month.",
        }[target_persona]
        return f"{opener}\n\n{proof}\n\n{closing}"

    def _build_job_cta(self, target_persona: TargetPersona) -> str:
        if target_persona == TargetPersona.RECRUITER:
            return "Confirm whether the role is active and invite resume review."
        return "Invite a brief conversation or request permission to share tailored materials."

    def _build_job_followup(self, job: JobListing, operator_profile, target_persona: TargetPersona, followup_number: int) -> str:
        display_name = operator_profile.display_name if operator_profile else "I"
        if followup_number == 1:
            return (
                f"Following up on the {job.title} role at {job.company}. "
                f"{display_name} remains interested and can share tailored materials if helpful."
            )
        persona_line = "a quick note to reopen the thread" if target_persona == TargetPersona.RECRUITER else "a short follow-up in case direct outreach is easier"
        return f"Sending {persona_line} regarding the {job.title} opportunity at {job.company}."
    
    def get_capabilities(self) -> list:
        """Return list of agent capabilities."""
        return [
            "job_search",
            "job_parsing",
            "job_matching",
            "resume_tailoring",
            "cover_letter_generation",
            "company_research"
        ]
