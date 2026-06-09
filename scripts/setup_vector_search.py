#!/usr/bin/env python3
"""
MongoDB Atlas Vector Search Setup Script
Run this after creating the vector search index in Atlas UI
"""

import asyncio
import os
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Determine embedding provider and dimensions
llm_provider = os.getenv("LLM_PROVIDER", "gemini").lower()
embedding_dimensions = 768 if llm_provider == "gemini" else 1536

# MongoDB Atlas connection
MONGODB_URL = os.getenv("MONGODB_URL")
if not MONGODB_URL:
    print("MONGODB_URL not found in environment variables")
    exit(1)

print(f"Using {llm_provider.upper()} embeddings ({embedding_dimensions} dimensions)")

async def test_vector_search():
    """Test that vector search is working"""
    try:
        client = AsyncIOMotorClient(MONGODB_URL)
        db = client.arm_len_quant
        collection = db.knowledge_base

        # Test basic connection
        count = await collection.count_documents({})
        print(f"✅ Connected to MongoDB. Documents in knowledge_base: {count}")

        # Test vector search index exists
        indexes = await collection.list_indexes().to_list(length=None)
        vector_index_exists = any(
            idx.get("name") == "vector_index" for idx in indexes
        )

        if vector_index_exists:
            print("✅ Vector search index 'vector_index' exists")
        else:
            print("❌ Vector search index 'vector_index' not found")
            print("   Please create it in MongoDB Atlas UI first")
            return False

        # Test a simple vector search
        # Using a dummy embedding for testing
        test_embedding = [0.1] * embedding_dimensions

        pipeline = [
            {
                "$vectorSearch": {
                    "index": "vector_index",
                    "path": "embedding",
                    "queryVector": test_embedding,
                    "numCandidates": 10,
                    "limit": 5
                }
            },
            {
                "$project": {
                    "_id": 1,
                    "title": 1,
                    "source": 1,
                    "score": {"$meta": "vectorSearchScore"}
                }
            }
        ]

        results = await collection.aggregate(pipeline).to_list(length=5)

        if results:
            print(f"✅ Vector search working! Found {len(results)} results")
            for result in results[:2]:
                print(f"   - {result.get('title', 'Unknown')}: {result.get('score', 0):.3f}")
        else:
            print("⚠️  Vector search returned no results (expected for empty collection)")

        print("\n🎉 MongoDB Atlas Vector Search is ready!")
        return True

    except Exception as e:
        print(f"❌ Error testing vector search: {e}")
        return False

async def create_sample_document():
    """Create a sample document to test with"""
    try:
        from app.rag.embeddings import get_embedding_service

        client = AsyncIOMotorClient(MONGODB_URL)
        db = client.arm_len_quant
        collection = db.knowledge_base

        # Get embedding service
        embedding_service = get_embedding_service()

        # Sample content
        sample_content = """
        This is a sample document for testing vector search functionality.
        The Ideas Machine creates complete, production-ready projects through
        sequential AI API calls. Each phase generates complete files with
        proper models, APIs, comprehensive tests, and automatic error detection.
        """

        # Generate embedding
        embedding = await embedding_service.embed_text(sample_content)

        # Create document
        doc = {
            "doc_id": "test_sample",
            "content": sample_content,
            "embedding": embedding,
            "source": "TEST_SAMPLE",
            "title": "Sample Document for Vector Search Testing",
            "tags": ["test", "sample", "vector_search"],
            "metadata": {"test": True},
            "created_at": asyncio.get_event_loop().time(),
            "updated_at": asyncio.get_event_loop().time()
        }

        result = await collection.insert_one(doc)
        print(f"✅ Created sample document with ID: {result.inserted_id}")

    except Exception as e:
        print(f"❌ Error creating sample document: {e}")

if __name__ == "__main__":
    print("🧪 Testing MongoDB Atlas Vector Search Setup...\n")

    # Test vector search
    success = asyncio.run(test_vector_search())

    if success:
        # Ask if user wants to create sample data
        response = input("\nWould you like to create a sample document for testing? (y/n): ")
        if response.lower() == 'y':
            asyncio.run(create_sample_document())

    print("\n📋 Next Steps:")
    print("1. Run your Ideas Machine to generate projects")
    print("2. Project contexts will be stored in knowledge_base collection")
    print("3. Future prompts will be enriched with relevant context")
    print("4. Enjoy intelligent, context-aware project generation! 🚀")
