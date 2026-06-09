"""
Commercial discovery source adapters.
"""
from dataclasses import dataclass
import re
from typing import List, Optional
from urllib.parse import urlparse

from .models import LeadSource


@dataclass(frozen=True)
class LeadSourceAdapter:
    source: LeadSource
    template: str
    allowed_domains: List[str]

    def build_query(self, persona: str, keyword: str, location: str) -> str:
        return self.template.format(persona=persona, keyword=keyword, location=location)

    def accepts_url(self, url: str) -> bool:
        return any(domain in url for domain in self.allowed_domains)

    def normalize_url(self, url: str) -> Optional[str]:
        parsed = urlparse(url)
        clean_url = f"{parsed.scheme}://{parsed.netloc}{parsed.path}".rstrip("/")
        return clean_url if self.accepts_url(clean_url) else None

    def parse_result(self, url: str, text: str) -> dict:
        clean = self.normalize_url(url) or url
        title = " ".join((text or "").split())
        person_name = ""
        company = ""
        if self.source == LeadSource.LINKEDIN:
            slug = clean.rstrip("/").split("/")[-1].replace("-", " ")
            person_name = slug.title()
        elif self.source == LeadSource.COMPANY_WEBSITE:
            company = urlparse(clean).netloc.replace("www.", "").split(".")[0].replace("-", " ").title()
        return {
            "url": clean,
            "title": title,
            "person_name": person_name,
            "company": company,
            "source": self.source.value,
        }


LINKEDIN_LEAD_ADAPTER = LeadSourceAdapter(
    source=LeadSource.LINKEDIN,
    template='site:linkedin.com/in "{persona}" "{keyword}" "{location}"',
    allowed_domains=["linkedin.com/in/", "linkedin.com/pub/"],
)

COMPANY_SITE_ADAPTER = LeadSourceAdapter(
    source=LeadSource.COMPANY_WEBSITE,
    template='"{keyword}" "{persona}" "{location}"',
    allowed_domains=[".com/", ".io/", ".ai/"],
)


ADAPTERS = [LINKEDIN_LEAD_ADAPTER, COMPANY_SITE_ADAPTER]


def adapter_for_url(url: str) -> Optional[LeadSourceAdapter]:
    for adapter in ADAPTERS:
        if adapter.accepts_url(url):
            return adapter
    return None
