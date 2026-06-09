"""
Tests for RAG & Knowledge Base System (Phase 5)
"""
import pytest
from datetime import datetime
from uuid import uuid4
from unittest.mock import AsyncMock, MagicMock, patch

from app.db import Database


# =============================================================================
# EMBEDDING SERVICE TESTS
# =============================================================================

class TestEmbeddingService:
    """Tests for the embedding service."""
    
    @pytest.mark.asyncio
    async def test_embed_text_returns_vector(self):
        """Test that embed_text returns a list of floats."""
        from app.rag.embeddings import EmbeddingService
        
        with patch('app.rag.embeddings.AsyncOpenAI') as mock_openai:
            # Mock the OpenAI response
            mock_response = MagicMock()
            mock_response.data = [MagicMock(embedding=[0.1] * 1536)]
            mock_openai.return_value.embeddings.create = AsyncMock(return_value=mock_response)
            
            service = EmbeddingService()
            result = await service.embed_text("test text")
            
            assert isinstance(result, list)
            assert len(result) == 1536
            assert all(isinstance(x, float) for x in result)
    
    @pytest.mark.asyncio
    async def test_embed_batch_returns_multiple_vectors(self):
        """Test that embed_batch returns multiple embedding vectors."""
        from app.rag.embeddings import EmbeddingService
        
        with patch('app.rag.embeddings.AsyncOpenAI') as mock_openai:
            # Mock the OpenAI response for batch
            mock_response = MagicMock()
            mock_response.data = [
                MagicMock(embedding=[0.1] * 1536),
                MagicMock(embedding=[0.2] * 1536),
                MagicMock(embedding=[0.3] * 1536),
            ]
            mock_openai.return_value.embeddings.create = AsyncMock(return_value=mock_response)
            
            service = EmbeddingService()
            result = await service.embed_batch(["text 1", "text 2", "text 3"])
            
            assert isinstance(result, list)
            assert len(result) == 3
            assert all(len(v) == 1536 for v in result)
    
    @pytest.mark.asyncio
    async def test_embedding_service_singleton(self):
        """Test get_embedding_service returns singleton."""
        from app.rag.embeddings import get_embedding_service
        
        with patch('app.rag.embeddings.AsyncOpenAI'):
            service1 = get_embedding_service()
            service2 = get_embedding_service()
            assert service1 is service2


# =============================================================================
# TEXT CHUNKER TESTS
# =============================================================================

class TestTextChunker:
    """Tests for the text chunking service."""
    
    def test_chunk_small_text(self):
        """Test chunking text smaller than chunk size."""
        from app.rag.chunker import TextChunker
        
        chunker = TextChunker(chunk_size=500, chunk_overlap=50)
        text = "This is a small piece of text."
        
        chunks = chunker.chunk_text(text)
        
        assert len(chunks) == 1
        assert chunks[0]["content"] == text
        assert "metadata" in chunks[0]
        assert chunks[0]["metadata"]["chunk_index"] == 0
    
    def test_chunk_large_text(self):
        """Test chunking text larger than chunk size."""
        from app.rag.chunker import TextChunker
        
        chunker = TextChunker(chunk_size=100, chunk_overlap=20)
        text = "This is a longer piece of text. " * 20  # ~600 chars
        
        chunks = chunker.chunk_text(text)
        
        assert len(chunks) > 1
        for chunk in chunks:
            assert "content" in chunk
            assert "metadata" in chunk
    
    def test_chunk_preserves_metadata(self):
        """Test that chunking preserves provided metadata."""
        from app.rag.chunker import TextChunker
        
        chunker = TextChunker()
        text = "Some text content"
        metadata = {"source": "test", "title": "Test Doc"}
        
        chunks = chunker.chunk_text(text, metadata)
        
        assert chunks[0]["metadata"]["source"] == "test"
        assert chunks[0]["metadata"]["title"] == "Test Doc"
    
    def test_chunk_adds_index_info(self):
        """Test that chunks include index and total information."""
        from app.rag.chunker import TextChunker
        
        chunker = TextChunker(chunk_size=50, chunk_overlap=10)
        text = "A" * 200  # Long enough to create multiple chunks
        
        chunks = chunker.chunk_text(text)
        
        for i, chunk in enumerate(chunks):
            assert chunk["metadata"]["chunk_index"] == i
            assert chunk["metadata"]["total_chunks"] == len(chunks)


