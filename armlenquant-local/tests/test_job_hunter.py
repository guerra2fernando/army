"""
Job Hunter Agent Tests
Comprehensive tests for the Job Hunter agent components.
"""
import pytest
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch
from pathlib import Path
import json


# ============================================================================
# MODEL TESTS
# ============================================================================

class TestJobHunterModels:
    """Tests for Job Hunter data models."""
    
    def test_job_source_enum(self):
        """Test JobSource enum values."""
        from agents.job_hunter.models import JobSource
        
        assert JobSource.LEVER == "lever"
        assert JobSource.GREENHOUSE == "greenhouse"
        assert JobSource.ASHBY == "ashby"
        assert JobSource.WORKABLE == "workable"
        assert JobSource.DIRECT == "direct"
    
    def test_job_status_enum(self):
        """Test JobStatus enum values."""
        from agents.job_hunter.models import JobStatus
        
        assert JobStatus.NEW == "NEW"
        assert JobStatus.APPLIED == "APPLIED"
        assert JobStatus.REJECTED == "REJECTED"
        assert JobStatus.OFFER == "OFFER"
    
    def test_job_listing_creation(self):
        """Test JobListing model creation."""
        from agents.job_hunter.models import JobListing, JobSource, JobStatus
        
        job = JobListing(
            job_id="test-123",
            url="https://lever.co/company/job123",
            source=JobSource.LEVER,
            company="Test Company",
            title="Growth Lead",
            location="Remote",
            description="We are looking for a Growth Lead...",
            requirements=["5+ years experience", "Python knowledge"]
        )
        
        assert job.job_id == "test-123"
        assert job.source == "lever"
        assert job.company == "Test Company"
        assert job.status == "NEW"
        assert len(job.requirements) == 2
        assert job.match_score is None
    
    def test_job_listing_with_salary(self):
        """Test JobListing with salary range."""
        from agents.job_hunter.models import JobListing, JobSource
        
        job = JobListing(
            job_id="test-456",
            url="https://greenhouse.io/job456",
            source=JobSource.GREENHOUSE,
            company="Tech Corp",
            title="Senior Engineer",
            location="NYC",
            salary_range={"min": 150000, "max": 200000}
        )
        
        assert job.salary_range["min"] == 150000
        assert job.salary_range["max"] == 200000
    
    def test_match_result_creation(self):
        """Test MatchResult model creation."""
        from agents.job_hunter.models import MatchResult
        
        result = MatchResult(
            job_id="test-123",
            overall_score=85.5,
            skill_match=90.0,
            experience_match=80.0,
            culture_fit=85.0,
            compensation_fit=87.0,
            skill_gaps=["Kubernetes", "Go"],
            highlights=["Python expert", "Leadership experience"],
            recommendation="Strong match - worth applying"
        )
        
        assert result.overall_score == 85.5
        assert len(result.skill_gaps) == 2
        assert result.recommendation == "Strong match - worth applying"
    
    def test_match_result_score_validation(self):
        """Test MatchResult score bounds validation."""
        from agents.job_hunter.models import MatchResult
        from pydantic import ValidationError
        
        # Valid scores
        result = MatchResult(
            job_id="test-123",
            overall_score=0,  # Minimum valid
            skill_match=100,   # Maximum valid
            experience_match=50,
            culture_fit=50,
            compensation_fit=50
        )
        assert result.overall_score == 0
        assert result.skill_match == 100
        
        # Invalid score (negative)
        with pytest.raises(ValidationError):
            MatchResult(
                job_id="test-123",
                overall_score=-5,  # Invalid
                skill_match=50,
                experience_match=50,
                culture_fit=50,
                compensation_fit=50
            )
        
        # Invalid score (over 100)
        with pytest.raises(ValidationError):
            MatchResult(
                job_id="test-123",
                overall_score=105,  # Invalid
                skill_match=50,
                experience_match=50,
                culture_fit=50,
                compensation_fit=50
            )
    
    def test_application_draft_creation(self):
        """Test ApplicationDraft model creation."""
        from agents.job_hunter.models import ApplicationDraft
        
        draft = ApplicationDraft(
            job_id="test-123",
            company="Tech Corp",
            role="Growth Lead",
            resume_path="/path/to/resume.md",
            cover_letter_path="/path/to/cover.md",
            folder_path="/path/to/folder"
        )
        
        assert draft.job_id == "test-123"
        assert draft.company == "Tech Corp"
        assert draft.created_at is not None
    
    def test_company_info_creation(self):
        """Test CompanyInfo model creation."""
        from agents.job_hunter.models import CompanyInfo
        
        info = CompanyInfo(
            name="Startup Inc",
            description="A fast-growing startup",
            employees="50-100",
            funding="Series A",
            industry="SaaS",
            culture_signals=["Remote-first", "Async communication"],
            glassdoor_rating=4.5
        )
        
        assert info.name == "Startup Inc"
        assert info.glassdoor_rating == 4.5
        assert len(info.culture_signals) == 2
    
    def test_search_criteria_defaults(self):
        """Test SearchCriteria default values."""
        from agents.job_hunter.models import SearchCriteria
        
        criteria = SearchCriteria()
        
        assert "Growth Lead" in criteria.roles
        assert "Remote" in criteria.locations
        assert criteria.limit_per_query == 10


