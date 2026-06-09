from unittest.mock import AsyncMock, patch

import pytest


@pytest.mark.asyncio
async def test_job_hunter_supports_legacy_search_action():
    from agents.job_hunter.agent import JobHunterAgent

    agent = JobHunterAgent()
    with patch.object(agent, "_action_search", AsyncMock()) as search:
        search.return_value.data = {"jobs_found": 1}
        search.return_value.success = True
        result = await agent.execute({"action": "search_jobs", "roles": ["Growth Lead"]})

    assert result.success is True
    search.assert_awaited_once()


@pytest.mark.asyncio
async def test_job_hunter_draft_outreach_distinguishes_recruiter():
    from agents.job_hunter.agent import JobHunterAgent
    from agents.job_hunter.models import MatchResult

    agent = JobHunterAgent()
    with patch("agents.job_hunter.agent.load_operator_profile") as load_profile:
        with patch("agents.job_hunter.agent.load_commercial_policy") as load_policy:
            with patch.object(agent, "_load_cv", AsyncMock(return_value=None)):
                with patch.object(agent.matcher, "match_job", AsyncMock(return_value=MatchResult(
                    job_id="job-1",
                    overall_score=88,
                    skill_match=90,
                    experience_match=86,
                    culture_fit=80,
                    compensation_fit=82,
                    highlights=["Built growth systems in prior operator roles."],
                    recommendation="Strong fit",
                ))):
                    load_profile.return_value = type(
                        "Profile",
                        (),
                        {
                            "slug": "default",
                            "display_name": "Fernando",
                            "preferred_roles": ["Growth Lead"],
                            "preferred_locations": ["Remote"],
                            "preferred_channels": ["EMAIL", "LINKEDIN_DM"],
                        },
                    )()
                    load_policy.return_value = type("Policy", (), {"slug": "default", "allowed_channels": ["EMAIL"]})()
                    result = await agent.execute(
                        {
                            "action": "draft_outreach",
                            "job": {
                                "job_id": "job-1",
                                "url": "https://jobs.example.com/1",
                                "source": "direct",
                                "company": "Example",
                                "title": "Growth Lead",
                                "location": "Remote",
                            },
                            "contact_title": "Senior Recruiter",
                        }
                    )

    draft = result.data["draft_package"]
    assert draft["target_persona"] == "RECRUITER"
    assert draft["profile_binding"]["operator_profile_slug"] == "default"
    assert draft["primary_draft"]["channel"] == "EMAIL"
    assert len(draft["followups"]) == 2


@pytest.mark.asyncio
async def test_commercial_scout_generates_lenquant_draft():
    from agents.commercial_scout.agent import CommercialScoutAgent

    agent = CommercialScoutAgent()
    with patch("agents.commercial_scout.agent.load_operator_profile") as load_operator:
        with patch("agents.commercial_scout.agent.load_commercial_policy") as load_policy:
            with patch("agents.commercial_scout.agent.load_business_profiles") as load_business:
                load_operator.return_value = type("Profile", (), {"slug": "default", "display_name": "Fernando"})()
                load_policy.return_value = type("Policy", (), {"slug": "default", "allowed_channels": ["EMAIL", "LINKEDIN_DM"]})()
                load_business.return_value = [
                    type(
                        "BusinessProfile",
                        (),
                        {
                            "slug": "lenquant",
                            "business_name": "LenQuant",
                            "product_name": "LenQuant",
                            "tagline": "AI-powered trading intelligence and execution support",
                            "target_personas": ["Founder", "Portfolio Manager"],
                            "approved_channels": ["LINKEDIN_DM", "EMAIL"],
                        },
                    )()
                ]
                result = await agent.execute(
                    {
                        "action": "draft_outreach",
                        "business_slug": "lenquant",
                        "source_url": "https://www.linkedin.com/in/jane-doe/",
                        "source": "linkedin",
                        "person_name": "Jane Doe",
                        "company": "Acme Capital",
                        "title": "Founder",
                    }
                )

    draft = result.data["draft_package"]
    assert draft["specialist"] == "LENQUANT_SELLER"
    assert draft["lane"] == "LENQUANT"
    assert draft["profile_binding"]["business_profile_slug"] == "lenquant"
    assert draft["recommended_channel"] == "LINKEDIN_DM"
    assert len(draft["followups"]) == 2


@pytest.mark.asyncio
async def test_commercial_scout_supports_services_and_trading_templates():
    from agents.commercial_scout.agent import CommercialScoutAgent

    agent = CommercialScoutAgent()
    with patch("agents.commercial_scout.agent.load_operator_profile", return_value=None):
        with patch("agents.commercial_scout.agent.load_commercial_policy") as load_policy:
            with patch("agents.commercial_scout.agent.load_business_profiles", return_value=[]):
                load_policy.return_value = type("Policy", (), {"slug": "default", "allowed_channels": ["EMAIL"]})()
                services = await agent.execute(
                    {
                        "action": "draft_outreach",
                        "lane": "services",
                        "source_url": "https://acme.io/contact",
                        "company": "Acme",
                        "title": "Founder",
                    }
                )
                trading = await agent.execute(
                    {
                        "action": "draft_outreach",
                        "lane": "trading",
                        "source_url": "https://fund.example/contact",
                        "company": "Blue Fund",
                        "title": "Portfolio Manager",
                    }
                )

    assert services.data["draft_package"]["lane"] == "SERVICES"
    assert trading.data["draft_package"]["lane"] == "TRADING"
