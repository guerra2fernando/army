"""
Job Matcher
Matches jobs against user profile using skills and experience analysis.
"""
import re
from typing import List, Dict, Optional
from loguru import logger

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
from poller.config import get_settings
from .models import JobListing, MatchResult

settings = get_settings()


class JobMatcher:
    """
    Matches jobs against user CV and preferences.
    """
    
    # Common technical and soft skills for matching
    SKILL_KEYWORDS = [
        # Programming languages
        "python", "javascript", "typescript", "java", "go", "rust", "c++", "ruby", "php",
        # Frontend
        "react", "vue", "angular", "svelte", "nextjs", "html", "css",
        # Backend
        "node", "django", "flask", "fastapi", "express", "spring",
        # Data
        "sql", "postgresql", "mysql", "mongodb", "redis", "elasticsearch",
        # Cloud & DevOps
        "aws", "gcp", "azure", "kubernetes", "docker", "terraform", "ci/cd",
        # Growth & Marketing
        "growth", "marketing", "acquisition", "retention", "analytics", "seo", "sem",
        "paid", "organic", "conversion", "funnel", "a/b testing",
        # Soft skills
        "leadership", "management", "strategy", "communication", "teamwork",
        "problem-solving", "analytical", "data-driven",
    ]
    
    def __init__(self):
        self.logger = logger.bind(component="matcher")
        # Legacy attribute retained for tests/backwards compatibility
        self.client = "LOCAL_MATCHER"
    
    async def match_job(
        self,
        job: JobListing,
        cv_content: str
    ) -> MatchResult:
        """
        Calculate match score for a job against user profile.
        
        Args:
            job: Job listing to match
            cv_content: User's CV content
            
        Returns:
            MatchResult with scores and analysis
        """
        # Calculate individual scores
        skill_match = self._calculate_skill_match(job, cv_content)
        experience_match = self._calculate_experience_match(job, cv_content)
        culture_fit = 0.70  # Default - would need more data
        compensation_fit = self._calculate_compensation_fit(job)
        
        # Calculate overall score (weighted average)
        overall = (
            skill_match * 0.35 +
            experience_match * 0.25 +
            culture_fit * 0.15 +
            compensation_fit * 0.15 +
            0.10  # Base score
        )
        
        # Identify gaps and highlights
        skill_gaps = self._identify_skill_gaps(job, cv_content)
        highlights = self._identify_highlights(job, cv_content)
        
        # Generate recommendation
        if overall >= 0.90:
            recommendation = "Perfect match - apply immediately"
        elif overall >= 0.75:
            recommendation = "Strong match - worth applying"
        elif overall >= 0.60:
            recommendation = "Decent match - consider if interested"
        else:
            recommendation = "Weak match - may be a stretch"
        
        return MatchResult(
            job_id=job.job_id,
            overall_score=round(overall * 100, 1),
            skill_match=round(skill_match * 100, 1),
            experience_match=round(experience_match * 100, 1),
            culture_fit=round(culture_fit * 100, 1),
            compensation_fit=round(compensation_fit * 100, 1),
            skill_gaps=skill_gaps,
            highlights=highlights,
            recommendation=recommendation
        )
    
    def _calculate_skill_match(
        self,
        job: JobListing,
        cv_content: str
    ) -> float:
        """Calculate skill match score."""
        cv_lower = cv_content.lower()
        
        # Extract skills from requirements and description
        required_skills = []
        
        # From requirements
        for req in job.requirements:
            skills = self._extract_skills_from_text(req)
            required_skills.extend(skills)
        
        # From description
        desc_skills = self._extract_skills_from_text(job.description)
        required_skills.extend(desc_skills)
        
        # Deduplicate
        required_skills = list(set(required_skills))
        
        if not required_skills:
            return 0.7  # Default if can't parse
        
        # Count matches
        matched = sum(1 for skill in required_skills if skill.lower() in cv_lower)
        
        return matched / len(required_skills) if required_skills else 0.7
    
    def _calculate_experience_match(
        self,
        job: JobListing,
        cv_content: str
    ) -> float:
        """Calculate experience match score."""
        # Extract required years from job
        years_pattern = r"(\d+)\+?\s*years?"
        job_text = " ".join(job.requirements) + " " + job.description
        job_years = re.findall(years_pattern, job_text.lower())
        
        if not job_years:
            return 0.8  # Default if no years specified
        
        required_years = max(int(y) for y in job_years)
        
        # Extract years from CV
        cv_years = re.findall(years_pattern, cv_content.lower())
        if not cv_years:
            return 0.5  # Can't determine experience
        
        user_years = max(int(y) for y in cv_years)
        
        # Calculate match
        if user_years >= required_years:
            return 1.0
        elif user_years >= required_years - 2:
            return 0.8
        elif user_years >= required_years - 4:
            return 0.6
        else:
            return 0.4
    
    def _calculate_compensation_fit(self, job: JobListing) -> float:
        """Calculate compensation fit score."""
        if not job.salary_range:
            return 0.7  # Unknown salary
        
        # Would compare against user expectations
        # For now, assume it's reasonable if provided
        return 0.8
    
    def _identify_skill_gaps(
        self,
        job: JobListing,
        cv_content: str
    ) -> List[str]:
        """Identify skills required but not in CV."""
        cv_lower = cv_content.lower()
        gaps = []
        
        # Check requirements
        for req in job.requirements:
            skills = self._extract_skills_from_text(req)
            for skill in skills:
                if skill.lower() not in cv_lower:
                    gaps.append(skill)
        
        # Also check description
        desc_skills = self._extract_skills_from_text(job.description)
        for skill in desc_skills:
            if skill.lower() not in cv_lower and skill not in gaps:
                gaps.append(skill)
        
        return list(set(gaps))[:5]  # Top 5 gaps
    
    def _identify_highlights(
        self,
        job: JobListing,
        cv_content: str
    ) -> List[str]:
        """Identify strong matches to highlight."""
        cv_lower = cv_content.lower()
        highlights = []
        
        for req in job.requirements:
            # Check if any significant keyword from requirement appears in CV
            req_words = set(req.lower().split())
            matching_keywords = [w for w in req_words if len(w) > 4 and w in cv_lower]
            if matching_keywords:
                highlights.append(f"Matches: {req[:50]}...")
        
        return highlights[:5]
    
    def _extract_skills_from_text(self, text: str) -> List[str]:
        """Extract skill keywords from text."""
        if not text:
            return []
            
        found = []
        text_lower = text.lower()
        
        for skill in self.SKILL_KEYWORDS:
            if skill in text_lower:
                found.append(skill)
        
        return found

