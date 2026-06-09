import pytest

from app.db import Database
from app.models.opportunity import OpportunityKind, OpportunityLane
from app.services.opportunity_router import OpportunityRouterService


@pytest.mark.asyncio
async def test_deterministic_job_routing_persists():
    service = OpportunityRouterService(llm_client=None)
    decision = await service.route_and_persist(
        {
            "opportunity_id": "opp-job-1",
            "kind": OpportunityKind.JOB.value,
            "lane": OpportunityLane.JOBS.value,
            "title": "Senior Growth Lead",
            "company": "Example Inc",
            "source_platform": "GREENHOUSE",
            "source_url": "https://boards.greenhouse.io/example/jobs/123",
            "profile_slug": "default",
        }
    )

    assert decision.specialist.value == "JOB_HUNTER"
    assert decision.target_persona.value == "HIRING_MANAGER"

    stored = await Database.get_collection("opportunity_routes").find_one({"opportunity_id": "opp-job-1"})
    assert stored is not None
    assert stored["specialist"] == "JOB_HUNTER"
    assert stored["routing_method"] == "DETERMINISTIC"


@pytest.mark.asyncio
async def test_llm_fallback_used_when_deterministic_is_weak():
    class StubLLM:
        is_available = True
        active_provider = "openai"

        async def chat(self, *args, **kwargs):
            class Response:
                content = (
                    '{"lane":"SERVICES","specialist":"SERVICES_SELLER",'
                    '"target_persona":"FOUNDER","confidence":0.81,'
                    '"recommended_channel":"EMAIL","should_draft":true,'
                    '"rationale":["Fallback matched consulting-style demand."]}'
                )

            return Response()

    service = OpportunityRouterService(llm_client=StubLLM())
    decision = await service.classify(
        {
            "opportunity_id": "opp-commercial-1",
            "kind": OpportunityKind.COMMERCIAL.value,
            "lane": OpportunityLane.COMMERCIAL.value,
            "title": "Operator support request",
            "company": "Acme",
            "person_name": "Jane Founder",
            "source_platform": "OTHER",
            "source_url": "https://acme.io/contact",
        }
    )

    assert decision.routing_method.value == "LLM_FALLBACK"
    assert decision.specialist.value == "SERVICES_SELLER"
    assert decision.target_persona.value == "FOUNDER"
