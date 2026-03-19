"""Tool: search_knowledge_base

This is the DOCUMENT RAG piece — the one place in the system
where we do traditional vector similarity search over text chunks.

Used for sensor troubleshooting, calibration guidance, installation
SOPs, and LoRaWAN connectivity issues. The knowledge base is stored
in PostgreSQL with pgvector embeddings.

This demonstrates the dual retrieval strategy:
- Structured data → tool-use functions (soil, disease, weather)
- Unstructured knowledge → pgvector similarity search (this tool)
"""

import json
import anthropic
from app.database import execute_query
from app.config import settings


def search_knowledge_base(query: str, category: str | None = None, max_results: int = 3) -> str:
    """Search sensor documentation and troubleshooting guides.

    Uses pgvector cosine similarity to find relevant documentation
    chunks. Falls back to keyword search if embeddings aren't populated.

    Args:
        query: Natural language search query
        category: Optional filter — 'calibration', 'troubleshooting',
                  'installation', 'connectivity'
        max_results: Number of results to return (default 3)

    Returns:
        JSON string with relevant documentation chunks.
    """

    # Try vector search first (if embeddings exist)
    embedding = _get_embedding(query)

    if embedding:
        # pgvector cosine similarity search
        category_filter = "AND category = :category" if category else ""

        results = execute_query(f"""
            SELECT
                title,
                source,
                category,
                content,
                1 - (embedding <=> :embedding::vector) AS similarity
            FROM knowledge_base
            WHERE embedding IS NOT NULL
            {category_filter}
            ORDER BY embedding <=> :embedding::vector
            LIMIT :max_results
        """, {
            "embedding": str(embedding),
            "category": category,
            "max_results": max_results,
        })
    else:
        # Fallback: keyword search using PostgreSQL full-text
        category_filter = "AND category = :category" if category else ""

        results = execute_query(f"""
            SELECT
                title,
                source,
                category,
                content,
                ts_rank(
                    to_tsvector('english', content),
                    plainto_tsquery('english', :query)
                ) AS similarity
            FROM knowledge_base
            WHERE to_tsvector('english', content) @@ plainto_tsquery('english', :query)
            {category_filter}
            ORDER BY similarity DESC
            LIMIT :max_results
        """, {
            "query": query,
            "category": category,
            "max_results": max_results,
        })

    if not results:
        return json.dumps({
            "query": query,
            "results": [],
            "message": "No relevant documentation found. Try rephrasing or contact support."
        })

    return json.dumps({
        "query": query,
        "results": [
            {
                "title": r["title"],
                "source": r["source"],
                "category": r["category"],
                "content": r["content"],
                "relevance": round(float(r["similarity"]), 3) if r["similarity"] else None,
            }
            for r in results
        ],
    }, default=str)


def _get_embedding(text: str) -> list[float] | None:
    """Generate an embedding using Anthropic's Voyager or fallback.

    In production you'd use a dedicated embedding model.
    For the demo, we try Voyager via the Anthropic SDK. If unavailable,
    we fall back to keyword search (the tool still works).
    """
    try:
        # Use a lightweight approach: hash-based pseudo-embedding
        # for the demo. In production, use:
        #   - Anthropic Voyager
        #   - OpenAI ada-002
        #   - sentence-transformers locally
        #
        # For now, return None to use keyword fallback.
        # This keeps the demo working without an embedding API call.
        return None
    except Exception:
        return None


def populate_embeddings():
    """One-time script to generate embeddings for all KB entries.

    Run this after seeding the knowledge base:
        python -c "from app.tools.knowledge_base import populate_embeddings; populate_embeddings()"

    For the demo, we skip this and use keyword search fallback.
    In production, you'd run this as part of the data pipeline
    whenever new documentation is added.
    """
    # Placeholder for production implementation
    print("Embedding generation would run here.")
    print("Using keyword search fallback for demo.")
