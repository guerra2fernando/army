"""
Embedding Generation Service
Generates vector embeddings using OpenAI or Gemini API.
"""
from typing import List, Optional
import google.generativeai as genai
from openai import AsyncOpenAI
from loguru import logger
from app.config import get_settings

settings = get_settings()


class EmbeddingService:
    """
    Generate embeddings using OpenAI or Gemini API based on configuration.
    """

    def __init__(self):
        configured_provider = (settings.embedding_provider or "openai").lower()
        self.provider = configured_provider
        self.dimensions = 768 if self.provider == "gemini" else 1536  # Gemini uses 768, OpenAI 1536
        self.logger = logger.bind(service="EmbeddingService")

        if self.provider == "openai":
            if not settings.openai_api_key:
                raise RuntimeError("OPENAI_API_KEY is required when EMBEDDING_PROVIDER=openai")
            self.openai_client = AsyncOpenAI(api_key=settings.openai_api_key)
            self.model = settings.openai_embedding_model
            self.logger.info("Using OpenAI for embeddings")
        elif self.provider == "gemini":
            if not settings.gemini_api_key:
                raise RuntimeError("GEMINI_API_KEY is required when EMBEDDING_PROVIDER=gemini")
            genai.configure(api_key=settings.gemini_api_key)
            self.model = "models/text-embedding-004"  # Gemini embedding model
            self.logger.info("Using Gemini for embeddings")
        else:
            raise ValueError(f"Unsupported embedding provider: {self.provider}. Use 'openai' or 'gemini'")
    
    async def embed_text(self, text: str) -> List[float]:
        """
        Generate embedding for a single text.

        Args:
            text: Input text to embed

        Returns:
            List of floats representing the embedding vector
        """
        try:
            if self.provider == "openai":
                response = await self.openai_client.embeddings.create(
                    input=text,
                    model=self.model
                )
                return response.data[0].embedding
            elif self.provider == "gemini":
                result = genai.embed_content(
                    model=self.model,
                    content=text,
                    task_type="retrieval_document"
                )
                return result['embedding']
            else:
                raise ValueError(f"Unsupported provider: {self.provider}")

        except Exception as e:
            logger.error("Embedding request failed")
            raise
    
    async def embed_batch(self, texts: List[str]) -> List[List[float]]:
        """
        Generate embeddings for multiple texts.

        Args:
            texts: List of texts to embed

        Returns:
            List of embedding vectors
        """
        if not texts:
            return []

        try:
            if self.provider == "openai":
                # OpenAI supports batch embedding
                response = await self.openai_client.embeddings.create(
                    input=texts,
                    model=self.model
                )
                return [item.embedding for item in response.data]
            elif self.provider == "gemini":
                # Gemini doesn't have native batch support, so we do individual calls
                # Note: This could be optimized with concurrent calls if needed
                embeddings = []
                for text in texts:
                    result = genai.embed_content(
                        model=self.model,
                        content=text,
                        task_type="retrieval_document"
                    )
                    embeddings.append(result['embedding'])
                return embeddings
            else:
                raise ValueError(f"Unsupported provider: {self.provider}")

        except Exception as e:
            logger.error("Batch embedding request failed")
            raise


# Singleton
_embedding_service = None


def get_embedding_service() -> EmbeddingService:
    """Get singleton EmbeddingService instance."""
    global _embedding_service
    if _embedding_service is None:
        _embedding_service = EmbeddingService()
    return _embedding_service
