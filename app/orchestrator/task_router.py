"""
Task Router
Routes parsed intents to appropriate agents.
"""
from typing import Optional, Dict, Any, List
from loguru import logger


class TaskRouter:
    """
    Routes tasks to appropriate agents based on intent.
    """
    
    # Mapping of intent categories to agents
    INTENT_TO_AGENT: Dict[str, Optional[str]] = {
        "CRYPTO": "CRYPTO_SENTINEL",
        "JOBS": "JOB_HUNTER",
        "COMMERCIAL_OPS": "COMMERCIAL_SCOUT",
        "PROJECTS": "IDEAS_MACHINE",
        "SYSTEM": None,  # Handled internally
        "META": "META_BUILDER",
        "UNKNOWN": None,
    }
    
    # Agent capabilities and actions
    AGENT_ACTIONS: Dict[str, List[str]] = {
        "CRYPTO_SENTINEL": [
            "morning_brief",
            "analyze_asset",
            "get_signals",
            "market_overview",
            "portfolio_check"
        ],
        "JOB_HUNTER": [
            "search_jobs",
            "generate_resume",
            "generate_cover_letter",
            "research_company",
            "track_application"
        ],
        "COMMERCIAL_SCOUT": [
            "discover_leads",
            "draft_outreach",
        ],
        "IDEAS_MACHINE": [
            "analyze",
            "scaffold",
            "generate",  # NEW: Complete project generation
            "recommend_stack",
            "generate_docs"
        ],
        "META_BUILDER": [
            "create_agent",
            "modify_agent",
            "generate_code"
        ]
    }

    DEFAULT_CRYPTO_ASSETS: List[str] = [
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
    
    def route(self, intent: dict, original_message: str = "") -> Dict[str, Any]:
        """
        Route an intent to the appropriate agent and action.
        
        Args:
            intent: Parsed intent dictionary
            
        Returns:
            Routing decision with agent, action, and parameters
        """
        category = intent.get("intent_category", "UNKNOWN")
        action = intent.get("action")
        entities = intent.get("entities", {})
        
        # Determine target agent
        target_agent = self.INTENT_TO_AGENT.get(category)
        
        if not target_agent:
            if category == "SYSTEM":
                return self._handle_system_query(intent)
            return {
                "target_agent": None,
                "action": None,
                "parameters": {},
                "error": f"Cannot route intent category: {category}"
            }
        
        # Map action to agent-specific action
        agent_action = self._map_action(target_agent, action, entities)
        
        # Build parameters
        parameters = self._build_parameters(target_agent, agent_action, entities, intent, original_message)

        # Debug logging for PROJECTS intents
        if category == "PROJECTS":
            logger.info(f"PROJECTS routing - intent: {intent}")
            logger.info(f"PROJECTS routing - entities: {entities}")
            logger.info(f"PROJECTS routing - original: '{original_message}'")
            logger.info(f"PROJECTS routing - final params: {parameters}")
        
        logger.info(f"Routed to {target_agent}.{agent_action}")
        
        return {
            "target_agent": target_agent,
            "action": agent_action,
            "parameters": parameters,
            "confidence": self._calculate_confidence(intent, target_agent, agent_action)
        }
    
    def _map_action(
        self,
        agent: str,
        action: Optional[str],
        entities: dict
    ) -> str:
        """Map a general action to an agent-specific action."""
        
        # Default actions per agent
        defaults = {
            "CRYPTO_SENTINEL": "morning_brief",
            "JOB_HUNTER": "search_jobs",
            "COMMERCIAL_SCOUT": "discover_leads",
            "IDEAS_MACHINE": "analyze",
            "META_BUILDER": "create_agent"
        }
        
        if not action:
            return defaults.get(agent, "unknown")
        
        # Try to match action to agent capabilities
        available_actions = self.AGENT_ACTIONS.get(agent, [])
        
        # Exact match
        if action in available_actions:
            return action
        
        # Fuzzy matching
        action_lower = action.lower()
        for available in available_actions:
            if action_lower in available or available in action_lower:
                return available
        
        # Keywords matching
        if agent == "JOB_HUNTER":
            if any(kw in action_lower for kw in ["search", "find", "look"]):
                return "search_jobs"
            if any(kw in action_lower for kw in ["resume", "cv"]):
                return "generate_resume"
            if any(kw in action_lower for kw in ["cover", "letter"]):
                return "generate_cover_letter"
            if any(kw in action_lower for kw in ["company", "research"]):
                return "research_company"
        
        elif agent == "CRYPTO_SENTINEL":
            if any(kw in action_lower for kw in ["brief", "overview", "summary"]):
                return "morning_brief"
            if any(kw in action_lower for kw in ["analyze", "check", "look"]):
                return "analyze_asset"
            if any(kw in action_lower for kw in ["signal", "trade"]):
                return "get_signals"
        
        elif agent == "COMMERCIAL_SCOUT":
            if any(kw in action_lower for kw in ["draft", "message", "outreach"]):
                return "draft_outreach"
            if any(kw in action_lower for kw in ["lead", "discover", "find", "search"]):
                return "discover_leads"

        elif agent == "IDEAS_MACHINE":
            # Route to "generate" for complete project creation requests
            if any(kw in action_lower for kw in ["build", "create", "develop", "make", "generate", "project"]):
                return "generate"
            # Keep "scaffold" for legacy/basic scaffolding
            if any(kw in action_lower for kw in ["scaffold", "start", "basic", "simple"]):
                return "scaffold"
            if any(kw in action_lower for kw in ["analyze", "review", "evaluate"]):
                return "analyze"
            if any(kw in action_lower for kw in ["stack", "tech", "recommend"]):
                return "recommend_stack"
        
        elif agent == "META_BUILDER":
            if any(kw in action_lower for kw in ["create", "new", "build"]):
                return "create_agent"
            if any(kw in action_lower for kw in ["modify", "update", "change"]):
                return "modify_agent"
        
        return defaults.get(agent, action)
    
    def _build_parameters(
        self,
        agent: str,
        action: str,
        entities: dict,
        intent: dict,
        original_message: str = ""
    ) -> dict:
        """Build parameters for the agent task."""
        
        params = {"action": action}
        
        if agent == "JOB_HUNTER":
            if entities.get("locations"):
                params["locations"] = entities["locations"]
            if entities.get("job_titles"):
                params["roles"] = entities["job_titles"]
            if entities.get("companies"):
                params["companies"] = entities["companies"]
        
        elif agent == "CRYPTO_SENTINEL":
            assets = entities.get("crypto_assets") or []
            normalized: List[str] = []

            for symbol in assets:
                try:
                    sym = str(symbol).strip().upper()
                except Exception:
                    continue
                if sym and sym not in normalized:
                    normalized.append(sym)

            for symbol in self.DEFAULT_CRYPTO_ASSETS:
                if len(normalized) >= 10:
                    break
                if symbol not in normalized:
                    normalized.append(symbol)

            params["assets"] = normalized[: max(10, len(normalized))]
        
        elif agent == "IDEAS_MACHINE":
            logger.info(f"Building IDEAS_MACHINE params - action: {action}, intent: {intent.get('intent_category')}, entities: {entities}, original: '{original_message}'")

            if entities.get("project_name"):
                params["project_name"] = entities["project_name"]

            # Extract project description with multiple fallbacks
            description = None

            # Try entities first
            if entities.get("project_description"):
                desc_list = entities["project_description"]
                if isinstance(desc_list, list) and desc_list:
                    description = desc_list[0]
                else:
                    description = str(desc_list)
                logger.info(f"Found project_description in entities: '{description}'")

            # Fallback to original message for PROJECTS category
            if not description and intent.get("intent_category") == "PROJECTS" and original_message:
                # Remove common prefixes and extract the core description
                import re
                cleaned = re.sub(r'^(create\s+a\s+project|scaffold|build|make|generate|develop)\s+(for|about|a|an)?\s*', '', original_message, flags=re.IGNORECASE).strip()
                if cleaned and len(cleaned) > 3:  # Very low threshold
                    description = cleaned
                    logger.info(f"Extracted description from cleaned message: '{description}'")
                else:
                    # Use the full original message
                    description = original_message.strip()
                    logger.info(f"Using full original message: '{description}'")

            # Ensure we always have a description for PROJECTS
            if not description and intent.get("intent_category") == "PROJECTS":
                description = original_message.strip() if original_message else "Create a new software project"
                logger.warning(f"Using PROJECTS fallback description: '{description}'")

            # Final fallback: Always ensure we have a description for IDEAS_MACHINE
            if not description and original_message:
                description = original_message.strip()
                logger.info(f"Using IDEAS_MACHINE final fallback: '{description[:100]}...'")

            if description:
                params["description"] = description
                logger.info(f"Final project description set: '{description[:100]}...'")
            else:
                # Absolute last resort
                params["description"] = "Create a software project"
                logger.error("No description available for IDEAS_MACHINE task - using generic fallback")

            # For "generate" action, enable full project generation
            if action == "generate":
                params["execute_phases"] = True
                logger.info("Enabled execute_phases for generate action")

        elif agent == "COMMERCIAL_SCOUT":
            business_slug = entities.get("business_slug") or entities.get("product_slug")
            if not business_slug and original_message:
                lowered = original_message.lower()
                for slug in ["lenquant", "lenxys", "services", "trading"]:
                    if slug in lowered:
                        business_slug = slug
                        params["lane"] = slug.upper()
                        break
            if business_slug:
                params["business_slug"] = business_slug
            if entities.get("companies"):
                params["keywords"] = entities["companies"]
            if entities.get("locations"):
                params["locations"] = entities["locations"]
        
        return params
    
    def _calculate_confidence(
        self,
        intent: dict,
        agent: str,
        action: str
    ) -> float:
        """Calculate routing confidence score."""
        
        base_confidence = 0.7
        
        # Increase if action explicitly matched
        if intent.get("action") and action != "unknown":
            base_confidence += 0.15
        
        # Increase if entities found
        if intent.get("entities"):
            entity_count = sum(
                len(v) if isinstance(v, list) else 1
                for v in intent["entities"].values()
                if v
            )
            if entity_count > 0:
                base_confidence += min(0.1, entity_count * 0.03)
        
        # Decrease if clarification needed
        if intent.get("requires_clarification"):
            base_confidence -= 0.2
        
        return min(max(base_confidence, 0.0), 1.0)
    
    def _handle_system_query(self, intent: dict) -> dict:
        """Handle system-level queries internally."""
        action = (intent.get("action") or "").lower()
        
        if any(kw in action for kw in ["status", "health", "check"]):
            return {
                "target_agent": None,
                "action": "system_status",
                "parameters": {},
                "internal": True
            }
        
        if any(kw in action for kw in ["help", "what can", "capabilities", "what do"]):
            return {
                "target_agent": None,
                "action": "show_capabilities",
                "parameters": {},
                "internal": True
            }
        
        if any(kw in action for kw in ["agents", "list agents"]):
            return {
                "target_agent": None,
                "action": "list_agents",
                "parameters": {},
                "internal": True
            }
        
        return {
            "target_agent": None,
            "action": "unknown_system",
            "parameters": {},
            "internal": True
        }

