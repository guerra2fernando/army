"""
Knowledge Base Service
Main interface for RAG operations.
"""
from typing import List, Dict, Any, Optional
from loguru import logger

from app.db import Database
from app.rag.ingestion import KnowledgeIngestion, KnowledgeSource
from app.rag.retriever import SemanticRetriever, get_retriever


class KnowledgeBase:
    """
    Main interface for the knowledge base system.
    Provides unified access to ingestion and retrieval operations.
    """
    
    def __init__(self):
        self.ingestion = KnowledgeIngestion()
        self.retriever = get_retriever()
    
    # =========================================================================
    # Ingestion
    # =========================================================================
    
    async def add_document(
        self,
        content: str,
        source: str,
        title: str,
        tags: List[str] = None,
        user_id: str = None
    ) -> Dict[str, Any]:
        """Add a document to the knowledge base."""
        return await self.ingestion.ingest_document(
            content=content,
            source=source,
            title=title,
            tags=tags,
            user_id=user_id
        )
    
    async def add_cv(self, content: str, user_id: str) -> Dict[str, Any]:
        """Add user's CV."""
        return await self.ingestion.ingest_cv(content, user_id)
    
    async def add_trading_rules(self, content: str, user_id: str) -> Dict[str, Any]:
        """Add trading rules."""
        return await self.ingestion.ingest_trading_rules(content, user_id)
    
    async def remove_document(self, title: str, user_id: str) -> int:
        """Remove a document by title."""
        return await self.ingestion.delete_document(title, user_id)
    
    # =========================================================================
    # Retrieval
    # =========================================================================
    
    async def search(
        self,
        query: str,
        limit: int = 5,
        source: str = None,
        tags: List[str] = None,
        user_id: str = None
    ) -> List[Dict[str, Any]]:
        """Search the knowledge base."""
        return await self.retriever.search(
            query=query,
            limit=limit,
            source_filter=source,
            tag_filter=tags,
            user_id=user_id
        )
    
    async def get_context(
        self,
        query: str,
        user_id: str = None,
        max_tokens: int = 2000
    ) -> str:
        """Get context for LLM augmentation."""
        return await self.retriever.get_context_for_query(
            query=query,
            max_tokens=max_tokens,
            user_id=user_id
        )
    
    # =========================================================================
    # Management
    # =========================================================================
    
    async def list_documents(
        self,
        user_id: str = None,
        source: str = None
    ) -> List[Dict[str, Any]]:
        """List all documents (unique titles)."""
        kb = Database.get_collection("knowledge_base")
        
        match_stage = {}
        if user_id:
            match_stage["user_id"] = user_id
        if source:
            match_stage["source"] = source
        
        pipeline = [
            {"$match": match_stage} if match_stage else {"$match": {}},
            {
                "$group": {
                    "_id": "$title",
                    "source": {"$first": "$source"},
                    "tags": {"$first": "$tags"},
                    "chunks": {"$sum": 1},
                    "created_at": {"$min": "$created_at"}
                }
            },
            {"$sort": {"created_at": -1}}
        ]
        
        cursor = kb.aggregate(pipeline)
        return await cursor.to_list(length=100)
    
    async def get_stats(self, user_id: str = None) -> Dict[str, Any]:
        """Get knowledge base statistics."""
        kb = Database.get_collection("knowledge_base")
        
        match_stage = {"user_id": user_id} if user_id else {}
        
        pipeline = [
            {"$match": match_stage},
            {
                "$group": {
                    "_id": "$source",
                    "count": {"$sum": 1}
                }
            }
        ]
        
        cursor = kb.aggregate(pipeline)
        by_source = {}
        async for doc in cursor:
            by_source[doc["_id"]] = doc["count"]
        
        total = sum(by_source.values())
        
        return {
            "total_chunks": total,
            "by_source": by_source
        }


# Singleton
_knowledge_base = None


def get_knowledge_base() -> KnowledgeBase:
    """Get singleton KnowledgeBase instance."""
    global _knowledge_base
    if _knowledge_base is None:
        _knowledge_base = KnowledgeBase()
    return _knowledge_base

