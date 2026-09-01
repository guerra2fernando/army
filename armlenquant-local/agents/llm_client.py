"""
LLM Client - Unified interface for multiple LLM providers.
Supports Google Gemini (default) and OpenAI.
"""
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List
from enum import Enum
import json
import asyncio
from loguru import logger


class LLMProvider(str, Enum):
    """Supported LLM providers."""
    GEMINI = "gemini"
    OPENAI = "openai"
    CLOUDFLARE = "cloudflare"


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
        # Gemini uses a different format: system instruction + conversation
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


class CloudflareWorkersAIClient(BaseLLMClient):
    """Authenticated OpenAI-compatible client for the Workers AI gateway."""

    TRANSIENT_STATUS_CODES = {429, 502, 503, 504}

    def __init__(self, api_key: str, base_url: str, model: str, timeout: float = 30.0):
        try:
            from openai import AsyncOpenAI
            self.client = AsyncOpenAI(api_key=api_key, base_url=base_url, timeout=timeout, max_retries=0)
            self.model = model
            self._available = bool(api_key and base_url and model)
            logger.bind(component="llm_client", provider="cloudflare").info(
                "Cloudflare Workers AI client initialized"
            )
        except ImportError:
            logger.bind(component="llm_client", provider="cloudflare").warning("openai not installed")
            self._available = False
        except Exception:
            logger.bind(component="llm_client", provider="cloudflare").error(
                "Failed to initialize Cloudflare Workers AI client"
            )
            self._available = False

    @property
    def is_available(self) -> bool:
        return self._available

    async def chat(self, messages, temperature=0.7, max_tokens=None, json_response=False):
        kwargs = {"model": self.model, "messages": messages, "temperature": temperature}
        if max_tokens is not None:
            kwargs["max_completion_tokens"] = max_tokens
        if json_response:
            kwargs["response_format"] = {"type": "json_object"}
        for attempt in range(4):
            try:
                response = await self.client.chat.completions.create(**kwargs)
                return LLMResponse(content=response.choices[0].message.content or "", raw_response=response)
            except Exception as exc:
                status = getattr(exc, "status_code", None)
                if status in (400, 401, 403):
                    raise RuntimeError("Cloudflare Workers AI request failed") from exc
                if status not in self.TRANSIENT_STATUS_CODES and status is not None:
                    raise RuntimeError("Cloudflare Workers AI request failed") from exc
                if attempt == 3:
                    raise RuntimeError("Cloudflare Workers AI request failed after retries") from exc
                await asyncio.sleep(0.5 * (2 ** attempt))
        raise RuntimeError("Cloudflare Workers AI request failed")


