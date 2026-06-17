"""Long-term memory using in-memory dict with vector search via embedding comparison"""
import time
import logging
import json
from typing import Optional
from ..config import settings

logger = logging.getLogger(__name__)


class LongTermMemory:
    """In-memory long-term memory. Stores facts and session summaries."""

    def __init__(self):
        self._facts: list[dict] = []
        self._summaries: list[dict] = []

    async def store_fact(self, user_id: str, fact: str, memory_type: str = "knowledge",
                         importance: float = 0.5, embedding: Optional[list[float]] = None):
        entry = {
            "id": f"fact_{int(time.time() * 1000)}_{len(self._facts)}",
            "user_id": user_id,
            "memory_type": memory_type,
            "content": fact,
            "importance": importance,
            "embedding": embedding,
            "access_count": 0,
            "created_at": time.time(),
        }
        self._facts.append(entry)
        logger.debug(f"LongTermMemory: stored fact '{fact[:40]}...'")

    async def search_similar(self, user_id: str, query: str,
                             top_k: int = 5) -> list[dict]:
        """Simple text-based similarity (keyword matching fallback when no embeddings)."""
        results = []
        query_lower = query.lower()
        for fact in self._facts:
            if fact["user_id"] != user_id:
                continue
            content = fact.get("content", "")
            # Simple keyword overlap
            query_words = set(query_lower.split())
            content_words = set(content.lower().split())
            overlap = len(query_words & content_words)
            if overlap > 0:
                score = overlap / max(len(query_words), 1)
                results.append((fact, score))
        results.sort(key=lambda x: x[1], reverse=True)
        top = results[:top_k]
        for fact, score in top:
            fact["access_count"] = fact.get("access_count", 0) + 1
        return [dict(r[0], score=r[1]) for r in top]

    async def store_session_summary(self, user_id: str, session_id: str, summary: dict):
        entry = {
            "id": f"sum_{int(time.time() * 1000)}",
            "user_id": user_id,
            "session_id": session_id,
            "summary": summary.get("summary", ""),
            "key_topics": summary.get("key_topics", []),
            "extracted_facts": summary.get("extracted_facts", []),
            "user_preferences": summary.get("user_preferences", []),
            "created_at": time.time(),
        }
        self._summaries.append(entry)

    async def get_user_context(self, user_id: str, max_tokens: int = 2000) -> str:
        """Build a context string from stored facts."""
        user_facts = [f for f in self._facts if f["user_id"] == user_id]
        user_facts.sort(key=lambda f: f.get("importance", 0), reverse=True)
        parts = []
        total = 0
        for fact in user_facts[:settings.MAX_LONG_TERM_RESULTS]:
            text = f"- {fact['content']}"
            tokens = len(text) // 2
            if total + tokens > max_tokens:
                break
            parts.append(text)
            total += tokens
        return "\n".join(parts)
