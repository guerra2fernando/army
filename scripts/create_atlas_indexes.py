#!/usr/bin/env python3
"""
Create MongoDB Atlas Search Indexes
This script helps create the necessary indexes for vector search.
Note: Atlas Search indexes must be created via the Atlas UI or API.
"""

import json
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Determine embedding provider and dimensions
llm_provider = os.getenv("LLM_PROVIDER", "gemini").lower()
embedding_dimensions = 768 if llm_provider == "gemini" else 1536

print(f"MongoDB Atlas Vector Search Index Configuration")
print(f"Provider: {llm_provider.upper()} | Dimensions: {embedding_dimensions}")
print("=" * 60)

print("""
VECTOR SEARCH INDEX (Required for semantic search)
Create this in: Atlas UI -> Search -> Create Search Index -> JSON Editor

Collection: knowledge_base
Index Name: vector_index
""")

vector_index = {
    "name": "vector_index",
    "type": "vectorSearch",
    "fields": [
        {
            "numDimensions": embedding_dimensions,
            "path": "embedding",
            "similarity": "cosine",
            "type": "vector"
        },
        {
            "path": "source",
            "type": "filter"
        },
        {
            "path": "tags",
            "type": "filter"
        }
    ]
}

print("Vector Index JSON:")
print(json.dumps(vector_index, indent=2))

print("""
TEXT SEARCH INDEX (Optional fallback)
Create this in: Atlas UI -> Search -> Create Search Index -> JSON Editor

Collection: knowledge_base
Index Name: text_index
""")

text_index = {
    "name": "text_index",
    "mappings": {
        "dynamic": False,
        "fields": {
            "content": {
                "type": "string",
                "analyzer": "lucene.standard"
            },
            "metadata.tags": {
                "type": "string"
            }
        }
    }
}

print("Text Index JSON:")
print(json.dumps(text_index, indent=2))

print("""
SETUP CHECKLIST:
1. Go to MongoDB Atlas Dashboard
2. Select your cluster
3. Go to 'Atlas Search' tab
4. Click 'Create Search Index'
5. Choose 'JSON Editor' method
6. Select database: arm_len_quant
7. Select collection: knowledge_base
8. Copy-paste the Vector Index JSON above
9. Click 'Create Search Index'
10. Wait for index to build (can take 1-5 minutes)

TESTING:
After creating the index, run:
    python scripts/setup_vector_search.py

This will verify your vector search setup and create sample data.

READY FOR IDEAS MACHINE:
Once vector search is active, your Ideas Machine will:
- Store project contexts in the knowledge base
- Retrieve relevant patterns for new projects
- Enrich AI prompts with contextual information
- Learn from successful implementations

Happy coding!
""")

# Save configurations to files for reference
with open("scripts/vector_index_config.json", "w") as f:
    json.dump(vector_index, f, indent=2)

with open("scripts/text_index_config.json", "w") as f:
    json.dump(text_index, f, indent=2)

print("💾 Index configurations saved to:")
print("   - scripts/vector_index_config.json")
print("   - scripts/text_index_config.json")
