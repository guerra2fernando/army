"""
Job Parser
Parses job listing pages to extract details.
"""
import re
from typing import Dict, Optional, List

try:
    from bs4 import BeautifulSoup
    BS4_AVAILABLE = True
except ImportError:
    BS4_AVAILABLE = False
    BeautifulSoup = None

try:
    from playwright.async_api import Browser, Page
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False
    Browser = None
    Page = None

from loguru import logger

from .models import JobListing, JobSource


class JobParser:
    """
    Parses job listing pages from various ATS platforms.
    """
    
    def __init__(self, browser: Optional[Browser]):
        self.browser = browser
        self.logger = logger.bind(component="parser")
    
    async def parse_job(self, job: JobListing) -> JobListing:
        """
        Parse a job listing page to extract details.
        
        Args:
            job: Job listing with URL
            
        Returns:
            Updated job listing with parsed details
        """
        if not self.browser or not BS4_AVAILABLE:
            self.logger.warning("Browser or BeautifulSoup not available")
            return job
            
        page = await self.browser.new_page()
        
        try:
            await page.goto(job.url, timeout=30000)
            await page.wait_for_load_state("domcontentloaded")
            
            html = await page.content()
            soup = BeautifulSoup(html, "html.parser")
            
            # Parse based on source
            if job.source == JobSource.LEVER or job.source == "lever":
                job = self._parse_lever(job, soup)
            elif job.source == JobSource.GREENHOUSE or job.source == "greenhouse":
                job = self._parse_greenhouse(job, soup)
            elif job.source == JobSource.ASHBY or job.source == "ashby":
                job = self._parse_ashby(job, soup)
            elif job.source == JobSource.WORKABLE or job.source == "workable":
                job = self._parse_workable(job, soup)
            
            self.logger.debug(f"Parsed job: {job.company} - {job.title}")
            
        except Exception as e:
            self.logger.error(f"Error parsing {job.url}: {e}")
        finally:
            await page.close()
        
        return job
    
    def _parse_lever(self, job: JobListing, soup) -> JobListing:
        """Parse Lever job listing."""
        # Company name
        company_elem = soup.select_one("a.main-header-logo, div.company-name, .posting-headline h1")
        if company_elem:
            job.company = company_elem.get_text(strip=True)
        
        # Job title
        title_elem = soup.select_one("h2.posting-headline, h1, .posting-title")
        if title_elem:
            job.title = title_elem.get_text(strip=True)
        
        # Location
        location_elem = soup.select_one("div.location, span.location, .posting-categories .location")
        if location_elem:
            job.location = location_elem.get_text(strip=True)
        
        # Description
        desc_elem = soup.select_one("div.section-wrapper, div.content, .posting-description")
        if desc_elem:
            job.description = desc_elem.get_text(separator="\n", strip=True)
        
        # Extract requirements
        job.requirements = self._extract_requirements(job.description)
        
        return job
    
    def _parse_greenhouse(self, job: JobListing, soup) -> JobListing:
        """Parse Greenhouse job listing."""
        # Company - often in title or header
        title_elem = soup.select_one("h1.app-title, h1")
        if title_elem:
            job.title = title_elem.get_text(strip=True)
        
        # Location
        location_elem = soup.select_one("div.location, span.location, .location")
        if location_elem:
            job.location = location_elem.get_text(strip=True)
        
        # Description
        desc_elem = soup.select_one("#content, div.content, .job-description")
        if desc_elem:
            job.description = desc_elem.get_text(separator="\n", strip=True)
        
        # Extract company from URL
        match = re.search(r"boards\.(?:eu\.)?greenhouse\.io/([^/]+)", job.url)
        if match:
            job.company = match.group(1).replace("-", " ").title()
        
        job.requirements = self._extract_requirements(job.description)
        
        return job
    
    def _parse_ashby(self, job: JobListing, soup) -> JobListing:
        """Parse Ashby job listing."""
        # Title
        title_elem = soup.select_one("h1")
        if title_elem:
            job.title = title_elem.get_text(strip=True)
        
        # Company
        company_elem = soup.select_one("a[href='/'] img, .company-name")
        if company_elem:
            job.company = company_elem.get("alt", "").strip() or company_elem.get_text(strip=True)
        
        # Description
        desc_elem = soup.select_one("div[class*='description'], main, .job-description")
        if desc_elem:
            job.description = desc_elem.get_text(separator="\n", strip=True)
        
        job.requirements = self._extract_requirements(job.description)
        
        return job
    
    def _parse_workable(self, job: JobListing, soup) -> JobListing:
        """Parse Workable job listing."""
        # Title
        title_elem = soup.select_one("h1")
        if title_elem:
            job.title = title_elem.get_text(strip=True)
        
        # Company
        company_elem = soup.select_one("h2, .company-name")
        if company_elem:
            job.company = company_elem.get_text(strip=True)
        
        # Description
        desc_elem = soup.select_one("section[data-ui='job-description'], .job-description")
        if desc_elem:
            job.description = desc_elem.get_text(separator="\n", strip=True)
        
        job.requirements = self._extract_requirements(job.description)
        
        return job
    
    def _extract_requirements(self, description: str) -> List[str]:
        """Extract requirements from job description."""
        if not description:
            return []
            
        requirements = []
        
        # Look for requirement patterns
        patterns = [
            r"(\d+\+?\s*years?.+?experience)",
            r"(proficient\s+(?:in|with).+?)(?:\.|$)",
            r"(strong\s+.+?skills)",
            r"(experience\s+(?:with|in).+?)(?:\.|$)",
            r"(bachelor'?s?\s+degree.+?)(?:\.|$)",
        ]
        
        desc_lower = description.lower()
        
        for pattern in patterns:
            matches = re.findall(pattern, desc_lower, re.IGNORECASE)
            requirements.extend(matches)
        
        # Deduplicate and clean
        seen = set()
        clean_reqs = []
        for req in requirements:
            req_clean = req.strip()[:200]  # Limit length
            if req_clean and req_clean not in seen:
                seen.add(req_clean)
                clean_reqs.append(req_clean)
        
        return clean_reqs[:10]  # Max 10 requirements

