"""
Knowledge Ingestion Pipeline
Handles ingestion of documents into the knowledge base.
"""
import re
from datetime import datetime
from typing import List, Dict, Any, Optional
from uuid import uuid4
from loguru import logger

from app.db import Database
from app.rag.embeddings import get_embedding_service
from app.rag.chunker import TextChunker, MarkdownChunker


class KnowledgeSource:
    """Knowledge source types."""
    CV = "CV"
    TRADING_RULES = "TRADING_RULES"
    PROJECT_DOC = "PROJECT_DOC"
    USER_PREFERENCE = "USER_PREFERENCE"
    JOB_DESCRIPTION = "JOB_DESCRIPTION"
    COMPANY_INFO = "COMPANY_INFO"


class KnowledgeIngestion:
    """
    Handles ingestion of documents into the knowledge base.
    """
    
    def __init__(self):
        self.embedding_service = get_embedding_service()
        self.text_chunker = TextChunker()
        self.markdown_chunker = MarkdownChunker()
    
    async def ingest_document(
        self,
        content: str,
        source: str,
        title: Optional[str] = None,
        tags: List[str] = None,
        metadata: Dict[str, Any] = None,
        user_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Ingest a document into the knowledge base.
        
        Args:
            content: Document content
            source: Source type (CV, TRADING_RULES, etc.)
            title: Optional document title
            tags: Tags for filtering
            metadata: Additional metadata
            user_id: Owner user ID
            
        Returns:
            Ingestion result with document IDs
        """
        logger.info(f"Ingesting document: {title or 'Untitled'} ({source})")
        
        if not content:
            return {
                "document_title": title,
                "source": source,
                "chunks_created": 0,
                "doc_ids": []
            }
        
        # Choose chunker based on content
        chunker = self.markdown_chunker if self._is_markdown(content) else self.text_chunker
        
        # Chunk the document
        base_metadata = {
            "source": source,
            "title": title,
            "tags": tags or [],
            "user_id": user_id,
            **(metadata or {})
        }
        
        chunks = chunker.chunk_text(content, base_metadata)
        
        if not chunks:
            return {
                "document_title": title,
                "source": source,
                "chunks_created": 0,
                "doc_ids": []
            }
        
        # Generate embeddings
        texts = [chunk["content"] for chunk in chunks]
        embeddings = await self.embedding_service.embed_batch(texts)
        
        # Store in database
        kb = Database.get_collection("knowledge_base")
        
        doc_ids = []
        now = datetime.utcnow()
        
        for i, (chunk, embedding) in enumerate(zip(chunks, embeddings)):
            doc_id = str(uuid4())
            doc = {
                "_id": doc_id,
                "doc_id": doc_id,
                "content": chunk["content"],
                "embedding": embedding,
                "source": source,
                "title": title,
                "tags": tags or [],
                "metadata": chunk["metadata"],
                "user_id": user_id,
                "chunk_index": i,
                "total_chunks": len(chunks),
                "created_at": now,
                "updated_at": now
            }
            await kb.insert_one(doc)
            doc_ids.append(doc_id)
        
        logger.info(f"Ingested {len(doc_ids)} chunks for document: {title}")
        
        return {
            "document_title": title,
            "source": source,
            "chunks_created": len(doc_ids),
            "doc_ids": doc_ids
        }
    
    async def ingest_cv(
        self,
        content: str,
        user_id: str,
        title: str = "Master CV"
    ) -> Dict[str, Any]:
        """Ingest user's CV."""
        return await self.ingest_document(
            content=content,
            source=KnowledgeSource.CV,
            title=title,
            tags=["cv", "career", "skills", "experience"],
            user_id=user_id
        )
    
    async def ingest_trading_rules(
        self,
        content: str,
        user_id: str
    ) -> Dict[str, Any]:
        """Ingest trading rules and preferences."""
        return await self.ingest_document(
            content=content,
            source=KnowledgeSource.TRADING_RULES,
            title="Trading Rules",
            tags=["trading", "crypto", "rules", "risk"],
            user_id=user_id
        )
    
    async def delete_document(
        self,
        title: str,
        user_id: str
    ) -> int:
        """Delete all chunks of a document."""
        kb = Database.get_collection("knowledge_base")
        result = await kb.delete_many({
            "title": title,
            "user_id": user_id
        })
        logger.info(f"Deleted {result.deleted_count} chunks for: {title}")
        return result.deleted_count
    
    def _is_markdown(self, content: str) -> bool:
        """Check if content is markdown."""
        markdown_patterns = [
            r'^#{1,6}\s',      # Headers
            r'^\*\s',          # Unordered lists (asterisk)
            r'^-\s',           # Unordered lists (dash)
            r'^\d+\.\s',       # Ordered lists
            r'\*\*.+\*\*',     # Bold
            r'`.+`',           # Code
        ]
        for pattern in markdown_patterns:
            if re.search(pattern, content, re.MULTILINE):
                return True
        return False

