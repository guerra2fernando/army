"""
Job Searcher
Uses Google Dorks to find job listings.
"""
import asyncio
import hashlib
from typing import List, Dict, Optional
from datetime import datetime
from urllib.parse import quote_plus
import httpx
from loguru import logger

try:
    from playwright.async_api import async_playwright, Browser, Page
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False
    Browser = None
    Page = None

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
from poller.config import get_settings
from .models import JobListing, JobSource
from .source_adapters import ADAPTERS

settings = get_settings()


class JobSearcher:
    """
    Searches for jobs using Google Dorks.
    """
    
    # Representative Google dork templates for each ATS platform
    DORK_TEMPLATES = {source: adapter.templates[0] for source, adapter in ADAPTERS.items()}
    SEARCH_PROVIDERS = [
        {
            "name": "bing",
            "url": "https://www.bing.com/search?q={query}&count={limit}",
            "selector": "#b_results",
        },
        {
            "name": "duckduckgo",
            "url": "https://html.duckduckgo.com/html/?q={query}",
            "selector": "body",
        },
        {
            "name": "google",
            "url": "https://www.google.com/search?q={query}&num={limit}",
            "selector": "div#search",
        },
    ]
    REMOTIVE_URL = "https://remotive.com/api/remote-jobs"
    REMOTEOK_API_URL = "https://remoteok.com/api"
    REMOTEOK_PYTHON_URL = "https://remoteok.com/remote-python-jobs.json"
    
    def __init__(self):
        self.logger = logger.bind(component="searcher")
        self.browser: Optional[Browser] = None
        self.seen_urls: set = set()
        self._playwright = None
        self._results_timeout_ms = max(10000, int(settings.browser_timeout))
    
    async def initialize(self):
        """Initialize browser."""
        if not PLAYWRIGHT_AVAILABLE:
            self.logger.warning("Playwright not available, browser features disabled")
            return
            
        self._playwright = await async_playwright().start()
        self.browser = await self._playwright.chromium.launch(
            headless=settings.headless_mode
        )
        self.logger.info("Browser initialized")
    
    async def close(self):
        """Close browser."""
        if self.browser:
            await self.browser.close()
            self.browser = None
        if self._playwright:
            await self._playwright.stop()
            self._playwright = None
    
    async def search_jobs(
        self,
        roles: List[str],
        locations: List[str],
        sources: Optional[List[JobSource]] = None,
        limit_per_query: int = 10
    ) -> List[JobListing]:
        """
        Search for jobs across multiple sources.
        
        Args:
            roles: Job titles to search for
            locations: Locations to search
            sources: ATS platforms to search
            limit_per_query: Max results per search query
            
        Returns:
            List of discovered job listings
        """
        sources = sources or [JobSource.LEVER, JobSource.GREENHOUSE, JobSource.ASHBY, JobSource.WORKABLE]
        all_jobs: List[JobListing] = []

        # Prefer direct job sources first; they are much more reliable than search-engine scraping.
        fallback_jobs = await self._search_remoteok_jobs(
            roles=roles,
            locations=locations,
            limit_per_query=limit_per_query,
        )
        all_jobs.extend(fallback_jobs)

        fallback_jobs = await self._search_remotive_jobs(
            roles=roles,
            locations=locations,
            limit_per_query=limit_per_query,
        )
        all_jobs.extend(fallback_jobs)

        # If we already have any jobs, return immediately and avoid brittle search-engine automation.
        if all_jobs:
            unique_jobs = self._deduplicate(all_jobs)
            self.logger.info(f"Found {len(unique_jobs)} unique jobs")
            return unique_jobs

        if not self.browser:
            await self.initialize()
        
        if not self.browser:
            unique_jobs = self._deduplicate(all_jobs)
            if unique_jobs:
                self.logger.info(f"Found {len(unique_jobs)} unique jobs")
                return unique_jobs
            self.logger.error("Browser not available for searching")
            return []
        
        for role in roles:
            for location in locations:
                for source in sources:
                    try:
                        jobs = await self._search_single(
                            role, location, source, limit_per_query
                        )
                        all_jobs.extend(jobs)
                        
                        # Rate limiting
                        await asyncio.sleep(2)
                        
                    except Exception as e:
                        self.logger.error(f"Search failed for {role}/{location}/{source}: {e}")
        
        # Deduplicate
        unique_jobs = self._deduplicate(all_jobs)
        
        self.logger.info(f"Found {len(unique_jobs)} unique jobs")
        return unique_jobs
    
    async def _search_single(
        self,
        role: str,
        location: str,
        source: JobSource,
        limit: int
    ) -> List[JobListing]:
        """Execute a single search query."""
        
        adapter = ADAPTERS.get(source)
        if not adapter:
            return []
        if not self.browser:
            return []

        collected_urls: List[str] = []

        for query in adapter.build_queries(role=role, location=location):
            self.logger.debug(f"Searching: {query}")
            links = await self._search_query_links(query=query, limit=limit)

            for link in links:
                clean_url = self._clean_url(link)
                if clean_url and clean_url not in self.seen_urls and clean_url not in collected_urls:
                    collected_urls.append(clean_url)

            if len(collected_urls) >= limit:
                break

        self.seen_urls.update(collected_urls)

        jobs = []
        for url in collected_urls[:limit]:
            job = JobListing(
                job_id=self._generate_job_id(url),
                url=url,
                source=self._detect_source(url),
                company="",
                title=role,
                location=location,
                description="",
                discovered_at=datetime.utcnow()
            )
            jobs.append(job)

        return jobs

    async def _search_query_links(self, query: str, limit: int) -> List[str]:
        """Try multiple search engines for the same query."""
        if not self.browser:
            return []

        encoded_query = quote_plus(query)

        for provider in self.SEARCH_PROVIDERS:
            page = await self.browser.new_page()
            try:
                search_url = provider["url"].format(query=encoded_query, limit=limit)
                await page.goto(search_url, timeout=settings.browser_timeout)
                await page.wait_for_load_state("domcontentloaded", timeout=self._results_timeout_ms)
                await page.wait_for_selector(provider["selector"], timeout=self._results_timeout_ms)

                links = await page.evaluate("""
                    () => Array.from(document.querySelectorAll('a[href]')).map(a => a.href)
                """)
                filtered = [
                    href for href in links
                    if isinstance(href, str) and (
                        'lever.co' in href or
                        'greenhouse.io' in href or
                        'ashbyhq.com' in href or
                        'workable.com' in href
                    )
                ]

                if filtered:
                    self.logger.debug(
                        f"Provider {provider['name']} returned {len(filtered)} raw links for query: {query}"
                    )
                    return filtered

            except Exception as e:
                self.logger.warning(
                    f"Provider {provider['name']} failed for query '{query}': {e}"
                )
            finally:
                await page.close()

        return []

    async def _search_remotive_jobs(
        self,
        roles: List[str],
        locations: List[str],
        limit_per_query: int,
    ) -> List[JobListing]:
        """Fallback to a stable remote jobs API when ATS discovery yields nothing."""
        jobs: List[JobListing] = []
        location_terms = {location.lower() for location in locations}

        async with httpx.AsyncClient(timeout=20.0) as client:
            for role in roles:
                try:
                    response = await client.get(
                        self.REMOTIVE_URL,
                        params={"search": role},
                    )
                    response.raise_for_status()
                    payload = response.json()
                    for item in payload.get("jobs", [])[: max(limit_per_query * 3, 20)]:
                        job = self._job_from_remotive(
                            item,
                            requested_location_terms=location_terms,
                            requested_role=role,
                        )
                        if not job:
                            continue
                        if job.url in self.seen_urls:
                            continue
                        self.seen_urls.add(job.url)
                        jobs.append(job)
                        if len(jobs) >= limit_per_query * max(1, len(roles)):
                            break
                except Exception as e:
                    self.logger.warning(f"Remotive fallback failed for role '{role}': {e}")

        if jobs:
            self.logger.info(f"Remotive fallback returned {len(jobs)} jobs")

        return jobs

    async def _search_remoteok_jobs(
        self,
        roles: List[str],
        locations: List[str],
        limit_per_query: int,
    ) -> List[JobListing]:
        """Use RemoteOK JSON feeds as the primary stable remote job source."""
        jobs: List[JobListing] = []
        location_terms = {location.lower() for location in locations}

        async with httpx.AsyncClient(
            timeout=20.0,
            headers={"User-Agent": "Mozilla/5.0"},
        ) as client:
            for role in roles:
                try:
                    role_lower = role.lower()
                    url = self.REMOTEOK_PYTHON_URL if "python" in role_lower else self.REMOTEOK_API_URL
                    response = await client.get(url)
                    response.raise_for_status()
                    payload = response.json()
                    items = [item for item in payload if isinstance(item, dict) and item.get("position")]

                    for item in items:
                        job = self._job_from_remoteok(
                            item,
                            requested_location_terms=location_terms,
                            requested_role=role,
                        )
                        if not job or job.url in self.seen_urls:
                            continue
                        self.seen_urls.add(job.url)
                        jobs.append(job)
                        if len(jobs) >= limit_per_query * max(1, len(roles)):
                            break
                except Exception as e:
                    self.logger.warning(f"RemoteOK fallback failed for role '{role}': {e}")

        if jobs:
            self.logger.info(f"RemoteOK fallback returned {len(jobs)} jobs")

        return jobs

    def _job_from_remotive(
        self,
        item: dict,
        requested_location_terms: set,
        requested_role: str,
    ) -> Optional[JobListing]:
        """Convert a Remotive API job payload into our internal model."""
        url = item.get("url")
        title = item.get("title")
        company = item.get("company_name", "")
        location = item.get("candidate_required_location") or "Remote"
        description = item.get("description", "")

        if not url or not title:
            return None

        location_lower = str(location).lower()
        if requested_location_terms and "remote" not in requested_location_terms:
            if not any(term in location_lower for term in requested_location_terms):
                return None

        haystack = f"{title} {description}".lower()
        role_tokens = [token for token in requested_role.lower().split() if len(token) >= 4]
        if role_tokens and not any(token in haystack for token in role_tokens):
            return None

        return JobListing(
            job_id=str(item.get("id") or self._generate_job_id(url)),
            url=url,
            source=JobSource.DIRECT,
            company=company,
            title=title,
            location=location,
            description=description,
            discovered_at=datetime.utcnow(),
        )

    def _job_from_remoteok(
        self,
        item: dict,
        requested_location_terms: set,
        requested_role: str,
    ) -> Optional[JobListing]:
        """Convert a RemoteOK payload into our internal model."""
        url = item.get("url")
        title = item.get("position")
        company = item.get("company", "")
        location = item.get("location") or "Remote"
        description = item.get("description", "") or ""
        tags = item.get("tags") or []

        if not url or not title:
            return None

        location_lower = str(location).lower()
        if requested_location_terms and "remote" not in requested_location_terms:
            if not any(term in location_lower for term in requested_location_terms):
                return None

        haystack = f"{title} {description} {' '.join(tags)}".lower()
        role_tokens = [token for token in requested_role.lower().split() if len(token) >= 4]
        if role_tokens and not any(token in haystack for token in role_tokens):
            return None

        return JobListing(
            job_id=str(item.get("id") or self._generate_job_id(url)),
            url=url,
            source=JobSource.DIRECT,
            company=company,
            title=title,
            location=location,
            description=description,
            discovered_at=datetime.utcnow(),
        )
    
    def _clean_url(self, url: str) -> Optional[str]:
        """Clean and validate a job URL."""
        for adapter in ADAPTERS.values():
            clean_url = adapter.normalize_url(url)
            if clean_url:
                return clean_url
        return None
    
    def _detect_source(self, url: str) -> JobSource:
        """Detect the ATS source from URL."""
        if "lever.co" in url:
            return JobSource.LEVER
        elif "greenhouse.io" in url:
            return JobSource.GREENHOUSE
        elif "ashbyhq.com" in url:
            return JobSource.ASHBY
        elif "workable.com" in url:
            return JobSource.WORKABLE
        return JobSource.DIRECT
    
    def _generate_job_id(self, url: str) -> str:
        """Generate unique job ID from URL."""
        return hashlib.md5(url.encode()).hexdigest()[:12]
    
    def _deduplicate(self, jobs: List[JobListing]) -> List[JobListing]:
        """Remove duplicate job listings."""
        seen = set()
        unique = []
        
        for job in jobs:
            if job.url not in seen:
                seen.add(job.url)
                unique.append(job)
        
        return unique

