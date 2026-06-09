"""
Tests for Stub Agents
"""
import pytest


class TestJobHunterAgent:
    """Tests for JobHunter stub agent."""

    def test_job_hunter_initialization(self):
        """Test JobHunter agent initialization."""
        from agents.job_hunter.agent import JobHunterAgent
        
        agent = JobHunterAgent()
        
        assert agent.name == "JOB_HUNTER"
        assert agent.version == "2.0.0"

    def test_job_hunter_capabilities(self):
        """Test JobHunter capabilities."""
        from agents.job_hunter.agent import JobHunterAgent
        
        agent = JobHunterAgent()
        capabilities = agent.get_capabilities()
        
        assert "job_search" in capabilities
        assert "resume_tailoring" in capabilities
        assert "cover_letter_generation" in capabilities

    @pytest.mark.asyncio
    async def test_job_hunter_execute_search(self):
        """Test JobHunter search action - requires browser, returns error without it."""
        from agents.job_hunter.agent import JobHunterAgent
        
        agent = JobHunterAgent()
        # Without Playwright browsers installed, search returns jobs_found: 0
        result = await agent.execute({"action": "search"})
        
        # Either success with 0 jobs (no browser) or error
        if result.success:
            assert "jobs_found" in result.data
        else:
            assert result.error is not None

    @pytest.mark.asyncio
    async def test_job_hunter_execute_generate_materials(self):
        """Test JobHunter generate_materials action - requires job data."""
        from agents.job_hunter.agent import JobHunterAgent
        
        agent = JobHunterAgent()
        # Without job data, should fail
        result = await agent.execute({"action": "generate_materials"})
        
        assert result.success is False
        assert "No job data" in result.error

    @pytest.mark.asyncio
    async def test_job_hunter_execute_unknown_action(self):
        """Test JobHunter with unknown action."""
        from agents.job_hunter.agent import JobHunterAgent
        
        agent = JobHunterAgent()
        result = await agent.execute({"action": "unknown_action"})
        
        assert result.success is False
        assert "Unknown action" in result.error


class TestIdeasMachineAgent:
    """Tests for IdeasMachine stub agent."""

    def test_ideas_machine_initialization(self):
        """Test IdeasMachine agent initialization."""
        from agents.ideas_machine.agent import IdeasMachineAgent
        
        agent = IdeasMachineAgent()
        
        assert agent.name == "IDEAS_MACHINE"
        assert agent.version == "2.0.0"

    def test_ideas_machine_capabilities(self):
        """Test IdeasMachine capabilities."""
        from agents.ideas_machine.agent import IdeasMachineAgent
        
        agent = IdeasMachineAgent()
        capabilities = agent.get_capabilities()
        
        assert "idea_analysis" in capabilities
        assert "project_scaffolding" in capabilities
        assert "documentation_generation" in capabilities

    @pytest.mark.asyncio
    async def test_ideas_machine_execute_scaffold_no_description(self):
        """Test IdeasMachine scaffold action without description."""
        from agents.ideas_machine.agent import IdeasMachineAgent
        
        agent = IdeasMachineAgent()
        result = await agent.execute({"action": "scaffold"})
        
        # Without description, should fail
        assert result.success is False
        assert "No project description" in result.error

    @pytest.mark.asyncio
    async def test_ideas_machine_execute_analyze_no_description(self):
        """Test IdeasMachine analyze action without description."""
        from agents.ideas_machine.agent import IdeasMachineAgent
        
        agent = IdeasMachineAgent()
        result = await agent.execute({"action": "analyze", "description": ""})
        
        # Without description, should fail
        assert result.success is False
        assert "No project description" in result.error
    
    @pytest.mark.asyncio
    async def test_ideas_machine_execute_unknown_action(self):
        """Test IdeasMachine unknown action."""
        from agents.ideas_machine.agent import IdeasMachineAgent
        
        agent = IdeasMachineAgent()
        result = await agent.execute({"action": "unknown"})
        
        assert result.success is False
        assert "Unknown action" in result.error


class TestMetaBuilderAgent:
    """Tests for MetaBuilder stub agent."""

    def test_meta_builder_initialization(self):
        """Test MetaBuilder agent initialization."""
        from agents.meta_builder.agent import MetaBuilderAgent
        
        agent = MetaBuilderAgent()
        
        assert agent.name == "META_BUILDER"
        assert agent.version == "2.0.0"

    def test_meta_builder_capabilities(self):
        """Test MetaBuilder capabilities."""
        from agents.meta_builder.agent import MetaBuilderAgent
        
        agent = MetaBuilderAgent()
        capabilities = agent.get_capabilities()
        
        assert "agent_specification" in capabilities
        assert "code_generation" in capabilities

    @pytest.mark.asyncio
    async def test_meta_builder_execute_build_no_input(self):
        """Test MetaBuilder build without input fails gracefully."""
        from agents.meta_builder.agent import MetaBuilderAgent
        
        agent = MetaBuilderAgent()
        result = await agent.execute({"action": "build"})
        
        # Without description or spec, should fail
        assert result.success is False
        assert "No description or spec provided" in result.error
    
    @pytest.mark.asyncio
    async def test_meta_builder_execute_unknown_action(self):
        """Test MetaBuilder with unknown action."""
        from agents.meta_builder.agent import MetaBuilderAgent
        
        agent = MetaBuilderAgent()
        result = await agent.execute({"action": "unknown_action"})
        
        assert result.success is False
        assert "Unknown action" in result.error

