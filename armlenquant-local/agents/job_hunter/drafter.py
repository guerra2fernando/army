"""
Document Drafter
Generates tailored resumes and cover letters.
"""
import os
from pathlib import Path
from datetime import datetime
from typing import Optional

from loguru import logger

import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
from agents.llm_client import get_llm_client, LLMClient
from poller.config import get_settings
from .models import JobListing, MatchResult, ApplicationDraft, CompanyInfo

settings = get_settings()


class DocumentDrafter:
    """
    Generates application materials using AI.
    """
    
    def __init__(self, llm_client: LLMClient = None):
        self.logger = logger.bind(component="drafter")
        self.output_path = Path(settings.job_drafts_path)
        
        try:
            self.client = llm_client or get_llm_client()
            if not self.client.is_available:
                self.client = None
                self.logger.warning("No LLM client available")
        except Exception as e:
            self.client = None
            self.logger.warning(f"LLM client not available: {e}")
        
        # Ensure output path exists
        try:
            self.output_path.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            self.logger.warning(f"Could not create output path: {e}")
    
    async def generate_application(
        self,
        job: JobListing,
        match_result: MatchResult,
        cv_content: str,
        company_info: Optional[CompanyInfo] = None
    ) -> ApplicationDraft:
        """
        Generate complete application package.
        
        Args:
            job: Job listing
            match_result: Match analysis
            cv_content: Base CV content
            company_info: Company research
            
        Returns:
            ApplicationDraft with file paths
        """
        self.logger.info(f"Generating application for {job.company} - {job.title}")
        
        # Create folder for this application
        date_str = datetime.now().strftime("%Y-%m-%d")
        company_slug = self._slugify(job.company)
        title_slug = self._slugify(job.title)
        folder_name = f"{date_str}_{company_slug}_{title_slug}"
        folder_path = self.output_path / folder_name
        folder_path.mkdir(parents=True, exist_ok=True)
        
        # Generate tailored resume
        resume_content = await self._generate_resume(job, cv_content, match_result)
        resume_path = folder_path / "resume_tailored.md"
        resume_path.write_text(resume_content, encoding="utf-8")
        
        # Generate cover letter
        cover_letter = await self._generate_cover_letter(
            job, cv_content, match_result, company_info
        )
        cover_letter_path = folder_path / "cover_letter.md"
        cover_letter_path.write_text(cover_letter, encoding="utf-8")
        
        # Save company research
        research_path = folder_path / "company_research.md"
        if company_info:
            research_content = self._format_company_research(company_info)
            research_path.write_text(research_content, encoding="utf-8")
        else:
            research_path.write_text("# Company Research\n\nNo company research available.", encoding="utf-8")
        
        # Save job description
        jd_path = folder_path / "job_description.txt"
        jd_path.write_text(job.description or "No description available", encoding="utf-8")
        
        # Save match analysis
        analysis_path = folder_path / "match_analysis.json"
        analysis_path.write_text(match_result.model_dump_json(indent=2), encoding="utf-8")
        
        # Create README
        readme_content = self._generate_readme(job, match_result)
        (folder_path / "README.md").write_text(readme_content, encoding="utf-8")
        
        self.logger.info(f"Application package created: {folder_path}")
        
        return ApplicationDraft(
            job_id=job.job_id,
            company=job.company,
            role=job.title,
            resume_path=str(resume_path),
            cover_letter_path=str(cover_letter_path),
            company_research_path=str(research_path),
            match_analysis=match_result,
            created_at=datetime.utcnow(),
            folder_path=str(folder_path)
        )
    
    def _slugify(self, text: str) -> str:
        """Convert text to URL-safe slug."""
        import re
        text = text.lower().strip()
        text = re.sub(r'[^\w\s-]', '', text)
        text = re.sub(r'[\s_-]+', '_', text)
        return text[:50]  # Limit length
    
    async def _generate_resume(
        self,
        job: JobListing,
        cv_content: str,
        match_result: MatchResult
    ) -> str:
        """Generate tailored resume."""
        
        if not self.client:
            return self._generate_fallback_resume(job, cv_content, match_result)
        
        requirements_text = '\n'.join(f'- {r}' for r in job.requirements[:10]) if job.requirements else 'Not specified'
        skill_gaps = ', '.join(match_result.skill_gaps) if match_result.skill_gaps else 'None'
        highlights = ', '.join(match_result.highlights) if match_result.highlights else 'General experience'
        
        prompt = f"""You are an expert resume writer. Tailor this resume for the following job:

**Job Title:** {job.title}
**Company:** {job.company}
**Key Requirements:**
{requirements_text}

**Match Analysis:**
- Overall Match: {match_result.overall_score}%
- Skill Gaps to Address: {skill_gaps}
- Highlights: {highlights}

**Original CV:**
{cv_content[:3000]}

**Instructions:**
1. Tailor the professional summary for this specific role
2. Highlight relevant experience that matches requirements
3. Use keywords from the job description naturally
4. Keep the same structure but emphasize relevant skills
5. Output in clean Markdown format

Generate the tailored resume:"""

        try:
            response = await self.client.chat(
                messages=[{"role": "user", "content": prompt}],
                temperature=0.7,
                max_tokens=2000
            )
            
            return response.content
        except Exception as e:
            self.logger.error(f"LLM resume generation failed: {e}")
            return self._generate_fallback_resume(job, cv_content, match_result)
    
    def _generate_fallback_resume(
        self,
        job: JobListing,
        cv_content: str,
        match_result: MatchResult
    ) -> str:
        """Generate fallback resume when OpenAI is unavailable."""
        return f"""# Resume - Tailored for {job.company}

## Target Position: {job.title}

---

## Match Score: {match_result.overall_score}%

### Key Highlights
{chr(10).join('- ' + h for h in match_result.highlights) if match_result.highlights else '- See original CV'}

### Areas to Emphasize
{chr(10).join('- Address: ' + g for g in match_result.skill_gaps) if match_result.skill_gaps else '- Strong overall match'}

---

## Original CV Content

{cv_content}

---

*Note: This is a template. Please tailor manually before submitting.*
"""
    
    async def _generate_cover_letter(
        self,
        job: JobListing,
        cv_content: str,
        match_result: MatchResult,
        company_info: Optional[CompanyInfo]
    ) -> str:
        """Generate personalized cover letter."""
        
        if not self.client:
            return self._generate_fallback_cover_letter(job, match_result, company_info)
        
        company_context = ""
        if company_info:
            company_context = f"""
**Company Context:**
- Industry: {company_info.industry}
- Employees: {company_info.employees or 'Unknown'}
- Recent News: {company_info.recent_news[0].get('title', 'N/A') if company_info.recent_news else 'N/A'}
- Culture: {', '.join(company_info.culture_signals) if company_info.culture_signals else 'N/A'}
"""
        
        highlights = ', '.join(match_result.highlights) if match_result.highlights else 'Strong relevant experience'
        
        prompt = f"""You are an expert cover letter writer. Write a compelling cover letter for this job:

**Job Title:** {job.title}
**Company:** {job.company}
**Location:** {job.location}

**Job Description Highlights:**
{job.description[:1500] if job.description else 'Not available'}
{company_context}

**Candidate Background (from CV):**
{cv_content[:1500]}

**Match Highlights:**
{highlights}

**Instructions:**
1. Start with a compelling hook that shows you understand the company
2. Demonstrate genuine interest in THIS specific company
3. Highlight 2-3 specific achievements that match their needs
4. Show personality but stay professional
5. End with enthusiasm and a clear call to action
6. Keep it under 400 words

Write the cover letter:"""

        try:
            response = await self.client.chat(
                messages=[{"role": "user", "content": prompt}],
                temperature=0.7,
                max_tokens=1000
            )
            
            return response.content
        except Exception as e:
            self.logger.error(f"LLM cover letter generation failed: {e}")
            return self._generate_fallback_cover_letter(job, match_result, company_info)
    
    def _generate_fallback_cover_letter(
        self,
        job: JobListing,
        match_result: MatchResult,
        company_info: Optional[CompanyInfo]
    ) -> str:
        """Generate fallback cover letter when OpenAI is unavailable."""
        company_desc = company_info.description if company_info else "your innovative company"
        
        return f"""# Cover Letter

**Position:** {job.title}  
**Company:** {job.company}  
**Location:** {job.location}

---

Dear Hiring Manager,

I am writing to express my strong interest in the {job.title} position at {job.company}.

{company_desc}

Based on my background and experience, I believe I would be an excellent fit for this role. My key qualifications include:

{chr(10).join('- ' + h.replace('Matches: ', '') for h in match_result.highlights) if match_result.highlights else '- Relevant experience in the field'}

I am excited about the opportunity to contribute to {job.company}'s continued success and would welcome the chance to discuss how my skills and experience align with your needs.

Thank you for considering my application. I look forward to hearing from you.

Best regards,
[Your Name]

---

*Note: This is a template. Please personalize before submitting.*
"""
    
    def _format_company_research(self, info: CompanyInfo) -> str:
        """Format company research as Markdown."""
        culture = chr(10).join('- ' + s for s in info.culture_signals) if info.culture_signals else 'No data available'
        growth = chr(10).join('- ' + s for s in info.growth_signals) if info.growth_signals else 'No data available'
        news = chr(10).join('- ' + n.get('title', '') for n in info.recent_news[:5]) if info.recent_news else 'No recent news'
        people = chr(10).join('- ' + p.get('name', '') + ' (' + p.get('title', '') + ')' for p in info.key_people[:5]) if info.key_people else 'No data available'
        
        return f"""# Company Research: {info.name}

## Overview
{info.description or 'No description available'}

## Basic Info
- **Employees:** {info.employees or 'Unknown'}
- **Funding:** {info.funding or 'Unknown'}
- **Industry:** {info.industry or 'Unknown'}
- **Glassdoor Rating:** {info.glassdoor_rating or 'N/A'}

## Culture Signals
{culture}

## Growth Signals
{growth}

## Recent News
{news}

## Key People
{people}
"""
    
    def _generate_readme(self, job: JobListing, match: MatchResult) -> str:
        """Generate README for application folder."""
        skill_gaps = chr(10).join('- ' + g for g in match.skill_gaps) if match.skill_gaps else '- None identified'
        discovered_date = job.discovered_at.strftime('%B %d, %Y') if job.discovered_at else 'Unknown'
        source_value = job.source if isinstance(job.source, str) else job.source.value
        
        return f"""# Application: {job.company} — {job.title}

## Match Score: {match.overall_score}%

## Quick Stats
- **Discovered:** {discovered_date}
- **Location:** {job.location}
- **Source:** {source_value}

## Files Included
- ✅ Tailored Resume (`resume_tailored.md`)
- ✅ Cover Letter (`cover_letter.md`)
- ✅ Company Research (`company_research.md`)
- ✅ Job Description (`job_description.txt`)
- ✅ Match Analysis (`match_analysis.json`)

## To Apply
1. Review and edit the resume if needed
2. Review and personalize the cover letter
3. Go to: {job.url}
4. Upload materials and submit
5. Update status in ArmLenQuant dashboard

## Recommendation
{match.recommendation}

## Skill Gaps to Address
{skill_gaps}
"""

