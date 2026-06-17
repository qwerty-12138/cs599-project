"""MCP server and tool management API routes"""
import uuid
import logging
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from ..mcp.server_registry import server_registry
from ..mcp.client import mcp_client_manager
from ..mcp.config import MCPServerConfig, MCPTransport

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/mcp")


class CreateServerRequest(BaseModel):
    name: str
    description: str = ""
    url: str = ""
    transportType: str = "SSE"
    command: Optional[str] = None
    configJson: Optional[str] = None
    enabled: bool = True


class UpdateServerRequest(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    url: Optional[str] = None
    transportType: Optional[str] = None
    command: Optional[str] = None
    configJson: Optional[str] = None
    enabled: Optional[bool] = None


class ToggleToolRequest(BaseModel):
    enabled: bool


def _server_to_dict(server: MCPServerConfig) -> dict:
    return {
        "id": server.id,
        "name": server.name,
        "description": server.description,
        "url": server.url,
        "transportType": server.transportType.value if isinstance(server.transportType, MCPTransport) else server.transportType,
        "command": server.command or "",
        "configJson": server.configJson or "",
        "enabled": server.enabled,
        "status": server.status,
        "createdAt": "",
        "updatedAt": "",
    }


@router.get("/servers")
async def list_servers():
    servers = server_registry.get_servers()
    return {"code": 0, "message": "ok", "data": [_server_to_dict(s) for s in servers]}


@router.get("/servers/enabled")
async def list_enabled_servers():
    servers = server_registry.get_enabled_servers()
    return {"code": 0, "message": "ok", "data": [_server_to_dict(s) for s in servers]}


@router.get("/servers/{server_id}")
async def get_server(server_id: str):
    server = server_registry.get_server(server_id)
    if not server:
        raise HTTPException(404, "服务器不存在")
    return {"code": 0, "message": "ok", "data": _server_to_dict(server)}


@router.post("/servers")
async def create_server(req: CreateServerRequest):
    sid = str(uuid.uuid4())
    now = datetime.utcnow().isoformat()
    try:
        transport = MCPTransport(req.transportType)
    except ValueError:
        transport = MCPTransport.SSE

    config = MCPServerConfig(
        id=sid,
        name=req.name,
        description=req.description,
        url=req.url,
        transportType=transport,
        command=req.command or "",
        configJson=req.configJson or "{}",
        enabled=req.enabled,
        status="DISCONNECTED",
    )
    server_registry.add_server(config)
    return {"code": 0, "message": "ok", "data": _server_to_dict(config)}


@router.put("/servers/{server_id}")
async def update_server(server_id: str, req: UpdateServerRequest):
    server = server_registry.get_server(server_id)
    if not server:
        raise HTTPException(404, "服务器不存在")

    updates = {}
    if req.name is not None:
        updates["name"] = req.name
    if req.description is not None:
        updates["description"] = req.description
    if req.url is not None:
        updates["url"] = req.url
    if req.transportType is not None:
        try:
            updates["transportType"] = MCPTransport(req.transportType)
        except ValueError:
            pass
    if req.command is not None:
        updates["command"] = req.command
    if req.configJson is not None:
        updates["configJson"] = req.configJson
    
    prev_enabled = server.enabled
    if req.enabled is not None:
        updates["enabled"] = req.enabled

    server_registry.update_server(server_id, updates)
    updated = server_registry.get_server(server_id)
    
    if updated and req.enabled is not None:
        if req.enabled and not prev_enabled:
            mcp_client_manager.enable_server_tools(server_id)
        elif not req.enabled and prev_enabled:
            mcp_client_manager.disable_server_tools(server_id)

    if updated:
        return {"code": 0, "message": "ok", "data": _server_to_dict(updated)}
    raise HTTPException(500, "更新失败")


@router.delete("/servers/{server_id}")
async def delete_server(server_id: str):
    mcp_client_manager.disable_server_tools(server_id)
    server_registry.remove_server(server_id)
    return {"code": 0, "message": "deleted", "data": None}


@router.post("/servers/{server_id}/test")
async def test_connection(server_id: str):
    try:
        result = await mcp_client_manager.test_connection(server_id)
        return {"code": 0, "message": "ok", "data": result}
    except ValueError as e:
        return {"code": 500, "message": str(e), "data": None}
    except Exception as e:
        return {"code": 500, "message": f"连接失败: {str(e)}", "data": None}


@router.post("/servers/{server_id}/discover")
async def discover_tools(server_id: str):
    try:
        tools = await mcp_client_manager.discover_tools(server_id)
        result = [
            {
                "id": t.id,
                "name": t.name,
                "description": t.description,
                "inputSchema": t.inputSchema,
                "enabled": t.enabled,
                "serverId": t.serverId,
                "discoveredAt": datetime.utcnow().isoformat(),
            }
            for t in tools
        ]
        return {"code": 0, "message": "ok", "data": result}
    except ValueError as e:
        logger.warning(f"Discover failed: {e}")
        return {"code": 500, "message": str(e), "data": None}


@router.get("/servers/{server_id}/tools")
async def get_server_tools(server_id: str):
    tools = mcp_client_manager.get_server_tools(server_id)
    result = [
        {
            "id": t.id,
            "server": _server_to_dict(server_registry.get_server(t.serverId)) if server_registry.get_server(t.serverId) else {},
            "name": t.name,
            "description": t.description,
            "inputSchema": t.inputSchema,
            "enabled": t.enabled,
            "discoveredAt": "",
        }
        for t in tools
    ]
    return {"code": 0, "message": "ok", "data": result}


@router.get("/tools/enabled")
async def get_enabled_tools():
    tools = mcp_client_manager.get_enabled_tools()
    result = [
        {
            "id": t["id"],
            "server": {},
            "name": t["name"],
            "description": t["description"],
            "inputSchema": {},
            "enabled": True,
            "discoveredAt": "",
        }
        for t in tools
    ]
    return {"code": 0, "message": "ok", "data": result}


@router.put("/tools/{tool_id}/toggle")
async def toggle_tool(tool_id: str, req: ToggleToolRequest):
    mcp_client_manager.toggle_tool(tool_id, req.enabled)
    return {
        "code": 0,
        "message": "ok",
        "data": {"id": tool_id, "enabled": req.enabled}
    }
