"""Agent state type definition"""
from typing import TypedDict, Annotated, Sequence, Any
from langgraph.graph.message import add_messages
from langchain_core.messages import BaseMessage


class AgentState(TypedDict):
    messages: Annotated[Sequence[BaseMessage], add_messages]
    user_id: str
    session_id: str
    intent: str
    needs_rag: bool
    rag_context: list[str]
    rag_sources: list[dict]
    enabled_tools: list[str]
    tool_calls: list[dict]
    tool_results: list[dict]
    tool_call_count: int
    short_term_memories: list[dict]
    long_term_memories: list[dict]
    cancelled: bool
    error: str | None
    final_response: str
    total_tokens: int
    start_time: float
