"""RAG pipeline main entry"""
import logging
from typing import Optional
from .embedding import embedding_manager
from .knowledge_base import kb_manager

logger = logging.getLogger(__name__)


class RAGPipeline:
    """Main RAG pipeline orchestration."""

    async def retrieve(self, kb_id: str, query: str, top_k: int = 5) -> list[dict]:
        """Retrieve relevant contexts from the knowledge base."""
        results = await kb_manager.search(kb_id, query, top_k)
        return results

    async def format_context(self, results: list[dict]) -> str:
        """Format retrieval results as a context string."""
        if not results:
            return ""
        lines = ["## 知识库检索结果\n"]
        for i, r in enumerate(results, 1):
            source = r.get("documentName", "Unknown")
            score = r.get("score", 0)
            content = r.get("content", "")
            lines.append(
                f"### [{i}] 来源: {source} (相关性: {score:.0%})\n"
                f"{content}\n"
            )
        return "\n".join(lines)

    async def format_sources(self, results: list[dict]) -> list[dict]:
        """Format as source metadata for frontend."""
        return [
            {
                "documentId": r.get("documentId", ""),
                "documentName": r.get("documentName", "Unknown"),
                "chunkId": r.get("chunkId", ""),
                "content": r.get("content", "")[:200],
                "score": r.get("score", 0),
            }
            for r in results
        ]


rag_pipeline = RAGPipeline()
