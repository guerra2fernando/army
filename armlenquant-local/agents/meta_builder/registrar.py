"""
Agent Registrar
Handles saving agent files and registration with the cloud.
"""
from pathlib import Path
from typing import Optional, List, TYPE_CHECKING
from loguru import logger

from poller.config import get_settings
from poller.api_client import CloudAPIClient

if TYPE_CHECKING:
    from .models import AgentSpec, GeneratedCode

settings = get_settings()


class AgentRegistrar:
    """
    Registers new agents with the ArmLenQuant system.
    Handles file creation and cloud registration.
    """
    
    def __init__(self):
        self.logger = logger.bind(component="registrar")
        self.api_url = settings.api_url
    
    async def register_agent(self, spec: 'AgentSpec') -> Optional[str]:
        """
        Register an agent with the cloud API.
        
        Args:
            spec: Agent specification
            
        Returns:
            Agent ID if successful, None otherwise
        """
        self.logger.info(f"Registering agent: {spec.name}")

        client = CloudAPIClient()
        try:
            response = await client.register_agent(
                agent_name=spec.name.upper(),
                version=spec.version,
                location=spec.location.value,
                trigger_type=spec.trigger_type.value,
                capabilities=spec.capabilities,
                trigger_config=spec.trigger_config,
            )
            await client.close()
            if response:
                agent_id = response.get("agent_id")
                self.logger.info(f"Agent registered: {agent_id}")
                return agent_id
            self.logger.error("Registration failed: no response from cloud")
            return None
        except Exception as e:
            await client.close()
            self.logger.error(f"Registration error: {e}")
            return None
    
    def save_agent_files(
        self,
        spec: 'AgentSpec',
        code: 'GeneratedCode',
        base_path: Path
    ) -> List[str]:
        """
        Save generated agent files to disk.
        
        Args:
            spec: Agent specification
            code: Generated code
            base_path: Base path for agents
            
        Returns:
            List of created file paths
        """
        # Create agent directory (lowercase)
        agent_name_lower = spec.name.lower()
        agent_dir = base_path / agent_name_lower
        agent_dir.mkdir(parents=True, exist_ok=True)
        
        created_files = []
        
        # Save main agent file
        agent_path = agent_dir / "agent.py"
        agent_path.write_text(code.agent_file, encoding="utf-8")
        created_files.append(str(agent_path))
        self.logger.debug(f"Created: {agent_path}")
        
        # Save __init__.py
        init_path = agent_dir / "__init__.py"
        init_path.write_text(code.init_file, encoding="utf-8")
        created_files.append(str(init_path))
        self.logger.debug(f"Created: {init_path}")
        
        # Save models if present
        if code.models_file:
            models_path = agent_dir / "models.py"
            models_path.write_text(code.models_file, encoding="utf-8")
            created_files.append(str(models_path))
            self.logger.debug(f"Created: {models_path}")
        
        # Save documentation
        doc_path = agent_dir / f"AGENT_{spec.name.upper()}.md"
        doc_path.write_text(code.documentation, encoding="utf-8")
        created_files.append(str(doc_path))
        self.logger.debug(f"Created: {doc_path}")
        
        # Save tests
        if code.test_file:
            tests_dir = agent_dir / "tests"
            tests_dir.mkdir(exist_ok=True)
            test_path = tests_dir / f"test_{agent_name_lower}.py"
            test_path.write_text(code.test_file, encoding="utf-8")
            created_files.append(str(test_path))
            self.logger.debug(f"Created: {test_path}")
        
        self.logger.info(f"Saved {len(created_files)} files to {agent_dir}")
        
        return created_files
    
    def update_poller_imports(
        self,
        spec: 'AgentSpec',
        poller_path: Path
    ) -> None:
        """
        Log instructions for updating the main poller to import the new agent.
        
        Note: This doesn't automatically modify files for safety reasons.
        Instead, it logs what needs to be done manually.
        
        Args:
            spec: Agent specification
            poller_path: Path to poller directory
        """
        self.logger.info(
            f"Manual step required: Add import for {spec.name}Agent "
            f"in poller/main.py and register in task_router"
        )
        
        # Log the specific changes needed
        self.logger.info(f"""
To integrate {spec.name}Agent:

1. Add to poller/task_router.py:
   from agents.{spec.name.lower()}.agent import {spec.name}Agent
   
   And in the agent_map:
   "{spec.name.upper()}": {spec.name}Agent()

2. Update config/settings if needed for any agent-specific config.
""")