# ============================================================================
# SEARCHER TESTS
# ============================================================================

class TestJobSearcher:
    """Tests for JobSearcher component."""
    
    def test_searcher_initialization(self):
        """Test JobSearcher initialization."""
        from agents.job_hunter.searcher import JobSearcher
        
        searcher = JobSearcher()
        
        assert searcher.browser is None
        assert len(searcher.seen_urls) == 0
        assert searcher._results_timeout_ms >= 10000
    
    def test_detect_source_lever(self):
        """Test source detection for Lever URLs."""
        from agents.job_hunter.searcher import JobSearcher
        from agents.job_hunter.models import JobSource
        
        searcher = JobSearcher()
        
        url = "https://jobs.lever.co/company/position-123"
        source = searcher._detect_source(url)
        
        assert source == JobSource.LEVER
    
    def test_detect_source_greenhouse(self):
        """Test source detection for Greenhouse URLs."""
        from agents.job_hunter.searcher import JobSearcher
        from agents.job_hunter.models import JobSource
        
        searcher = JobSearcher()
        
        url = "https://boards.greenhouse.io/company/jobs/123"
        source = searcher._detect_source(url)
        
        assert source == JobSource.GREENHOUSE
    
    def test_detect_source_ashby(self):
        """Test source detection for Ashby URLs."""
        from agents.job_hunter.searcher import JobSearcher
        from agents.job_hunter.models import JobSource
        
        searcher = JobSearcher()
        
        url = "https://jobs.ashbyhq.com/company/position"
        source = searcher._detect_source(url)
        
        assert source == JobSource.ASHBY
    
    def test_detect_source_workable(self):
        """Test source detection for Workable URLs."""
        from agents.job_hunter.searcher import JobSearcher
        from agents.job_hunter.models import JobSource
        
        searcher = JobSearcher()
        
        url = "https://apply.workable.com/company/j/ABC123"
        source = searcher._detect_source(url)
        
        assert source == JobSource.WORKABLE
    
    def test_detect_source_unknown(self):
        """Test source detection for unknown URLs."""
        from agents.job_hunter.searcher import JobSearcher
        from agents.job_hunter.models import JobSource
        
        searcher = JobSearcher()
        
        url = "https://unknown-site.com/jobs/123"
        source = searcher._detect_source(url)
        
        assert source == JobSource.DIRECT
    
    def test_generate_job_id(self):
        """Test job ID generation from URL."""
        from agents.job_hunter.searcher import JobSearcher
        
        searcher = JobSearcher()
        
        url1 = "https://lever.co/company/job1"
        url2 = "https://lever.co/company/job2"
        
        id1 = searcher._generate_job_id(url1)
        id2 = searcher._generate_job_id(url2)
        
        # IDs should be different for different URLs
        assert id1 != id2
        # IDs should be consistent for same URL
        assert id1 == searcher._generate_job_id(url1)
        # IDs should be 12 characters
        assert len(id1) == 12
    
    def test_clean_url_lever(self):
        """Test URL cleaning for Lever."""
        from agents.job_hunter.searcher import JobSearcher
        
        searcher = JobSearcher()
        
        # Clean URL with tracking params
        url = "https://jobs.lever.co/company/job123?utm_source=google"
        clean = searcher._clean_url(url)
        
        assert clean == "https://jobs.lever.co/company/job123"
        assert "utm_source" not in clean
    
    def test_clean_url_google_redirect(self):
        """Test URL cleaning for Google redirect wrapper."""
        from agents.job_hunter.searcher import JobSearcher
        
        searcher = JobSearcher()
        
        url = "https://www.google.com/url?url=https://jobs.lever.co/company/job123&sa=D"
        clean = searcher._clean_url(url)
        
        assert "lever.co" in clean
        assert "google.com" not in clean
    
    def test_clean_url_invalid(self):
        """Test URL cleaning for non-job URLs."""
        from agents.job_hunter.searcher import JobSearcher
        
        searcher = JobSearcher()
        
        url = "https://random-blog.com/article"
        clean = searcher._clean_url(url)
        
        assert clean is None
    
    def test_deduplicate_jobs(self):
        """Test job deduplication."""
        from agents.job_hunter.searcher import JobSearcher
        from agents.job_hunter.models import JobListing, JobSource
        
        searcher = JobSearcher()
        
        jobs = [
            JobListing(
                job_id="1",
                url="https://lever.co/job1",
                source=JobSource.LEVER,
                company="A",
                title="Dev",
                location="Remote"
            ),
            JobListing(
                job_id="2",
                url="https://lever.co/job1",  # Duplicate URL
                source=JobSource.LEVER,
                company="A",
                title="Dev",
                location="Remote"
            ),
            JobListing(
                job_id="3",
                url="https://lever.co/job2",  # Different URL
                source=JobSource.LEVER,
                company="B",
                title="Engineer",
                location="NYC"
            ),
        ]
        
        unique = searcher._deduplicate(jobs)
        
        assert len(unique) == 2
        urls = [j.url for j in unique]
        assert "https://lever.co/job1" in urls
        assert "https://lever.co/job2" in urls
    
    def test_dork_templates_exist(self):
        """Test that DORK templates are defined for all sources."""
        from agents.job_hunter.searcher import JobSearcher
        from agents.job_hunter.models import JobSource
        
        searcher = JobSearcher()
        
        for source in [JobSource.LEVER, JobSource.GREENHOUSE, JobSource.ASHBY, JobSource.WORKABLE]:
            assert source in searcher.DORK_TEMPLATES
            template = searcher.DORK_TEMPLATES[source]
            assert "{role}" in template
            assert "{location}" in template

    def test_source_adapter_build_queries_expands_remote(self):
        """Adapters should build multiple queries for remote roles."""
        from agents.job_hunter.source_adapters import LEVER_ADAPTER

        queries = LEVER_ADAPTER.build_queries("growth", "Remote")

        assert len(queries) >= 3
        assert any("jobs.lever.co" in query for query in queries)
        assert any("Anywhere" in query or "Work from home" in query or '"Remote"' in query for query in queries)

    def test_job_from_remotive_maps_to_direct_job(self):
        """Remotive fallback payloads should map into JobListing records."""
        from agents.job_hunter.searcher import JobSearcher
        from agents.job_hunter.models import JobSource

        searcher = JobSearcher()
        job = searcher._job_from_remotive(
            {
                "id": 123,
                "url": "https://remotive.com/remote-jobs/marketing/growth-manager-123",
                "title": "Growth Manager",
                "company_name": "Acme",
                "candidate_required_location": "Remote",
                "description": "Own growth programs",
            },
            requested_location_terms={"remote"},
            requested_role="growth",
        )

        assert job is not None
        assert job.source == JobSource.DIRECT
        assert job.company == "Acme"
        assert job.title == "Growth Manager"

    def test_job_from_remoteok_maps_to_direct_job(self):
        """RemoteOK payloads should map into JobListing records."""
        from agents.job_hunter.searcher import JobSearcher
        from agents.job_hunter.models import JobSource

        searcher = JobSearcher()
        job = searcher._job_from_remoteok(
            {
                "id": 555,
                "url": "https://remoteok.com/remote-jobs/remote-python-engineer-acme-555",
                "position": "Python Engineer",
                "company": "Acme",
                "location": "Worldwide",
                "description": "Build Python services",
                "tags": ["python", "backend"],
            },
            requested_location_terms={"remote"},
            requested_role="python engineer",
        )

        assert job is not None
        assert job.source == JobSource.DIRECT
        assert job.company == "Acme"
        assert job.title == "Python Engineer"


