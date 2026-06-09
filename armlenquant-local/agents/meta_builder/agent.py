"""
Meta Builder Agent
Creates new agents for the ArmLenQuant system.

The self-evolution engine that generates new agents from specifications.
"""
from typing import Dict, Any
from pathlib import Path
from loguru import logger

from agents.base_agent import BaseAgent, AgentResult
from models.capability import CapabilityGrant, CapabilityPolicy, CapabilityLimits
from poller.config import get_settings
from .spec_parser import SpecParser
from .code_generator import CodeGenerator
from .registrar import AgentRegistrar
from .models import AgentBuildResult

settings = get_settings()


class MetaBuilderAgent(BaseAgent):
    """
    Meta Builder - The Self-Evolution Agent
    
    Creates new agents based on specifications.
    Supports natural language, YAML, and structured specs.
    """
    
    def __init__(self):
        self.agents_path = Path(settings.base_path) / "agents"
        super().__init__("META_BUILDER", version="2.0.0")
        self.spec_parser = SpecParser()
        self.code_generator = CodeGenerator()
        self.registrar = AgentRegistrar()

    def get_capability_grants(self) -> list[CapabilityGrant]:
        """Capability allowlist for agent generation."""
        agents_root = str(self.agents_path)
        tests_root = str(Path(settings.base_path) / "tests")
        return [
            CapabilityGrant(
                capability_id="file_write",
                policy_override=CapabilityPolicy(
                    allowed_paths=[
                        agents_root,
                        f"{agents_root}/**",
                        tests_root,
                        f"{tests_root}/**",
                    ],
                    max_file_size_mb=50,
                ),
                limits_override=CapabilityLimits(daily_quota=200),
            ),
            CapabilityGrant(
                capability_id="file_modify",
                policy_override=CapabilityPolicy(
                    allowed_paths=[str(Path(settings.base_path) / "poller/**")]
                ),
            ),
        ]
    
    async def execute(self, payload: Dict[str, Any]) -> AgentResult:
        """Execute Meta Builder task."""
        action = payload.get("action", "build")
        
        self.logger.info(f"Executing action: {action}")
        
        try:
            if action == "build":
                return await self._action_build(payload)
            elif action == "validate":
                return await self._action_validate(payload)
            elif action == "generate_spec":
                return await self._action_generate_spec(payload)
            else:
                return AgentResult(
                    success=False,
                    error=f"Unknown action: {action}"
                )
        except Exception as e:
            self.logger.error(f"Action {action} failed: {e}")
            return AgentResult(success=False, error=str(e))
    
    async def _action_build(self, payload: Dict[str, Any]) -> AgentResult:
        """
        Build a new agent from specification.
        
        Payload:
            description: str - Natural language description (optional)
            spec: dict - Structured specification (optional)
            
        One of description or spec is required.
        """
        description = payload.get("description")
        spec_dict = payload.get("spec")
        
        # Parse specification
        if description:
            self.logger.info("Parsing natural language description...")
            spec = await self.spec_parser.parse_natural_language(description)
        elif spec_dict:
            self.logger.info("Parsing spec dictionary...")
            spec = self.spec_parser.parse_dict(spec_dict)
        else:
            return AgentResult(
                success=False,
                error="No description or spec provided"
            )
        
        # Validate specification
        self.logger.info("Validating specification...")
        is_valid, errors = self.spec_parser.validate_spec(spec)
        
        if not is_valid:
            return AgentResult(
                success=False,
                error=f"Invalid specification: {', '.join(errors)}"
            )
        
        # Generate code
        self.logger.info("Generating agent code...")
        code = self.code_generator.generate(spec)
        
        # Save files
        self.logger.info("Saving agent files...")
        created_files = self.registrar.save_agent_files(
            spec, code, self.agents_path
        )
        
        # Register with cloud (optional - may fail if cloud not available)
        self.logger.info("Registering agent with cloud...")
        registration_id = await self.registrar.register_agent(spec)
        
        # Update poller (manual step notification)
        self.registrar.update_poller_imports(spec, self.agents_path.parent / "poller")
        
        result = AgentBuildResult(
            success=True,
            agent_name=spec.name,
            agent_path=str(self.agents_path / spec.name.lower()),
            files_created=created_files,
            validation_passed=True,
            registration_id=registration_id,
            warnings=[] if registration_id else ["Agent not registered with cloud"]
        )
        
        self.logger.info(f"Agent {spec.name} built successfully!")
        
        return AgentResult(
            success=True,
            data=result.model_dump()
        )
    
    async def _action_validate(self, payload: Dict[str, Any]) -> AgentResult:
        """
        Validate an agent specification without building.
        
        Payload:
            description: str - Natural language description (optional)
            spec: dict - Structured specification (optional)
        """
        description = payload.get("description")
        spec_dict = payload.get("spec")
        
        if description:
            spec = await self.spec_parser.parse_natural_language(description)
        elif spec_dict:
            spec = self.spec_parser.parse_dict(spec_dict)
        else:
            return AgentResult(
                success=False,
                error="No description or spec provided"
            )
        
        is_valid, errors = self.spec_parser.validate_spec(spec)
        
        return AgentResult(
            success=True,
            data={
                "valid": is_valid,
                "errors": errors,
                "spec": spec.model_dump()
            }
        )
    
    async def _action_generate_spec(self, payload: Dict[str, Any]) -> AgentResult:
        """
        Generate a spec from natural language without building.
        
        Payload:
            description: str - Natural language description of the agent
        """
        description = payload.get("description", "")
        
        if not description:
            return AgentResult(
                success=False,
                error="No description provided"
            )
        
        spec = await self.spec_parser.parse_natural_language(description)
        
        return AgentResult(
            success=True,
            data={"spec": spec.model_dump()}
        )
    
    def get_capabilities(self) -> list:
        """Get list of agent capabilities."""
        return [
            "agent_specification",
            "code_generation",
            "agent_registration",
            "spec_validation",
            "documentation_generation"
        ]
