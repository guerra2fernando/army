"""
Tests for Task Router
"""
import pytest
from unittest.mock import AsyncMock, MagicMock


class TestTaskRouter:
    """Tests for TaskRouter class."""

    def test_router_initialization(self):
        """Test router initializes with empty agents."""
        from poller.task_router import TaskRouter
        
        router = TaskRouter()
        
        assert router.get_registered_types() == []

    def test_register_agent_success(self):
        """Test successful agent registration."""
        from poller.task_router import TaskRouter
        from agents.base_agent import BaseAgent, AgentResult
        
        class TestAgent(BaseAgent):
            async def execute(self, payload):
                return AgentResult(success=True)
            def get_capabilities(self):
                return ["test"]
        
        router = TaskRouter()
        agent = TestAgent("TEST_AGENT")
        
        router.register_agent("TEST_TYPE", agent)
        
        assert "TEST_TYPE" in router.get_registered_types()
        assert router.get_agent("TEST_TYPE") is agent

    def test_get_agent_not_found(self):
        """Test getting non-existent agent."""
        from poller.task_router import TaskRouter
        
        router = TaskRouter()
        
        assert router.get_agent("NONEXISTENT") is None

    def test_register_multiple_agents(self):
        """Test registering multiple agents."""
        from poller.task_router import TaskRouter
        from agents.base_agent import BaseAgent, AgentResult
        
        class TestAgent(BaseAgent):
            async def execute(self, payload):
                return AgentResult(success=True)
            def get_capabilities(self):
                return ["test"]
        
        router = TaskRouter()
        router.register_agent("TYPE_A", TestAgent("AGENT_A"))
        router.register_agent("TYPE_B", TestAgent("AGENT_B"))
        
        registered = router.get_registered_types()
        assert "TYPE_A" in registered
        assert "TYPE_B" in registered
        assert len(registered) == 2

    @pytest.mark.asyncio
    async def test_route_task_success(self):
        """Test successful task routing."""
        from poller.task_router import TaskRouter
        from agents.base_agent import BaseAgent, AgentResult
        
        class TestAgent(BaseAgent):
            async def execute(self, payload):
                return AgentResult(success=True, data={"processed": payload})
            def get_capabilities(self):
                return ["test"]
        
        router = TaskRouter()
        router.register_agent("TEST_TYPE", TestAgent("TEST_AGENT"))
        
        result = await router.route_task(
            task_id="task-123",
            agent_target="TEST_TYPE",
            payload={"action": "test"}
        )
        
        assert result.success is True
        assert result.data["processed"]["action"] == "test"

    @pytest.mark.asyncio
    async def test_route_task_unknown_agent(self):
        """Test routing to unknown agent type."""
        from poller.task_router import TaskRouter
        
        router = TaskRouter()
        
        result = await router.route_task(
            task_id="task-123",
            agent_target="UNKNOWN_TYPE",
            payload={}
        )
        
        assert result.success is False
        assert "No agent registered" in result.error

    def test_get_all_statuses(self):
        """Test getting all agent statuses."""
        from poller.task_router import TaskRouter
        from agents.base_agent import BaseAgent, AgentResult
        
        class TestAgent(BaseAgent):
            async def execute(self, payload):
                return AgentResult(success=True)
            def get_capabilities(self):
                return ["test"]
        
        router = TaskRouter()
        router.register_agent("TYPE_A", TestAgent("AGENT_A", version="1.0.0"))
        router.register_agent("TYPE_B", TestAgent("AGENT_B", version="2.0.0"))
        
        statuses = router.get_all_statuses()
        
        assert "TYPE_A" in statuses
        assert "TYPE_B" in statuses
        assert statuses["TYPE_A"]["name"] == "AGENT_A"
        assert statuses["TYPE_B"]["name"] == "AGENT_B"

