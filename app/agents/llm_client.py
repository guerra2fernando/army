"""
LLM Client - Unified interface for multiple LLM providers.
Supports Google Gemini (default) and OpenAI.

This is the cloud API version that uses app.config settings.
"""
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List
from enum import Enum
import json
from loguru import logger


class LLMProvider(str, Enum):
    """Supported LLM providers."""
    GEMINI = "gemini"
    OPENAI = "openai"


class LLMResponse:
    """Standardized LLM response."""
    
    def __init__(self, content: str, raw_response: Any = None):
        self.content = content
        self.raw_response = raw_response
    
    def json(self) -> Dict[str, Any]:
        """Parse response as JSON."""
        return json.loads(self.content)


class BaseLLMClient(ABC):
    """Abstract base class for LLM clients."""
    
    @abstractmethod
    async def chat(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        json_response: bool = False
    ) -> LLMResponse:
        """Send a chat completion request."""
        pass


class GeminiClient(BaseLLMClient):
    """Google Gemini API client."""
    
    def __init__(self, api_key: str, model: str = "gemini-2.0-flash"):
        try:
            import google.generativeai as genai
            genai.configure(api_key=api_key)
            self.model = genai.GenerativeModel(model)
            self.model_name = model
            self._available = True
            logger.bind(component="llm_client").info(f"Gemini client initialized with model: {model}")
        except ImportError:
            logger.bind(component="llm_client").warning("google-generativeai not installed")
            self._available = False
        except Exception as e:
            logger.bind(component="llm_client").error(f"Failed to initialize Gemini client: {e}")
            self._available = False
    
    @property
    def is_available(self) -> bool:
        return self._available
    
    async def chat(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        json_response: bool = False
    ) -> LLMResponse:
        """Send a chat completion request to Gemini."""
        import google.generativeai as genai
        
        # Convert OpenAI-style messages to Gemini format
        system_instruction = None
        conversation_parts = []
        
        for msg in messages:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            
            if role == "system":
                system_instruction = content
            elif role == "user":
                conversation_parts.append({"role": "user", "parts": [content]})
            elif role == "assistant":
                conversation_parts.append({"role": "model", "parts": [content]})
        
        # Configure generation settings
        generation_config = genai.GenerationConfig(
            temperature=temperature,
            max_output_tokens=max_tokens or 4096,
        )
        
        if json_response:
            generation_config.response_mime_type = "application/json"
        
        # Create model with system instruction if provided
        if system_instruction:
            model = genai.GenerativeModel(
                self.model_name,
                system_instruction=system_instruction,
                generation_config=generation_config
            )
        else:
            model = genai.GenerativeModel(
                self.model_name,
                generation_config=generation_config
            )
        
        # If only one user message, use simple generate_content
        if len(conversation_parts) == 1:
            response = await model.generate_content_async(
                conversation_parts[0]["parts"][0]
            )
        else:
            # Use chat for multi-turn conversations
            chat = model.start_chat(history=conversation_parts[:-1])
            last_message = conversation_parts[-1]["parts"][0] if conversation_parts else ""
            response = await chat.send_message_async(last_message)
        
        return LLMResponse(
            content=response.text,
            raw_response=response
        )


class OpenAIClient(BaseLLMClient):
    """OpenAI API client."""
    
    def __init__(self, api_key: str, model: str = "gpt-4o"):
        try:
            from openai import AsyncOpenAI
            self.client = AsyncOpenAI(api_key=api_key)
            self.model = model
            self._available = True
            logger.bind(component="llm_client").info(f"OpenAI client initialized with model: {model}")
        except ImportError:
            logger.bind(component="llm_client").warning("openai not installed")
            self._available = False
        except Exception as e:
            logger.bind(component="llm_client").error(f"Failed to initialize OpenAI client: {e}")
            self._available = False
    
    @property
    def is_available(self) -> bool:
        return self._available
    
    async def chat(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        json_response: bool = False
    ) -> LLMResponse:
        """Send a chat completion request to OpenAI."""
        kwargs = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
        }
        
        if max_tokens:
            kwargs["max_tokens"] = max_tokens
        
        if json_response:
            kwargs["response_format"] = {"type": "json_object"}
        
        response = await self.client.chat.completions.create(**kwargs)
        
        return LLMResponse(
            content=response.choices[0].message.content,
            raw_response=response
        )