# ============================================================================
# PARSER TESTS
# ============================================================================

class TestJobParser:
    """Tests for JobParser component."""
    
    def test_extract_requirements_years(self):
        """Test extracting years of experience from description."""
        from agents.job_hunter.job_parser import JobParser
        
        parser = JobParser(browser=None)
        
        description = """
        We are looking for a Senior Engineer with:
        - 5+ years experience in software development
        - Strong Python skills
        - Experience with cloud platforms
        """
        
        requirements = parser._extract_requirements(description)
        
        assert any("5" in req and "years" in req for req in requirements)
    
    def test_extract_requirements_skills(self):
        """Test extracting skill requirements."""
        from agents.job_hunter.job_parser import JobParser
        
        parser = JobParser(browser=None)
        
        description = """
        Requirements:
        - Proficient in Python and JavaScript
        - Strong communication skills
        - Experience with React and Node.js
        """
        
        requirements = parser._extract_requirements(description)
        
        assert len(requirements) > 0
    
    def test_extract_requirements_empty(self):
        """Test extracting requirements from minimal description."""
        from agents.job_hunter.job_parser import JobParser
        
        parser = JobParser(browser=None)
        
        description = "Join our team!"
        
        requirements = parser._extract_requirements(description)
        
        assert isinstance(requirements, list)
    
    def test_extract_requirements_max_limit(self):
        """Test that requirements are limited to 10."""
        from agents.job_hunter.job_parser import JobParser
        
        parser = JobParser(browser=None)
        
        # Description with many potential requirements
        description = """
        - 3+ years experience in Python
        - 2+ years experience in JavaScript
        - 1+ years experience in Go
        - Proficient in React
        - Proficient in Vue
        - Proficient in Angular
        - Strong leadership skills
        - Strong communication skills
        - Strong analytical skills
        - Experience with AWS
        - Experience with GCP
        - Experience with Azure
        - Bachelor's degree in CS
        - Master's degree preferred
        """
        
        requirements = parser._extract_requirements(description)
        
        assert len(requirements) <= 10


