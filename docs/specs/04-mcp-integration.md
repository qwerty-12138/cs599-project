# 04 — MCP 集成规格

## 4.1 概述

MCP (Model Context Protocol) 集成允许 Agent 动态连接外部工具服务器。用户可在前端界面配置 MCP 服务器地址，并为每次对话选择性启用工具。

## 4.2 MCP 架构

```
┌──────────────────────────────────────────────────┐
│                    前端 MCP 面板                    │
│  ┌────────────┐ ┌────────────┐ ┌──────────────┐  │
│  │ 服务器列表  │ │ 工具选择器  │ │ 连接状态指示   │  │
│  └────────────┘ └────────────┘ └──────────────┘  │
└───────────────────────┬──────────────────────────┘
                        │ POST /mcp/servers
                        │ POST /mcp/tools/toggle
┌───────────────────────▼──────────────────────────┐
│                 MCP 管理层 (FastAPI)               │
│  ┌────────────┐ ┌────────────┐ ┌──────────────┐  │
│  │ 服务器注册  │ │ 工具发现    │ │ 连接管理      │  │
│  └────────────┘ └────────────┘ └──────────────┘  │
└───────────────────────┬──────────────────────────┘
                        │
┌───────────────────────▼──────────────────────────┐
│               MCP Client Manager                   │
│                                                    │
│  ┌────────────────────────────────────────────┐   │
│  │ Server A (filesystem)                       │   │
│  │  ├─ read_file                               │   │
│  │  ├─ write_file                              │   │
│  │  └─ list_directory                          │   │
│  ├────────────────────────────────────────────┤   │
│  │ Server B (web_search)                       │   │
│  │  └─ search_web                              │   │
│  └────────────────────────────────────────────┘   │
│                                                    │
│  Tool Registry → LangChain Tool Wrapper → Agent    │
└────────────────────────────────────────────────────┘
```

## 4.3 数据模型

```python
from pydantic import BaseModel
from typing import Optional
from enum import Enum

class MCPTransport(str, Enum):
    STDIO = "stdio"
    SSE = "sse"
    HTTP = "http"

class MCPServerConfig(BaseModel):
    id: str
    name: str                    # 显示名称
    transport: MCPTransport      # 传输方式
    command: Optional[str] = None   # STDIO 命令
    args: Optional[list[str]] = None
    url: Optional[str] = None       # SSE/HTTP 地址
    env: Optional[dict[str, str]] = None
    enabled: bool = True
    tools: list["MCPToolInfo"] = []

class MCPToolInfo(BaseModel):
    name: str                    # 工具名称
    description: str             # 工具描述
    parameters: dict             # JSON Schema 参数定义
    enabled: bool = True         # 用户是否启用
    server_id: str               # 所属服务器 ID

class MCPServerStatus(BaseModel):
    server_id: str
    connected: bool
    tool_count: int
    error: Optional[str] = None
```

## 4.4 MCP 客户端管理器

```python
class MCPClientManager:
    """管理多个 MCP 服务器连接和工具持久化"""

    def __init__(self):
        self._tools: dict[str, MCPToolWrapper] = {}     # tool_id → ToolWrapper
        self._servers: dict[str, list[MCPToolInfo]] = {} # server_id → [ToolInfo]
        self._load_tools()  # 启动时加载持久化工具

    async def discover_tools(self, server_id: str) -> list[MCPToolInfo]:
        """发现并注册工具，自动持久化"""
        server_cfg = server_registry.get_server(server_id)
        url = server_cfg.url.rstrip("/")
        auth_headers = self._build_auth_headers(server_cfg)

        # 通过 JSON-RPC 调用 tools/list
        payload = {"jsonrpc": "2.0", "method": "tools/list", "params": {}, "id": str(uuid.uuid4())}
        # ... HTTP 请求处理 ...

        tools = []
        for t in tools_data:
            tool_info = MCPToolInfo(
                id=str(uuid.uuid4()),
                name=t.get("name", "unknown"),
                description=t.get("description", ""),
                inputSchema=t.get("inputSchema", {}),
                enabled=True,
                serverId=server_id,
            )
            tools.append(tool_info)

        self._servers[server_id] = tools
        for tool in tools:
            if tool.enabled:
                self._tools[tool.id] = MCPToolWrapper(tool, url, auth_headers)

        self._save_tools()  # 持久化工具列表
        return tools

    def _load_tools(self):
        """启动时从 JSON 文件加载工具"""
        if os.path.exists(TOOLS_FILE):
            data = json.load(open(TOOLS_FILE))
            for server_id, tools_data in data.items():
                server_cfg = server_registry.get_server(server_id)
                if server_cfg and server_cfg.enabled:
                    tools = [MCPToolInfo(**t) for t in tools_data]
                    self._servers[server_id] = tools
                    url = server_cfg.url.rstrip("/")
                    auth_headers = self._build_auth_headers(server_cfg)
                    for tool in tools:
                        if tool.enabled:
                            self._tools[tool.id] = MCPToolWrapper(tool, url, auth_headers)

    def _save_tools(self):
        """保存工具到 JSON 文件"""
        data = {sid: [t.dict() for t in tools] for sid, tools in self._servers.items()}
        json.dump(data, open(TOOLS_FILE, "w"))

    def enable_server_tools(self, server_id: str):
        """启用服务器时自动加载工具"""
        if server_id not in self._servers:
            return
        server_cfg = server_registry.get_server(server_id)
        url = server_cfg.url.rstrip("/")
        auth_headers = self._build_auth_headers(server_cfg)
        for tool in self._servers[server_id]:
            if tool.enabled:
                self._tools[tool.id] = MCPToolWrapper(tool, url, auth_headers)

    def disable_server_tools(self, server_id: str):
        """禁用服务器时自动移除工具"""
        if server_id not in self._servers:
            return
        for tool in self._servers[server_id]:
            self._tools.pop(tool.id, None)
```

