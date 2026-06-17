"""Tool call (ReAct loop) node — orchestrates tool selection and execution"""
import json
import logging
from typing import Optional
from ..state import AgentState
from ..llm import get_llm_client, get_model_name
from ..cancel import cancel_manager
from ..prompts import build_system_prompt
from ...mcp.native_tools import native_tool_registry, NATIVE_TOOLS
from ...mcp.client import mcp_client_manager

logger = logging.getLogger(__name__)


async def tool_call_node(state: AgentState) -> dict:
    """Execute tool calls in a ReAct-style loop.

    This node:
    1. Checks if there are pending tool calls from the LLM
    2. Executes them
    3. Returns results
    """
    if cancel_manager.is_cancelled(state["session_id"]):
        return {"cancelled": True}

    # Get the last AI message to check for tool calls
    messages = state.get("messages", [])
    if not messages:
        return {}

    last_msg = messages[-1]
    tool_calls = getattr(last_msg, "tool_calls", []) or []

    if not tool_calls:
        return {}

    count = state.get("tool_call_count", 0)
    if count >= 10:
        return {"tool_call_count": count, "error": "工具调用次数超过上限 (10)"}

    results = []
    for tc in tool_calls:
        name = tc.get("name", tc.get("function", {}).get("name", ""))
        args_raw = tc.get("args", tc.get("function", {}).get("arguments", "{}"))
        if isinstance(args_raw, str):
            try:
                args = json.loads(args_raw)
            except json.JSONDecodeError:
                args = {}
        else:
            args = args_raw

        call_id = tc.get("id", "")

        logger.info(f"Tool call: {name}({args})")

        # Try MCP tools first, then native
        result = await _execute_tool(name, args, call_id)
        results.append(result)

    tool_results = state.get("tool_results", []) + results

    return {
        "tool_calls": tool_calls,
        "tool_results": tool_results,
        "tool_call_count": count + len(tool_calls),
    }


async def _execute_tool(name: str, args: dict, call_id: str) -> dict:
    """Execute a tool by name, checking MCP then native."""
    # Check native tools
    for nt in NATIVE_TOOLS:
        if nt["name"] == name:
            try:
                output = await native_tool_registry.execute(name, args)
                return {"call_id": call_id, "name": name, "output": output, "error": None}
            except Exception as e:
                return {"call_id": call_id, "name": name, "output": "", "error": str(e)}

    # Check MCP tools (search by name)
    enabled_tools = mcp_client_manager.get_enabled_tools()
    for et in enabled_tools:
        if et["name"] == name:
            result_str = await mcp_client_manager.call_tool(et["id"], args)
            return {"call_id": call_id, "name": name, "output": result_str, "error": None}

    return {"call_id": call_id, "name": name, "output": "", "error": f"未知工具: {name}"}


async def prepare_tool_definitions(state: AgentState) -> Optional[list[dict]]:
    """Build tool definitions list for the LLM to choose from."""
    tool_defs = []

    # Add native tools
    tool_defs.extend(native_tool_registry.get_tool_definitions())

    # Add MCP tools
    enabled = mcp_client_manager.get_enabled_tools()
    for et in enabled:
        schema = et.get("inputSchema", {}) or {}
        # Clean schema for OpenAI function calling
        if schema and "type" not in schema:
            schema = {"type": "object", "properties": schema.get("properties", {}), "required": schema.get("required", [])}
        base_desc = et["description"] or et["name"]
        # Append tool selection hint to description so LLM chooses the most relevant one
        tool_defs.append({
            "type": "function",
            "function": {
                "name": et["name"],
                "description": f"{base_desc}\n（如果用户问题只需要一个工具即可完成，请只选择最直接相关的这一个工具，不要选择其他功能相似的工具）",
                "parameters": schema if schema else {"type": "object", "properties": {}},
            }
        })

    return tool_defs if tool_defs else None