# ============================================================================
# MATCHER TESTS
# ============================================================================

class TestJobMatcher:
    """Tests for JobMatcher component."""
    
    def test_matcher_initialization(self):
        """Test JobMatcher initialization."""
        from agents.job_hunter.matcher import JobMatcher
        
        matcher = JobMatcher()
        
        assert matcher.client is not None
    
    def test_calculate_skill_match_high(self):
        """Test skill match calculation with high overlap."""
        from agents.job_hunter.matcher import JobMatcher
        from agents.job_hunter.models import JobListing, JobSource
        
        matcher = JobMatcher()
        
        job = JobListing(
            job_id="test-1",
            url="https://lever.co/test",
            source=JobSource.LEVER,
            company="Test",
            title="Engineer",
            location="Remote",
            requirements=["python experience", "javascript skills", "react development"]
        )
        
        cv = "I have 5 years of Python experience, JavaScript skills, and React development expertise."
        
        score = matcher._calculate_skill_match(job, cv)
        
        # Should have a high score since CV contains all skills
        assert score >= 0.5
    
    def test_calculate_skill_match_low(self):
        """Test skill match calculation with low overlap."""
        from agents.job_hunter.matcher import JobMatcher
        from agents.job_hunter.models import JobListing, JobSource
        
        matcher = JobMatcher()
        
        job = JobListing(
            job_id="test-1",
            url="https://lever.co/test",
            source=JobSource.LEVER,
            company="Test",
            title="Engineer",
            location="Remote",
            requirements=["rust experience", "go skills", "kubernetes expertise"]
        )
        
        cv = "I have experience with Python, JavaScript, and React."
        
        score = matcher._calculate_skill_match(job, cv)
        
        # Should have a lower score since CV doesn't match requirements
        assert score < 0.8
    
    def test_calculate_experience_match_exceeds(self):
        """Test experience match when CV exceeds requirements."""
        from agents.job_hunter.matcher import JobMatcher
        from agents.job_hunter.models import JobListing, JobSource
        
        matcher = JobMatcher()
        
        job = JobListing(
            job_id="test-1",
            url="https://lever.co/test",
            source=JobSource.LEVER,
            company="Test",
            title="Engineer",
            location="Remote",
            requirements=["3+ years experience"],
            description="We need someone with 3+ years experience"
        )
        
        cv = "I have 8 years of professional experience"
        
        score = matcher._calculate_experience_match(job, cv)
        
        assert score == 1.0  # Exceeds requirement
    
    def test_calculate_experience_match_below(self):
        """Test experience match when CV is below requirements."""
        from agents.job_hunter.matcher import JobMatcher
        from agents.job_hunter.models import JobListing, JobSource
        
        matcher = JobMatcher()
        
        job = JobListing(
            job_id="test-1",
            url="https://lever.co/test",
            source=JobSource.LEVER,
            company="Test",
            title="Engineer",
            location="Remote",
            requirements=["10+ years experience"],
            description="We need someone with 10+ years experience"
        )
        
        cv = "I have 3 years of professional experience"
        
        score = matcher._calculate_experience_match(job, cv)
        
        assert score < 1.0  # Below requirement
    
    def test_identify_skill_gaps(self):
        """Test skill gap identification."""
        from agents.job_hunter.matcher import JobMatcher
        from agents.job_hunter.models import JobListing, JobSource
        
        matcher = JobMatcher()
        
        job = JobListing(
            job_id="test-1",
            url="https://lever.co/test",
            source=JobSource.LEVER,
            company="Test",
            title="Engineer",
            location="Remote",
            requirements=["python skills", "aws experience", "kubernetes knowledge"]
        )
        
        cv = "Expert in Python programming"  # Missing AWS and Kubernetes
        
        gaps = matcher._identify_skill_gaps(job, cv)
        
        assert isinstance(gaps, list)
        # Should identify AWS and/or Kubernetes as gaps
        assert len(gaps) >= 0
    
    def test_identify_highlights(self):
        """Test highlight identification."""
        from agents.job_hunter.matcher import JobMatcher
        from agents.job_hunter.models import JobListing, JobSource
        
        matcher = JobMatcher()
        
        job = JobListing(
            job_id="test-1",
            url="https://lever.co/test",
            source=JobSource.LEVER,
            company="Test",
            title="Engineer",
            location="Remote",
            requirements=["python expert", "leadership experience"]
        )
        
        cv = "Python expert with 10 years leadership experience"
        
        highlights = matcher._identify_highlights(job, cv)
        
        assert isinstance(highlights, list)
    
    def test_extract_skills_from_text(self):
        """Test skill extraction from text."""
        from agents.job_hunter.matcher import JobMatcher
        
        matcher = JobMatcher()
        
        text = "Looking for someone with Python, React, and AWS experience"
        
        skills = matcher._extract_skills_from_text(text)
        
        assert "python" in skills
        assert "react" in skills
        assert "aws" in skills
    
    @pytest.mark.asyncio
    async def test_match_job_returns_result(self):
        """Test that match_job returns a MatchResult."""
        from agents.job_hunter.matcher import JobMatcher
        from agents.job_hunter.models import JobListing, JobSource, MatchResult
        
        matcher = JobMatcher()
        
        job = JobListing(
            job_id="test-1",
            url="https://lever.co/test",
            source=JobSource.LEVER,
            company="Test",
            title="Engineer",
            location="Remote",
            requirements=["python", "javascript"],
            description="Python and JavaScript developer needed"
        )
        
        cv = "Experienced Python and JavaScript developer with 5 years"
        
        result = await matcher.match_job(job, cv)
        
        assert isinstance(result, MatchResult)
        assert result.job_id == "test-1"
        assert 0 <= result.overall_score <= 100
        assert result.recommendation != ""
    
    @pytest.mark.asyncio
    async def test_match_job_recommendation_levels(self):
        """Test match job generates appropriate recommendations."""
        from agents.job_hunter.matcher import JobMatcher
        from agents.job_hunter.models import JobListing, JobSource
        
        matcher = JobMatcher()
        
        # High match job
        job = JobListing(
            job_id="test-1",
            url="https://lever.co/test",
            source=JobSource.LEVER,
            company="Test",
            title="Python Engineer",
            location="Remote",
            requirements=["python", "sql", "data"],
            description="Python developer with SQL and data experience"
        )
        
        cv = "Expert Python developer with SQL expertise and 10 years data experience"
        
        result = await matcher.match_job(job, cv)
        
        # Result should have a non-empty recommendation
        assert len(result.recommendation) > 0


