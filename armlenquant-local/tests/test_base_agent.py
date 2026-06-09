"""
Tests for Base Agent Class
"""
import pytest
import asyncio
from datetime import datetime


class TestAgentResult:
    """Tests for AgentResult class."""

    def test_agent_result_creation_success(self):
        """Test creating a successful result."""
        from agents.base_agent import AgentResult
        
        result = AgentResult(
            success=True,
            data={"jobs_found": 5},
            execution_time_ms=1000
        )
        
        assert result.success is True
        assert result.data["jobs_found"] == 5
        assert result.error is None
        assert result.execution_time_ms == 1000

    def test_agent_result_creation_failure(self):
        """Test creating a failure result."""
        from agents.base_agent import AgentResult
        
        result = AgentResult(
            success=False,
            error="Connection timeout"
        )
        
        assert result.success is False
        assert result.error == "Connection timeout"
        assert result.data == {}

    def test_agent_result_to_dict(self):
        """Test converting result to dictionary."""
        from agents.base_agent import AgentResult
        
        result = AgentResult(
            success=True,
            data={"test": "data"},
            execution_time_ms=500
        )
        
        result_dict = result.to_dict()
        
        assert "success" in result_dict
        assert "data" in result_dict
        assert "error" in result_dict
        assert "execution_time_ms" in result_dict
        assert "timestamp" in result_dict

    def test_agent_result_has_timestamp(self):
        """Test that result has timestamp."""
        from agents.base_agent import AgentResult
        
        before = datetime.utcnow()
        result = AgentResult(success=True)
        after = datetime.utcnow()
        
        assert before <= result.timestamp <= after


class TestBaseAgent:
    """Tests for BaseAgent class."""

    def test_cannot_instantiate_abstract_agent(self):
        """Test that BaseAgent cannot be instantiated directly."""
        from agents.base_agent import BaseAgent
        
        with pytest.raises(TypeError):
            BaseAgent("TEST_AGENT")

    def test_concrete_agent_initialization(self):
        """Test that concrete agent can be initialized."""
        from agents.base_agent import BaseAgent, AgentResult
        
        class ConcreteAgent(BaseAgent):
            async def execute(self, payload):
                return AgentResult(success=True)
            
            def get_capabilities(self):
                return ["test"]
        
        agent = ConcreteAgent("TEST_AGENT", version="1.0.0")
        
        assert agent.name == "TEST_AGENT"
        assert agent.version == "1.0.0"
        assert agent.agent_name == "TEST_AGENT"

    @pytest.mark.asyncio
    async def test_agent_run_success(self):
        """Test successful agent execution."""
        from agents.base_agent import BaseAgent, AgentResult
        
        class ConcreteAgent(BaseAgent):
            async def execute(self, payload):
                return AgentResult(success=True, data={"result": "done"})
            
            def get_capabilities(self):
                return ["test"]
        
        agent = ConcreteAgent("TEST_AGENT")
        result = await agent.run("task-123", {"action": "test"})
        
        assert result.success is True
        assert result.data["result"] == "done"
        assert result.execution_time_ms >= 0  # May be 0 for very fast executions

    @pytest.mark.asyncio
    async def test_agent_run_handles_exception(self):
        """Test that agent handles exceptions gracefully."""
        from agents.base_agent import BaseAgent, AgentResult
        
        class FailingAgent(BaseAgent):
            async def execute(self, payload):
                raise ValueError("Something went wrong")
            
            def get_capabilities(self):
                return ["test"]
        
        agent = FailingAgent("FAILING_AGENT")
        result = await agent.run("task-123", {})
        
        assert result.success is False
        assert "Something went wrong" in result.error

    @pytest.mark.asyncio
    async def test_agent_run_tracks_running_state(self):
        """Test that agent tracks running state."""
        from agents.base_agent import BaseAgent, AgentResult
        
        running_states = []
        
        class TrackingAgent(BaseAgent):
            async def execute(self, payload):
                running_states.append(self.is_running)
                running_states.append(self.current_task)
                return AgentResult(success=True)
            
            def get_capabilities(self):
                return ["test"]
        
        agent = TrackingAgent("TRACKING_AGENT")
        
        assert agent.is_running is False
        assert agent.current_task is None
        
        await agent.run("task-123", {})
        
        # During execution, should have been running
        assert running_states[0] is True
        assert running_states[1] == "task-123"
        
        # After execution, should not be running
        assert agent.is_running is False
        assert agent.current_task is None

    def test_agent_get_status(self):
        """Test getting agent status."""
        from agents.base_agent import BaseAgent, AgentResult
        
        class StatusAgent(BaseAgent):
            async def execute(self, payload):
                return AgentResult(success=True)
            
            def get_capabilities(self):
                return ["cap1", "cap2"]
        
        agent = StatusAgent("STATUS_AGENT", version="2.0.0")
        status = agent.get_status()
        
        assert status["name"] == "STATUS_AGENT"
        assert status["version"] == "2.0.0"
        assert status["is_running"] is False
        assert status["current_task"] is None
        assert "cap1" in status["capabilities"]
        assert "cap2" in status["capabilities"]

