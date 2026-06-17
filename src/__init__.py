"""Agent state definition for LangGraph"""
from typing import TypedDict, Annotated, Sequence
from langgraph.graph.message import add_messages
from langchain_core.messages import BaseMessage


class ToolCall(TypedDict):
    id: str
    name: str
    args: dict
    source: str  # "native" | "mcp"


class ToolResult(TypedDict):
    call_id: str
    name: str
    output: str
    error: str | None


class AgentState(TypedDict):
    messages: Annotated[Sequence[BaseMessage], add_messages]
    user_id: str
    session_id: str
    intent: str  # "knowledge" | "chitchat" | "tool_use" | "complex"
    needs_rag: bool
    rag_context: list[str]
    rag_sources: list[dict]
    tool_calls: list[ToolCall]
    tool_results: list[ToolResult]
    tool_call_count: int
    short_term_memories: list[dict]
    long_term_memories: list[dict]
    cancelled: bool
    error: str | None
    final_response: str
    total_tokens: int
    start_time: float
