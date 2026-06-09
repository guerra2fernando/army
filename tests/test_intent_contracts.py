import pytest

from app.db import Database
from app.utils.intent_contracts import IntentContractService, ClarificationQuestion


@pytest.mark.asyncio
async def test_contract_requires_clarification():
    service = IntentContractService(Database.get_collection("intent_contracts"))

    await service.seed_contract(
        agent_name="JOB_HUNTER",
        payload_schema={
            "required": ["search_terms"],
            "properties": {"search_terms": {"type": "array", "minItems": 1}},
        },
        clarification_rules=[
            {"condition": "search_terms_empty", "question": "What job roles are you interested in?"}
        ],
    )

    result = await service.validate("JOB_HUNTER", {"location": "remote"})

    assert result["valid"] is False
    assert result["clarifications"]
    assert isinstance(result["clarifications"][0], ClarificationQuestion)
    assert "job" in result["clarifications"][0].question.lower()


@pytest.mark.asyncio
async def test_contract_flags_approval():
    service = IntentContractService(Database.get_collection("intent_contracts"))

    await service.seed_contract(
        agent_name="JOB_HUNTER",
        approval_required={"high_risk_actions": True},
    )

    result = await service.validate("JOB_HUNTER", {"action": "apply_job"})

    assert result["needs_approval"] is True
    assert "High-risk" in (result.get("approval_reason") or "High-risk action detected")









