"""
Tests for Orchestrator Module (Agent 00)
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime
from uuid import uuid4

from app.db import Database
from app.orchestrator.prompts import (
    ORCHESTRATOR_SYSTEM_PROMPT,
    INTENT_EXTRACTION_PROMPT,
    TASK_GENERATION_PROMPT
)
from app.orchestrator.intent_parser import IntentParser, EntityExtractor
from app.orchestrator.task_router import TaskRouter
from app.orchestrator.agent_00 import (
    Orchestrator,
    OrchestratorResponse,
    get_orchestrator,
    reset_orchestrator
)


# =============================================================================
# PROMPTS TESTS
# =============================================================================

class TestPrompts:
    """Tests for orchestrator prompts."""
    
    def test_orchestrator_system_prompt_exists(self):
        """Test that system prompt is defined and non-empty."""
        assert ORCHESTRATOR_SYSTEM_PROMPT
        assert len(ORCHESTRATOR_SYSTEM_PROMPT) > 100
    
    def test_orchestrator_system_prompt_contains_agents(self):
        """Test that system prompt mentions all agents."""
        assert "CRYPTO_SENTINEL" in ORCHESTRATOR_SYSTEM_PROMPT
        assert "JOB_HUNTER" in ORCHESTRATOR_SYSTEM_PROMPT
        assert "IDEAS_MACHINE" in ORCHESTRATOR_SYSTEM_PROMPT
        assert "META_BUILDER" in ORCHESTRATOR_SYSTEM_PROMPT
    
    def test_intent_extraction_prompt_has_placeholders(self):
        """Test that intent extraction prompt has required placeholders."""
        assert "{message}" in INTENT_EXTRACTION_PROMPT
        assert "{context}" in INTENT_EXTRACTION_PROMPT
    
    def test_task_generation_prompt_has_placeholders(self):
        """Test that task generation prompt has required placeholders."""
        assert "{agent}" in TASK_GENERATION_PROMPT
        assert "{request}" in TASK_GENERATION_PROMPT
        assert "{intent}" in TASK_GENERATION_PROMPT
        assert "{context}" in TASK_GENERATION_PROMPT


# =============================================================================
# ENTITY EXTRACTOR TESTS
# =============================================================================

class TestEntityExtractor:
    """Tests for entity extraction."""
    
    def test_extract_locations_remote(self):
        """Test extracting 'remote' location."""
        locations = EntityExtractor.extract_locations("Looking for remote jobs")
        assert "remote" in locations
    
    def test_extract_locations_cities(self):
        """Test extracting city locations."""
        locations = EntityExtractor.extract_locations("Jobs in NYC or San Francisco")
        assert "nyc" in locations
        assert "san francisco" in locations
    
    def test_extract_locations_empty(self):
        """Test with no locations."""
        locations = EntityExtractor.extract_locations("Looking for any job")
        assert locations == []
    
    def test_extract_job_titles_growth(self):
        """Test extracting growth-related titles."""
        titles = EntityExtractor.extract_job_titles("Find growth lead positions")
        assert "growth lead" in titles
    
    def test_extract_job_titles_tech(self):
        """Test extracting tech titles."""
        titles = EntityExtractor.extract_job_titles("I'm a backend developer")
        assert "backend" in titles or "developer" in titles
    
    def test_extract_job_titles_multiple(self):
        """Test extracting multiple titles."""
        titles = EntityExtractor.extract_job_titles(
            "Looking for product manager or growth lead roles"
        )
        assert "product manager" in titles
        assert "growth lead" in titles
    
    def test_extract_crypto_assets_bitcoin(self):
        """Test extracting Bitcoin."""
        assets = EntityExtractor.extract_crypto_assets("Analyze BTC")
        assert "BTC" in assets
    
    def test_extract_crypto_assets_multiple(self):
        """Test extracting multiple assets."""
        assets = EntityExtractor.extract_crypto_assets(
            "Compare Bitcoin, Ethereum and Solana"
        )
        assert "BTC" in assets
        assert "ETH" in assets
        assert "SOL" in assets
    
    def test_extract_crypto_assets_no_duplicates(self):
        """Test no duplicate extractions."""
        assets = EntityExtractor.extract_crypto_assets("BTC bitcoin Bitcoin")
        assert assets.count("BTC") == 1
    
    def test_extract_all(self):
        """Test extracting all entity types."""
        entities = EntityExtractor.extract_all(
            "Find remote growth lead jobs, also analyze BTC"
        )
        assert "remote" in entities["locations"]
        assert "growth lead" in entities["job_titles"]
        assert "BTC" in entities["crypto_assets"]


# =============================================================================
# TASK ROUTER TESTS
# =============================================================================

class TestTaskRouter:
    """Tests for task routing."""
    
    def setup_method(self):
        """Set up router for each test."""
        self.router = TaskRouter()
    
    def test_route_crypto_intent(self):
        """Test routing crypto intents."""
        intent = {
            "intent_category": "CRYPTO",
            "action": "analyze",
            "entities": {"crypto_assets": ["BTC"]}
        }
        result = self.router.route(intent)
        
        assert result["target_agent"] == "CRYPTO_SENTINEL"
        assert result["action"] == "analyze_asset"
    
    def test_route_jobs_intent(self):
        """Test routing job intents."""
        intent = {
            "intent_category": "JOBS",
            "action": "search",
            "entities": {"locations": ["nyc"]}
        }
        result = self.router.route(intent)
        
        assert result["target_agent"] == "JOB_HUNTER"
        assert result["action"] == "search_jobs"
        assert "locations" in result["parameters"]
    
    def test_route_projects_intent(self):
        """Test routing project intents."""
        intent = {
            "intent_category": "PROJECTS",
            "action": "scaffold",
            "entities": {}
        }
        result = self.router.route(intent)
        
        assert result["target_agent"] == "IDEAS_MACHINE"
        assert result["action"] == "scaffold"
    
    def test_route_meta_intent(self):
        """Test routing meta/builder intents."""
        intent = {
            "intent_category": "META",
            "action": "create",
            "entities": {}
        }
        result = self.router.route(intent)
        
        assert result["target_agent"] == "META_BUILDER"
    
    def test_route_system_status(self):
        """Test routing system status queries."""
        intent = {
            "intent_category": "SYSTEM",
            "action": "status",
            "entities": {}
        }
        result = self.router.route(intent)
        
        assert result["target_agent"] is None
        assert result["action"] == "system_status"
        assert result["internal"] is True
    
    def test_route_system_capabilities(self):
        """Test routing capabilities queries."""
        intent = {
            "intent_category": "SYSTEM",
            "action": "what can you do",
            "entities": {}
        }
        result = self.router.route(intent)
        
        assert result["action"] == "show_capabilities"
        assert result["internal"] is True
    
    def test_route_unknown_returns_error(self):
        """Test routing unknown intents returns error."""
        intent = {
            "intent_category": "UNKNOWN",
            "action": None,
            "entities": {}
        }
        result = self.router.route(intent)
        
        assert result["target_agent"] is None
        assert "error" in result
    
    def test_confidence_increases_with_entities(self):
        """Test confidence increases when entities are present."""
        intent_without = {
            "intent_category": "JOBS",
            "action": "search",
            "entities": {}
        }
        intent_with = {
            "intent_category": "JOBS",
            "action": "search",
            "entities": {"locations": ["nyc", "remote"]}
        }
        
        result_without = self.router.route(intent_without)
        result_with = self.router.route(intent_with)
        
        assert result_with["confidence"] >= result_without["confidence"]
    
    def test_map_action_defaults(self):
        """Test default action mapping."""
        # JOB_HUNTER default
        action = self.router._map_action("JOB_HUNTER", None, {})
        assert action == "search_jobs"
        
        # CRYPTO_SENTINEL default
        action = self.router._map_action("CRYPTO_SENTINEL", None, {})
        assert action == "morning_brief"
    
    def test_map_action_fuzzy_matching(self):
        """Test fuzzy action matching."""
        # Should match "search_jobs"
        action = self.router._map_action("JOB_HUNTER", "find jobs", {})
        assert action == "search_jobs"
        
        # Should match "generate_resume"
        action = self.router._map_action("JOB_HUNTER", "update resume", {})
        assert action == "generate_resume"


# =============================================================================
# ORCHESTRATOR RESPONSE TESTS
# =============================================================================

class TestOrchestratorResponse:
    """Tests for OrchestratorResponse class."""
    
    def test_response_creation(self):
        """Test creating a response."""
        response = OrchestratorResponse(
            success=True,
            message="Test message",
            task_created=True,
            task_id="test-id"
        )
        
        assert response.success is True
        assert response.message == "Test message"
        assert response.task_created is True
        assert response.task_id == "test-id"
    
    def test_response_to_dict(self):
        """Test converting response to dict."""
        response = OrchestratorResponse(
            success=True,
            message="Test",
            agent_target="JOB_HUNTER"
        )
        
        result = response.to_dict()
        
        assert isinstance(result, dict)
        assert result["success"] is True
        assert result["message"] == "Test"
        assert result["agent_target"] == "JOB_HUNTER"
    
    def test_response_defaults(self):
        """Test response default values."""
        response = OrchestratorResponse(success=True, message="Test")
        
        assert response.task_created is False
        assert response.task_id is None
        assert response.requires_clarification is False
        assert response.data == {}


# =============================================================================
# INTENT PARSER TESTS
# =============================================================================

class TestIntentParser:
    """Tests for IntentParser class."""
    
    @pytest.mark.asyncio
    async def test_parse_with_mock_client(self):
        """Test parsing with mocked LLM client."""
        from app.agents.llm_client import LLMResponse
        mock_client = AsyncMock()
        mock_client.chat = AsyncMock(return_value=LLMResponse(
            content='{"intent_category": "JOBS", "action": "search", "entities": {}, "urgency": "MEDIUM", "requires_clarification": false}'
        ))

        parser = IntentParser(llm_client=mock_client)
        result = await parser.parse("Find me a job")

        assert result["intent_category"] == "JOBS"
        assert result["action"] == "search"
    
    @pytest.mark.asyncio
    async def test_parse_handles_json_error(self):
        """Test parsing handles invalid JSON gracefully."""
        from app.agents.llm_client import LLMResponse
        mock_client = AsyncMock()
        mock_client.chat = AsyncMock(return_value=LLMResponse(
            content="invalid json"
        ))

        parser = IntentParser(llm_client=mock_client)
        result = await parser.parse("Something")

        assert result["intent_category"] == "UNKNOWN"
        assert result["requires_clarification"] is True


# =============================================================================
# ORCHESTRATOR CLASS TESTS
# =============================================================================

class TestOrchestrator:
    """Tests for Orchestrator class."""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Reset orchestrator before each test."""
        reset_orchestrator()
    
    def test_get_orchestrator_singleton(self):
        """Test get_orchestrator returns singleton."""
        orch1 = get_orchestrator()
        orch2 = get_orchestrator()
        assert orch1 is orch2
    
    def test_reset_orchestrator(self):
        """Test resetting the singleton."""
        orch1 = get_orchestrator()
        reset_orchestrator()
        orch2 = get_orchestrator()
        assert orch1 is not orch2
    
    @pytest.mark.asyncio
    async def test_process_command_creates_task(self, test_user):
        """Test processing a command creates a task."""
        # Mock the OpenAI client
        from app.agents.llm_client import LLMResponse
        mock_client = AsyncMock()
        mock_client.chat = AsyncMock(return_value=LLMResponse(
            content='{"intent_category": "JOBS", "action": "search", "entities": {}, "urgency": "MEDIUM", "requires_clarification": false}'
        ))
        
        orchestrator = Orchestrator(llm_client=mock_client)
        
        response = await orchestrator.process_command(
            command="Find me jobs in NYC",
            user_id=test_user["_id"]
        )
        
        assert response.success is True
        assert response.task_created is True
        assert response.agent_target == "JOB_HUNTER"
        assert response.task_id is not None
    
    @pytest.mark.asyncio
    async def test_process_command_returns_clarification(self, test_user):
        """Test that unclear commands return clarification request."""
        from app.agents.llm_client import LLMResponse
        mock_client = AsyncMock()
        mock_client.chat = AsyncMock(return_value=LLMResponse(
            content='{"intent_category": "UNKNOWN", "action": null, "entities": {}, "urgency": "MEDIUM", "requires_clarification": true, "clarification_question": "What would you like me to do?"}'
        ))
        
        orchestrator = Orchestrator(llm_client=mock_client)
        
        response = await orchestrator.process_command(
            command="Do something",
            user_id=test_user["_id"]
        )
        
        assert response.requires_clarification is True
        assert response.clarification_question is not None
    
    @pytest.mark.asyncio
    async def test_handle_system_status(self, test_user, test_agent):
        """Test handling system status request."""
        from app.agents.llm_client import LLMResponse
        mock_client = AsyncMock()
        mock_client.chat = AsyncMock(return_value=LLMResponse(
            content='{"intent_category": "SYSTEM", "action": "status", "entities": {}, "urgency": "LOW", "requires_clarification": false}'
        ))
        
        orchestrator = Orchestrator(llm_client=mock_client)
        
        response = await orchestrator.process_command(
            command="System status",
            user_id=test_user["_id"]
        )
        
        assert response.success is True
        assert response.task_created is False
        assert "status" in response.data
    
    @pytest.mark.asyncio
    async def test_handle_capabilities_request(self, test_user):
        """Test handling capabilities request."""
        from app.agents.llm_client import LLMResponse
        mock_client = AsyncMock()
        mock_client.chat = AsyncMock(return_value=LLMResponse(
            content='{"intent_category": "SYSTEM", "action": "what can you do", "entities": {}, "urgency": "LOW", "requires_clarification": false}'
        ))
        
        orchestrator = Orchestrator(llm_client=mock_client)
        
        response = await orchestrator.process_command(
            command="What can you do?",
            user_id=test_user["_id"]
        )
        
        assert response.success is True
        assert "capabilities" in response.data
    
    def test_generate_response_message_job_hunter(self):
        """Test generating response message for Job Hunter."""
        orchestrator = Orchestrator()
        
        message = orchestrator._generate_response_message(
            "JOB_HUNTER", "search_jobs", {}
        )
        
        assert "🔍" in message or "job search" in message.lower()
    
    def test_generate_response_message_crypto_sentinel(self):
        """Test generating response message for Crypto Sentinel."""
        orchestrator = Orchestrator()
        
        message = orchestrator._generate_response_message(
            "CRYPTO_SENTINEL", "morning_brief", {}
        )
        
        assert "📊" in message or "crypto" in message.lower() or "brief" in message.lower()
    
    def test_get_capabilities_message(self):
        """Test capabilities message generation."""
        orchestrator = Orchestrator()
        
        message = orchestrator._get_capabilities_message()
        
        assert "Crypto" in message
        assert "Job" in message
        assert "Project" in message


