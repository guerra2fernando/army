"""
Semantic Retrieval Service
Retrieves relevant documents using vector similarity search.
"""
from typing import List, Dict, Any, Optional
from loguru import logger

from app.db import Database
from app.rag.embeddings import get_embedding_service


class SemanticRetriever:
    """
    Retrieves relevant documents using vector similarity search.
    """
    
    def __init__(self):
        self.embedding_service = get_embedding_service()
        self.default_limit = 5
    
    async def search(
        self,
        query: str,
        limit: int = None,
        source_filter: Optional[str] = None,
        tag_filter: Optional[List[str]] = None,
        user_id: Optional[str] = None,
        min_score: float = 0.7
    ) -> List[Dict[str, Any]]:
        """
        Search the knowledge base using semantic similarity.
        
        Args:
            query: Search query
            limit: Maximum results to return
            source_filter: Filter by source type
            tag_filter: Filter by tags
            user_id: Filter by user
            min_score: Minimum similarity score
            
        Returns:
            List of matching documents with scores
        """
        limit = limit or self.default_limit
        
        # Generate query embedding
        query_embedding = await self.embedding_service.embed_text(query)
        
        # Build vector search pipeline
        pipeline = self._build_search_pipeline(
            query_embedding=query_embedding,
            limit=limit * 2,  # Get more for filtering
            source_filter=source_filter,
            tag_filter=tag_filter,
            user_id=user_id
        )
        
        # Execute search
        kb = Database.get_collection("knowledge_base")
        
        try:
            cursor = kb.aggregate(pipeline)
            results = await cursor.to_list(length=limit * 2)
        except Exception as e:
            # If vector search not available (e.g., mock DB), fall back to empty
            logger.warning(f"Vector search not available: {e}")
            results = []
        
        # Filter by score and limit
        filtered_results = [
            r for r in results
            if r.get("score", 0) >= min_score
        ][:limit]
        
        logger.debug(f"Retrieved {len(filtered_results)} documents for query: {query[:50]}...")
        
        return filtered_results
    
    def _build_search_pipeline(
        self,
        query_embedding: List[float],
        limit: int,
        source_filter: Optional[str],
        tag_filter: Optional[List[str]],
        user_id: Optional[str]
    ) -> List[dict]:
        """Build MongoDB aggregation pipeline for vector search."""
        
        # Build filter
        filter_conditions = {}
        if source_filter:
            filter_conditions["source"] = source_filter
        if tag_filter:
            filter_conditions["tags"] = {"$in": tag_filter}
        if user_id:
            filter_conditions["user_id"] = user_id
        
        vector_search_stage = {
            "$vectorSearch": {
                "index": "vector_index",
                "path": "embedding",
                "queryVector": query_embedding,
                "numCandidates": limit * 10,
                "limit": limit,
            }
        }
        
        # Add filter if present
        if filter_conditions:
            vector_search_stage["$vectorSearch"]["filter"] = filter_conditions
        
        pipeline = [
            vector_search_stage,
            {
                "$project": {
                    "_id": 1,
                    "doc_id": 1,
                    "content": 1,
                    "source": 1,
                    "title": 1,
                    "tags": 1,
                    "metadata": 1,
                    "score": {"$meta": "vectorSearchScore"}
                }
            }
        ]
        
        return pipeline
    
    async def get_context_for_query(
        self,
        query: str,
        max_tokens: int = 2000,
        user_id: Optional[str] = None
    ) -> str:
        """
        Get formatted context string for LLM augmentation.
        
        Args:
            query: Search query
            max_tokens: Maximum context length (approximate)
            user_id: User to filter by
            
        Returns:
            Formatted context string
        """
        results = await self.search(
            query=query,
            limit=10,
            user_id=user_id,
            min_score=0.5  # Lower threshold for context
        )
        
        if not results:
            return ""
        
        context_parts = []
        total_length = 0
        max_chars = max_tokens * 4  # Rough estimate: ~4 chars per token
        
        for result in results:
            content = result.get("content", "")
            source = result.get("source", "UNKNOWN")
            title = result.get("title", "")
            
            # Format context piece
            piece = f"[{source}] {title}\n{content}\n---"
            
            if total_length + len(piece) > max_chars:
                break
            
            context_parts.append(piece)
            total_length += len(piece)
        
        return "\n\n".join(context_parts)


# Singleton
_retriever = None


def get_retriever() -> SemanticRetriever:
    """Get singleton SemanticRetriever instance."""
    global _retriever
    if _retriever is None:
        _retriever = SemanticRetriever()
    return _retriever