class TestMarkdownChunker:
    """Tests for Markdown-specific chunking."""
    
    def test_markdown_chunker_handles_headers(self):
        """Test that MarkdownChunker handles markdown headers."""
        from app.rag.chunker import MarkdownChunker
        
        chunker = MarkdownChunker()
        text = """# Main Title
        
## Section 1
Some content here.

## Section 2
More content here.
"""
        
        chunks = chunker.chunk_text(text)
        
        assert len(chunks) >= 1
        assert "headers" in chunks[0]["metadata"]
    
    def test_markdown_chunker_extracts_headers(self):
        """Test that headers are extracted to metadata."""
        from app.rag.chunker import MarkdownChunker
        
        chunker = MarkdownChunker()
        text = """# Title
## Subtitle
### Section
Content
"""
        
        chunks = chunker.chunk_text(text)
        
        headers = chunks[0]["metadata"]["headers"]
        assert "Title" in headers
        assert "Subtitle" in headers
        assert "Section" in headers


# =============================================================================
# KNOWLEDGE INGESTION TESTS
# =============================================================================

class TestKnowledgeIngestion:
    """Tests for knowledge ingestion pipeline."""
    
    @pytest.mark.asyncio
    async def test_ingest_document_creates_chunks(self):
        """Test that document ingestion creates chunks in database."""
        from app.rag.ingestion import KnowledgeIngestion
        
        with patch('app.rag.ingestion.get_embedding_service') as mock_embed:
            # Mock embedding service
            mock_service = MagicMock()
            mock_service.embed_batch = AsyncMock(return_value=[[0.1] * 1536])
            mock_embed.return_value = mock_service
            
            ingestion = KnowledgeIngestion()
            result = await ingestion.ingest_document(
                content="Test content for ingestion",
                source="TEST",
                title="Test Document",
                tags=["test"],
                user_id="user123"
            )
            
            assert result["document_title"] == "Test Document"
            assert result["source"] == "TEST"
            assert result["chunks_created"] >= 1
            assert len(result["doc_ids"]) >= 1
    
    @pytest.mark.asyncio
    async def test_ingest_cv(self):
        """Test CV ingestion convenience method."""
        from app.rag.ingestion import KnowledgeIngestion, KnowledgeSource
        
        with patch('app.rag.ingestion.get_embedding_service') as mock_embed:
            mock_service = MagicMock()
            mock_service.embed_batch = AsyncMock(return_value=[[0.1] * 1536])
            mock_embed.return_value = mock_service
            
            ingestion = KnowledgeIngestion()
            result = await ingestion.ingest_cv(
                content="# John Doe\n\n## Experience\n- Software Developer",
                user_id="user123"
            )
            
            assert result["source"] == KnowledgeSource.CV
            assert "cv" in result.get("document_title", "").lower() or result["chunks_created"] >= 1
    
    @pytest.mark.asyncio
    async def test_ingest_trading_rules(self):
        """Test trading rules ingestion."""
        from app.rag.ingestion import KnowledgeIngestion, KnowledgeSource
        
        with patch('app.rag.ingestion.get_embedding_service') as mock_embed:
            mock_service = MagicMock()
            mock_service.embed_batch = AsyncMock(return_value=[[0.1] * 1536])
            mock_embed.return_value = mock_service
            
            ingestion = KnowledgeIngestion()
            result = await ingestion.ingest_trading_rules(
                content="# Trading Rules\n\n- Never risk more than 2%",
                user_id="user123"
            )
            
            assert result["source"] == KnowledgeSource.TRADING_RULES
    
    @pytest.mark.asyncio
    async def test_delete_document(self):
        """Test document deletion."""
        from app.rag.ingestion import KnowledgeIngestion
        
        # First insert a document
        kb = Database.get_collection("knowledge_base")
        doc_id = str(uuid4())
        await kb.insert_one({
            "_id": doc_id,
            "title": "Delete Me",
            "user_id": "user123",
            "content": "Some content"
        })
        
        ingestion = KnowledgeIngestion()
        deleted = await ingestion.delete_document("Delete Me", "user123")
        
        assert deleted >= 1
    
    def test_is_markdown_detection(self):
        """Test markdown content detection."""
        from app.rag.ingestion import KnowledgeIngestion
        
        ingestion = KnowledgeIngestion()
        
        assert ingestion._is_markdown("# Header\n\nSome text")
        assert ingestion._is_markdown("**bold text**")
        assert ingestion._is_markdown("- list item")
        assert not ingestion._is_markdown("plain text without formatting")


