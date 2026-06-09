"""
Agent Specification Parser
Parses agent specifications from various formats.
"""
from typing import Dict, Any, List, Tuple
from loguru import logger
import json
import yaml

from agents.llm_client import get_llm_client, LLMClient
from poller.config import get_settings
from .models import AgentSpec, AgentLocation, TriggerType

settings = get_settings()


class SpecParser:
    """
    Parses agent specifications from various formats.
    Supports natural language, YAML, and dictionary inputs.
    """
    
    def __init__(self, llm_client: LLMClient = None):
        self.client = llm_client or get_llm_client()
        self.logger = logger.bind(component="spec_parser")
    
    async def parse_natural_language(self, description: str) -> AgentSpec:
        """
        Parse a natural language description into an agent spec.
        
        Args:
            description: Natural language description of the agent
            
        Returns:
            Structured AgentSpec
        """
        self.logger.info("Parsing natural language spec...")
        
        prompt = f"""Convert this agent description into a structured specification.

**Description:**
{description}

Return a JSON object with this structure:
{{
    "name": "AgentName (PascalCase, no spaces, alphanumeric with underscores only)",
    "version": "1.0.0",
    "description": "One line description",
    "purpose": "What problem does this agent solve?",
    
    "location": "CLOUD or LOCAL",
    "trigger_type": "CRON|TASK_QUEUE|EVENT|MANUAL",
    "trigger_config": {{"cron": "0 8 * * *"}} or null,
    
    "inputs": [
        {{"name": "input_name", "type": "string|number|object", "description": "What is this input?"}}
    ],
    "outputs": [
        {{"name": "output_name", "type": "string|object", "description": "What does this output?"}}
    ],
    
    "capabilities": ["capability1", "capability2"],
    "dependencies": ["package1", "package2"],
    
    "actions": [
        {{
            "name": "action_name",
            "description": "What does this action do?",
            "parameters": [{{"name": "param", "type": "string", "required": true}}],
            "returns": "Description of return value"
        }}
    ],
    
    "system_prompt": "System prompt for the agent if it uses LLM"
}}

Be specific and practical. Use sensible defaults. Agent name must be alphanumeric with underscores only (e.g., WeatherAgent, DataProcessor)."""

        response = await self.client.chat(
            messages=[
                {"role": "system", "content": "You are an expert software architect. Return valid JSON only."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.5,
            json_response=True
        )
        
        result = response.json()
        
        return AgentSpec(
            name=result["name"],
            version=result.get("version", "1.0.0"),
            description=result["description"],
            purpose=result["purpose"],
            location=AgentLocation(result["location"]),
            trigger_type=TriggerType(result["trigger_type"]),
            trigger_config=result.get("trigger_config"),
            inputs=result.get("inputs", []),
            outputs=result.get("outputs", []),
            capabilities=result.get("capabilities", []),
            dependencies=result.get("dependencies", []),
            actions=result.get("actions", []),
            system_prompt=result.get("system_prompt")
        )
    
    def parse_yaml(self, yaml_content: str) -> AgentSpec:
        """
        Parse a YAML specification.
        
        Args:
            yaml_content: YAML string containing agent spec
            
        Returns:
            Parsed AgentSpec
        """
        self.logger.info("Parsing YAML spec...")
        data = yaml.safe_load(yaml_content)
        return self.parse_dict(data)
    
    def parse_dict(self, spec_dict: Dict[str, Any]) -> AgentSpec:
        """
        Parse a dictionary specification.
        
        Args:
            spec_dict: Dictionary containing agent spec
            
        Returns:
            Parsed AgentSpec
        """
        self.logger.info("Parsing dict spec...")
        
        # Handle enum conversions
        location = spec_dict.get("location", "LOCAL")
        if isinstance(location, str):
            location = AgentLocation(location)
        
        trigger_type = spec_dict.get("trigger_type", "MANUAL")
        if isinstance(trigger_type, str):
            trigger_type = TriggerType(trigger_type)
        
        return AgentSpec(
            name=spec_dict["name"],
            version=spec_dict.get("version", "1.0.0"),
            description=spec_dict["description"],
            purpose=spec_dict["purpose"],
            location=location,
            trigger_type=trigger_type,
            trigger_config=spec_dict.get("trigger_config"),
            inputs=spec_dict.get("inputs", []),
            outputs=spec_dict.get("outputs", []),
            capabilities=spec_dict.get("capabilities", []),
            dependencies=spec_dict.get("dependencies", []),
            actions=spec_dict.get("actions", []),
            system_prompt=spec_dict.get("system_prompt")
        )
    
    def validate_spec(self, spec: AgentSpec) -> Tuple[bool, List[str]]:
        """
        Validate an agent specification.
        
        Args:
            spec: Agent specification to validate
            
        Returns:
            Tuple of (is_valid, list_of_errors)
        """
        errors = []
        
        # Name validation - must be alphanumeric with underscores
        if not spec.name:
            errors.append("Agent name is required")
        elif not spec.name.replace("_", "").isalnum():
            errors.append("Invalid agent name - must be alphanumeric with underscores only")
        elif " " in spec.name:
            errors.append("Invalid agent name - must not contain spaces")
        
        # Must have at least one capability
        if not spec.capabilities:
            errors.append("Agent must have at least one capability")
        
        # Must have at least one action
        if not spec.actions:
            errors.append("Agent must have at least one action")
        
        # Validate actions
        for i, action in enumerate(spec.actions):
            if not action.get("name"):
                errors.append(f"Action at index {i} must have a name")
        
        # Cloud agents shouldn't need browser automation
        if spec.location == AgentLocation.CLOUD:
            browser_deps = ["playwright", "selenium", "puppeteer", "pyppeteer"]
            for dep in spec.dependencies:
                if dep.lower() in browser_deps:
                    errors.append(f"Cloud agents cannot use browser automation ({dep})")
        
        is_valid = len(errors) == 0
        
        if is_valid:
            self.logger.info("Spec validation passed")
        else:
            self.logger.warning(f"Spec validation failed: {errors}")
        
        return is_valid, errors

