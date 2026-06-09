"""
Meta Builder Agent Tests
Comprehensive tests for the Meta Builder agent components.
"""
import pytest
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch
from pathlib import Path
import json
import tempfile
import shutil


# ============================================================================
# MODEL TESTS
# ============================================================================

class TestMetaBuilderModels:
    """Tests for Meta Builder data models."""
    
    def test_agent_location_enum(self):
        """Test AgentLocation enum values."""
        from agents.meta_builder.models import AgentLocation
        
        assert AgentLocation.CLOUD == "CLOUD"
        assert AgentLocation.LOCAL == "LOCAL"
    
    def test_trigger_type_enum(self):
        """Test TriggerType enum values."""
        from agents.meta_builder.models import TriggerType
        
        assert TriggerType.CRON == "CRON"
        assert TriggerType.TASK_QUEUE == "TASK_QUEUE"
        assert TriggerType.EVENT == "EVENT"
        assert TriggerType.MANUAL == "MANUAL"
    
    def test_agent_spec_creation(self):
        """Test AgentSpec model creation."""
        from agents.meta_builder.models import AgentSpec, AgentLocation, TriggerType
        
        spec = AgentSpec(
            name="TestAgent",
            version="1.0.0",
            description="A test agent for testing",
            purpose="To test agent creation",
            location=AgentLocation.LOCAL,
            trigger_type=TriggerType.TASK_QUEUE,
            inputs=[{"name": "query", "type": "string", "description": "Search query"}],
            outputs=[{"name": "results", "type": "list", "description": "Search results"}],
            capabilities=["search", "analyze"],
            dependencies=["httpx", "beautifulsoup4"],
            actions=[{"name": "search", "description": "Search for items", "parameters": [], "returns": "list"}],
            system_prompt="You are a helpful agent."
        )
        
        assert spec.name == "TestAgent"
        assert spec.version == "1.0.0"
        assert spec.location == AgentLocation.LOCAL
        assert spec.trigger_type == TriggerType.TASK_QUEUE
        assert len(spec.capabilities) == 2
        assert len(spec.actions) == 1
    
    def test_agent_spec_defaults(self):
        """Test AgentSpec default values."""
        from agents.meta_builder.models import AgentSpec, AgentLocation, TriggerType
        
        spec = AgentSpec(
            name="MinimalAgent",
            description="Minimal agent",
            purpose="Basic purpose",
            location=AgentLocation.LOCAL,
            trigger_type=TriggerType.MANUAL
        )
        
        assert spec.version == "1.0.0"
        assert spec.inputs == []
        assert spec.outputs == []
        assert spec.capabilities == []
        assert spec.dependencies == []
        assert spec.actions == []
        assert spec.trigger_config is None
        assert spec.system_prompt is None
    
    def test_generated_code_creation(self):
        """Test GeneratedCode model creation."""
        from agents.meta_builder.models import GeneratedCode
        
        code = GeneratedCode(
            agent_file="class TestAgent(BaseAgent): pass",
            models_file="from pydantic import BaseModel",
            routes_file="from fastapi import APIRouter",
            init_file="from .agent import TestAgent",
            documentation="# TestAgent\n\nAgent documentation",
            test_file="def test_agent(): pass"
        )
        
        assert "TestAgent" in code.agent_file
        assert code.models_file is not None
        assert code.routes_file is not None
        assert "TestAgent" in code.init_file
    
    def test_generated_code_minimal(self):
        """Test GeneratedCode with minimal fields."""
        from agents.meta_builder.models import GeneratedCode
        
        code = GeneratedCode(
            agent_file="class Agent: pass",
            init_file="from .agent import Agent",
            documentation="# Agent docs"
        )
        
        assert code.agent_file is not None
        assert code.models_file is None
        assert code.routes_file is None
        assert code.test_file is None
    
    def test_agent_build_result_success(self):
        """Test AgentBuildResult for success case."""
        from agents.meta_builder.models import AgentBuildResult
        
        result = AgentBuildResult(
            success=True,
            agent_name="TestAgent",
            agent_path="/path/to/agent",
            files_created=["agent.py", "__init__.py", "models.py"],
            validation_passed=True,
            registration_id="agent-123-456",
            errors=[],
            warnings=[]
        )
        
        assert result.success is True
        assert result.agent_name == "TestAgent"
        assert len(result.files_created) == 3
        assert result.registration_id == "agent-123-456"
    
    def test_agent_build_result_failure(self):
        """Test AgentBuildResult for failure case."""
        from agents.meta_builder.models import AgentBuildResult
        
        result = AgentBuildResult(
            success=False,
            agent_name="FailedAgent",
            agent_path="",
            files_created=[],
            validation_passed=False,
            errors=["Invalid agent name", "Missing capabilities"],
            warnings=["No system prompt provided"]
        )
        
        assert result.success is False
        assert len(result.errors) == 2
        assert len(result.warnings) == 1
        assert result.registration_id is None
    
    def test_validation_result_creation(self):
        """Test ValidationResult model creation."""
        from agents.meta_builder.models import ValidationResult
        
        result = ValidationResult(
            is_valid=True,
            errors=[],
            warnings=["Consider adding more capabilities"],
            spec_summary={"name": "TestAgent", "capabilities_count": 2}
        )
        
        assert result.is_valid is True
        assert len(result.errors) == 0
        assert len(result.warnings) == 1


