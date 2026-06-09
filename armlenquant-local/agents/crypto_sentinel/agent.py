"""
Crypto Sentinel (Local)
Lightweight implementation to produce morning briefs and crypto summaries
using the configured LLM. Designed to unblock task processing even without
live market data feeds.
"""
from datetime import datetime
from typing import Any, Dict, List, Optional

from agents.base_agent import AgentResult, BaseAgent
from agents.llm_client import LLMClient, get_llm_client
from poller.config import get_settings

# Default high-liquidity majors used when payload doesn't provide enough assets
DEFAULT_ASSETS = [
    "BTC",
    "ETH",
    "BNB",
    "SOL",
    "XRP",
    "ADA",
    "AVAX",
    "DOGE",
    "LINK",
    "MATIC",
    "DOT",
    "UNI",
    "LTC",
]


class CryptoSentinelAgent(BaseAgent):
    """
    Local Crypto Sentinel agent.
    Generates structured briefs with a conservative, risk-first stance.
    """

    def __init__(self, llm_client: Optional[LLMClient] = None):
        super().__init__("CRYPTO_SENTINEL", version="0.1.0")
        self.llm = llm_client or get_llm_client()
        self.settings = get_settings()

    def get_capabilities(self) -> list:
        return ["morning_brief", "market_overview", "analyze_asset", "get_signals"]

    async def execute(self, payload: Dict[str, Any]) -> AgentResult:
        action = (payload.get("action") or "morning_brief").lower()

        if action in ("morning_brief", "market_overview"):
            return await self._action_morning_brief(payload)

        return AgentResult(success=False, error=f"Unsupported action: {action}")

    # ------------------------------------------------------------------ #
    # Actions
    # ------------------------------------------------------------------ #
    async def _action_morning_brief(self, payload: Dict[str, Any]) -> AgentResult:
        """Generate a morning brief with at least 10 assets covered."""
        assets = self._normalize_assets(payload.get("assets"))
        budget = payload.get("budget", 100)
        instruction = payload.get("original_command") or payload.get("instruction", "")

        prompt = self._build_prompt(assets, budget, instruction)

        try:
            llm_response = await self.llm.chat(
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "You are Crypto Sentinel, a cautious crypto day-trading assistant. "
                            "You do NOT have live data; work from generic, conservative heuristics. "
                            "Always prioritize capital preservation and note that prices are illustrative. "
                            "Follow the exact output structure requested. Keep it concise."
                        ),
                    },
                    {"role": "user", "content": prompt},
                ],
                temperature=0.4,
                max_tokens=900,
            )

            content = llm_response.content.strip()
            return AgentResult(
                success=True,
                data={
                    "generated_at": datetime.utcnow().isoformat(),
                    "assets": assets,
                    "message": content,
                },
            )
        except Exception as e:
            # Fallback deterministic template when LLM is unavailable
            self.logger.warning(f"LLM unavailable, using fallback brief: {e}")
            fallback_message = self._fallback_brief(assets, budget)
            return AgentResult(
                success=True,
                data={
                    "generated_at": datetime.utcnow().isoformat(),
                    "assets": assets,
                    "message": fallback_message,
                    "note": "LLM unavailable, used static fallback brief.",
                },
            )

    # ------------------------------------------------------------------ #
    # Helpers
    # ------------------------------------------------------------------ #
    def _normalize_assets(self, assets: Any) -> List[str]:
        """Ensure we have at least 10 unique, uppercased symbols."""
        normalized: List[str] = []

        if isinstance(assets, list):
            for symbol in assets:
                try:
                    sym = str(symbol).strip().upper()
                except Exception:
                    continue
                if sym and sym not in normalized:
                    normalized.append(sym)

        for symbol in DEFAULT_ASSETS:
            if len(normalized) >= 10:
                break
            if symbol not in normalized:
                normalized.append(symbol)

        # Cap to a reasonable length to avoid runaway prompts
        return normalized[: max(10, len(normalized))]

    def _build_prompt(self, assets: List[str], budget: Any, instruction: str) -> str:
        """Compose the user prompt for the LLM."""
        asset_line = ", ".join(assets)
        user_budget = budget if isinstance(budget, (int, float)) else 100

        return (
            "Create a weekday 09:00 crypto morning brief for short-term day trading.\n"
            f"Assets to consider (ensure at least 10 in recs): {asset_line}\n"
            f"Assume total budget: {user_budget} units; max 25-30% per coin.\n"
            "You lack real-time data; use conservative, hypothetical levels with clear risk management.\n"
            "Structure strictly:\n"
            "1) MARKET OVERVIEW\n"
            "- Market mood: [Bullish / Bearish / Sideways / Highly Uncertain]\n"
            "- BTC/ETH context: short directional summary\n"
            "- Notable general news: up to 3 bullets (generic, no fabrications about real companies)\n\n"
            "2) BUY RECOMMENDATIONS (3-8 coins). For each coin include:\n"
            "- COIN / ACTION BUY / ENTRY ZONE / TAKE PROFIT (2) / STOP LOSS / POSITION SIZE % / TIMEFRAME / RISK LEVEL / 1-3 bullets reasoning\n"
            "If no setups, say so clearly.\n\n"
            "3) SELL / EXIT RECOMMENDATIONS\n"
            "- If none, say: 'No immediate SELL actions required based on current information.'\n\n"
            "4) RISK & REMINDERS\n"
            "- List key risks and remind user this is not financial advice.\n\n"
            "Be concise, avoid hype, and highlight capital preservation. "
            "If instruction context was provided, align tone but keep the structure. "
            f"Original instruction (for context): {instruction or 'n/a'}"
        )

    def _fallback_brief(self, assets: List[str], budget: Any) -> str:
        """Simple deterministic fallback brief."""
        top_assets = assets[:8]
        buys = "\n".join(
            [
                f"- COIN: {sym}\n  ACTION: BUY\n  ENTRY ZONE: placeholder\n  "
                f"TAKE PROFIT: TP1/TP2 placeholder\n  STOP LOSS: tight below entry\n  "
                f"POSITION SIZE: ~10% of capital\n  TIMEFRAME: Intraday\n  "
                f"RISK LEVEL: Medium\n  REASONING: Using static fallback levels; prioritize risk management."
                for sym in top_assets
            ]
        )

        return (
            "1) MARKET OVERVIEW\n"
            "- Market mood: Highly Uncertain\n"
            "- BTC/ETH context: Use tight stops; no live data available.\n"
            "- Notable news: Data feed unavailable; operate cautiously.\n\n"
            "2) BUY RECOMMENDATIONS\n"
            f"{buys or 'No strong BUY setups today. Best action: stay in cash and wait.'}\n\n"
            "3) SELL / EXIT RECOMMENDATIONS\n"
            "No immediate SELL actions required based on current information.\n\n"
            "4) RISK & REMINDERS\n"
            "- Operating without live data; levels are illustrative only.\n"
            "- Keep position sizes small (<25-30% per coin) and use stops.\n"
            "- This is not financial advice."
        )
