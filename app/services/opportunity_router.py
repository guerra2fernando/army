"""
Opportunity router for Commercial Ops.
"""
import json
from typing import Any, Dict, List, Optional

from loguru import logger

from app.agents.llm_client import get_llm_client
from app.db import Database
from app.models.commercial_ops import (
    OpportunityRoutingDecision,
    RoutingMethod,
    SpecialistName,
    SpecialistProfileBinding,
    TargetPersona,
    new_route_id,
)
from app.models.opportunity import OpportunityKind, OpportunityLane
from app.models.profiles import OutreachChannel


class OpportunityRouterService:
    """Classify opportunities deterministically, then with LLM fallback."""

    def __init__(self, llm_client=None):
        self.llm_client = llm_client or get_llm_client()
        self.routes = Database.get_collection("opportunity_routes")
        self.logger = logger.bind(component="opportunity_router")

    async def route_and_persist(self, opportunity_doc: Dict[str, Any]) -> OpportunityRoutingDecision:
        """Route an opportunity and persist the result."""
        decision = await self.classify(opportunity_doc)
        route_id = new_route_id()
        await self.routes.update_one(
            {"opportunity_id": decision.opportunity_id},
            {
                "$set": {
                    "opportunity_id": decision.opportunity_id,
                    "kind": decision.kind.value,
                    "lane": decision.lane.value,
                    "specialist": decision.specialist.value,
                    "target_persona": decision.target_persona.value,
                    "routing_method": decision.routing_method.value,
                    "confidence": decision.confidence,
                    "profile_binding": decision.profile_binding.model_dump(),
                    "recommended_channel": decision.recommended_channel.value,
                    "should_draft": decision.should_draft,
                    "rationale": decision.rationale,
                    "metadata": decision.metadata,
                },
                "$setOnInsert": {"_id": route_id, "route_id": route_id},
            },
            upsert=True,
        )
        return decision

    async def classify(self, opportunity_doc: Dict[str, Any]) -> OpportunityRoutingDecision:
        """Route an opportunity into a specialist."""
        deterministic = self._deterministic_route(opportunity_doc)
        if deterministic.specialist != SpecialistName.IGNORE and deterministic.confidence >= 0.75:
            return deterministic

        fallback = await self._llm_fallback(opportunity_doc, deterministic)
        return fallback or deterministic

    def _deterministic_route(self, opportunity_doc: Dict[str, Any]) -> OpportunityRoutingDecision:
        kind = OpportunityKind(opportunity_doc.get("kind", OpportunityKind.COMMERCIAL.value))
        lane = OpportunityLane(opportunity_doc.get("lane", OpportunityLane.COMMERCIAL.value))
        rationale: List[str] = []
        metadata = {"source_platform": opportunity_doc.get("source_platform")}

        specialist = SpecialistName.IGNORE
        target_persona = self._infer_persona(opportunity_doc)
        channel = self._pick_channel(opportunity_doc)
        confidence = 0.45

        if kind == OpportunityKind.JOB or lane == OpportunityLane.JOBS:
            specialist = SpecialistName.JOB_HUNTER
            lane = OpportunityLane.JOBS
            confidence = 0.92
            rationale.append("Job opportunities route directly to Job Hunter.")
        else:
            business_slug = (opportunity_doc.get("business_slug") or "").strip().lower()
            haystack = " ".join(
                str(value)
                for value in [
                    opportunity_doc.get("title", ""),
                    opportunity_doc.get("company", ""),
                    opportunity_doc.get("person_name", ""),
                    json.dumps(opportunity_doc.get("source_data", {}), sort_keys=True, default=str),
                    " ".join(opportunity_doc.get("reasons", [])),
                ]
            ).lower()

            lane_map = {
                "lenquant": (OpportunityLane.LENQUANT, SpecialistName.LENQUANT_SELLER, 0.9, "Business profile bound to LenQuant."),
                "lenxys": (OpportunityLane.LENXYS, SpecialistName.LENXYS_SELLER, 0.9, "Business profile bound to Lenxys."),
            }
            if business_slug in lane_map:
                lane, specialist, confidence, reason = lane_map[business_slug]
                rationale.append(reason)
            elif lane in {OpportunityLane.LENQUANT, OpportunityLane.LENXYS, OpportunityLane.SERVICES, OpportunityLane.TRADING}:
                specialist = {
                    OpportunityLane.LENQUANT: SpecialistName.LENQUANT_SELLER,
                    OpportunityLane.LENXYS: SpecialistName.LENXYS_SELLER,
                    OpportunityLane.SERVICES: SpecialistName.SERVICES_SELLER,
                    OpportunityLane.TRADING: SpecialistName.TRADING_SELLER,
                }[lane]
                confidence = 0.85
                rationale.append(f"Discovery lane already identifies {lane.value.lower()} fit.")
            elif any(term in haystack for term in ["quant", "trading", "portfolio manager", "hedge fund", "execution"]):
                lane = OpportunityLane.LENQUANT
                specialist = SpecialistName.LENQUANT_SELLER
                confidence = 0.78
                rationale.append("Trading and quant signals match LenQuant.")
            elif any(term in haystack for term in ["growth ops", "automation", "systems", "revops", "head of growth"]):
                lane = OpportunityLane.LENXYS
                specialist = SpecialistName.LENXYS_SELLER
                confidence = 0.78
                rationale.append("Systems and growth signals match Lenxys.")
            elif any(term in haystack for term in ["consulting", "service", "fractional", "agency"]):
                lane = OpportunityLane.SERVICES
                specialist = SpecialistName.SERVICES_SELLER
                confidence = 0.76
                rationale.append("Consulting-style demand matches Services.")
            elif any(term in haystack for term in ["trading partner", "liquidity", "broker", "deal desk"]):
                lane = OpportunityLane.TRADING
                specialist = SpecialistName.TRADING_SELLER
                confidence = 0.76
                rationale.append("Trading partnership signals match Trading.")
            else:
                rationale.append("No strong deterministic specialist signal found.")

        return OpportunityRoutingDecision(
            opportunity_id=opportunity_doc["opportunity_id"],
            kind=kind,
            lane=lane,
            specialist=specialist,
            target_persona=target_persona,
            routing_method=RoutingMethod.DETERMINISTIC,
            confidence=confidence,
            profile_binding=SpecialistProfileBinding(
                operator_profile_slug=opportunity_doc.get("profile_slug"),
                business_profile_slug=opportunity_doc.get("business_slug"),
                policy_slug=opportunity_doc.get("policy_slug"),
            ),
            recommended_channel=channel,
            should_draft=specialist != SpecialistName.IGNORE,
            rationale=rationale,
            metadata=metadata,
        )

    async def _llm_fallback(
        self,
        opportunity_doc: Dict[str, Any],
        deterministic: OpportunityRoutingDecision,
    ) -> Optional[OpportunityRoutingDecision]:
        if not self.llm_client or not getattr(self.llm_client, "is_available", False):
            return None

        system = (
            "Classify one opportunity into a Commercial Ops specialist. "
            "Return JSON with keys: lane, specialist, target_persona, confidence, "
            "recommended_channel, should_draft, rationale."
        )
        user = json.dumps(
            {
                "opportunity": opportunity_doc,
                "deterministic_guess": deterministic.model_dump(mode="json"),
                "allowed_lanes": [item.value for item in OpportunityLane],
                "allowed_specialists": [item.value for item in SpecialistName],
                "allowed_personas": [item.value for item in TargetPersona],
                "allowed_channels": [item.value for item in OutreachChannel],
            },
            default=str,
        )
        try:
            response = await self.llm_client.chat(
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
                temperature=0.1,
                max_tokens=500,
                json_response=True,
            )
            payload = json.loads(response.content)
            return OpportunityRoutingDecision(
                opportunity_id=opportunity_doc["opportunity_id"],
                kind=OpportunityKind(opportunity_doc.get("kind", OpportunityKind.COMMERCIAL.value)),
                lane=OpportunityLane(payload["lane"]),
                specialist=SpecialistName(payload["specialist"]),
                target_persona=TargetPersona(payload.get("target_persona", TargetPersona.GENERIC.value)),
                routing_method=RoutingMethod.LLM_FALLBACK,
                confidence=float(payload.get("confidence", deterministic.confidence)),
                profile_binding=deterministic.profile_binding,
                recommended_channel=OutreachChannel(payload.get("recommended_channel", deterministic.recommended_channel.value)),
                should_draft=bool(payload.get("should_draft", True)),
                rationale=list(payload.get("rationale", [])) or ["LLM fallback classification used."],
                metadata={
                    **deterministic.metadata,
                    "llm_provider": getattr(self.llm_client, "active_provider", None),
                },
            )
        except Exception as exc:
            self.logger.warning(f"LLM fallback classification failed: {exc}")
            return None

    def _infer_persona(self, opportunity_doc: Dict[str, Any]) -> TargetPersona:
        haystack = " ".join(
            str(value)
            for value in [
                opportunity_doc.get("title", ""),
                opportunity_doc.get("person_name", ""),
                json.dumps(opportunity_doc.get("source_data", {}), sort_keys=True, default=str),
            ]
        ).lower()
        if any(term in haystack for term in ["recruiter", "talent", "sourcer", "people ops"]):
            return TargetPersona.RECRUITER
        if "head of growth" in haystack:
            return TargetPersona.HEAD_OF_GROWTH
        if "portfolio manager" in haystack:
            return TargetPersona.PORTFOLIO_MANAGER
        if "coo" in haystack:
            return TargetPersona.COO
        if "ceo" in haystack:
            return TargetPersona.CEO
        if any(term in haystack for term in ["founder", "cofounder"]):
            return TargetPersona.FOUNDER
        if opportunity_doc.get("kind") == OpportunityKind.JOB.value:
            return TargetPersona.HIRING_MANAGER
        return TargetPersona.GENERIC

    def _pick_channel(self, opportunity_doc: Dict[str, Any]) -> OutreachChannel:
        platform = (opportunity_doc.get("source_platform") or "").upper()
        if platform == "LINKEDIN":
            return OutreachChannel.LINKEDIN_DM
        return OutreachChannel.EMAIL


def get_opportunity_router() -> OpportunityRouterService:
    """Return the router service."""

    return OpportunityRouterService()
