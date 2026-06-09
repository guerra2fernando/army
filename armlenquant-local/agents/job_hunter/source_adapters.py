"""
Job discovery source adapters.
"""
from dataclasses import dataclass
from typing import List, Optional
from urllib.parse import urlparse, unquote
import re

from .models import JobSource


@dataclass(frozen=True)
class JobSourceAdapter:
    source: JobSource
    templates: List[str]
    allowed_domains: List[str]

    def build_queries(self, role: str, location: str) -> List[str]:
        """Build a small set of progressively broader search queries."""
        role = role.strip()
        location = location.strip()
        location_terms = self._expand_location_terms(location)
        queries: List[str] = []
        seen: set = set()

        for template in self.templates:
            for location_term in location_terms:
                query = template.format(role=role, location=location_term).strip()
                if query and query not in seen:
                    seen.add(query)
                    queries.append(query)

        return queries

    def accepts_url(self, url: str) -> bool:
        return any(domain in url for domain in self.allowed_domains)

    def normalize_url(self, url: str) -> Optional[str]:
        if "google.com/url" in url:
            match = re.search(r"url=([^&]+)", url)
            if match:
                url = unquote(match.group(1))
        parsed = urlparse(url)
        clean_url = f"{parsed.scheme}://{parsed.netloc}{parsed.path}"
        return clean_url if self.accepts_url(clean_url) else None

    def _expand_location_terms(self, location: str) -> List[str]:
        """Add a few search-friendly alternatives for remote roles."""
        if not location:
            return [""]

        normalized = location.lower()
        if normalized == "remote":
            return ["Remote", '"Remote"', '"Work from home"', '"Anywhere"']

        return [location, f'"{location}"']

LEVER_ADAPTER = JobSourceAdapter(
    JobSource.LEVER,
    [
        'site:jobs.lever.co "{role}" "{location}"',
        'site:jobs.lever.co "{role}" jobs "{location}"',
        'site:jobs.lever.co "{role}" careers',
    ],
    ["lever.co"],
)
GREENHOUSE_ADAPTER = JobSourceAdapter(
    JobSource.GREENHOUSE,
    [
        'site:boards.greenhouse.io "{role}" "{location}"',
        'site:boards.greenhouse.io "{role}" jobs "{location}"',
        'site:boards.greenhouse.io "{role}" careers',
    ],
    ["greenhouse.io"],
)
ASHBY_ADAPTER = JobSourceAdapter(
    JobSource.ASHBY,
    [
        'site:jobs.ashbyhq.com "{role}" "{location}"',
        'site:jobs.ashbyhq.com "{role}" jobs "{location}"',
        'site:jobs.ashbyhq.com "{role}" careers',
    ],
    ["ashbyhq.com"],
)
WORKABLE_ADAPTER = JobSourceAdapter(
    JobSource.WORKABLE,
    [
        'site:apply.workable.com "{role}" "{location}"',
        'site:apply.workable.com "{role}" jobs "{location}"',
        'site:apply.workable.com "{role}" careers',
    ],
    ["workable.com"],
)

ADAPTERS = {
    JobSource.LEVER: LEVER_ADAPTER,
    JobSource.GREENHOUSE: GREENHOUSE_ADAPTER,
    JobSource.ASHBY: ASHBY_ADAPTER,
    JobSource.WORKABLE: WORKABLE_ADAPTER,
}