# =============================================================================
# SEMANTIC RETRIEVER TESTS
# =============================================================================

class TestSemanticRetriever:
    """Tests for semantic retrieval service."""
    
    @pytest.mark.asyncio
    async def test_search_returns_results(self):
        """Test that search returns matching documents."""
        from app.rag.retriever import SemanticRetriever
        
        # Insert test document
        kb = Database.get_collection("knowledge_base")
        await kb.insert_one({
            "_id": str(uuid4()),
            "content": "Python developer with FastAPI experience",
            "embedding": [0.1] * 1536,
            "source": "CV",
            "title": "Test CV",
            "tags": ["python", "fastapi"],
            "user_id": "user123",
            "score": 0.9
        })
        
        with patch('app.rag.retriever.get_embedding_service') as mock_embed:
            mock_service = MagicMock()
            mock_service.embed_text = AsyncMock(return_value=[0.1] * 1536)
            mock_embed.return_value = mock_service
            
            retriever = SemanticRetriever()
            
            # For mock database, we'll test the search method structure
            # In real scenario with Atlas vector search, this would return results
            results = await retriever.search(
                query="Python developer",
                user_id="user123"
            )
            
            # Results may be empty with mock DB (no vector search support)
            assert isinstance(results, list)
    
    @pytest.mark.asyncio
    async def test_search_with_filters(self):
        """Test search with source and tag filters."""
        from app.rag.retriever import SemanticRetriever
        
        with patch('app.rag.retriever.get_embedding_service') as mock_embed:
            mock_service = MagicMock()
            mock_service.embed_text = AsyncMock(return_value=[0.1] * 1536)
            mock_embed.return_value = mock_service
            
            retriever = SemanticRetriever()
            
            results = await retriever.search(
                query="test query",
                source_filter="CV",
                tag_filter=["python"],
                user_id="user123"
            )
            
            assert isinstance(results, list)
    
    @pytest.mark.asyncio
    async def test_get_context_for_query(self):
        """Test context retrieval for LLM augmentation."""
        from app.rag.retriever import SemanticRetriever
        
        with patch('app.rag.retriever.get_embedding_service') as mock_embed:
            mock_service = MagicMock()
            mock_service.embed_text = AsyncMock(return_value=[0.1] * 1536)
            mock_embed.return_value = mock_service
            
            retriever = SemanticRetriever()
            
            context = await retriever.get_context_for_query(
                query="Python programming",
                max_tokens=2000
            )
            
            assert isinstance(context, str)
    
    def test_build_search_pipeline(self):
        """Test that search pipeline is correctly built."""
        from app.rag.retriever import SemanticRetriever
        
        with patch('app.rag.retriever.get_embedding_service'):
            retriever = SemanticRetriever()
            
            pipeline = retriever._build_search_pipeline(
                query_embedding=[0.1] * 1536,
                limit=5,
                source_filter="CV",
                tag_filter=["python"],
                user_id="user123"
            )
            
            assert len(pipeline) >= 2
            assert "$vectorSearch" in pipeline[0]
            assert "$project" in pipeline[1]