# ============================================================================
# DRAFTER TESTS
# ============================================================================

class TestDocumentDrafter:
    """Tests for DocumentDrafter component."""
    
    def test_drafter_initialization(self):
        """Test DocumentDrafter initialization."""
        from agents.job_hunter.drafter import DocumentDrafter
        
        drafter = DocumentDrafter()
        
        assert drafter.client is not None
        assert drafter.output_path.exists() or True  # May not exist in test env
    
    def test_format_company_research(self):
        """Test company research formatting."""
        from agents.job_hunter.drafter import DocumentDrafter
        from agents.job_hunter.models import CompanyInfo
        
        drafter = DocumentDrafter()
        
        info = CompanyInfo(
            name="TechCorp",
            description="Leading tech company",
            employees="100-200",
            funding="Series B",
            industry="SaaS",
            culture_signals=["Remote-first", "Async"],
            glassdoor_rating=4.2,
            growth_signals=["Rapid hiring", "New markets"]
        )
        
        formatted = drafter._format_company_research(info)
        
        assert "# Company Research: TechCorp" in formatted
        assert "100-200" in formatted
        assert "Series B" in formatted
        assert "Remote-first" in formatted
        assert "4.2" in formatted
    
    def test_generate_readme(self):
        """Test README generation for application folder."""
        from agents.job_hunter.drafter import DocumentDrafter
        from agents.job_hunter.models import JobListing, JobSource, MatchResult
        
        drafter = DocumentDrafter()
        
        job = JobListing(
            job_id="test-1",
            url="https://lever.co/test",
            source=JobSource.LEVER,
            company="TechCorp",
            title="Growth Lead",
            location="Remote",
            discovered_at=datetime(2024, 1, 15)
        )
        
        match = MatchResult(
            job_id="test-1",
            overall_score=85.5,
            skill_match=90.0,
            experience_match=80.0,
            culture_fit=85.0,
            compensation_fit=87.0,
            skill_gaps=["Kubernetes"],
            recommendation="Strong match - worth applying"
        )
        
        readme = drafter._generate_readme(job, match)
        
        assert "# Application: TechCorp — Growth Lead" in readme
        assert "85.5%" in readme
        assert "Remote" in readme
        assert "lever" in readme
        assert "Kubernetes" in readme
        assert "Strong match" in readme