# ============================================================================
# SPEC PARSER TESTS
# ============================================================================

class TestSpecParser:
    """Tests for SpecParser component."""
    
    def test_spec_parser_initialization(self):
        """Test SpecParser initialization."""
        from agents.meta_builder.spec_parser import SpecParser
        
        parser = SpecParser()
        
        assert parser.client is not None
    
    def test_parse_dict_basic(self):
        """Test parsing specification from dictionary."""
        from agents.meta_builder.spec_parser import SpecParser
        from agents.meta_builder.models import AgentSpec, AgentLocation, TriggerType
        
        parser = SpecParser()
        
        spec_dict = {
            "name": "TestAgent",
            "description": "A test agent",
            "purpose": "Testing",
            "location": "LOCAL",
            "trigger_type": "TASK_QUEUE",
            "capabilities": ["test"],
            "actions": [{"name": "test_action", "description": "Test action"}]
        }
        
        spec = parser.parse_dict(spec_dict)
        
        assert isinstance(spec, AgentSpec)
        assert spec.name == "TestAgent"
        assert spec.location == AgentLocation.LOCAL
        assert spec.trigger_type == TriggerType.TASK_QUEUE
    
    def test_parse_dict_with_all_fields(self):
        """Test parsing full specification from dictionary."""
        from agents.meta_builder.spec_parser import SpecParser
        
        parser = SpecParser()
        
        spec_dict = {
            "name": "FullAgent",
            "version": "2.0.0",
            "description": "Full specification agent",
            "purpose": "Complete testing",
            "location": "CLOUD",
            "trigger_type": "CRON",
            "trigger_config": {"cron": "0 8 * * *"},
            "inputs": [{"name": "data", "type": "object", "description": "Input data"}],
            "outputs": [{"name": "result", "type": "string", "description": "Output result"}],
            "capabilities": ["process", "analyze", "report"],
            "dependencies": ["pandas", "numpy"],
            "actions": [
                {"name": "process", "description": "Process data", "parameters": [], "returns": "dict"},
                {"name": "analyze", "description": "Analyze data", "parameters": [], "returns": "dict"}
            ],
            "system_prompt": "You analyze data."
        }
        
        spec = parser.parse_dict(spec_dict)
        
        assert spec.version == "2.0.0"
        assert spec.trigger_config == {"cron": "0 8 * * *"}
        assert len(spec.inputs) == 1
        assert len(spec.outputs) == 1
        assert len(spec.actions) == 2
    
    def test_parse_yaml_basic(self):
        """Test parsing specification from YAML string."""
        from agents.meta_builder.spec_parser import SpecParser
        
        parser = SpecParser()
        
        yaml_content = """
name: YamlAgent
description: An agent from YAML
purpose: YAML parsing test
location: LOCAL
trigger_type: MANUAL
capabilities:
  - yaml_parsing
actions:
  - name: parse
    description: Parse YAML
"""
        
        spec = parser.parse_yaml(yaml_content)
        
        assert spec.name == "YamlAgent"
        assert "yaml_parsing" in spec.capabilities
    
    def test_validate_spec_valid(self):
        """Test validation of a valid specification."""
        from agents.meta_builder.spec_parser import SpecParser
        from agents.meta_builder.models import AgentSpec, AgentLocation, TriggerType
        
        parser = SpecParser()
        
        spec = AgentSpec(
            name="ValidAgent",
            description="Valid agent",
            purpose="Testing validation",
            location=AgentLocation.LOCAL,
            trigger_type=TriggerType.TASK_QUEUE,
            capabilities=["test"],
            actions=[{"name": "test", "description": "Test action"}]
        )
        
        is_valid, errors = parser.validate_spec(spec)
        
        assert is_valid is True
        assert len(errors) == 0
    
    def test_validate_spec_invalid_name(self):
        """Test validation fails for invalid agent name."""
        from agents.meta_builder.spec_parser import SpecParser
        from agents.meta_builder.models import AgentSpec, AgentLocation, TriggerType
        
        parser = SpecParser()
        
        spec = AgentSpec(
            name="Invalid Agent Name!",  # Invalid - has spaces and special chars
            description="Agent",
            purpose="Testing",
            location=AgentLocation.LOCAL,
            trigger_type=TriggerType.MANUAL,
            capabilities=["test"],
            actions=[{"name": "test", "description": "Test"}]
        )
        
        is_valid, errors = parser.validate_spec(spec)
        
        assert is_valid is False
        assert any("name" in e.lower() for e in errors)
    
    def test_validate_spec_no_capabilities(self):
        """Test validation fails when no capabilities provided."""
        from agents.meta_builder.spec_parser import SpecParser
        from agents.meta_builder.models import AgentSpec, AgentLocation, TriggerType
        
        parser = SpecParser()
        
        spec = AgentSpec(
            name="NoCapAgent",
            description="Agent",
            purpose="Testing",
            location=AgentLocation.LOCAL,
            trigger_type=TriggerType.MANUAL,
            capabilities=[],  # No capabilities
            actions=[{"name": "test", "description": "Test"}]
        )
        
        is_valid, errors = parser.validate_spec(spec)
        
        assert is_valid is False
        assert any("capability" in e.lower() for e in errors)
    
    def test_validate_spec_no_actions(self):
        """Test validation fails when no actions provided."""
        from agents.meta_builder.spec_parser import SpecParser
        from agents.meta_builder.models import AgentSpec, AgentLocation, TriggerType
        
        parser = SpecParser()
        
        spec = AgentSpec(
            name="NoActionAgent",
            description="Agent",
            purpose="Testing",
            location=AgentLocation.LOCAL,
            trigger_type=TriggerType.MANUAL,
            capabilities=["test"],
            actions=[]  # No actions
        )
        
        is_valid, errors = parser.validate_spec(spec)
        
        assert is_valid is False
        assert any("action" in e.lower() for e in errors)
    
    def test_validate_spec_cloud_with_browser(self):
        """Test validation warns about browser deps for cloud agents."""
        from agents.meta_builder.spec_parser import SpecParser
        from agents.meta_builder.models import AgentSpec, AgentLocation, TriggerType
        
        parser = SpecParser()
        
        spec = AgentSpec(
            name="CloudBrowserAgent",
            description="Agent",
            purpose="Testing",
            location=AgentLocation.CLOUD,  # Cloud agent
            trigger_type=TriggerType.CRON,
            capabilities=["scrape"],
            dependencies=["playwright"],  # Browser automation - not allowed in cloud
            actions=[{"name": "scrape", "description": "Scrape web"}]
        )
        
        is_valid, errors = parser.validate_spec(spec)
        
        assert is_valid is False
        assert any("browser" in e.lower() for e in errors)
    
    def test_validate_spec_actions_without_name(self):
        """Test validation fails when actions lack names."""
        from agents.meta_builder.spec_parser import SpecParser
        from agents.meta_builder.models import AgentSpec, AgentLocation, TriggerType
        
        parser = SpecParser()
        
        spec = AgentSpec(
            name="BadActionAgent",
            description="Agent",
            purpose="Testing",
            location=AgentLocation.LOCAL,
            trigger_type=TriggerType.MANUAL,
            capabilities=["test"],
            actions=[{"description": "Missing name"}]  # No name field
        )
        
        is_valid, errors = parser.validate_spec(spec)
        
        assert is_valid is False
        assert any("name" in e.lower() for e in errors)
    
    @pytest.mark.asyncio
    async def test_parse_natural_language(self):
        """Test parsing natural language description."""
        from agents.meta_builder.spec_parser import SpecParser
        from agents.meta_builder.models import AgentSpec
        from agents.llm_client import LLMResponse
        
        parser = SpecParser()
        
        mock_response = LLMResponse(content=json.dumps({
            "name": "WeatherAgent",
            "version": "1.0.0",
            "description": "An agent that fetches weather data",
            "purpose": "Provide weather information to users",
            "location": "CLOUD",
            "trigger_type": "TASK_QUEUE",
            "inputs": [{"name": "location", "type": "string", "description": "City name"}],
            "outputs": [{"name": "weather", "type": "object", "description": "Weather data"}],
            "capabilities": ["weather_fetch", "forecast"],
            "dependencies": ["httpx"],
            "actions": [
                {"name": "get_weather", "description": "Get current weather", "parameters": [], "returns": "dict"}
            ],
            "system_prompt": "You are a weather agent."
        }))
        
        with patch.object(parser.client, 'chat', new_callable=AsyncMock) as mock_chat:
            mock_chat.return_value = mock_response
            
            spec = await parser.parse_natural_language("Create an agent that fetches weather data")
            
            assert isinstance(spec, AgentSpec)
            assert spec.name == "WeatherAgent"
            assert "weather_fetch" in spec.capabilities


