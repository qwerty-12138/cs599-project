"""Memory read/write node"""
import logging
import time
from ..state import AgentState
from ..cancel import cancel_manager

logger = logging.getLogger(__name__)


async def load_memory_node(state: AgentState) -> dict:
    """Load session memory — initializes state"""
    sid = state.get("session_id", "")
    cancel_manager.ensure(sid)

    return {
        "start_time": time.time(),
        "total_tokens": 0,
        "tool_call_count": 0,
        "cancelled": False,
        "final_response": "",
        "error": None,
    }


async def write_memory_node(state: AgentState) -> dict:
    """Write to short-term memory. Skip long-term if cancelled."""
    if state.get("cancelled"):
        logger.info(f"Session {state.get('session_id')} cancelled — skipping persistence")
        return {}

    messages_list = []
    for msg in state.get("messages", [])[-6:]:
        messages_list.append({
            "role": "user" if msg.type == "human" else "assistant",
            "content": msg.content[:500],
            "timestamp": "",
        })

    short_term = (state.get("short_term_memories", []) or []) + messages_list
    logger.info(f"Memory: {len(messages_list)} messages stored")

    return {"short_term_memories": short_term[-50:]}
