"""Short-term memory using in-memory dict (Redis-compatible interface)"""
import time
import logging
from typing import Optional
from ..config import settings

logger = logging.getLogger(__name__)


class ShortTermMemory:
    """In-memory short-term memory. Can be swapped for Redis."""

    def __init__(self):
        self._store: dict[str, list[dict]] = {}
        self._ttl: dict[str, float] = {}  # session_key -> expiry

    def _key(self, user_id: str, session_id: str) -> str:
        return f"{user_id}:{session_id}"

    def _check_ttl(self, key: str):
        if key in self._ttl and time.time() > self._ttl[key]:
            self._store.pop(key, None)
            self._ttl.pop(key, None)

    async def add_turn(self, user_id: str, session_id: str, message: dict):
        key = self._key(user_id, session_id)
        self._check_ttl(key)
        if key not in self._store:
            self._store[key] = []
        self._store[key].append(message)
        self._ttl[key] = time.time() + settings.SHORT_TERM_TTL
        logger.debug(f"Memory: added turn to {key}, total={len(self._store[key])}")

    async def get_recent(self, user_id: str, session_id: str, n: int = 20) -> list[dict]:
        key = self._key(user_id, session_id)
        self._check_ttl(key)
        messages = self._store.get(key, [])
        return messages[-n:]

    async def get_context(self, user_id: str, session_id: str, max_tokens: int = 4000) -> list[dict]:
        messages = await self.get_recent(user_id, session_id, settings.MAX_SHORT_TERM_MESSAGES)
        result = []
        total = 0
        for msg in reversed(messages):
            tokens = msg.get("token_count", len(msg.get("content", "")) // 2)
            if total + tokens > max_tokens:
                break
            result.insert(0, msg)
            total += tokens
        return result

    async def clear_session(self, user_id: str, session_id: str):
        key = self._key(user_id, session_id)
        self._store.pop(key, None)
        self._ttl.pop(key, None)

    async def update_message_id(self, user_id: str, session_id: str, temp_id: str, real_id: str, metadata: dict = None):
        """Update a temp message's ID after server-side persistence."""
        key = self._key(user_id, session_id)
        messages = self._store.get(key, [])
        for msg in messages:
            if msg.get("id") == temp_id:
                msg["id"] = real_id
                if metadata:
                    msg.update(metadata)
                break