# ============================================================================
# CODE GENERATOR TESTS
# ============================================================================

class TestCodeGenerator:
    """Tests for CodeGenerator component."""
    
    def test_code_generator_initialization(self):
        """Test CodeGenerator initialization."""
        from agents.meta_builder.code_generator import CodeGenerator
        
        generator = CodeGenerator()
        
        assert generator is not None
    
    def test_generate_basic_agent(self):
        """Test generating code for a basic agent."""
        from agents.meta_builder.code_generator import CodeGenerator
        from agents.meta_builder.models import AgentSpec, AgentLocation, TriggerType, GeneratedCode
        
        generator = CodeGenerator()
        
        spec = AgentSpec(
            name="BasicAgent",
            description="A basic test agent",
            purpose="Testing code generation",
            location=AgentLocation.LOCAL,
            trigger_type=TriggerType.TASK_QUEUE,
            capabilities=["basic"],
            actions=[{"name": "test", "description": "Test action", "parameters": [], "returns": "dict"}]
        )
        
        code = generator.generate(spec)
        
        assert isinstance(code, GeneratedCode)
        assert "class BasicAgentAgent" in code.agent_file or "class BasicAgent" in code.agent_file
        assert "BaseAgent" in code.agent_file
        assert "async def execute" in code.agent_file
        assert "BASIC" in code.agent_file.upper()
    
    def test_generate_agent_with_multiple_actions(self):
        """Test generating agent with multiple actions."""
        from agents.meta_builder.code_generator import CodeGenerator
        from agents.meta_builder.models import AgentSpec, AgentLocation, TriggerType
        
        generator = CodeGenerator()
        
        spec = AgentSpec(
            name="MultiAgent",
            description="Agent with multiple actions",
            purpose="Testing multiple actions",
            location=AgentLocation.LOCAL,
            trigger_type=TriggerType.TASK_QUEUE,
            capabilities=["search", "analyze", "report"],
            actions=[
                {"name": "search", "description": "Search for items"},
                {"name": "analyze", "description": "Analyze results"},
                {"name": "report", "description": "Generate report"}
            ]
        )
        
        code = generator.generate(spec)
        
        assert "_action_search" in code.agent_file
        assert "_action_analyze" in code.agent_file
        assert "_action_report" in code.agent_file
    
    def test_generate_init_file(self):
        """Test generating __init__.py file."""
        from agents.meta_builder.code_generator import CodeGenerator
        from agents.meta_builder.models import AgentSpec, AgentLocation, TriggerType
        
        generator = CodeGenerator()
        
        spec = AgentSpec(
            name="InitTest",
            description="Test",
            purpose="Testing",
            location=AgentLocation.LOCAL,
            trigger_type=TriggerType.MANUAL,
            capabilities=["test"],
            actions=[{"name": "test", "description": "Test"}]
        )
        
        code = generator.generate(spec)
        
        assert "from .agent import" in code.init_file
        assert "__all__" in code.init_file
    
    def test_generate_models_file(self):
        """Test generating models file when inputs/outputs exist."""
        from agents.meta_builder.code_generator import CodeGenerator
        from agents.meta_builder.models import AgentSpec, AgentLocation, TriggerType
        
        generator = CodeGenerator()
        
        spec = AgentSpec(
            name="ModelAgent",
            description="Agent with models",
            purpose="Testing model generation",
            location=AgentLocation.LOCAL,
            trigger_type=TriggerType.TASK_QUEUE,
            inputs=[{"name": "user_input", "type": "string", "description": "User input"}],
            outputs=[{"name": "result", "type": "object", "description": "Result"}],
            capabilities=["process"],
            actions=[{"name": "process", "description": "Process input"}]
        )
        
        code = generator.generate(spec)
        
        assert code.models_file is not None
        assert "BaseModel" in code.models_file
    
    def test_generate_no_models_when_no_io(self):
        """Test no models file when no inputs/outputs."""
        from agents.meta_builder.code_generator import CodeGenerator
        from agents.meta_builder.models import AgentSpec, AgentLocation, TriggerType
        
        generator = CodeGenerator()
        
        spec = AgentSpec(
            name="NoIOAgent",
            description="Agent without I/O",
            purpose="Testing",
            location=AgentLocation.LOCAL,
            trigger_type=TriggerType.MANUAL,
            inputs=[],
            outputs=[],
            capabilities=["run"],
            actions=[{"name": "run", "description": "Run something"}]
        )
        
        code = generator.generate(spec)
        
        assert code.models_file is None
    
    def test_generate_tests_file(self):
        """Test generating test file."""
        from agents.meta_builder.code_generator import CodeGenerator
        from agents.meta_builder.models import AgentSpec, AgentLocation, TriggerType
        
        generator = CodeGenerator()
        
        spec = AgentSpec(
            name="TestableAgent",
            description="Agent with tests",
            purpose="Testing test generation",
            location=AgentLocation.LOCAL,
            trigger_type=TriggerType.TASK_QUEUE,
            capabilities=["test"],
            actions=[{"name": "action1", "description": "Action 1"}, {"name": "action2", "description": "Action 2"}]
        )
        
        code = generator.generate(spec)
        
        assert code.test_file is not None
        assert "pytest" in code.test_file
        assert "test_action1" in code.test_file
        assert "test_action2" in code.test_file
        assert "test_agent_initialization" in code.test_file
    
    def test_generate_documentation(self):
        """Test generating documentation."""
        from agents.meta_builder.code_generator import CodeGenerator
        from agents.meta_builder.models import AgentSpec, AgentLocation, TriggerType
        
        generator = CodeGenerator()
        
        spec = AgentSpec(
            name="DocAgent",
            description="Agent documentation test",
            purpose="Testing documentation",
            location=AgentLocation.CLOUD,
            trigger_type=TriggerType.CRON,
            trigger_config={"cron": "0 9 * * *"},
            capabilities=["document", "report"],
            actions=[{"name": "generate", "description": "Generate docs"}]
        )
        
        code = generator.generate(spec)
        
        assert "# AGENT: DOCAGENT" in code.documentation
        assert "CLOUD" in code.documentation
        assert "CRON" in code.documentation
        assert "document" in code.documentation
        assert "generate" in code.documentation
    
    def test_generate_capabilities_list(self):
        """Test that capabilities are properly included in agent code."""
        from agents.meta_builder.code_generator import CodeGenerator
        from agents.meta_builder.models import AgentSpec, AgentLocation, TriggerType
        
        generator = CodeGenerator()
        
        spec = AgentSpec(
            name="CapAgent",
            description="Test",
            purpose="Testing",
            location=AgentLocation.LOCAL,
            trigger_type=TriggerType.MANUAL,
            capabilities=["cap1", "cap2", "cap3"],
            actions=[{"name": "test", "description": "Test"}]
        )
        
        code = generator.generate(spec)
        
        assert "get_capabilities" in code.agent_file
        assert "cap1" in code.agent_file
        assert "cap2" in code.agent_file
        assert "cap3" in code.agent_file


