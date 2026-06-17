"""Agent nodes — each node is a standalone async function"""
import json
import time
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage

from ..state import AgentState
from ..llm import get_llm_client, get_model_name
from ..cancel import cancel_manager
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def load_memory_node(state: AgentState) -> dict:
    """Initialize session state"""
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
