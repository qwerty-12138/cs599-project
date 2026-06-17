"""MCP Client Manager — connects to MCP servers and manages tools"""
import json
import uuid
import logging
import os
from typing import Optional
from .config import MCPServerConfig, MCPToolInfo
from .tool_wrapper import MCPToolWrapper
from .native_tools import NATIVE_TOOLS, native_tool_registry
from .server_registry import server_registry

logger = logging.getLogger(__name__)

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))), "data")
TOOLS_FILE = os.path.join(DATA_DIR, "mcp_tools.json")


class MCPClientManager:
    """Manages connections to MCP servers and their tools."""

    def __init__(self):
        self._tools: dict[str, MCPToolWrapper] = {}
        self._servers: dict[str, list[MCPToolInfo]] = {}
        self._load_tools()

    async def discover_tools(self, server_id: str) -> list[MCPToolInfo]:
        """Discover tools from an MCP server via HTTP JSON-RPC introspection."""
        server_cfg = server_registry.get_server(server_id)
        if not server_cfg:
            raise ValueError(f"Server {server_id} not found")

        url = server_cfg.url.rstrip("/")
        if not url:
            raise ValueError("Server URL is empty")

        # Build auth headers from configJson
        auth_headers = self._build_auth_headers(server_cfg)

        # Try to call list_tools via JSON-RPC
        payload = {
            "jsonrpc": "2.0",
            "method": "tools/list",
            "params": {},
            "id": str(uuid.uuid4()),
        }
        try:
            import httpx
            async with httpx.AsyncClient(timeout=15.0) as client:
                resp = await client.post(
                    url,
                    json=payload,
                    headers={**auth_headers, "Content-Type": "application/json", "Accept": "application/json, text/event-stream"},
                )
                resp.raise_for_status()

                # Handle SSE-style response (text/event-stream)
                content_type = resp.headers.get("content-type", "")
                if "text/event-stream" in content_type:
                    result = self._parse_sse_response(resp.text)
                else:
                    result = resp.json()

                if "error" in result and result["error"]:
                    err_msg = result['error'].get('message', str(result['error']))
                    logger.warning(f"MCP list_tools error: {err_msg}")
                    server_cfg.status = "ERROR"
                    raise ValueError(f"服务器返回错误: {err_msg}")

                tools_data = result.get("result", {}).get("tools", [])
        except httpx.HTTPStatusError as e:
            server_cfg.status = "ERROR"
            logger.warning(f"HTTP {e.response.status_code} from {url}: {e.response.text[:200]}")
            raise ValueError(f"HTTP {e.response.status_code}: {e.response.text[:200] or '认证失败或服务器错误'}")
        except Exception as e:
            server_cfg.status = "ERROR"
            logger.warning(f"Failed to discover tools from {url}: {e}")
            raise ValueError(f"连接失败: {str(e)}")

        server_cfg.status = "CONNECTED"
        tools = []
        for t in tools_data:
            tool_info = MCPToolInfo(
                id=str(uuid.uuid4()),
                name=t.get("name", "unknown"),
                description=t.get("description", ""),
                inputSchema=t.get("inputSchema", t.get("parameters", {})),
                enabled=True,
                serverId=server_id,
            )
            tools.append(tool_info)

        self._servers[server_id] = tools

        # Create wrappers with auth headers
        for tool in tools:
            self._tools[tool.id] = MCPToolWrapper(tool, url, auth_headers)
            # Store input schema for LLM tool definition
            self._tool_schemas = getattr(self, '_tool_schemas', {})
            self._tool_schemas[tool.id] = tool.inputSchema

        logger.info(f"Discovered {len(tools)} tools from server {server_cfg.name}")
        self._save_tools()
        return tools

    def _load_tools(self):
        """Load tools from persistent storage on startup."""
        if os.path.exists(TOOLS_FILE):
            try:
                with open(TOOLS_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    for server_id, tools_data in data.items():
                        server_cfg = server_registry.get_server(server_id)
                        if server_cfg and server_cfg.enabled:
                            tools = []
                            for t in tools_data:
                                tool_info = MCPToolInfo(**t)
                                tools.append(tool_info)
                            self._servers[server_id] = tools
                            
                            url = server_cfg.url.rstrip("/")
                            auth_headers = self._build_auth_headers(server_cfg)
                            for tool in tools:
                                if tool.enabled:
                                    self._tools[tool.id] = MCPToolWrapper(tool, url, auth_headers)
                                    self._tool_schemas = getattr(self, '_tool_schemas', {})
                                    self._tool_schemas[tool.id] = tool.inputSchema
                logger.info(f"Loaded {sum(len(v) for v in self._servers.values())} MCP tools from persistent storage")
            except Exception as e:
                logger.warning(f"Failed to load tools: {e}")

    def _save_tools(self):
        """Save tools to persistent storage."""
        os.makedirs(DATA_DIR, exist_ok=True)
        try:
            data = {}
            for server_id, tools in self._servers.items():
                data[server_id] = [t.dict() for t in tools]
            with open(TOOLS_FILE, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.warning(f"Failed to save tools: {e}")

    def enable_server_tools(self, server_id: str):
        """Enable all tools for a server when it's enabled."""
        server_cfg = server_registry.get_server(server_id)
        if not server_cfg:
            return
        
        if server_id not in self._servers:
            return
        
        url = server_cfg.url.rstrip("/")
        auth_headers = self._build_auth_headers(server_cfg)
        
        for tool in self._servers[server_id]:
            if tool.enabled:
                self._tools[tool.id] = MCPToolWrapper(tool, url, auth_headers)
                self._tool_schemas = getattr(self, '_tool_schemas', {})
                self._tool_schemas[tool.id] = tool.inputSchema
        
        logger.info(f"Enabled {len(self._servers[server_id])} tools for server {server_cfg.name}")

    def disable_server_tools(self, server_id: str):
        """Disable all tools for a server when it's disabled."""
        if server_id not in self._servers:
            return
        
        for tool in self._servers[server_id]:
            self._tools.pop(tool.id, None)
            schemas = getattr(self, '_tool_schemas', {})
            schemas.pop(tool.id, None)
        
        logger.info(f"Disabled all tools for server {server_id}")

    def _build_auth_headers(self, server_cfg) -> dict:
        """Build auth headers from server config (configJson field)."""
        headers = {}
        if server_cfg.configJson:
            try:
                extra = json.loads(server_cfg.configJson)
                # Support multiple auth header formats
                if "headers" in extra and isinstance(extra["headers"], dict):
                    headers.update(extra["headers"])
                if "Authorization" in extra:
                    headers["Authorization"] = extra["Authorization"]
                if "authorization" in extra:
                    headers["Authorization"] = extra["authorization"]
                if "apiKey" in extra:
                    headers["Authorization"] = f"Bearer {extra['apiKey']}"
                if "api_key" in extra:
                    headers["Authorization"] = f"Bearer {extra['api_key']}"
                if "token" in extra:
                    headers["Authorization"] = f"Bearer {extra['token']}"
            except json.JSONDecodeError:
                pass
        return headers

    def _parse_sse_response(self, text: str) -> dict:
        """Parse SSE-formatted response to extract JSON-RPC data."""
        for line in text.splitlines():
            line = line.strip()
            if line.startswith("data:"):
                data_str = line[5:].strip()
                try:
                    return json.loads(data_str)
                except json.JSONDecodeError:
                    continue
        return {}

    async def test_connection(self, server_id: str) -> str:
        """Test connection to an MCP server."""
        server_cfg = server_registry.get_server(server_id)
        if not server_cfg:
            raise ValueError(f"Server {server_id} not found")

        url = server_cfg.url.rstrip("/")
        if not url:
            raise ValueError("Server URL is empty")

        auth_headers = self._build_auth_headers(server_cfg)

        try:
            import httpx
            async with httpx.AsyncClient(timeout=10.0) as client:
                # Try JSON-RPC tools/list with auth
                resp = await client.post(
                    url,
                    json={"jsonrpc": "2.0", "method": "tools/list", "params": {}, "id": "1"},
                    headers={**auth_headers, "Content-Type": "application/json", "Accept": "application/json, text/event-stream"},
                    timeout=10.0,
                )
                if resp.status_code == 200:
                    server_cfg.status = "CONNECTED"
                    return "连接成功"
                elif resp.status_code == 401:
                    server_cfg.status = "ERROR"
                    return "连接失败: 401 未授权 - 请在 configJson 中配置正确的 Authorization/apiKey"
                elif resp.status_code == 404:
                    server_cfg.status = "ERROR"
                    return f"连接失败: 404 路径不存在 - 请检查 URL 是否正确（应为 MCP 端点）"
                else:
                    server_cfg.status = "ERROR"
                    return f"连接失败: HTTP {resp.status_code} - {resp.text[:200]}"
        except Exception as e:
            server_cfg.status = "ERROR"
            return f"连接失败: {str(e)}"

    def get_server_tools(self, server_id: str) -> list[MCPToolInfo]:
        """Get tools discovered from a server."""
        return self._servers.get(server_id, [])

    def get_enabled_tools(self) -> list[dict]:
        """Get all enabled tools for agent use."""
        tools = []
        schemas = getattr(self, '_tool_schemas', {})
        for tid, wrapper in self._tools.items():
            server_id = wrapper.tool_id  # Actually the tool's server association
            # Find the server ID from stored data
            sid = None
            for sid_candidate, sts in self._servers.items():
                for t in sts:
                    if t.id == tid:
                        sid = sid_candidate
                        break
            tools.append({
                "id": tid,
                "name": wrapper.name,
                "description": wrapper.description,
                "serverId": sid or "",
                "inputSchema": schemas.get(tid, wrapper.input_schema or {}),
            })
        # Also add native tools
        for nt in NATIVE_TOOLS:
            tools.append({
                "id": f"native_{nt['name']}",
                "name": nt["name"],
                "description": nt["description"],
                "serverId": "__native__",
                "inputSchema": nt.get("parameters", {}),
            })
        return tools

    async def call_tool(self, tool_id: str, args: dict) -> str:
        """Call a tool by ID."""
        # Check native tools first
        if tool_id.startswith("native_"):
            native_name = tool_id[7:]
            try:
                return await native_tool_registry.execute(native_name, args)
            except ValueError:
                return f"未知原生工具: {native_name}"

        wrapper = self._tools.get(tool_id)
        if not wrapper:
            return f"工具 {tool_id} 不可用"
        return await wrapper.call(args)

    def toggle_tool(self, tool_id: str, enabled: bool):
        """Enable or disable a tool."""
        if enabled:
            pass  # Already in registry if discovered
        else:
            self._tools.pop(tool_id, None)


mcp_client_manager = MCPClientManager()