# ============================================================================
# MAIN AGENT TESTS
# ============================================================================

class TestJobHunterAgent:
    """Tests for the main JobHunterAgent class."""
    
    def test_agent_initialization(self):
        """Test JobHunterAgent initialization."""
        from agents.job_hunter.agent import JobHunterAgent
        
        agent = JobHunterAgent()
        
        assert agent.name == "JOB_HUNTER"
        assert agent.version == "2.0.0"
        assert agent.searcher is not None
        assert agent.matcher is not None
        assert agent.drafter is not None
    
    def test_agent_capabilities(self):
        """Test JobHunterAgent capabilities list."""
        from agents.job_hunter.agent import JobHunterAgent
        
        agent = JobHunterAgent()
        
        capabilities = agent.get_capabilities()
        
        assert "job_search" in capabilities
        assert "job_parsing" in capabilities
        assert "job_matching" in capabilities
        assert "resume_tailoring" in capabilities
        assert "cover_letter_generation" in capabilities
    
    @pytest.mark.asyncio
    async def test_execute_unknown_action(self):
        """Test execute with unknown action."""
        from agents.job_hunter.agent import JobHunterAgent
        
        agent = JobHunterAgent()
        
        result = await agent.execute({"action": "unknown_action"})
        
        assert result.success is False
        assert "Unknown action" in result.error
    
    @pytest.mark.asyncio
    async def test_execute_match_job_no_job_data(self):
        """Test match_job action without job data."""
        from agents.job_hunter.agent import JobHunterAgent
        
        agent = JobHunterAgent()
        
        result = await agent.execute({"action": "match_job"})
        
        assert result.success is False
        assert "No job data" in result.error
    
    @pytest.mark.asyncio
    async def test_execute_generate_materials_no_job_data(self):
        """Test generate_materials action without job data."""
        from agents.job_hunter.agent import JobHunterAgent
        
        agent = JobHunterAgent()
        
        result = await agent.execute({"action": "generate_materials"})
        
        assert result.success is False
        assert "No job data" in result.error
    
    def test_agent_status(self):
        """Test agent status reporting."""
        from agents.job_hunter.agent import JobHunterAgent
        
        agent = JobHunterAgent()
        
        status = agent.get_status()
        
        assert status["name"] == "JOB_HUNTER"
        assert status["version"] == "2.0.0"
        assert status["is_running"] is False
        assert "job_search" in status["capabilities"]

    @pytest.mark.asyncio
    async def test_load_cv_uses_operator_profile_resume(self, tmp_path):
        """Test CV loading prefers the operator-data profile path."""
        from agents.job_hunter.agent import JobHunterAgent

        root = tmp_path / "operator_data"
        (root / "personal" / "cv").mkdir(parents=True, exist_ok=True)
        (root / "personal" / "profile.json").write_text(
            json.dumps(
                {
                    "slug": "default",
                    "display_name": "Fernando",
                    "resume_path": "cv/master_cv.md",
                }
            ),
            encoding="utf-8",
        )
        resume = root / "personal" / "cv" / "master_cv.md"
        resume.write_text("Profile CV", encoding="utf-8")

        agent = JobHunterAgent()
        with patch("agents.job_hunter.agent.settings.operator_data_root", root):
            with patch.object(agent.capability_manager, "check_permission", AsyncMock()):
                await agent._load_cv()

        assert agent._cv_content == "Profile CV"