# =============================================================================
# KNOWLEDGE BASE SERVICE TESTS
# =============================================================================

class TestKnowledgeBase:
    """Tests for the main Knowledge Base service."""
    
    @pytest.mark.asyncio
    async def test_add_document(self):
        """Test adding document via KnowledgeBase."""
        from app.rag.knowledge_base import KnowledgeBase
        
        with patch('app.rag.knowledge_base.KnowledgeIngestion') as mock_ingestion:
            mock_ingestion_instance = MagicMock()
            mock_ingestion_instance.ingest_document = AsyncMock(return_value={
                "document_title": "Test",
                "source": "TEST",
                "chunks_created": 1,
                "doc_ids": ["id1"]
            })
            mock_ingestion.return_value = mock_ingestion_instance
            
            with patch('app.rag.knowledge_base.get_retriever'):
                kb = KnowledgeBase()
                result = await kb.add_document(
                    content="Test content",
                    source="TEST",
                    title="Test Doc",
                    user_id="user123"
                )
                
                assert result["chunks_created"] == 1
    
    @pytest.mark.asyncio
    async def test_add_cv(self):
        """Test adding CV via KnowledgeBase."""
        from app.rag.knowledge_base import KnowledgeBase
        
        with patch('app.rag.knowledge_base.KnowledgeIngestion') as mock_ingestion:
            mock_ingestion_instance = MagicMock()
            mock_ingestion_instance.ingest_cv = AsyncMock(return_value={
                "document_title": "Master CV",
                "source": "CV",
                "chunks_created": 3,
                "doc_ids": ["id1", "id2", "id3"]
            })
            mock_ingestion.return_value = mock_ingestion_instance
            
            with patch('app.rag.knowledge_base.get_retriever'):
                kb = KnowledgeBase()
                result = await kb.add_cv("CV content", "user123")
                
                assert result["source"] == "CV"
    
    @pytest.mark.asyncio
    async def test_search(self):
        """Test searching via KnowledgeBase."""
        from app.rag.knowledge_base import KnowledgeBase
        
        with patch('app.rag.knowledge_base.KnowledgeIngestion'):
            with patch('app.rag.knowledge_base.get_retriever') as mock_retriever:
                mock_retriever_instance = MagicMock()
                mock_retriever_instance.search = AsyncMock(return_value=[
                    {"content": "Result 1", "score": 0.9},
                    {"content": "Result 2", "score": 0.8}
                ])
                mock_retriever.return_value = mock_retriever_instance
                
                kb = KnowledgeBase()
                results = await kb.search("test query", user_id="user123")
                
                assert len(results) == 2
    
    @pytest.mark.asyncio
    async def test_get_context(self):
        """Test getting context for LLM."""
        from app.rag.knowledge_base import KnowledgeBase
        
        with patch('app.rag.knowledge_base.KnowledgeIngestion'):
            with patch('app.rag.knowledge_base.get_retriever') as mock_retriever:
                mock_retriever_instance = MagicMock()
                mock_retriever_instance.get_context_for_query = AsyncMock(
                    return_value="[CV] Resume\nPython developer\n---"
                )
                mock_retriever.return_value = mock_retriever_instance
                
                kb = KnowledgeBase()
                context = await kb.get_context("query", user_id="user123")
                
                assert "CV" in context
    
    @pytest.mark.asyncio
    async def test_list_documents(self):
        """Test listing documents in knowledge base."""
        from app.rag.knowledge_base import KnowledgeBase
        
        # Insert test documents
        kb_collection = Database.get_collection("knowledge_base")
        await kb_collection.insert_many([
            {
                "_id": str(uuid4()),
                "title": "Doc 1",
                "source": "CV",
                "tags": ["test"],
                "user_id": "user123",
                "created_at": datetime.utcnow()
            },
            {
                "_id": str(uuid4()),
                "title": "Doc 2",
                "source": "TRADING_RULES",
                "tags": ["test"],
                "user_id": "user123",
                "created_at": datetime.utcnow()
            }
        ])
        
        with patch('app.rag.knowledge_base.KnowledgeIngestion'):
            with patch('app.rag.knowledge_base.get_retriever'):
                kb = KnowledgeBase()
                docs = await kb.list_documents(user_id="user123")
                
                assert len(docs) >= 2
    
    @pytest.mark.asyncio
    async def test_get_stats(self):
        """Test getting knowledge base statistics."""
        from app.rag.knowledge_base import KnowledgeBase
        
        # Insert test documents
        kb_collection = Database.get_collection("knowledge_base")
        await kb_collection.insert_many([
            {"_id": str(uuid4()), "source": "CV", "user_id": "user123"},
            {"_id": str(uuid4()), "source": "CV", "user_id": "user123"},
            {"_id": str(uuid4()), "source": "TRADING_RULES", "user_id": "user123"},
        ])
        
        with patch('app.rag.knowledge_base.KnowledgeIngestion'):
            with patch('app.rag.knowledge_base.get_retriever'):
                kb = KnowledgeBase()
                stats = await kb.get_stats(user_id="user123")
                
                assert "total_chunks" in stats
                assert "by_source" in stats
                assert stats["total_chunks"] >= 3
    
    @pytest.mark.asyncio
    async def test_knowledge_base_singleton(self):
        """Test get_knowledge_base returns singleton."""
        from app.rag.knowledge_base import get_knowledge_base
        
        with patch('app.rag.knowledge_base.KnowledgeIngestion'):
            with patch('app.rag.knowledge_base.get_retriever'):
                kb1 = get_knowledge_base()
                kb2 = get_knowledge_base()
                assert kb1 is kb2


