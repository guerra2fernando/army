"""
Intent Parser
Extracts structured intent from natural language input.
"""
import json
from typing import Optional, Dict, Any, List
from loguru import logger
from app.config import get_settings
from app.orchestrator.prompts import INTENT_EXTRACTION_PROMPT

# Import unified LLM client from cloud API agents
from app.agents.llm_client import get_llm_client

settings = get_settings()


class IntentParser:
    """
    Parses natural language input to extract structured intent.
    """
    
    def __init__(self, llm_client = None):
        self.llm_client = llm_client or get_llm_client()
    
    async def parse(
        self,
        message: str,
        context: str = ""
    ) -> dict:
        """
        Parse a user message to extract intent.
        
        Args:
            message: User's natural language input
            context: Relevant context from RAG
            
        Returns:
            Structured intent dictionary
        """
        try:
            prompt = INTENT_EXTRACTION_PROMPT.format(
                message=message,
                context=context or "No additional context available."
            )

            messages = [
                {"role": "system", "content": "You are an intent extraction system. Return only valid JSON."},
                {"role": "user", "content": prompt}
            ]

            response = await self.llm_client.chat(
                messages=messages,
                temperature=0.1,
                max_tokens=500,
                json_response=True
            )

            result = response.json()
            if not isinstance(result, dict):
                raise ValueError("Intent parser returned non-dict result")

            result["entities"] = self._normalize_entities(result.get("entities"))
            logger.debug(f"Parsed intent: {result}")
            return result
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse intent JSON: {e}")
            return {
                "intent_category": "UNKNOWN",
                "action": None,
                "entities": {},
                "urgency": "MEDIUM",
                "requires_clarification": True,
                "clarification_question": "I didn't understand that. Could you rephrase?"
            }
        except Exception as e:
            logger.error(f"Intent parsing error: {e}")
            raise

    def _normalize_entities(self, raw_entities: Any) -> Dict[str, List[str]]:
        """Ensure entities are returned as a dict of lists."""
        if isinstance(raw_entities, dict):
            normalized: Dict[str, List[str]] = {}
            for key, value in raw_entities.items():
                if value is None:
                    continue
                if isinstance(value, list):
                    normalized[key] = value
                else:
                    normalized[key] = [value]
            return normalized

        if isinstance(raw_entities, list):
            normalized: Dict[str, List[str]] = {}
            for item in raw_entities:
                if not isinstance(item, dict):
                    continue
                entity = item.get("entity") or item.get("value")
                entity_type = item.get("type") or item.get("category") or "unknown"
                if not entity:
                    continue
                normalized.setdefault(entity_type, []).append(entity)
            return normalized

        return {}


class EntityExtractor:
    """
    Extracts specific entities from text.
    """
    
    @staticmethod
    def extract_locations(text: str) -> List[str]:
        """Extract location mentions."""
        locations = []
        location_keywords = [
            "remote", "nyc", "new york", "san francisco", "sf",
            "london", "europe", "asia", "us", "usa", "berlin",
            "tel aviv", "singapore", "tokyo", "los angeles", "la",
            "chicago", "seattle", "austin", "boston", "denver",
            "miami", "atlanta", "toronto", "vancouver"
        ]
        text_lower = text.lower()
        for loc in location_keywords:
            if loc in text_lower:
                locations.append(loc)
        return locations
    
    @staticmethod
    def extract_job_titles(text: str) -> List[str]:
        """Extract job title mentions."""
        titles = []
        title_keywords = [
            "growth lead", "head of growth", "growth manager",
            "marketing lead", "vp growth", "director of growth",
            "product manager", "engineer", "developer", "designer",
            "data scientist", "ml engineer", "devops", "sre",
            "frontend", "backend", "fullstack", "full stack",
            "cto", "vp engineering", "tech lead", "staff engineer"
        ]
        text_lower = text.lower()
        for title in title_keywords:
            if title in text_lower:
                titles.append(title)
        return titles
    
    @staticmethod
    def extract_companies(text: str) -> List[str]:
        """Extract company mentions."""
        # This would need a company database or NER
        # For now, extract common patterns like "at X" or "for X"
        companies = []
        # Placeholder - could be enhanced with NER
        return companies
    
    @staticmethod
    def extract_crypto_assets(text: str) -> List[str]:
        """Extract cryptocurrency mentions."""
        assets = []
        crypto_keywords = {
            "btc": "BTC", "bitcoin": "BTC",
            "eth": "ETH", "ethereum": "ETH",
            "sol": "SOL", "solana": "SOL",
            "avax": "AVAX", "avalanche": "AVAX",
            "bnb": "BNB", "binance": "BNB",
            "xrp": "XRP", "ripple": "XRP",
            "ada": "ADA", "cardano": "ADA",
            "doge": "DOGE", "dogecoin": "DOGE",
            "dot": "DOT", "polkadot": "DOT",
            "matic": "MATIC", "polygon": "MATIC",
            "link": "LINK", "chainlink": "LINK",
            "uni": "UNI", "uniswap": "UNI"
        }
        text_lower = text.lower()
        for keyword, symbol in crypto_keywords.items():
            if keyword in text_lower and symbol not in assets:
                assets.append(symbol)
        return assets
    
    @staticmethod
    def extract_all(text: str) -> Dict[str, List[str]]:
        """Extract all entity types from text."""
        return {
            "locations": EntityExtractor.extract_locations(text),
            "job_titles": EntityExtractor.extract_job_titles(text),
            "companies": EntityExtractor.extract_companies(text),
            "crypto_assets": EntityExtractor.extract_crypto_assets(text)
        }

