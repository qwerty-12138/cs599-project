"""Embedding manager for RAG pipeline"""
import os
import logging
from typing import Optional
from openai import AsyncOpenAI
from ..config import settings

logger = logging.getLogger(__name__)


class EmbeddingManager:
    """Manages text embeddings via DashScope API."""

    def __init__(self):
        self._client: Optional[AsyncOpenAI] = None

    def _get_client(self) -> AsyncOpenAI:
        if self._client is None:
            self._client = AsyncOpenAI(
                api_key=settings.DASHSCOPE_API_KEY,
                base_url=settings.DASHSCOPE_BASE_URL,
            )
        return self._client

    async def embed_text(self, text: str) -> list[float]:
        client = self._get_client()
        resp = await client.embeddings.create(
            model=settings.DASHSCOPE_EMBEDDING_MODEL,
            input=text,
        )
        return resp.data[0].embedding

    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        """Embed multiple texts, respecting API limits."""
        client = self._get_client()
        batch_size = 20
        all_embeddings = []
        for i in range(0, len(texts), batch_size):
            batch = texts[i:i + batch_size]
            resp = await client.embeddings.create(
                model=settings.DASHSCOPE_EMBEDDING_MODEL,
                input=batch,
            )
            # Sort by index to maintain order
            sorted_data = sorted(resp.data, key=lambda x: x.index)
            all_embeddings.extend(d.embedding for d in sorted_data)
        return all_embeddings


embedding_manager = EmbeddingManager()