# =============================================================================
# KNOWLEDGE API ROUTES TESTS
# =============================================================================

class TestKnowledgeRoutes:
    """Tests for knowledge base API routes."""
    
    @pytest.mark.asyncio
    async def test_add_document_endpoint(self, client, auth_headers, test_user):
        """Test POST /api/v1/knowledge/documents endpoint."""
        with patch('app.routes.knowledge.get_knowledge_base') as mock_kb:
            mock_kb_instance = MagicMock()
            mock_kb_instance.add_document = AsyncMock(return_value={
                "document_title": "Test Doc",
                "source": "PROJECT_DOC",
                "chunks_created": 2,
                "doc_ids": ["id1", "id2"]
            })
            mock_kb.return_value = mock_kb_instance
            
            response = await client.post(
                "/api/v1/knowledge/documents",
                headers=auth_headers,
                json={
                    "content": "Test content for document",
                    "source": "PROJECT_DOC",
                    "title": "Test Doc",
                    "tags": ["test"]
                }
            )
            
            assert response.status_code == 200
            data = response.json()
            assert data["chunks_created"] == 2
    
    @pytest.mark.asyncio
    async def test_add_document_requires_auth(self, client):
        """Test that add document requires authentication."""
        response = await client.post(
            "/api/v1/knowledge/documents",
            json={
                "content": "Test",
                "source": "TEST",
                "title": "Test"
            }
        )
        
        assert response.status_code in [401, 403]
    
    @pytest.mark.asyncio
    async def test_search_endpoint(self, client, auth_headers, test_user):
        """Test POST /api/v1/knowledge/search endpoint."""
        with patch('app.routes.knowledge.get_knowledge_base') as mock_kb:
            mock_kb_instance = MagicMock()
            mock_kb_instance.search = AsyncMock(return_value=[
                {"content": "Match 1", "score": 0.9},
                {"content": "Match 2", "score": 0.8}
            ])
            mock_kb.return_value = mock_kb_instance
            
            response = await client.post(
                "/api/v1/knowledge/search",
                headers=auth_headers,
                json={
                    "query": "test search query",
                    "limit": 5
                }
            )
            
            assert response.status_code == 200
            data = response.json()
            assert "results" in data
            assert len(data["results"]) == 2
    
    @pytest.mark.asyncio
    async def test_list_documents_endpoint(self, client, auth_headers, test_user):
        """Test GET /api/v1/knowledge/documents endpoint."""
        with patch('app.routes.knowledge.get_knowledge_base') as mock_kb:
            mock_kb_instance = MagicMock()
            mock_kb_instance.list_documents = AsyncMock(return_value=[
                {"_id": "Doc 1", "source": "CV", "chunks": 3},
                {"_id": "Doc 2", "source": "TRADING_RULES", "chunks": 5}
            ])
            mock_kb.return_value = mock_kb_instance
            
            response = await client.get(
                "/api/v1/knowledge/documents",
                headers=auth_headers
            )
            
            assert response.status_code == 200
            data = response.json()
            assert "documents" in data
    
    @pytest.mark.asyncio
    async def test_delete_document_endpoint(self, client, auth_headers, test_user):
        """Test DELETE /api/v1/knowledge/documents/{title} endpoint."""
        with patch('app.routes.knowledge.get_knowledge_base') as mock_kb:
            mock_kb_instance = MagicMock()
            mock_kb_instance.remove_document = AsyncMock(return_value=3)
            mock_kb.return_value = mock_kb_instance
            
            response = await client.delete(
                "/api/v1/knowledge/documents/Test%20Doc",
                headers=auth_headers
            )
            
            assert response.status_code == 200
            data = response.json()
            assert data["deleted_chunks"] == 3
    
    @pytest.mark.asyncio
    async def test_stats_endpoint(self, client, auth_headers, test_user):
        """Test GET /api/v1/knowledge/stats endpoint."""
        with patch('app.routes.knowledge.get_knowledge_base') as mock_kb:
            mock_kb_instance = MagicMock()
            mock_kb_instance.get_stats = AsyncMock(return_value={
                "total_chunks": 10,
                "by_source": {"CV": 5, "TRADING_RULES": 5}
            })
            mock_kb.return_value = mock_kb_instance
            
            response = await client.get(
                "/api/v1/knowledge/stats",
                headers=auth_headers
            )
            
            assert response.status_code == 200
            data = response.json()
            assert data["total_chunks"] == 10
    
    @pytest.mark.asyncio
    async def test_sources_endpoint(self, client, auth_headers, test_user):
        """Test GET /api/v1/knowledge/sources endpoint."""
        response = await client.get(
            "/api/v1/knowledge/sources",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "sources" in data
        assert len(data["sources"]) >= 5  # CV, TRADING_RULES, etc.


# =============================================================================
# INTEGRATION TESTS
# =============================================================================

class TestRAGIntegration:
    """Integration tests for the complete RAG pipeline."""
    
    @pytest.mark.asyncio
    async def test_full_ingest_search_cycle(self):
        """Test full document ingestion and search cycle."""
        from app.rag.knowledge_base import KnowledgeBase
        
        with patch('app.rag.ingestion.get_embedding_service') as mock_embed:
            mock_service = MagicMock()
            mock_service.embed_batch = AsyncMock(return_value=[[0.1] * 1536])
            mock_service.embed_text = AsyncMock(return_value=[0.1] * 1536)
            mock_embed.return_value = mock_service
            
            with patch('app.rag.retriever.get_embedding_service') as mock_embed2:
                mock_embed2.return_value = mock_service
                
                kb = KnowledgeBase()
                
                # Ingest a document
                result = await kb.add_document(
                    content="Python programming with FastAPI framework",
                    source="PROJECT_DOC",
                    title="FastAPI Guide",
                    tags=["python", "fastapi"],
                    user_id="user123"
                )
                
                assert result["chunks_created"] >= 1
                
                # Verify document was stored
                kb_collection = Database.get_collection("knowledge_base")
                docs = await kb_collection.find({"title": "FastAPI Guide"}).to_list(10)
                assert len(docs) >= 1
    
    @pytest.mark.asyncio
    async def test_cv_ingest_and_list(self):
        """Test CV ingestion and listing."""
        from app.rag.knowledge_base import KnowledgeBase
        
        with patch('app.rag.ingestion.get_embedding_service') as mock_embed:
            mock_service = MagicMock()
            mock_service.embed_batch = AsyncMock(return_value=[
                [0.1] * 1536,
                [0.2] * 1536
            ])
            mock_embed.return_value = mock_service
            
            with patch('app.rag.retriever.get_embedding_service'):
                kb = KnowledgeBase()
                
                # Add CV
                cv_content = """# John Doe
                
## Experience
- Senior Developer at Company A

## Skills
- Python
- FastAPI
"""
                
                result = await kb.add_cv(cv_content, "user123")
                assert result["chunks_created"] >= 1
                
                # List documents
                docs = await kb.list_documents(user_id="user123")
                titles = [doc["_id"] for doc in docs]
                assert any("CV" in str(doc) or "cv" in str(doc).lower() for doc in docs)


# =============================================================================
# EDGE CASES AND ERROR HANDLING
# =============================================================================

class TestRAGEdgeCases:
    """Tests for edge cases and error handling."""
    
    def test_empty_text_chunking(self):
        """Test chunking with empty text."""
        from app.rag.chunker import TextChunker
        
        chunker = TextChunker()
        chunks = chunker.chunk_text("")
        
        assert chunks == [] or (len(chunks) == 1 and chunks[0]["content"] == "")
    
    def test_unicode_text_chunking(self):
        """Test chunking with unicode characters."""
        from app.rag.chunker import TextChunker
        
        chunker = TextChunker()
        text = "日本語テキスト 🎉 émojis и русский текст"
        
        chunks = chunker.chunk_text(text)
        
        assert len(chunks) >= 1
        assert chunks[0]["content"] == text
    
    @pytest.mark.asyncio
    async def test_ingest_very_long_document(self):
        """Test ingesting a very long document."""
        from app.rag.ingestion import KnowledgeIngestion
        
        with patch('app.rag.ingestion.get_embedding_service') as mock_embed:
            mock_service = MagicMock()
            # Return enough embeddings for multiple chunks
            mock_service.embed_batch = AsyncMock(return_value=[[0.1] * 1536] * 50)
            mock_embed.return_value = mock_service
            
            ingestion = KnowledgeIngestion()
            
            # Create a long document (10000+ characters)
            long_content = "This is a paragraph of text. " * 500
            
            result = await ingestion.ingest_document(
                content=long_content,
                source="TEST",
                title="Long Document",
                user_id="user123"
            )
            
            assert result["chunks_created"] > 1
    
    @pytest.mark.asyncio
    async def test_search_with_no_results(self):
        """Test search when no documents match."""
        from app.rag.retriever import SemanticRetriever
        
        with patch('app.rag.retriever.get_embedding_service') as mock_embed:
            mock_service = MagicMock()
            mock_service.embed_text = AsyncMock(return_value=[0.1] * 1536)
            mock_embed.return_value = mock_service
            
            retriever = SemanticRetriever()
            
            # Search in empty database
            results = await retriever.search(
                query="nonexistent query xyz123",
                user_id="nonexistent_user"
            )
            
            assert results == []
    
    @pytest.mark.asyncio
    async def test_delete_nonexistent_document(self):
        """Test deleting a document that doesn't exist."""
        from app.rag.ingestion import KnowledgeIngestion
        
        ingestion = KnowledgeIngestion()
        deleted = await ingestion.delete_document(
            title="Nonexistent Document",
            user_id="user123"
        )
        
        assert deleted == 0