# ============================================================================
# REGISTRAR TESTS
# ============================================================================

class TestAgentRegistrar:
    """Tests for AgentRegistrar component."""
    
    def test_registrar_initialization(self):
        """Test AgentRegistrar initialization."""
        from agents.meta_builder.registrar import AgentRegistrar
        
        registrar = AgentRegistrar()
        
        assert registrar.api_url is not None
    
    def test_save_agent_files(self):
        """Test saving agent files to disk."""
        from agents.meta_builder.registrar import AgentRegistrar
        from agents.meta_builder.models import AgentSpec, GeneratedCode, AgentLocation, TriggerType
        
        registrar = AgentRegistrar()
        
        spec = AgentSpec(
            name="SaveTest",
            description="Test save",
            purpose="Testing",
            location=AgentLocation.LOCAL,
            trigger_type=TriggerType.MANUAL,
            capabilities=["test"],
            actions=[{"name": "test", "description": "Test"}]
        )
        
        code = GeneratedCode(
            agent_file="class SaveTestAgent(BaseAgent): pass",
            init_file="from .agent import SaveTestAgent",
            documentation="# SaveTest Agent",
            test_file="def test_save(): pass"
        )
        
        with tempfile.TemporaryDirectory() as temp_dir:
            base_path = Path(temp_dir)
            
            created_files = registrar.save_agent_files(spec, code, base_path)
            
            assert len(created_files) >= 3  # agent.py, __init__.py, docs
            assert (base_path / "savetest" / "agent.py").exists()
            assert (base_path / "savetest" / "__init__.py").exists()
    
    def test_save_agent_files_with_models(self):
        """Test saving agent files including models."""
        from agents.meta_builder.registrar import AgentRegistrar
        from agents.meta_builder.models import AgentSpec, GeneratedCode, AgentLocation, TriggerType
        
        registrar = AgentRegistrar()
        
        spec = AgentSpec(
            name="ModelSaveTest",
            description="Test save with models",
            purpose="Testing",
            location=AgentLocation.LOCAL,
            trigger_type=TriggerType.MANUAL,
            capabilities=["test"],
            actions=[{"name": "test", "description": "Test"}]
        )
        
        code = GeneratedCode(
            agent_file="class Agent: pass",
            models_file="from pydantic import BaseModel",
            init_file="from .agent import Agent",
            documentation="# Agent docs"
        )
        
        with tempfile.TemporaryDirectory() as temp_dir:
            base_path = Path(temp_dir)
            
            created_files = registrar.save_agent_files(spec, code, base_path)
            
            assert (base_path / "modelsavetest" / "models.py").exists()
    
    def test_save_agent_files_creates_tests_dir(self):
        """Test that tests directory is created when tests exist."""
        from agents.meta_builder.registrar import AgentRegistrar
        from agents.meta_builder.models import AgentSpec, GeneratedCode, AgentLocation, TriggerType
        
        registrar = AgentRegistrar()
        
        spec = AgentSpec(
            name="TestDirTest",
            description="Test",
            purpose="Testing",
            location=AgentLocation.LOCAL,
            trigger_type=TriggerType.MANUAL,
            capabilities=["test"],
            actions=[{"name": "test", "description": "Test"}]
        )
        
        code = GeneratedCode(
            agent_file="class Agent: pass",
            init_file="from .agent import Agent",
            documentation="# Docs",
            test_file="def test_something(): pass"
        )
        
        with tempfile.TemporaryDirectory() as temp_dir:
            base_path = Path(temp_dir)
            
            registrar.save_agent_files(spec, code, base_path)
            
            assert (base_path / "testdirtest" / "tests").is_dir()
    
    @pytest.mark.asyncio
    async def test_register_agent_success(self):
        """Test successful agent registration with cloud."""
        from agents.meta_builder.registrar import AgentRegistrar
        from agents.meta_builder.models import AgentSpec, AgentLocation, TriggerType
        import httpx
        
        registrar = AgentRegistrar()
        
        spec = AgentSpec(
            name="RegisterTest",
            version="1.0.0",
            description="Test",
            purpose="Testing",
            location=AgentLocation.LOCAL,
            trigger_type=TriggerType.TASK_QUEUE,
            capabilities=["test"],
            actions=[{"name": "test", "description": "Test"}]
        )
        
        # Mock the cloud API client
        with patch("agents.meta_builder.registrar.CloudAPIClient") as mock_client:
            mock_instance = AsyncMock()
            mock_instance.register_agent = AsyncMock(return_value={"agent_id": "agent-123"})
            mock_instance.close = AsyncMock()
            mock_client.return_value = mock_instance

            agent_id = await registrar.register_agent(spec)

            assert agent_id == "agent-123"
    
    @pytest.mark.asyncio
    async def test_register_agent_failure(self):
        """Test agent registration failure handling."""
        from agents.meta_builder.registrar import AgentRegistrar
        from agents.meta_builder.models import AgentSpec, AgentLocation, TriggerType
        
        registrar = AgentRegistrar()
        
        spec = AgentSpec(
            name="FailTest",
            description="Test",
            purpose="Testing",
            location=AgentLocation.LOCAL,
            trigger_type=TriggerType.MANUAL,
            capabilities=["test"],
            actions=[{"name": "test", "description": "Test"}]
        )
        
        with patch("agents.meta_builder.registrar.CloudAPIClient") as mock_client:
            mock_instance = AsyncMock()
            mock_instance.register_agent = AsyncMock(return_value=None)
            mock_instance.close = AsyncMock()
            mock_client.return_value = mock_instance

            agent_id = await registrar.register_agent(spec)

            assert agent_id is None


