"""MCP Tool Wrapper — wraps MCP tools into callable format"""
import json
import logging
import httpx
from typing import Optional
from .config import MCPToolInfo

logger = logging.getLogger(__name__)


class MCPToolWrapper:
    """Wraps an MCP tool (discovered from an MCP server) for invocation."""

    def __init__(self, tool_info: MCPToolInfo, server_url: str, headers: Optional[dict] = None):
        self.name = tool_info.name
        self.description = tool_info.description
        self.input_schema = tool_info.inputSchema or {}
        self.tool_id = tool_info.id
        self.server_url = server_url.rstrip("/")
        self.headers = headers or {}

    async def call(self, args: dict) -> str:
        """Call the MCP tool via JSON-RPC over HTTP."""
        payload = {
            "jsonrpc": "2.0",
            "method": "tools/call",
            "params": {
                "name": self.name,
                "arguments": args,
            },
            "id": self.tool_id,
        }
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                resp = await client.post(
                    self.server_url,
                    json=payload,
                    headers={**self.headers, "Content-Type": "application/json", "Accept": "application/json, text/event-stream"},
                )
                if resp.status_code >= 400:
                    logger.warning(f"Tool call HTTP {resp.status_code}: {resp.text[:500]}")
                    return json.dumps([{"type": "text", "text": f"call failed, status: {resp.status_code}, response: {resp.text[:300]}"}], ensure_ascii=False)

                # Handle SSE-style response
                content_type = resp.headers.get("content-type", "")
                if "text/event-stream" in content_type:
                    result = self._parse_sse_response(resp.text)
                else:
                    result = resp.json()

                if "error" in result and result["error"]:
                    err_msg = result['error'].get('message', str(result['error']))
                    return json.dumps([{"type": "text", "text": f"call failed: {err_msg}"}], ensure_ascii=False)
                content = result.get("result", {}).get("content", [])
                return json.dumps(content, ensure_ascii=False)
        except httpx.TimeoutException:
            return json.dumps([{"type": "text", "text": "call failed: 请求超时"}], ensure_ascii=False)
        except Exception as e:
            logger.error(f"Tool call exception: {e}")
            return json.dumps([{"type": "text", "text": f"call failed: {str(e)}"}], ensure_ascii=False)

    def _parse_sse_response(self, text: str) -> dict:
        """Parse SSE-formatted response to extract JSON-RPC data."""
        for line in text.splitlines():
            line = line.strip()
            if line.startswith("data:"):
                data_str = line[5:].strip()
                try:
                    import json as _json
                    return _json.loads(data_str)
                except Exception:
                    continue
        return {}

    def to_definition(self) -> dict:
        """Return tool definition in OpenAI function-calling format."""
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.input_schema,
            }
        }
