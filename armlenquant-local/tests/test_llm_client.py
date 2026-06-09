"""
Tests for LLM Client - Multi-provider support (Gemini and OpenAI)
"""
import pytest
import json
from unittest.mock import AsyncMock, MagicMock, patch


class TestLLMResponse:
    """Tests for LLMResponse class."""
    
    def test_response_creation(self):
        """Test creating an LLM response."""
        from agents.llm_client import LLMResponse
        
        response = LLMResponse(content="Hello, world!")
        
        assert response.content == "Hello, world!"
        assert response.raw_response is None
    
    def test_response_with_raw(self):
        """Test response with raw response object."""
        from agents.llm_client import LLMResponse
        
        raw = {"id": "123", "model": "test"}
        response = LLMResponse(content="Test", raw_response=raw)
        
        assert response.content == "Test"
        assert response.raw_response == raw
    
    def test_response_json_parsing(self):
        """Test JSON parsing from response."""
        from agents.llm_client import LLMResponse
        
        json_content = '{"name": "TestAgent", "version": "1.0.0"}'
        response = LLMResponse(content=json_content)
        
        parsed = response.json()
        
        assert parsed["name"] == "TestAgent"
        assert parsed["version"] == "1.0.0"
    
    def test_response_json_parsing_invalid(self):
        """Test JSON parsing with invalid JSON."""
        from agents.llm_client import LLMResponse
        
        response = LLMResponse(content="not valid json")
        
        with pytest.raises(json.JSONDecodeError):
            response.json()


class TestLLMProvider:
    """Tests for LLMProvider enum."""
    
    def test_provider_values(self):
        """Test provider enum values."""
        from agents.llm_client import LLMProvider
        
        assert LLMProvider.GEMINI == "gemini"
        assert LLMProvider.OPENAI == "openai"
    
    def test_provider_from_string(self):
        """Test creating provider from string."""
        from agents.llm_client import LLMProvider
        
        provider = LLMProvider("gemini")
        assert provider == LLMProvider.GEMINI
        
        provider = LLMProvider("openai")
        assert provider == LLMProvider.OPENAI


class TestGeminiClient:
    """Tests for GeminiClient."""
    
    def test_client_initialization_without_library(self):
        """Test client handles missing google-generativeai gracefully."""
        from agents.llm_client import GeminiClient
        
        with patch.dict('sys.modules', {'google.generativeai': None}):
            # This will set _available to False due to import error handling
            client = GeminiClient(api_key="test-key")
            # May or may not be available depending on actual library presence


class TestOpenAIClient:
    """Tests for OpenAIClient."""
    
    def test_client_initialization(self):
        """Test OpenAI client initialization."""
        from agents.llm_client import OpenAIClient
        
        with patch('openai.AsyncOpenAI') as mock_openai:
            client = OpenAIClient(api_key="test-key", model="gpt-4o")
            
            assert client.model == "gpt-4o"
            assert client._available is True


