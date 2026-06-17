"""Custom Tools management API routes"""
import json
import uuid
import logging
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/tools")

# In-memory storage
_tools: dict[str, dict] = {}

# Seed a built-in tool
_tools["tool_calculate"] = {
    "id": "tool_calculate",
    "name": "calculate",
    "description": "执行数学计算",
    "toolType": "native",
    "parameters": json.dumps({
        "type": "object",
        "properties": {
            "expression": {"type": "string", "description": "数学表达式"}
        },
        "required": ["expression"]
    }),
    "enabled": True,
    "createdAt": "2026-06-01T00:00:00Z",
    "updatedAt": "2026-06-01T00:00:00Z",
}
_tools["tool_time"] = {
    "id": "tool_time",
    "name": "get_current_time",
    "description": "获取当前时间",
    "toolType": "native",
    "parameters": json.dumps({
        "type": "object",
        "properties": {
            "timezone": {"type": "string", "description": "时区"}
        }
    }),
    "enabled": True,
    "createdAt": "2026-06-01T00:00:00Z",
    "updatedAt": "2026-06-01T00:00:00Z",
}

class CreateToolRequest(BaseModel):
    name: str
    description: str = ""
    toolType: str = "native"
    parameters: str = "{}"
    enabled: bool = True


class UpdateToolRequest(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    parameters: Optional[str] = None
    enabled: Optional[bool] = None


@router.get("")
async def list_tools(page: int = 1, pageSize: int = 20,
                      keyword: Optional[str] = None,
                      toolType: Optional[str] = None):
    result = list(_tools.values())
    if keyword:
        result = [t for t in result if keyword.lower() in t["name"].lower()]
    if toolType:
        result = [t for t in result if t.get("toolType") == toolType]
    total = len(result)
    start = (page - 1) * pageSize
    end = start + pageSize
    return {
        "code": 0,
        "message": "ok",
        "data": {
            "list": result[start:end],
            "total": total,
            "page": page,
            "pageSize": pageSize,
        }
    }


@router.get("/enabled")
async def get_enabled_tools():
    result = [t for t in _tools.values() if t.get("enabled")]
    return {"code": 0, "message": "ok", "data": result}


@router.get("/{tool_id}")
async def get_tool(tool_id: str):
    tool = _tools.get(tool_id)
    if not tool:
        raise HTTPException(404, "工具不存在")
    return {"code": 0, "message": "ok", "data": tool}


@router.post("")
async def create_tool(req: CreateToolRequest):
    tid = str(uuid.uuid4())
    now = datetime.utcnow().isoformat()
    tool = {
        "id": tid,
        "name": req.name,
        "description": req.description,
        "toolType": req.toolType,
        "parameters": req.parameters,
        "enabled": req.enabled,
        "createdAt": now,
        "updatedAt": now,
    }
    _tools[tid] = tool
    return {"code": 0, "message": "ok", "data": tool}


@router.put("/{tool_id}")
async def update_tool(tool_id: str, req: UpdateToolRequest):
    tool = _tools.get(tool_id)
    if not tool:
        raise HTTPException(404, "工具不存在")
    for field in ["name", "description", "parameters", "enabled"]:
        val = getattr(req, field, None)
        if val is not None:
            tool[field] = val
    tool["updatedAt"] = datetime.utcnow().isoformat()
    return {"code": 0, "message": "ok", "data": tool}


@router.delete("/{tool_id}")
async def delete_tool(tool_id: str):
    _tools.pop(tool_id, None)
    return {"code": 0, "message": "deleted", "data": None}
