"""LangGraph agent graph construction"""
import os
import time
import json
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage

from .state import AgentState
from .nodes.intent import intent_classifier_node
from .nodes.rag import rag_retrieve_node
from .nodes.response import generate_response_node
from .nodes.memory import write_memory_node, load_memory_node
from .nodes.tool_call import tool_call_node, _execute_tool


def build_graph() -> StateGraph:
    builder = StateGraph(AgentState)

    # Add nodes
    builder.add_node("load_memory", load_memory_node)
    builder.add_node("intent_classifier", intent_classifier_node)
    builder.add_node("rag_retrieve", rag_retrieve_node)
    builder.add_node("tool_call", tool_call_node)
    builder.add_node("generate_response", generate_response_node)
    builder.add_node("write_memory", write_memory_node)

    # Entry
    builder.set_entry_point("load_memory")

    # Memory → Intent
    builder.add_edge("load_memory", "intent_classifier")

    # Conditional routing from intent
    builder.add_conditional_edges(
        "intent_classifier",
        _route,
        {
            "rag_retrieve": "rag_retrieve",
            "tool_call": "tool_call",
            "generate_response": "generate_response",
            "end": END,
        }
    )

    # RAG (and complex) → Tool or Response
    builder.add_conditional_edges(
        "rag_retrieve",
        _route_after_rag,
        {
            "tool_call": "tool_call",
            "generate_response": "generate_response",
        }
    )

    # Tool → loop back or continue
    builder.add_conditional_edges(
        "tool_call",
        _route_after_tool,
        {
            "tool_call": "tool_call",
            "generate_response": "generate_response",
        }
    )

    # Response → Memory → End
    builder.add_edge("generate_response", "write_memory")
    builder.add_edge("write_memory", END)

    return builder.compile(checkpointer=MemorySaver())


def _route(state: AgentState) -> str:
    if state.get("cancelled"):
        return "end"
    intent = state.get("intent", "chitchat")
    if intent in ("knowledge", "complex", "chitchat"):
        # Always try RAG — the node checks if scores are meaningful
        return "rag_retrieve"
    elif intent == "tool_use":
        return "tool_call"
    else:
        return "generate_response"


def _route_after_rag(state: AgentState) -> str:
    """After RAG, decide if we need tools (complex queries)."""
    if state.get("cancelled"):
        return "generate_response"
    intent = state.get("intent", "")
    if intent == "complex":
        return "tool_call"
    return "generate_response"


def _route_after_tool(state: AgentState) -> str:
    """After tool call, continue looping if more tools needed."""
    if state.get("cancelled"):
        return "generate_response"

    # If there were tool results from this turn, feed them back to the LLM
    tool_results = state.get("tool_results", [])
    tool_calls = state.get("tool_calls", [])
    count = state.get("tool_call_count", 0)

    if not tool_calls:
        return "generate_response"

    if count >= 10:
        logger.warning(f"Tool call limit reached ({count})")
        return "generate_response"

    # Add tool results as messages so the LLM can see them
    # This happens via state mutations in the tool_call_node
    return "generate_response"


# Singleton for streaming
_graph_instance = None


def get_graph():
    global _graph_instance
    if _graph_instance is None:
        _graph_instance = build_graph()
    return _graph_instance


import logging
logger = logging.getLogger(__name__)
