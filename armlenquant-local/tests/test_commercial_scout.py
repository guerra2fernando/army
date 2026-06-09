import json
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest


class TestCommercialScoutAdapters:
    def test_linkedin_adapter_builds_query(self):
        from agents.commercial_scout.source_adapters import LINKEDIN_LEAD_ADAPTER

        query = LINKEDIN_LEAD_ADAPTER.build_query("Founder", "quant trading", "London")
        assert "linkedin.com/in" in query
        assert "Founder" in query

    def test_company_adapter_parses_result(self):
        from agents.commercial_scout.source_adapters import COMPANY_SITE_ADAPTER

        parsed = COMPANY_SITE_ADAPTER.parse_result("https://acme.io/team", "Acme Team")
        assert parsed["company"] == "Acme"


class TestCommercialScoutAgent:
    @pytest.mark.asyncio
    async def test_discover_leads_requires_business_profile(self):
        from agents.commercial_scout.agent import CommercialScoutAgent

        agent = CommercialScoutAgent()
        result = await agent.execute({"action": "discover_leads", "business_slug": "missing"})
        assert result.success is False
        assert "Business profile not found" in result.error

    @pytest.mark.asyncio
    async def test_discover_leads_uses_business_profile(self, tmp_path):
        from agents.commercial_scout.agent import CommercialScoutAgent

        root = tmp_path / "operator_data"
        profile_path = root / "businesses" / "lenquant" / "profile.json"
        profile_path.parent.mkdir(parents=True, exist_ok=True)
        profile_path.write_text(
            json.dumps(
                {
                    "slug": "lenquant",
                    "business_name": "LenQuant",
                    "product_name": "LenQuant",
                    "tagline": "AI trading ops",
                    "target_personas": ["Founder"],
                    "is_active": True,
                }
            ),
            encoding="utf-8",
        )

        agent = CommercialScoutAgent()
        mocked = [type("Lead", (), {"model_dump": lambda self: {"url": "https://linkedin.com/in/jane", "source": "linkedin"}})()]
        with patch("agents.commercial_scout.agent.load_business_profiles") as load_profiles:
            with patch.object(agent, "execute_with_capability", AsyncMock(return_value=mocked)):
                load_profiles.return_value = [
                    type(
                        "BusinessProfile",
                        (),
                        {
                            "slug": "lenquant",
                            "target_personas": ["Founder"],
                            "product_name": "LenQuant",
                            "tagline": "AI trading ops",
                            "business_name": "LenQuant",
                        },
                    )()
                ]
                result = await agent.execute({"action": "discover_leads", "business_slug": "lenquant"})

        assert result.success is True
        assert result.data["business_slug"] == "lenquant"
        assert result.data["leads_found"] == 1