class TestLLMClient:
    """Tests for unified LLMClient."""
    
    def test_client_creation_with_gemini_primary(self):
        """Test client creation with Gemini as primary."""
        from agents.llm_client import LLMClient, LLMProvider, GeminiClient
        
        with patch.object(GeminiClient, '__init__', return_value=None):
            with patch.object(GeminiClient, 'is_available', new_callable=lambda: property(lambda self: True)):
                client = LLMClient(
                    provider=LLMProvider.GEMINI,
                    gemini_api_key="test-key"
                )
                
                assert client.is_available is True
                assert client.active_provider == "gemini"
    
    def test_client_creation_with_openai_primary(self):
        """Test client creation with OpenAI as primary."""
        from agents.llm_client import LLMClient, LLMProvider, OpenAIClient
        
        with patch.object(OpenAIClient, '__init__', return_value=None):
            with patch.object(OpenAIClient, 'is_available', new_callable=lambda: property(lambda self: True)):
                client = LLMClient(
                    provider=LLMProvider.OPENAI,
                    openai_api_key="test-key"
                )
                
                assert client.is_available is True
                assert client.active_provider == "openai"
    
    def test_client_fallback_to_openai(self):
        """Test fallback from Gemini to OpenAI when Gemini unavailable."""
        from agents.llm_client import LLMClient, LLMProvider
        
        # Create a client where Gemini is unavailable and OpenAI is available
        # This simulates the fallback behavior
        client = LLMClient(
            provider=LLMProvider.GEMINI,
            gemini_api_key=None,  # No key = unavailable
            openai_api_key="test-openai-key",
            auto_fallback=True
        )
        
        # If Gemini is unavailable (no API key), should fall back to OpenAI
        assert client.is_available is True
        assert client.active_provider == "openai"
    
    def test_client_fallback_to_gemini(self):
        """Test fallback from OpenAI to Gemini when OpenAI unavailable."""
        from agents.llm_client import LLMClient, LLMProvider
        
        # Create a client where OpenAI is unavailable and Gemini is available
        client = LLMClient(
            provider=LLMProvider.OPENAI,
            gemini_api_key="test-gemini-key",
            openai_api_key=None,  # No key = unavailable
            auto_fallback=True
        )
        
        # If OpenAI is unavailable (no API key), should fall back to Gemini
        assert client.is_available is True
        assert client.active_provider == "gemini"
    
    def test_client_no_fallback(self):
        """Test no fallback when auto_fallback is disabled."""
        from agents.llm_client import LLMClient, LLMProvider
        
        with patch('agents.llm_client.GeminiClient') as mock_gemini, \
             patch('agents.llm_client.OpenAIClient') as mock_openai:
            
            # Gemini unavailable
            gemini_instance = MagicMock()
            gemini_instance.is_available = False
            mock_gemini.return_value = gemini_instance
            
            # OpenAI available but fallback disabled
            openai_instance = MagicMock()
            openai_instance.is_available = True
            mock_openai.return_value = openai_instance
            
            client = LLMClient(
                provider=LLMProvider.GEMINI,
                gemini_api_key="test-gemini-key",
                openai_api_key="test-openai-key",
                auto_fallback=False
            )
            
            # Should be unavailable since primary failed and fallback disabled
            assert client.is_available is False
    
    def test_client_no_providers_available(self):
        """Test when no providers are available."""
        from agents.llm_client import LLMClient, LLMProvider
        
        client = LLMClient(
            provider=LLMProvider.GEMINI,
            gemini_api_key=None,
            openai_api_key=None
        )
        
        assert client.is_available is False
    
    @pytest.mark.asyncio
    async def test_chat_success(self):
        """Test successful chat completion."""
        from agents.llm_client import LLMClient, LLMProvider, LLMResponse
        
        with patch('agents.llm_client.GeminiClient') as mock_gemini:
            gemini_instance = MagicMock()
            gemini_instance.is_available = True
            
            async def mock_chat(*args, **kwargs):
                return LLMResponse(content='{"response": "test"}')
            
            gemini_instance.chat = AsyncMock(side_effect=mock_chat)
            mock_gemini.return_value = gemini_instance
            
            client = LLMClient(
                provider=LLMProvider.GEMINI,
                gemini_api_key="test-key"
            )
            
            response = await client.chat(
                messages=[{"role": "user", "content": "Hello"}],
                temperature=0.7
            )
            
            assert response.content == '{"response": "test"}'
    
    @pytest.mark.asyncio
    async def test_chat_no_client_raises_error(self):
        """Test chat raises error when no client available."""
        from agents.llm_client import LLMClient, LLMProvider
        
        client = LLMClient(
            provider=LLMProvider.GEMINI,
            gemini_api_key=None,
            openai_api_key=None
        )
        
        with pytest.raises(RuntimeError) as exc_info:
            await client.chat(messages=[{"role": "user", "content": "Hello"}])
        
        assert "No LLM client available" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_chat_fallback_on_error(self):
        """Test chat falls back to alternative provider on error."""
        from agents.llm_client import LLMClient, LLMProvider, LLMResponse, GeminiClient, OpenAIClient
        
        # Create mock instances
        mock_gemini = MagicMock(spec=GeminiClient)
        mock_gemini.is_available = True
        mock_gemini.chat = AsyncMock(side_effect=Exception("Gemini error"))
        
        mock_openai = MagicMock(spec=OpenAIClient)
        mock_openai.is_available = True
        mock_openai.chat = AsyncMock(return_value=LLMResponse(content='{"from": "openai"}'))
        
        # Create client and manually set the clients
        client = LLMClient(
            provider=LLMProvider.GEMINI,
            gemini_api_key=None,
            openai_api_key=None,
            auto_fallback=True
        )
        
        # Manually set up the clients for testing
        client._gemini = mock_gemini
        client._openai = mock_openai
        client._active_client = mock_gemini
        
        response = await client.chat(
            messages=[{"role": "user", "content": "Hello"}]
        )
        
        assert response.content == '{"from": "openai"}'


class TestGetLLMClient:
    """Tests for get_llm_client factory function."""
    
    def test_get_llm_client_from_settings(self):
        """Test getting LLM client from settings."""
        from agents.llm_client import get_llm_client, LLMClient
        
        with patch('poller.config.get_settings') as mock_settings:
            settings = MagicMock()
            settings.llm_provider = "gemini"
            settings.llm_auto_fallback = True
            settings.gemini_api_key = "test-gemini-key"
            settings.gemini_model = "gemini-2.0-flash"
            settings.openai_api_key = "test-openai-key"
            settings.openai_model = "gpt-4o"
            mock_settings.return_value = settings
            
            # The client should be created successfully
            client = get_llm_client()
            
            assert client is not None
            assert client.primary_provider.value == "gemini"


class TestLLMClientIntegration:
    """Integration tests for LLM client components."""
    
    def test_provider_selection_logic(self):
        """Test the provider selection logic comprehensively."""
        from agents.llm_client import LLMClient, LLMProvider
        
        # Test: Both keys provided, Gemini primary -> Gemini selected
        client = LLMClient(
            provider=LLMProvider.GEMINI,
            gemini_api_key="key1",
            openai_api_key="key2"
        )
        
        # Should select Gemini as primary
        assert client.active_provider == "gemini"
    
    def test_model_configuration(self):
        """Test model configuration is passed correctly."""
        from agents.llm_client import LLMClient, LLMProvider
        
        with patch('agents.llm_client.GeminiClient') as mock_gemini:
            mock_gemini.return_value = MagicMock(is_available=True)
            
            client = LLMClient(
                provider=LLMProvider.GEMINI,
                gemini_api_key="test-key",
                gemini_model="gemini-1.5-pro"
            )
            
            # Verify model was passed to client
            mock_gemini.assert_called_once_with(
                api_key="test-key",
                model="gemini-1.5-pro"
            )

