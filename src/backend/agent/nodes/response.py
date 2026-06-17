"""Response generation node — produces final streaming response"""
import json
import logging
import time
from typing import AsyncGenerator
from ..state import AgentState
from ..llm import get_llm_client, get_model_name
from ..cancel import cancel_manager
from ..prompts import build_system_prompt
from .tool_call import prepare_tool_definitions

logger = logging.getLogger(__name__)


async def generate_response_node(state: AgentState) -> dict:
    """Generate final response from LLM."""
    if cancel_manager.is_cancelled(state["session_id"]):
        return {"cancelled": True}

    # Build context strings
    memory_context = "\n".join(
        m.get("content", "")[:200]
        for m in (state.get("short_term_memories", []) or [])[-5:]
    )
    rag_context = "\n".join(state.get("rag_context", []) or [])
    tool_context = "\n".join(
        f"工具 {r.get('name', '')}: {r.get('output', '')[:300]}"
        for r in (state.get("tool_results", []) or [])
    )

    system_prompt = build_system_prompt(
        memory_context=memory_context,
        rag_context=rag_context,
        tool_context=tool_context,
        skill_context=state.get("skill_context", "") or "",
    )

    # Build message list
    messages = [{"role": "system", "content": system_prompt}]

    # Add conversation history
    # Messages from LangGraph are BaseMessage objects; from direct calls may be tuples
    for msg in state.get("messages", []):
        # Handle tuple format: ("human", "content")
        if isinstance(msg, tuple):
            role_map = {"human": "user", "ai": "assistant", "user": "user", "assistant": "assistant"}
            role = role_map.get(msg[0], "user")
            messages.append({"role": role, "content": str(msg[1]) if len(msg) > 1 else ""})
            continue
        # Handle LangChain BaseMessage format
        if hasattr(msg, "type"):
            role = "user" if msg.type == "human" else "assistant"
            content = msg.content
            if hasattr(msg, "tool_calls") and msg.tool_calls:
                for tc in msg.tool_calls:
                    messages.append({
                        "role": "assistant",
                        "content": None,
                        "tool_calls": [{
                            "id": tc.get("id", ""),
                            "type": "function",
                            "function": {
                                "name": tc.get("name", ""),
                                "arguments": json.dumps(tc.get("args", {})),
                            }
                        }]
                    })
                continue
            # Tool results
            if hasattr(msg, "name") and msg.name:
                messages.append({
                    "role": "tool",
                    "tool_call_id": msg.tool_call_id if hasattr(msg, "tool_call_id") else "",
                    "content": msg.content[:2000],
                })
                continue
            messages.append({"role": role, "content": content})
        # Handle dict format
        elif isinstance(msg, dict):
            messages.append({"role": msg.get("role", "user"), "content": msg.get("content", "")})

    # Get tools if needed
    tools = None
    if state.get("intent") in ("tool_use", "complex"):
        tools = await prepare_tool_definitions(state)

    try:
        client = get_llm_client()
        model = get_model_name()

        kwargs = {
            "model": model,
            "messages": messages,
            "temperature": 0.7,
            "max_tokens": 2048,
        }
        if tools:
            kwargs["tools"] = tools
            kwargs["tool_choice"] = "auto"

        resp = await client.chat.completions.create(**kwargs)
        choice = resp.choices[0]
        msg = choice.message

        result = {"final_response": msg.content or ""}

        if msg.tool_calls:
            # Store tool calls for the next node
            tool_calls_data = []
            for tc in msg.tool_calls:
                tool_calls_data.append({
                    "id": tc.id,
                    "name": tc.function.name,
                    "args": json.loads(tc.function.arguments) if tc.function.arguments else {},
                    "source": "llm",
                })
            result["tool_calls"] = tool_calls_data

        return result

    except Exception as e:
        logger.error(f"Response generation failed: {e}")
        return {"final_response": f"生成回答时出错: {str(e)}", "error": str(e)}