# =============================================================================
# ORCHESTRATOR API ROUTES TESTS
# =============================================================================

class TestOrchestratorRoutes:
    """Tests for Orchestrator API routes."""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Reset orchestrator before each test."""
        reset_orchestrator()
    
    @pytest.mark.asyncio
    async def test_command_requires_auth(self, client):
        """Test that command endpoint requires authentication."""
        response = await client.post(
            "/api/v1/orchestrator/command",
            json={"command": "Find jobs"}
        )
        assert response.status_code == 403
    
    @pytest.mark.asyncio
    async def test_capabilities_endpoint(self, client, auth_headers):
        """Test capabilities endpoint returns agent info."""
        response = await client.get(
            "/api/v1/orchestrator/capabilities",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "agents" in data
        assert "categories" in data
        assert "JOB_HUNTER" in data["agents"]
        assert "CRYPTO_SENTINEL" in data["agents"]
    
    @pytest.mark.asyncio
    async def test_status_endpoint(self, client, auth_headers, test_agent):
        """Test status endpoint returns system status."""
        response = await client.get(
            "/api/v1/orchestrator/status",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert "agents" in data
        assert "tasks" in data
    
    @pytest.mark.asyncio
    async def test_command_endpoint_with_mock(self, client, auth_headers, test_user):
        """Test command endpoint with mocked orchestrator."""
        # We need to patch the OpenAI calls
        with patch('app.orchestrator.intent_parser.IntentParser.parse') as mock_parse:
            mock_parse.return_value = {
                "intent_category": "JOBS",
                "action": "search",
                "entities": {},
                "urgency": "MEDIUM",
                "requires_clarification": False
            }
            
            response = await client.post(
                "/api/v1/orchestrator/command",
                headers=auth_headers,
                json={"command": "Find jobs in NYC"}
            )
            
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert data["task_created"] is True
            assert data["agent_target"] == "JOB_HUNTER"
    
    @pytest.mark.asyncio
    async def test_command_endpoint_crypto(self, client, auth_headers, test_user):
        """Test command endpoint for crypto requests."""
        with patch('app.orchestrator.intent_parser.IntentParser.parse') as mock_parse:
            mock_parse.return_value = {
                "intent_category": "CRYPTO",
                "action": "analyze",
                "entities": {"crypto_assets": ["BTC"]},
                "urgency": "MEDIUM",
                "requires_clarification": False
            }
            
            response = await client.post(
                "/api/v1/orchestrator/command",
                headers=auth_headers,
                json={"command": "Analyze BTC"}
            )
            
            assert response.status_code == 200
            data = response.json()
            assert data["agent_target"] == "CRYPTO_SENTINEL"
    
    @pytest.mark.asyncio
    async def test_command_endpoint_projects(self, client, auth_headers, test_user):
        """Test command endpoint for project requests."""
        with patch('app.orchestrator.intent_parser.IntentParser.parse') as mock_parse:
            mock_parse.return_value = {
                "intent_category": "PROJECTS",
                "action": "scaffold",
                "entities": {},
                "urgency": "MEDIUM",
                "requires_clarification": False
            }
            
            response = await client.post(
                "/api/v1/orchestrator/command",
                headers=auth_headers,
                json={"command": "Create a new project"}
            )
            
            assert response.status_code == 200
            data = response.json()
            assert data["agent_target"] == "IDEAS_MACHINE"
    
    @pytest.mark.asyncio
    async def test_command_creates_task_in_db(self, client, auth_headers, test_user):
        """Test that command creates task in database."""
        with patch('app.orchestrator.intent_parser.IntentParser.parse') as mock_parse:
            mock_parse.return_value = {
                "intent_category": "JOBS",
                "action": "search",
                "entities": {},
                "urgency": "MEDIUM",
                "requires_clarification": False
            }
            
            response = await client.post(
                "/api/v1/orchestrator/command",
                headers=auth_headers,
                json={"command": "Find growth jobs"}
            )
            
            data = response.json()
            task_id = data["task_id"]
            
            # Verify task exists in database
            tasks = Database.get_collection("task_queue")
            task = await tasks.find_one({"task_id": task_id})
            
            assert task is not None
            assert task["agent_target"] == "JOB_HUNTER"
            assert task["status"] == "PENDING"
    
    @pytest.mark.asyncio
    async def test_command_logs_event(self, client, auth_headers, test_user):
        """Test that command logs event to event stream."""
        with patch('app.orchestrator.intent_parser.IntentParser.parse') as mock_parse:
            mock_parse.return_value = {
                "intent_category": "JOBS",
                "action": "search",
                "entities": {},
                "urgency": "MEDIUM",
                "requires_clarification": False
            }
            
            response = await client.post(
                "/api/v1/orchestrator/command",
                headers=auth_headers,
                json={"command": "Search for jobs"}
            )
            
            # Verify event was logged
            events = Database.get_collection("event_stream")
            event = await events.find_one({"event_type": "COMMAND_PROCESSED"})
            
            assert event is not None
            assert "command" in event["payload"]


# =============================================================================
# INTEGRATION TESTS
# =============================================================================

class TestOrchestratorIntegration:
    """Integration tests for orchestrator flow."""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Reset orchestrator before each test."""
        reset_orchestrator()
    
    @pytest.mark.asyncio
    async def test_full_job_search_flow(self, client, auth_headers, test_user):
        """Test complete flow from command to task creation."""
        with patch('app.orchestrator.intent_parser.IntentParser.parse') as mock_parse:
            mock_parse.return_value = {
                "intent_category": "JOBS",
                "action": "search",
                "entities": {},
                "urgency": "MEDIUM",
                "requires_clarification": False
            }
            
            # Send command
            response = await client.post(
                "/api/v1/orchestrator/command",
                headers=auth_headers,
                json={"command": "Find growth lead jobs in NYC"}
            )
            
            assert response.status_code == 200
            command_data = response.json()
            
            # Verify task was created
            task_response = await client.get(
                f"/api/v1/tasks/{command_data['task_id']}",
                headers=auth_headers
            )
            
            assert task_response.status_code == 200
            task_data = task_response.json()
            assert task_data["agent_target"] == "JOB_HUNTER"
            assert task_data["status"] == "PENDING"
    
    @pytest.mark.asyncio
    async def test_system_query_no_task_created(self, client, auth_headers, test_user):
        """Test that system queries don't create tasks."""
        with patch('app.orchestrator.intent_parser.IntentParser.parse') as mock_parse:
            mock_parse.return_value = {
                "intent_category": "SYSTEM",
                "action": "status",
                "entities": {},
                "urgency": "LOW",
                "requires_clarification": False
            }
            
            response = await client.post(
                "/api/v1/orchestrator/command",
                headers=auth_headers,
                json={"command": "System status"}
            )
            
            data = response.json()
            
            assert data["success"] is True
            assert data["task_created"] is False
            assert data["task_id"] is None