class LLMClient:
    """
    Unified LLM client with automatic fallback.
    Uses Gemini by default, falls back to OpenAI if Gemini is unavailable.
    """
    
    def __init__(
        self,
        provider: LLMProvider = LLMProvider.GEMINI,
        gemini_api_key: Optional[str] = None,
        gemini_model: str = "gemini-2.0-flash",
        openai_api_key: Optional[str] = None,
        openai_model: str = "gpt-4o",
        cloudflare_api_key: Optional[str] = None,
        cloudflare_base_url: str = "https://ai.army.lengrowth.com/v1",
        cloudflare_model: str = "@cf/deepseek-ai/deepseek-v4-pro-0813",
        auto_fallback: bool = True
    ):
        self.primary_provider = provider
        self.auto_fallback = auto_fallback
        self.logger = logger.bind(component="llm_client")
        
        # Initialize clients
        self._gemini: Optional[GeminiClient] = None
        self._openai: Optional[OpenAIClient] = None
        self._cloudflare: Optional[CloudflareWorkersAIClient] = None
        
        if gemini_api_key:
            self._gemini = GeminiClient(api_key=gemini_api_key, model=gemini_model)
        
        if openai_api_key:
            self._openai = OpenAIClient(api_key=openai_api_key, model=openai_model)
        if cloudflare_api_key:
            self._cloudflare = CloudflareWorkersAIClient(cloudflare_api_key, cloudflare_base_url, cloudflare_model)
        
        # Determine active client
        self._active_client: Optional[BaseLLMClient] = None
        self._setup_active_client()
    
    def _setup_active_client(self):
        """Set up the active client based on provider preference."""
        if self.primary_provider == LLMProvider.CLOUDFLARE:
            if self._cloudflare and self._cloudflare.is_available:
                self._active_client = self._cloudflare
                self.logger.info("Using Cloudflare Workers AI as primary LLM provider")
            elif self.auto_fallback:
                self._active_client = self._first_available(self._gemini, self._openai)
        elif self.primary_provider == LLMProvider.GEMINI:
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

    @staticmethod
    def _first_available(*clients):
        return next((client for client in clients if client and client.is_available), None)
    
    @property
    def is_available(self) -> bool:
        """Check if any LLM client is available."""
        return self._active_client is not None
    
    @property
    def active_provider(self) -> Optional[str]:
        """Get the name of the active provider."""
        if self._active_client is None:
            return None
        # Check by class name to work with both real and mocked classes
        client_class_name = type(self._active_client).__name__
        if "Gemini" in client_class_name or self._active_client is self._gemini:
            return "gemini"
        elif "OpenAI" in client_class_name or self._active_client is self._openai:
            return "openai"
        elif "Cloudflare" in client_class_name or self._active_client is self._cloudflare:
            return "cloudflare"
        # Fallback: check if it's one of our stored clients
        if self._active_client is self._gemini:
            return "gemini"
        if self._active_client is self._openai:
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
            raise RuntimeError("No LLM client available. Configure a supported chat provider.")
        
        import asyncio

        max_retries = 3
        base_delay = 2  # seconds

        for attempt in range(max_retries + 1):
            try:
                return await self._active_client.chat(
                    messages=messages,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    json_response=json_response
                )
            except Exception as e:
                error_msg = str(e).lower()

                # Check if it's a rate limit error (429)
                is_rate_limit = (
                    "429" in error_msg or
                    "resource exhausted" in error_msg or
                    "quota exceeded" in error_msg or
                    "rate limit" in error_msg
                )

                if is_rate_limit and attempt < max_retries:
                    delay = base_delay * (2 ** attempt)  # Exponential backoff
                    self.logger.warning(f"Rate limit hit (attempt {attempt + 1}/{max_retries + 1}). Retrying in {delay}s...")
                    await asyncio.sleep(delay)
                    continue

                self.logger.error(f"LLM request failed: {e}")

                # Try fallback if auto_fallback is enabled and not a rate limit
                if self.auto_fallback and not is_rate_limit:
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
        # Use identity check to determine which client is active
        if self._active_client is self._gemini:
            if self._openai and self._openai.is_available:
                return self._openai
        elif self._active_client is self._openai:
            if self._gemini and self._gemini.is_available:
                return self._gemini
        elif self._active_client is self._cloudflare:
            return self._first_available(self._gemini, self._openai)
        return None


def get_llm_client() -> LLMClient:
    """
    Factory function to create an LLM client from settings.
    
    Returns:
        Configured LLMClient instance
    """
    from poller.config import get_settings
    settings = get_settings()
    
    # Determine primary provider
    provider = LLMProvider(settings.llm_provider.lower())
    
    return LLMClient(
        provider=provider,
        gemini_api_key=settings.gemini_api_key or None,
        gemini_model=settings.gemini_model,
        openai_api_key=settings.openai_api_key or None,
        openai_model=settings.openai_model,
        cloudflare_api_key=settings.cloudflare_ai_gateway_token or None,
        cloudflare_base_url=settings.cloudflare_ai_base_url,
        cloudflare_model=settings.cloudflare_ai_model,
        auto_fallback=settings.llm_auto_fallback
    )