# ============================================================================
# MAIN AGENT TESTS
# ============================================================================

class TestMetaBuilderAgent:
    """Tests for the main MetaBuilderAgent class."""
    
    def test_agent_initialization(self):
        """Test MetaBuilderAgent initialization."""
        from agents.meta_builder.agent import MetaBuilderAgent
        
        agent = MetaBuilderAgent()
        
        assert agent.name == "META_BUILDER"
        assert agent.version == "2.0.0"
        assert agent.spec_parser is not None
        assert agent.code_generator is not None
        assert agent.registrar is not None
    
    def test_agent_capabilities(self):
        """Test MetaBuilderAgent capabilities list."""
        from agents.meta_builder.agent import MetaBuilderAgent
        
        agent = MetaBuilderAgent()
        
        capabilities = agent.get_capabilities()
        
        assert "agent_specification" in capabilities
        assert "code_generation" in capabilities
        assert "agent_registration" in capabilities
        assert "spec_validation" in capabilities
        assert "documentation_generation" in capabilities
    
    @pytest.mark.asyncio
    async def test_execute_unknown_action(self):
        """Test execute with unknown action."""
        from agents.meta_builder.agent import MetaBuilderAgent
        
        agent = MetaBuilderAgent()
        
        result = await agent.execute({"action": "unknown_action"})
        
        assert result.success is False
        assert "Unknown action" in result.error
    
    @pytest.mark.asyncio
    async def test_execute_validate_no_input(self):
        """Test validate action without input."""
        from agents.meta_builder.agent import MetaBuilderAgent
        
        agent = MetaBuilderAgent()
        
        result = await agent.execute({"action": "validate"})
        
        assert result.success is False
        assert "No description or spec provided" in result.error
    
    @pytest.mark.asyncio
    async def test_execute_validate_with_spec(self):
        """Test validate action with spec dict."""
        from agents.meta_builder.agent import MetaBuilderAgent
        
        agent = MetaBuilderAgent()
        
        spec_dict = {
            "name": "ValidateTest",
            "description": "Test",
            "purpose": "Testing",
            "location": "LOCAL",
            "trigger_type": "MANUAL",
            "capabilities": ["test"],
            "actions": [{"name": "test", "description": "Test"}]
        }
        
        result = await agent.execute({"action": "validate", "spec": spec_dict})
        
        assert result.success is True
        assert "valid" in result.data
        assert result.data["valid"] is True
    
    @pytest.mark.asyncio
    async def test_execute_validate_invalid_spec(self):
        """Test validate action with invalid spec."""
        from agents.meta_builder.agent import MetaBuilderAgent
        
        agent = MetaBuilderAgent()
        
        spec_dict = {
            "name": "Invalid!Agent",  # Invalid name
            "description": "Test",
            "purpose": "Testing",
            "location": "LOCAL",
            "trigger_type": "MANUAL",
            "capabilities": [],  # No capabilities
            "actions": []  # No actions
        }
        
        result = await agent.execute({"action": "validate", "spec": spec_dict})
        
        assert result.success is True
        assert result.data["valid"] is False
        assert len(result.data["errors"]) > 0
    
    @pytest.mark.asyncio
    async def test_execute_generate_spec_no_description(self):
        """Test generate_spec action without description."""
        from agents.meta_builder.agent import MetaBuilderAgent
        
        agent = MetaBuilderAgent()
        
        result = await agent.execute({"action": "generate_spec"})
        
        assert result.success is False
        assert "No description provided" in result.error
    
    @pytest.mark.asyncio
    async def test_execute_generate_spec_with_description(self):
        """Test generate_spec action with description."""
        from agents.meta_builder.agent import MetaBuilderAgent
        from agents.llm_client import LLMResponse
        
        agent = MetaBuilderAgent()
        
        mock_response = LLMResponse(content=json.dumps({
            "name": "GeneratedAgent",
            "version": "1.0.0",
            "description": "Generated agent",
            "purpose": "Testing",
            "location": "LOCAL",
            "trigger_type": "TASK_QUEUE",
            "capabilities": ["generated"],
            "dependencies": [],
            "actions": [{"name": "action", "description": "Action"}],
            "inputs": [],
            "outputs": [],
            "system_prompt": None
        }))
        
        with patch.object(agent.spec_parser.client, 'chat', new_callable=AsyncMock) as mock_chat:
            mock_chat.return_value = mock_response
            
            result = await agent.execute({
                "action": "generate_spec",
                "description": "Create an agent for testing"
            })
            
            assert result.success is True
            assert "spec" in result.data
            assert result.data["spec"]["name"] == "GeneratedAgent"
    
    @pytest.mark.asyncio
    async def test_execute_build_no_input(self):
        """Test build action without input."""
        from agents.meta_builder.agent import MetaBuilderAgent
        
        agent = MetaBuilderAgent()
        
        result = await agent.execute({"action": "build"})
        
        assert result.success is False
        assert "No description or spec provided" in result.error
    
    @pytest.mark.asyncio
    async def test_execute_build_with_spec(self):
        """Test build action with spec dict."""
        from agents.meta_builder.agent import MetaBuilderAgent
        
        agent = MetaBuilderAgent()
        
        spec_dict = {
            "name": "BuildTest",
            "description": "Build test agent",
            "purpose": "Testing build",
            "location": "LOCAL",
            "trigger_type": "TASK_QUEUE",
            "capabilities": ["build"],
            "actions": [{"name": "build", "description": "Build something"}]
        }
        
        # Mock the registration
        with patch.object(agent.registrar, 'register_agent', new_callable=AsyncMock) as mock_register:
            mock_register.return_value = "agent-build-123"
            
            with tempfile.TemporaryDirectory() as temp_dir:
                agent.agents_path = Path(temp_dir)
                
                result = await agent.execute({"action": "build", "spec": spec_dict})
                
                assert result.success is True
                assert result.data["agent_name"] == "BuildTest"
                assert len(result.data["files_created"]) > 0
    
    def test_agent_status(self):
        """Test agent status reporting."""
        from agents.meta_builder.agent import MetaBuilderAgent
        
        agent = MetaBuilderAgent()
        
        status = agent.get_status()
        
        assert status["name"] == "META_BUILDER"
        assert status["version"] == "2.0.0"
        assert status["is_running"] is False
        assert "agent_specification" in status["capabilities"]


