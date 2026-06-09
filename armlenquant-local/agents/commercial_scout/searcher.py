"""
Commercial lead searcher using Google dorks.
"""
import asyncio
import hashlib
from datetime import datetime
from typing import List, Optional

from loguru import logger

try:
    from playwright.async_api import async_playwright, Browser
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False
    Browser = None

from poller.config import get_settings
from .models import LeadCandidate
from .source_adapters import ADAPTERS, adapter_for_url

settings = get_settings()


class CommercialLeadSearcher:
    """Searches for commercial leads across supported sources."""

    def __init__(self):
        self.logger = logger.bind(component="commercial_searcher")
        self.browser: Optional[Browser] = None
        self._playwright = None
        self.seen_urls: set = set()

    async def initialize(self):
        if not PLAYWRIGHT_AVAILABLE:
            self.logger.warning("Playwright not available, browser features disabled")
            return
        self._playwright = await async_playwright().start()
        self.browser = await self._playwright.chromium.launch(headless=settings.headless_mode)

    async def close(self):
        if self.browser:
            await self.browser.close()
            self.browser = None
        if self._playwright:
            await self._playwright.stop()
            self._playwright = None

    async def search_leads(
        self,
        personas: List[str],
        keywords: List[str],
        locations: List[str],
        limit_per_query: int = 10,
    ) -> List[LeadCandidate]:
        if not self.browser:
            await self.initialize()
        if not self.browser:
            return []

        all_leads: List[LeadCandidate] = []
        for persona in personas:
            for keyword in keywords:
                for location in locations:
                    for adapter in ADAPTERS:
                        results = await self._search_single(adapter, persona, keyword, location, limit_per_query)
                        all_leads.extend(results)
                        await asyncio.sleep(1.5)
        return self._deduplicate(all_leads)

    async def _search_single(self, adapter, persona: str, keyword: str, location: str, limit: int) -> List[LeadCandidate]:
        query = adapter.build_query(persona, keyword, location)
        page = await self.browser.new_page()
        try:
            await page.goto(f"https://www.google.com/search?q={query}&num={limit}", timeout=settings.browser_timeout)
            await page.wait_for_selector("div#search", timeout=10000)
            entries = await page.evaluate(
                """
                () => Array.from(document.querySelectorAll('div#search a[href]'))
                  .map(a => ({ href: a.href, text: a.textContent || '' }))
                """
            )
            leads: List[LeadCandidate] = []
            for entry in entries:
                href = entry.get("href", "")
                if href in self.seen_urls:
                    continue
                normalized = adapter.normalize_url(href)
                if not normalized:
                    continue
                self.seen_urls.add(normalized)
                parsed = adapter.parse_result(normalized, entry.get("text", ""))
                leads.append(
                    LeadCandidate(
                        lead_id=self._generate_lead_id(normalized),
                        url=normalized,
                        source=parsed["source"],
                        title=parsed.get("title", ""),
                        person_name=parsed.get("person_name", ""),
                        company=parsed.get("company", ""),
                        location=location,
                        discovered_at=datetime.utcnow(),
                    )
                )
            return leads[:limit]
        finally:
            await page.close()

    def _generate_lead_id(self, url: str) -> str:
        return hashlib.md5(url.encode()).hexdigest()[:12]

    def _deduplicate(self, leads: List[LeadCandidate]) -> List[LeadCandidate]:
        seen = set()
        unique = []
        for lead in leads:
            if lead.url not in seen:
                seen.add(lead.url)
                unique.append(lead)
        return unique