async def stream_response(state: AgentState) -> AsyncGenerator[dict, None]:
    """Stream tokens from the LLM. Used by the streaming API."""
    import json
    from ...rag.pipeline import rag_pipeline

    yield {"event": "intent", "data": {"intent": state.get("intent", ""), "needs_rag": state.get("needs_rag", False)}}

    # RAG retrieval — try on every query, only include if scores are meaningful
    if state.get("messages"):
        last_msg = state["messages"]
        if isinstance(last_msg, list) and last_msg:
            msg = last_msg[-1]
            query_text = msg[1] if isinstance(msg, tuple) else (msg.content if hasattr(msg, "content") else str(msg))
        else:
            query_text = str(last_msg) if last_msg else ""
    else:
        query_text = ""

    if query_text:
        results = await rag_pipeline.retrieve("default", query_text, top_k=3)
        if results:
            # Only inject RAG context if the top result has a meaningful score (>0.05)
            if results[0].get("score", 0) > 0.05:
                state["rag_context"] = [await rag_pipeline.format_context(results)]
                state["rag_sources"] = await rag_pipeline.format_sources(results)
                yield {"event": "rag_sources", "data": {"sources": state["rag_sources"]}}

    # Build system prompt
    memory_context = "\n".join(
        m.get("content", "")[:200] for m in (state.get("short_term_memories", []) or [])[-5:]
    )
    rag_context = "\n".join(state.get("rag_context", []) or [])
    tool_context = "\n".join(
        f"工具 {r.get('name', '')}: {r.get('output', '')[:300]}"
        for r in (state.get("tool_results", []) or [])
    )

    system_prompt = build_system_prompt(
        memory_context=memory_context,
        rag_context=rag_context,
        tool_context=tool_context,
        skill_context=state.get("skill_context", "") or "",
    )

    messages = [{"role": "system", "content": system_prompt}]
    for msg in state.get("messages", []):
        # Handle tuple format: ("human", "content") or ("ai", "content")
        if isinstance(msg, tuple):
            role_map = {"human": "user", "ai": "assistant", "user": "user", "assistant": "assistant"}
            role = role_map.get(msg[0], "user")
            messages.append({"role": role, "content": msg[1]})
            continue
        # Handle LangChain BaseMessage format
        if hasattr(msg, "type"):
            role = "user" if msg.type == "human" else "assistant"
            content = msg.content
            if hasattr(msg, "tool_calls") and msg.tool_calls:
                messages.append({
                    "role": "assistant",
                    "content": None,
                    "tool_calls": [{
                        "id": tc["id"],
                        "type": "function",
                        "function": {"name": tc["name"], "arguments": json.dumps(tc.get("args", {}))}
                    } for tc in msg.tool_calls]
                })
                continue
            if hasattr(msg, "name") and msg.name:
                messages.append({
                    "role": "tool",
                    "tool_call_id": msg.tool_call_id if hasattr(msg, "tool_call_id") else "",
                    "content": msg.content[:2000],
                })
                continue
            messages.append({"role": role, "content": content})
        # Handle dict format
        elif isinstance(msg, dict):
            role = msg.get("role", "user")
            messages.append({"role": role, "content": msg.get("content", "")})

    tools = None
    if state.get("intent") in ("tool_use", "complex"):
        tools = await prepare_tool_definitions(state)

    client = get_llm_client()
    model = get_model_name()

    try:
        kwargs = {
            "model": model,
            "messages": messages,
            "temperature": 0.7,
            "max_tokens": 2048,
            "stream": True,
        }
        if tools:
            kwargs["tools"] = tools
            kwargs["tool_choice"] = "auto"

        stream_resp = await client.chat.completions.create(**kwargs)
        full_content = ""
        tool_calls_acc = {}

        async for chunk in stream_resp:
            if cancel_manager.is_cancelled(state["session_id"]):
                yield {"event": "cancelled", "data": {"session_id": state["session_id"]}}
                return

            delta = chunk.choices[0].delta if chunk.choices else None
            if not delta:
                continue

            # Content tokens
            if delta.content:
                full_content += delta.content
                yield {"event": "token", "data": {"content": delta.content, "index": len(full_content)}}

            # Tool calls
            if delta.tool_calls:
                for tc_delta in delta.tool_calls:
                    idx = tc_delta.index
                    if idx not in tool_calls_acc:
                        tool_calls_acc[idx] = {
                            "id": tc_delta.id or "",
                            "name": tc_delta.function.name or "" if tc_delta.function else "",
                            "arguments": "",
                        }
                    if tc_delta.function and tc_delta.function.arguments:
                        tool_calls_acc[idx]["arguments"] += tc_delta.function.arguments

        # Process accumulated tool calls
        if tool_calls_acc:
            for idx, tc_data in sorted(tool_calls_acc.items()):
                call_id = tc_data["id"]
                tool_name = tc_data["name"]
                args_str = tc_data["arguments"]
                try:
                    args = json.loads(args_str) if args_str else {}
                except json.JSONDecodeError:
                    args = {}

                yield {"event": "tool_start", "data": {"tool_name": tool_name, "args": args, "call_id": call_id}}

                # Execute tool
                from .tool_call import _execute_tool
                result = await _execute_tool(tool_name, args, call_id)

                yield {
                    "event": "tool_end",
                    "data": {
                        "tool_name": tool_name,
                        "result": result.get("output", result.get("error", "")),
                        "call_id": call_id,
                        "error": result.get("error"),
                    }
                }

                # Feed tool result back to LLM
                messages.append({
                    "role": "assistant",
                    "content": None,
                    "tool_calls": [{"id": call_id, "type": "function", "function": {"name": tool_name, "arguments": args_str}}]
                })
                messages.append({
                    "role": "tool",
                    "tool_call_id": call_id,
                    "content": result.get("output", result.get("error", "")),
                })

            # Continue generation with tool results
            kwargs["messages"] = messages
            kwargs.pop("stream", None)
            kwargs["stream"] = True
            stream_resp2 = await client.chat.completions.create(**kwargs)
            async for chunk in stream_resp2:
                if cancel_manager.is_cancelled(state["session_id"]):
                    yield {"event": "cancelled", "data": {"session_id": state["session_id"]}}
                    return
                delta = chunk.choices[0].delta if chunk.choices else None
                if delta and delta.content:
                    full_content += delta.content
                    yield {"event": "token", "data": {"content": delta.content, "index": len(full_content)}}

        yield {"event": "done", "data": {"session_id": state["session_id"], "total_tokens": 0, "latency_ms": 0}}

    except Exception as e:
        logger.error(f"Stream error: {e}")
        yield {"event": "error", "data": {"code": 500, "message": str(e)}}