class LLMClient:
    """
    Unified LLM client with automatic fallback.
    Uses the configured provider, falls back to alternative if unavailable.
    """
    
    def __init__(
        self,
        provider: LLMProvider = LLMProvider.GEMINI,
        gemini_api_key: Optional[str] = None,
        gemini_model: str = "gemini-2.0-flash",
        openai_api_key: Optional[str] = None,
        openai_model: str = "gpt-4o",
        auto_fallback: bool = True
    ):
        self.primary_provider = provider
        self.auto_fallback = auto_fallback
        self.logger = logger.bind(component="llm_client")
        
        # Initialize clients
        self._gemini: Optional[GeminiClient] = None
        self._openai: Optional[OpenAIClient] = None
        
        if gemini_api_key:
            self._gemini = GeminiClient(api_key=gemini_api_key, model=gemini_model)
        
        if openai_api_key:
            self._openai = OpenAIClient(api_key=openai_api_key, model=openai_model)
        
        # Determine active client
        self._active_client: Optional[BaseLLMClient] = None
        self._setup_active_client()
    
    def _setup_active_client(self):
        """Set up the active client based on provider preference."""
        if self.primary_provider == LLMProvider.GEMINI:
            if self._gemini and self._gemini.is_available:
                self._active_client = self._gemini
                self.logger.info("Using Gemini as primary LLM provider")
            elif self.auto_fallback and self._openai and self._openai.is_available:
                self._active_client = self._openai
                self.logger.warning("Gemini unavailable, falling back to OpenAI")
        else:  # OpenAI primary
            if self._openai and self._openai.is_available:
                self._active_client = self._openai
                self.logger.info("Using OpenAI as primary LLM provider")
            elif self.auto_fallback and self._gemini and self._gemini.is_available:
                self._active_client = self._gemini
                self.logger.warning("OpenAI unavailable, falling back to Gemini")
        
        if not self._active_client:
            self.logger.error("No LLM client available!")
    
    @property
    def is_available(self) -> bool:
        """Check if any LLM client is available."""
        return self._active_client is not None
    
    @property
    def active_provider(self) -> Optional[str]:
        """Get the name of the active provider."""
        if self._active_client is None:
            return None
        client_class_name = type(self._active_client).__name__
        if "Gemini" in client_class_name or self._active_client is self._gemini:
            return "gemini"
        elif "OpenAI" in client_class_name or self._active_client is self._openai:
            return "openai"
        return None
    
    async def chat(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        json_response: bool = False
    ) -> LLMResponse:
        """
        Send a chat completion request.
        
        Args:
            messages: List of message dicts with 'role' and 'content'
            temperature: Sampling temperature (0-1)
            max_tokens: Maximum tokens in response
            json_response: Request JSON-formatted response
            
        Returns:
            LLMResponse with content and raw response
            
        Raises:
            RuntimeError: If no LLM client is available
        """
        if not self._active_client:
            raise RuntimeError("No LLM client available. Please configure GEMINI_API_KEY or OPENAI_API_KEY.")
        
        try:
            return await self._active_client.chat(
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                json_response=json_response
            )
        except Exception as e:
            self.logger.error(f"LLM request failed: {e}")
            
            # Do not fallback if the failure is clearly due to invalid credentials;
            # switching providers won't help and just spams another error.
            auth_errors = ("invalid_api_key", "Incorrect API key", "401")
            if any(err in str(e) for err in auth_errors):
                raise

            # Try fallback if auto_fallback is enabled
            if self.auto_fallback:
                fallback_client = self._get_fallback_client()
                if fallback_client:
                    self.logger.info("Attempting fallback to alternative provider")
                    return await fallback_client.chat(
                        messages=messages,
                        temperature=temperature,
                        max_tokens=max_tokens,
                        json_response=json_response
                    )
            
            raise
    
    def _get_fallback_client(self) -> Optional[BaseLLMClient]:
        """Get the fallback client if available."""
        if self._active_client is self._gemini:
            if self._openai and self._openai.is_available:
                return self._openai
        elif self._active_client is self._openai:
            if self._gemini and self._gemini.is_available:
                return self._gemini
        return None


def get_llm_client() -> LLMClient:
    """
    Factory function to create an LLM client from cloud API settings.
    
    Returns:
        Configured LLMClient instance
    """
    from app.config import get_settings
    settings = get_settings()
    
    # Determine primary provider
    provider = LLMProvider(settings.llm_provider.lower())
    
    return LLMClient(
        provider=provider,
        gemini_api_key=settings.gemini_api_key or None,
        gemini_model=settings.gemini_model,
        openai_api_key=settings.openai_api_key or None,
        openai_model=settings.openai_model,
        auto_fallback=settings.llm_auto_fallback
    )

