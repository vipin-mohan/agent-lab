"""
Pinecone vector store + sentence-transformer embedding model.

Uses module-level singletons with a threading.Lock so both the Streamlit
app (which may call from multiple threads) and the MCP server (asyncio
with a thread pool) get a single shared instance rather than re-initialising
on every request.

No Streamlit imports. No st.cache_resource. No st.error.
Failures are surfaced as empty results rather than raised exceptions so
callers degrade gracefully when Pinecone credentials are absent.
"""

import logging
import threading

from .secrets import get_secret

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Embedding model singleton
# ---------------------------------------------------------------------------

_model = None
_model_lock = threading.Lock()


def get_embedding_model():
    """Return the shared SentenceTransformer instance, initialising once."""
    global _model
    with _model_lock:
        if _model is None:
            from sentence_transformers import SentenceTransformer
            _model = SentenceTransformer("all-MiniLM-L6-v2")
    return _model


# ---------------------------------------------------------------------------
# Pinecone index singleton
# ---------------------------------------------------------------------------

_index = None
_index_initialized = False
_index_lock = threading.Lock()


def get_pinecone_index():
    """Return the shared Pinecone Index, or None if unavailable."""
    global _index, _index_initialized
    with _index_lock:
        if not _index_initialized:
            try:
                from pinecone import Pinecone
                api_key = get_secret("PINECONE_API_KEY")
                if not api_key:
                    logger.warning("get_pinecone_index: PINECONE_API_KEY not set")
                    _index_initialized = True
                    return None
                logger.info(
                    "get_pinecone_index: connecting to Pinecone (api_key length=%d)",
                    len(api_key),
                )
                pc = Pinecone(api_key=api_key)
                index_name = get_secret("PINECONE_INDEX_NAME") or "coaching-notes"
                logger.info("get_pinecone_index: opening index %r", index_name)
                _index = pc.Index(index_name)
                logger.info("get_pinecone_index: connected successfully")
            except Exception:
                logger.exception(
                    "get_pinecone_index: failed to initialise Pinecone client"
                )
            _index_initialized = True
    return _index


# ---------------------------------------------------------------------------
# Public helpers
# ---------------------------------------------------------------------------

def retrieve_relevant_coaching(query: str, n_results: int = 5) -> str:
    """
    Return a formatted coaching-context block for injection into an LLM prompt,
    or an empty string if Pinecone is unavailable or the query returns nothing.
    """
    index = get_pinecone_index()
    if index is None:
        return ""
    try:
        model = get_embedding_model()
        embedding = model.encode(query).tolist()
        results = index.query(vector=embedding, top_k=n_results, include_metadata=True)
        chunks = [
            match["metadata"]["text"]
            for match in results["matches"]
            if "text" in match.get("metadata", {})
        ]
        if not chunks:
            return ""
        sections = "\n---\n".join(chunks)
        return f"\n\n## Relevant Coaching Patterns from 250+ Sessions\n{sections}"
    except Exception:
        return ""


def search_raw(query: str, top_k: int = 5) -> list[dict]:
    """
    Semantic search returning structured chunks.

    Each element is a dict with keys:
      - ``text``  (str)   — the coaching note chunk
      - ``score`` (float) — cosine similarity score from Pinecone
    """
    index = get_pinecone_index()
    if index is None:
        logger.warning("search_raw: Pinecone index not available")
        return []
    try:
        model = get_embedding_model()
        embedding = model.encode(query).tolist()
        results = index.query(vector=embedding, top_k=top_k, include_metadata=True)

        # Support both dict-style (older SDK) and attribute-style (newer SDK)
        # Pinecone response objects.
        matches = (
            results.get("matches", [])
            if isinstance(results, dict)
            else getattr(results, "matches", [])
        )

        logger.info(
            "search_raw: query=%r top_k=%d got %d matches",
            query, top_k, len(matches),
        )
        if matches:
            first = matches[0]
            metadata = (
                first.get("metadata", {})
                if isinstance(first, dict)
                else getattr(first, "metadata", {})
            )
            logger.info(
                "search_raw: first match metadata keys = %s",
                list(metadata.keys()) if metadata else "EMPTY",
            )

        out = []
        for match in matches:
            if isinstance(match, dict):
                metadata = match.get("metadata", {}) or {}
                score = match.get("score", 0.0)
            else:
                metadata = getattr(match, "metadata", {}) or {}
                score = getattr(match, "score", 0.0)
            text = metadata.get("text", "") if isinstance(metadata, dict) else ""
            if text:
                out.append({"text": text, "score": float(score)})
        return out
    except Exception:
        logger.exception("search_raw: Pinecone query failed")
        return []