# ============================================================================
# INTEGRATION TESTS
# ============================================================================

class TestMetaBuilderIntegration:
    """Integration tests for Meta Builder components working together."""
    
    def test_full_build_flow_with_spec(self):
        """Test full build flow from spec to files."""
        from agents.meta_builder.spec_parser import SpecParser
        from agents.meta_builder.code_generator import CodeGenerator
        from agents.meta_builder.registrar import AgentRegistrar
        from agents.meta_builder.models import AgentSpec, AgentLocation, TriggerType
        
        parser = SpecParser()
        generator = CodeGenerator()
        registrar = AgentRegistrar()
        
        # Parse spec
        spec_dict = {
            "name": "IntegrationAgent",
            "description": "Integration test agent",
            "purpose": "Testing integration",
            "location": "LOCAL",
            "trigger_type": "TASK_QUEUE",
            "capabilities": ["integrate", "test"],
            "actions": [
                {"name": "integrate", "description": "Integrate"},
                {"name": "test", "description": "Test"}
            ]
        }
        
        spec = parser.parse_dict(spec_dict)
        
        # Validate
        is_valid, errors = parser.validate_spec(spec)
        assert is_valid is True
        
        # Generate code
        code = generator.generate(spec)
        
        # Save files
        with tempfile.TemporaryDirectory() as temp_dir:
            files = registrar.save_agent_files(spec, code, Path(temp_dir))
            
            assert len(files) >= 3
            assert any("agent.py" in f for f in files)
            assert any("__init__.py" in f for f in files)
    
    def test_yaml_to_agent_flow(self):
        """Test creating agent from YAML specification."""
        from agents.meta_builder.spec_parser import SpecParser
        from agents.meta_builder.code_generator import CodeGenerator
        
        parser = SpecParser()
        generator = CodeGenerator()
        
        yaml_spec = """
name: YamlFlowAgent
description: Agent created from YAML
purpose: Test YAML flow
location: CLOUD
trigger_type: CRON
trigger_config:
  cron: "0 10 * * *"
capabilities:
  - yaml_processing
  - reporting
actions:
  - name: process
    description: Process YAML data
  - name: report
    description: Generate report
"""
        
        spec = parser.parse_yaml(yaml_spec)
        is_valid, errors = parser.validate_spec(spec)
        
        assert is_valid is True
        
        code = generator.generate(spec)
        
        assert "YamlFlowAgentAgent" in code.agent_file or "YamlFlowAgent" in code.agent_file
        assert "CRON" in code.documentation
    
    def test_models_serialization(self):
        """Test that models can be serialized to JSON."""
        from agents.meta_builder.models import (
            AgentSpec, GeneratedCode, AgentBuildResult,
            AgentLocation, TriggerType
        )
        
        spec = AgentSpec(
            name="SerializeTest",
            description="Test serialization",
            purpose="Testing",
            location=AgentLocation.LOCAL,
            trigger_type=TriggerType.MANUAL,
            capabilities=["serialize"],
            actions=[{"name": "test", "description": "Test"}]
        )
        
        # Should not raise
        spec_dict = spec.model_dump()
        spec_json = json.dumps(spec_dict, default=str)
        
        assert "SerializeTest" in spec_json
        assert "LOCAL" in spec_json
    
    def test_generated_code_is_valid_python(self):
        """Test that generated code is syntactically valid Python."""
        from agents.meta_builder.code_generator import CodeGenerator
        from agents.meta_builder.models import AgentSpec, AgentLocation, TriggerType
        import ast
        
        generator = CodeGenerator()
        
        spec = AgentSpec(
            name="SyntaxTest",
            description="Test syntax",
            purpose="Testing",
            location=AgentLocation.LOCAL,
            trigger_type=TriggerType.MANUAL,
            capabilities=["syntax"],
            actions=[
                {"name": "action_one", "description": "First action"},
                {"name": "action_two", "description": "Second action"}
            ]
        )
        
        code = generator.generate(spec)
        
        # This will raise SyntaxError if code is invalid
        try:
            ast.parse(code.agent_file)
            is_valid = True
        except SyntaxError:
            is_valid = False
        
        assert is_valid is True
    
    def test_spec_validation_comprehensive(self):
        """Test comprehensive spec validation."""
        from agents.meta_builder.spec_parser import SpecParser
        from agents.meta_builder.models import AgentSpec, AgentLocation, TriggerType
        
        parser = SpecParser()
        
        # Valid spec
        valid_spec = AgentSpec(
            name="ComprehensiveAgent",
            version="2.0.0",
            description="Comprehensive test",
            purpose="Testing comprehensive validation",
            location=AgentLocation.LOCAL,
            trigger_type=TriggerType.TASK_QUEUE,
            trigger_config={"timeout": 300},
            inputs=[{"name": "data", "type": "dict", "description": "Input"}],
            outputs=[{"name": "result", "type": "dict", "description": "Output"}],
            capabilities=["comprehensive", "testing"],
            dependencies=["httpx", "pydantic"],
            actions=[
                {"name": "process", "description": "Process", "parameters": [], "returns": "dict"},
                {"name": "validate", "description": "Validate", "parameters": [], "returns": "bool"}
            ],
            system_prompt="You are comprehensive."
        )
        
        is_valid, errors = parser.validate_spec(valid_spec)
        
        assert is_valid is True
        assert len(errors) == 0