## 4.5 工具包装器

```python
from langchain_core.tools import BaseTool
from pydantic import Field
import requests
import uuid
import json

class MCPToolWrapper(BaseTool):
    """MCP 工具 → LangChain Tool 适配器（HTTP JSON-RPC）"""

    name: str
    description: str
    args_schema: type[BaseModel] = Field(default_factory=dict)
    _tool_info: MCPToolInfo = None
    _url: str = ""
    _auth_headers: dict = {}

    def __init__(self, tool_info: MCPToolInfo, url: str, auth_headers: dict):
        super().__init__(
            name=tool_info.name,
            description=tool_info.description
        )
        self._tool_info = tool_info
        self._url = url
        self._auth_headers = auth_headers

    async def _arun(self, **kwargs) -> str:
        payload = {
            "jsonrpc": "2.0",
            "method": "tools/call",
            "params": {
                "name": self.name,
                "arguments": kwargs
            },
            "id": str(uuid.uuid4())
        }
        try:
            resp = requests.post(
                self._url + "/jsonrpc",
                json=payload,
                headers=self._auth_headers,
                timeout=60
            )
            resp.raise_for_status()
            result = resp.json()
            if "result" in result:
                return str(result["result"].get("content", ""))
            elif "error" in result:
                return f"工具调用失败: {result['error'].get('message', '未知错误')}"
            else:
                return str(result)
        except requests.exceptions.RequestException as e:
            return f"网络请求失败: {str(e)}"
        except Exception as e:
            return f"工具调用异常: {str(e)}"

    def _run(self, **kwargs) -> str:
        import asyncio
        return asyncio.run(self._arun(**kwargs))
```

## 4.6 原生工具

```python
# 内置的 Function Calling 工具，不依赖 MCP

NATIVE_TOOLS = [
    {
        "name": "calculate",
        "description": "执行数学计算",
        "parameters": {
            "type": "object",
            "properties": {
                "expression": {"type": "string", "description": "数学表达式"}
            },
            "required": ["expression"]
        }
    },
    {
        "name": "get_current_time",
        "description": "获取当前时间",
        "parameters": {
            "type": "object",
            "properties": {
                "timezone": {"type": "string", "description": "时区 (如 Asia/Shanghai)"}
            }
        }
    }
]
```

## 4.7 前端 MCP 配置界面

### 组件结构

```
MCPSettings.tsx (主面板)
├── ServerList (服务器列表)
│   ├── ServerCard (单个服务器)
│   │   ├── ServerHeader (名称 + 状态灯)
│   │   ├── ToolList (工具列表)
│   │   └── AddServerButton
│   └── AddServerModal (添加服务器弹窗)
│       ├── TransportSelector (STDIO/SSE/HTTP)
│       ├── CommandInput / URLInput
│       └── TestConnectionButton
├── ToolToggle (工具开关)
└── GlobalToggle (全部启用/禁用)
```

### 用户交互流程

```
1. 打开 MCP 设置面板
2. 点击"添加服务器"
3. 填写配置：
   - 名称: "File System"
   - 传输方式: STDIO
   - 命令: "npx -y @modelcontextprotocol/server-filesystem /path"
4. 点击"测试连接"
5. 连接成功后显示工具列表
6. 可单独开关每个工具
7. 在对话时，Agent 只会使用启用的工具
```

## 4.8 API 接口

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/mcp/servers` | 获取所有已配置的 MCP 服务器 |
| POST | `/mcp/servers` | 添加新 MCP 服务器 |
| DELETE | `/mcp/servers/{id}` | 移除 MCP 服务器 |
| POST | `/mcp/servers/{id}/test` | 测试连接 |
| GET | `/mcp/servers/{id}/tools` | 获取服务器工具列表 |
| POST | `/mcp/tools/{name}/toggle` | 启用/禁用工具 |
| POST | `/mcp/servers/{id}/toggle` | 启用/禁用整个服务器 |

## 4.9 实现文件清单

| 文件 | 职责 |
|------|------|
| `src/mcp/__init__.py` | 模块导出 |
| `src/mcp/client.py` | MCPClientManager |
| `src/mcp/server_registry.py` | 服务器配置持久化 (JSON/YAML) |
| `src/mcp/tool_wrapper.py` | MCPToolWrapper |
| `src/mcp/config.py` | Pydantic 配置模型 |
| `src/mcp/native_tools.py` | 原生 Function Calling 工具 |
