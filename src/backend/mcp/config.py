"""Pydantic models for MCP configuration"""
from pydantic import BaseModel
from typing import Optional
from enum import Enum


class MCPTransport(str, Enum):
    STDIO = "STDIO"
    SSE = "SSE"
    STREAMABLE_HTTP = "STREAMABLE_HTTP"


class MCPServerConfig(BaseModel):
    id: str
    name: str
    description: str = ""
    url: str = ""
    transportType: MCPTransport = MCPTransport.SSE
    command: Optional[str] = None
    configJson: Optional[str] = None
    enabled: bool = True
    status: str = "DISCONNECTED"


class MCPToolInfo(BaseModel):
    id: str
    name: str
    description: str = ""
    inputSchema: dict = {}
    enabled: bool = True
    serverId: str = ""
