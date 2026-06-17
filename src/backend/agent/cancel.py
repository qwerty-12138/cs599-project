"""Cancel manager — allows cancelling generation mid-stream"""
import asyncio
from collections import defaultdict


class CancelManager:
    """Manages cancellation signals per session."""

    def __init__(self):
        self._signals: dict[str, asyncio.Event] = defaultdict(asyncio.Event)

    def ensure(self, session_id: str):
        """Ensure an event exists for this session (idempotent)."""
        if session_id not in self._signals:
            self._signals[session_id] = asyncio.Event()

    def cancel(self, session_id: str):
        if session_id in self._signals:
            self._signals[session_id].set()

    def is_cancelled(self, session_id: str) -> bool:
        return self._signals[session_id].is_set()

    def reset(self, session_id: str):
        if session_id in self._signals:
            self._signals[session_id].clear()

    async def check(self, session_id: str):
        if self.is_cancelled(session_id):
            raise GenerationCancelled(session_id)


class GenerationCancelled(Exception):
    def __init__(self, session_id: str):
        self.session_id = session_id
        super().__init__(f"Generation cancelled for session {session_id}")


cancel_manager = CancelManager()
