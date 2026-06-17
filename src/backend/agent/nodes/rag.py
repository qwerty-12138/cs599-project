"""RAG retrieve node"""
import logging
from ..state import AgentState
from ..llm import get_llm_client, get_model_name
from ..cancel import cancel_manager
from ...rag.pipeline import rag_pipeline

logger = logging.getLogger(__name__)


def _get_last_message_text(state: AgentState) -> str:
    """Extract text from the last message, handling tuple/BaseMessage formats."""
    msgs = state.get("messages", [])
    if not msgs:
        return ""
    msg = msgs[-1]
    if isinstance(msg, tuple):
        return msg[1] if len(msg) > 1 else str(msg[0])
    if hasattr(msg, "content"):
        return msg.content
    return str(msg)


async def rag_retrieve_node(state: AgentState) -> dict:
    """Retrieve relevant documents from the knowledge base."""
    if cancel_manager.is_cancelled(state["session_id"]):
        return {"cancelled": True}

    last_msg = _get_last_message_text(state)
    if not last_msg:
        return {"rag_context": [], "rag_sources": []}

    logger.info(f"RAG retrieving for: {last_msg[:60]}...")

    results = await rag_pipeline.retrieve("default", last_msg, top_k=5)

    # Only inject context if the best score is meaningful
    rag_context = []
    rag_sources = []
    if results and results[0].get("score", 0) > 0.05:
        rag_context = [await rag_pipeline.format_context(results)]
        rag_sources = await rag_pipeline.format_sources(results)
        logger.info(f"RAG found {len(results)} relevant results (top score={results[0]['score']:.3f})")
    else:
        logger.info(f"RAG skipped — no relevant results found")

    return {
        "rag_context": rag_context,
        "rag_sources": rag_sources,
    }
