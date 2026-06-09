"""
Commercial scout agent for lead discovery.
"""
from typing import Any, Dict, List

from agents.base_agent import AgentResult, BaseAgent
from agents.commercial_ops.models import (
    DraftMessage,
    FollowupDraft,
    OutreachChannel,
    ProfileBinding,
    SpecialistDraftPackage,
    SpecialistLane,
    SpecialistName,
    TargetPersona,
)
from poller.profile_loader import load_business_profiles, load_commercial_policy, load_operator_profile
from models.capability import CapabilityGrant, CapabilityPolicy

from .searcher import CommercialLeadSearcher


class CommercialScoutAgent(BaseAgent):
    """Discover commercial leads using business profiles."""

    def __init__(self):
        super().__init__("COMMERCIAL_SCOUT", version="1.0.0")
        self.searcher = CommercialLeadSearcher()

    def get_capability_grants(self) -> list[CapabilityGrant]:
        return [
            CapabilityGrant(
                capability_id="web_scraping",
                policy_override=CapabilityPolicy(
                    allowed_domains=[
                        "*.google.com",
                        "*.linkedin.com",
                    ],
                ),
            ),
            CapabilityGrant(
                capability_id="browser_navigate",
                policy_override=CapabilityPolicy(
                    allowed_domains=["*.google.com", "*.linkedin.com"]
                ),
            ),
        ]

    def get_capabilities(self) -> list:
        return [
            "commercial_lead_discovery",
            "linkedin_lead_search",
            "company_lead_search",
        ]

    async def execute(self, payload: Dict[str, Any]) -> AgentResult:
        action = payload.get("action", "discover_leads")
        if action == "draft_outreach":
            return await self._action_draft_outreach(payload)
        if action != "discover_leads":
            return AgentResult(success=False, error=f"Unknown action: {action}")

        business_slug = payload.get("business_slug")
        business_profiles = load_business_profiles(only_active=False)
        business_profile = next((item for item in business_profiles if item.slug == business_slug), None)
        if not business_profile:
            return AgentResult(success=False, error=f"Business profile not found: {business_slug}")

        personas = payload.get("personas") or business_profile.target_personas or ["Founder"]
        keywords = payload.get("keywords") or [business_profile.product_name, business_profile.tagline or business_profile.business_name]
        locations = payload.get("locations") or ["Remote"]
        limit = payload.get("limit", 20)

        try:
            leads = await self.execute_with_capability(
                "web_scraping",
                self.searcher.search_leads,
                personas=personas,
                keywords=keywords,
                locations=locations,
                limit_per_query=max(1, min(limit, 10)),
            )
            return AgentResult(
                success=True,
                data={
                    "business_slug": business_slug,
                    "leads_found": len(leads),
                    "leads": [lead.model_dump() for lead in leads[:limit]],
                },
            )
        finally:
            await self.searcher.close()

    async def _action_draft_outreach(self, payload: Dict[str, Any]) -> AgentResult:
        """Generate structured commercial outreach draft packages."""
        operator_profile = load_operator_profile()
        policy = load_commercial_policy()
        business_slug = (payload.get("business_slug") or payload.get("lane") or "").strip().lower()
        business_profiles = load_business_profiles(only_active=False)
        business_profile = next((item for item in business_profiles if item.slug == business_slug), None)

        lane, specialist = self._resolve_specialist(payload, business_profile)
        target_persona = self._resolve_persona(payload, business_profile)
        recommended_channel = self._resolve_channel(policy, business_profile, payload)
        company = payload.get("company", "")
        person_name = payload.get("person_name", "")
        title = payload.get("title", "")
        source_url = payload.get("url") or payload.get("source_url")

        if not source_url:
            return AgentResult(success=False, error="No lead URL provided")

        draft = SpecialistDraftPackage(
            specialist=specialist,
            lane=lane,
            target_persona=target_persona,
            profile_binding=ProfileBinding(
                operator_profile_slug=operator_profile.slug if operator_profile else None,
                operator_display_name=operator_profile.display_name if operator_profile else None,
                business_profile_slug=business_profile.slug if business_profile else business_slug or None,
                business_name=business_profile.business_name if business_profile else None,
                product_name=business_profile.product_name if business_profile else self._default_product_name(lane),
                policy_slug=policy.slug if policy else None,
            ),
            opportunity_id=payload.get("opportunity_id") or payload.get("lead_id"),
            source_url=source_url,
            title=title,
            company=company,
            person_name=person_name,
            fit_score=self._score_fit(payload, lane),
            rationale=self._build_rationale(payload, lane, business_profile),
            recommended_channel=recommended_channel,
            recommended_next_step="Review the intelligence and approve the recommended outreach angle.",
            primary_draft=DraftMessage(
                channel=recommended_channel,
                subject=self._build_subject(company, lane),
                body=self._build_message(payload, lane, target_persona, operator_profile, business_profile),
                cta=self._build_cta(lane),
            ),
            followups=[
                FollowupDraft(
                    delay_days=3,
                    channel=recommended_channel,
                    body=self._build_followup(payload, lane, followup_number=1),
                ),
                FollowupDraft(
                    delay_days=7,
                    channel=recommended_channel,
                    body=self._build_followup(payload, lane, followup_number=2),
                ),
            ],
            metadata={
                "source": payload.get("source"),
                "location": payload.get("location", ""),
                "business_slug": business_slug or None,
            },
        )
        return AgentResult(success=True, data={"draft_package": draft.model_dump(mode="json")})

    def _resolve_specialist(self, payload: Dict[str, Any], business_profile) -> tuple[SpecialistLane, SpecialistName]:
        raw = (payload.get("lane") or payload.get("business_slug") or "").strip().lower()
        if business_profile:
            raw = business_profile.slug.lower()
        mapping = {
            "lenquant": (SpecialistLane.LENQUANT, SpecialistName.LENQUANT_SELLER),
            "lenxys": (SpecialistLane.LENXYS, SpecialistName.LENXYS_SELLER),
            "services": (SpecialistLane.SERVICES, SpecialistName.SERVICES_SELLER),
            "trading": (SpecialistLane.TRADING, SpecialistName.TRADING_SELLER),
        }
        if raw in mapping:
            return mapping[raw]

        haystack = " ".join(
            str(value)
            for value in [payload.get("title", ""), payload.get("company", ""), payload.get("person_name", "")]
        ).lower()
        if any(term in haystack for term in ["portfolio", "trading", "quant"]):
            return SpecialistLane.TRADING, SpecialistName.TRADING_SELLER
        if any(term in haystack for term in ["growth", "automation", "systems"]):
            return SpecialistLane.LENXYS, SpecialistName.LENXYS_SELLER
        return SpecialistLane.SERVICES, SpecialistName.SERVICES_SELLER

    def _resolve_persona(self, payload: Dict[str, Any], business_profile) -> TargetPersona:
        haystack = " ".join(
            [
                payload.get("title", ""),
                payload.get("person_name", ""),
                payload.get("persona", ""),
                " ".join(getattr(business_profile, "target_personas", []) or []),
            ]
        ).lower()
        if "portfolio manager" in haystack:
            return TargetPersona.PORTFOLIO_MANAGER
        if "head of growth" in haystack:
            return TargetPersona.HEAD_OF_GROWTH
        if "coo" in haystack:
            return TargetPersona.COO
        if "ceo" in haystack:
            return TargetPersona.CEO
        if "founder" in haystack:
            return TargetPersona.FOUNDER
        return TargetPersona.GENERIC

    def _resolve_channel(self, policy, business_profile, payload: Dict[str, Any]) -> OutreachChannel:
        channels: List[str] = []
        if payload.get("source") == "linkedin":
            channels.append("LINKEDIN_DM")
        if business_profile:
            channels.extend(business_profile.approved_channels)
        if policy:
            channels.extend(policy.allowed_channels)
        normalized = [str(channel).upper() for channel in channels]
        if "LINKEDIN_DM" in normalized:
            return OutreachChannel.LINKEDIN_DM
        if "EMAIL" in normalized:
            return OutreachChannel.EMAIL
        return OutreachChannel.MANUAL

    def _default_product_name(self, lane: SpecialistLane) -> str:
        defaults = {
            SpecialistLane.LENQUANT: "LenQuant",
            SpecialistLane.LENXYS: "Lenxys",
            SpecialistLane.SERVICES: "Services",
            SpecialistLane.TRADING: "Trading",
        }
        return defaults[lane]

    def _score_fit(self, payload: Dict[str, Any], lane: SpecialistLane) -> float:
        base = {
            SpecialistLane.LENQUANT: 0.84,
            SpecialistLane.LENXYS: 0.8,
            SpecialistLane.SERVICES: 0.74,
            SpecialistLane.TRADING: 0.78,
        }[lane]
        if payload.get("source") == "linkedin":
            base += 0.03
        return min(0.98, base)

    def _build_rationale(self, payload: Dict[str, Any], lane: SpecialistLane, business_profile) -> List[str]:
        product_name = business_profile.product_name if business_profile else self._default_product_name(lane)
        rationale = [f"Lead is routed to the {product_name} specialist."]
        if payload.get("company"):
            rationale.append(f"{payload['company']} is treated as the primary account target.")
        if business_profile and business_profile.tagline:
            rationale.append(f"Draft anchors to the active business profile tagline: {business_profile.tagline}.")
        return rationale

    def _build_subject(self, company: str, lane: SpecialistLane) -> str:
        if lane == SpecialistLane.LENQUANT:
            return f"Trading ops leverage for {company or 'your team'}"
        if lane == SpecialistLane.LENXYS:
            return f"Growth systems for {company or 'your company'}"
        if lane == SpecialistLane.TRADING:
            return f"Exploring trading collaboration with {company or 'your team'}"
        return f"Operator support for {company or 'your team'}"

    def _build_message(self, payload: Dict[str, Any], lane: SpecialistLane, persona: TargetPersona, operator_profile, business_profile) -> str:
        person_name = payload.get("person_name") or "there"
        opener = f"Hi {person_name},"
        sender = operator_profile.display_name if operator_profile else "I"
        product = business_profile.product_name if business_profile else self._default_product_name(lane)
        angle = {
            SpecialistLane.LENQUANT: f"{product} helps trading teams tighten execution support and decision speed.",
            SpecialistLane.LENXYS: f"{product} helps operators build cleaner growth systems and execution loops.",
            SpecialistLane.SERVICES: "We can support execution with targeted operator services where internal bandwidth is thin.",
            SpecialistLane.TRADING: "We can explore a trading-focused collaboration with a concrete execution angle.",
        }[lane]
        persona_line = {
            TargetPersona.FOUNDER: "I’m reaching out directly because founder-level context usually shapes the fastest decision.",
            TargetPersona.CEO: "I’m reaching out because this looks like a CEO-level systems decision.",
            TargetPersona.COO: "I’m reaching out because this looks operationally urgent.",
            TargetPersona.PORTFOLIO_MANAGER: "I’m reaching out because the fit looks strongest at the portfolio and execution layer.",
            TargetPersona.HEAD_OF_GROWTH: "I’m reaching out because the strongest fit appears in growth execution.",
            TargetPersona.GENERIC: "I’m reaching out because the fit looks strong from the available public signal.",
        }[persona]
        return f"{opener}\n\nI’m {sender}. {angle}\n\n{persona_line}\n\nIf useful, I can send a short outline tailored to {payload.get('company') or 'your team'}."

    def _build_cta(self, lane: SpecialistLane) -> str:
        if lane == SpecialistLane.LENQUANT:
            return "Ask for a brief call about trading operations and execution bottlenecks."
        if lane == SpecialistLane.LENXYS:
            return "Ask for a short call to review systems and growth ops bottlenecks."
        if lane == SpecialistLane.TRADING:
            return "Ask whether a short conversation on trading collaboration makes sense."
        return "Ask whether a short call on operator support would be useful."

    def _build_followup(self, payload: Dict[str, Any], lane: SpecialistLane, followup_number: int) -> str:
        company = payload.get("company") or "your team"
        if followup_number == 1:
            return f"Following up in case a short {lane.value.lower()} conversation for {company} would be useful."
        return f"Closing the loop on the earlier note for {company}. Happy to share a tighter outline if timing is better now."