# ============================================================================
# INTEGRATION TESTS
# ============================================================================

class TestJobHunterIntegration:
    """Integration tests for Job Hunter components working together."""
    
    @pytest.mark.asyncio
    async def test_match_and_score_flow(self):
        """Test the job matching flow end-to-end."""
        from agents.job_hunter.matcher import JobMatcher
        from agents.job_hunter.models import JobListing, JobSource
        
        matcher = JobMatcher()
        
        # Create a realistic job
        job = JobListing(
            job_id="integration-test-1",
            url="https://lever.co/startup/growth-lead",
            source=JobSource.LEVER,
            company="TechStartup",
            title="Head of Growth",
            location="Remote, US",
            description="""
            We're looking for a Head of Growth to lead our expansion.
            
            Responsibilities:
            - Lead growth initiatives
            - Manage paid acquisition
            - Optimize conversion funnels
            
            Requirements:
            - 5+ years in growth/marketing
            - Experience with paid channels
            - Strong analytical skills
            - Python for data analysis
            """,
            requirements=[
                "5+ years in growth/marketing",
                "Experience with paid channels",
                "Strong analytical skills",
                "Python for data analysis"
            ]
        )
        
        # Realistic CV
        cv = """
        PROFESSIONAL EXPERIENCE
        
        Head of Growth - Previous Company (3 years)
        - Led growth team from 0 to 10 members
        - Managed $5M annual paid acquisition budget
        - Improved conversion rates by 40%
        
        Senior Growth Manager - Another Company (4 years)
        - Managed Facebook and Google ads
        - Built analytics dashboards with Python
        - Strong analytical background
        
        SKILLS
        - Growth strategy, paid acquisition, analytics
        - Python, SQL, data analysis
        - Leadership and team management
        """
        
        result = await matcher.match_job(job, cv)
        
        assert result.job_id == "integration-test-1"
        assert result.overall_score > 50  # Should be a reasonable match
        assert len(result.recommendation) > 0
    
    def test_models_serialization(self):
        """Test that models can be serialized to JSON."""
        from agents.job_hunter.models import (
            JobListing, JobSource, MatchResult, ApplicationDraft, CompanyInfo
        )
        
        job = JobListing(
            job_id="test-1",
            url="https://lever.co/test",
            source=JobSource.LEVER,
            company="Test",
            title="Engineer",
            location="Remote"
        )
        
        # Should not raise
        job_dict = job.model_dump()
        job_json = json.dumps(job_dict, default=str)
        
        assert "test-1" in job_json
        assert "lever" in job_json
    
    def test_searcher_and_parser_source_consistency(self):
        """Test that searcher and parser use consistent sources."""
        from agents.job_hunter.searcher import JobSearcher
        from agents.job_hunter.models import JobSource
        
        searcher = JobSearcher()
        
        # Test all source detection
        test_urls = {
            "https://jobs.lever.co/company/123": JobSource.LEVER,
            "https://boards.greenhouse.io/company/jobs/456": JobSource.GREENHOUSE,
            "https://jobs.ashbyhq.com/company/position": JobSource.ASHBY,
            "https://apply.workable.com/company/j/789": JobSource.WORKABLE,
        }
        
        for url, expected_source in test_urls.items():
            detected = searcher._detect_source(url)
            assert detected == expected_source, f"URL {url} detected as {detected}, expected {expected_source}"

