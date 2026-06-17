"""MemoryManager — unified access to short-term and long-term memory"""
import logging
from .short_term import ShortTermMemory
from .long_term import LongTermMemory

logger = logging.getLogger(__name__)


class MemoryManager:
    """Unified memory interface."""

    def __init__(self):
        self.short_term = ShortTermMemory()
        self.long_term = LongTermMemory()

    async def load_context(self, user_id: str, session_id: str) -> dict:
        """Load full session context: short-term + long-term."""
        short = await self.short_term.get_context(user_id, session_id)
        long_ctx = ""
        if short:
            last_msg = short[-1].get("content", "")
            long_facts = await self.long_term.search_similar(user_id, last_msg)
            long_ctx = "\n".join(f.get("content", "") for f in long_facts)
        return {"short_term": short, "long_term": long_ctx}

    async def add_message(self, user_id: str, session_id: str, message: dict):
        await self.short_term.add_turn(user_id, session_id, message)

    async def end_session(self, user_id: str, session_id: str):
        # Placeholder for summarization and long-term storage
        pass

    async def clear_session(self, user_id: str, session_id: str):
        await self.short_term.clear_session(user_id, session_id)

    async def update_message_id(self, user_id: str, session_id: str,
                                 temp_id: str, real_id: str, metadata: dict = None):
        await self.short_term.update_message_id(user_id, session_id, temp_id, real_id, metadata)


memory_manager = MemoryManager()
