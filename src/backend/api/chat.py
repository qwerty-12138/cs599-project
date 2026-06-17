"""Chat API routes — sessions and streaming messages"""
import json
import uuid
import time
import asyncio
import logging
import os
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from ..agent.graph import get_graph
from ..agent.state import AgentState
from ..agent.cancel import cancel_manager
from ..agent.nodes.response import stream_response
from ..agent.llm import get_llm_client, get_model_name
from ..memory.manager import memory_manager
from ..mcp.client import mcp_client_manager
from .skills import get_skill_by_id

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/chat")

# Persistent file storage
_DATA_DIR = os.environ.get("DATA_DIR", "/app/data")
_SESSIONS_FILE = os.path.join(_DATA_DIR, "sessions.json")
_MESSAGES_FILE = os.path.join(_DATA_DIR, "messages.json")


def _load_json(path: str, default):
    if not os.path.exists(path):
        return default
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        logger.warning(f"Failed to load {path}: {e}")
        return default


def _save_json(path: str, data) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    try:
        tmp = path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        os.replace(tmp, path)
    except Exception as e:
        logger.error(f"Failed to save {path}: {e}")


# In-memory cache, backed by JSON files
_sessions: dict[str, dict] = _load_json(_SESSIONS_FILE, {})
_messages: dict[str, list[dict]] = _load_json(_MESSAGES_FILE, {})


def _persist_sessions() -> None:
    _save_json(_SESSIONS_FILE, _sessions)


def _persist_messages() -> None:
    _save_json(_MESSAGES_FILE, _messages)


class CreateSessionRequest(BaseModel):
    title: str


class SendMessageRequest(BaseModel):
    content: str
    skillIds: Optional[list[str]] = None
    toolIds: Optional[list[str]] = None


@router.post("/sessions")
async def create_session(req: CreateSessionRequest):
    sid = str(uuid.uuid4())
    now = datetime.utcnow().isoformat()
    _sessions[sid] = {
        "id": sid,
        "title": req.title,
        "lastMessage": "",
        "messageCount": 0,
        "createdAt": now,
        "updatedAt": now,
    }
    _messages[sid] = []
    _persist_sessions()
    _persist_messages()
    return {"code": 0, "message": "ok", "data": _sessions[sid]}


@router.get("/sessions")
async def list_sessions(page: int = 1, pageSize: int = 10):
    sessions = sorted(
        _sessions.values(),
        key=lambda s: s.get("updatedAt", ""),
        reverse=True,
    )
    total = len(sessions)
    start = (page - 1) * pageSize
    end = start + pageSize
    return {
        "code": 0,
        "message": "ok",
        "data": {
            "list": sessions[start:end],
            "total": total,
            "page": page,
            "pageSize": pageSize,
        }
    }


@router.get("/sessions/{session_id}")
async def get_session(session_id: str):
    session = _sessions.get(session_id)
    if not session:
        raise HTTPException(404, "会话不存在")
    return {"code": 0, "message": "ok", "data": session}


@router.get("/sessions/{session_id}/messages")
async def get_session_messages(session_id: str):
    msgs = _messages.get(session_id, [])
    return {"code": 0, "message": "ok", "data": msgs}


@router.delete("/sessions/{session_id}")
async def delete_session(session_id: str):
    _sessions.pop(session_id, None)
    _messages.pop(session_id, None)
    _persist_sessions()
    _persist_messages()
    cancel_manager.reset(session_id)
    await memory_manager.clear_session("default", session_id)
    return {"code": 0, "message": "deleted", "data": None}


@router.post("/sessions/{session_id}/messages")
async def send_message(session_id: str, req: SendMessageRequest):
    """Non-streaming send message (fallback)."""
    if session_id not in _sessions:
        raise HTTPException(404, "会话不存在")

    # Save user message
    user_msg = {
        "id": str(uuid.uuid4()),
        "sessionId": session_id,
        "role": "user",
        "content": req.content,
        "sources": [],
        "createdAt": datetime.utcnow().isoformat(),
    }
    _messages[session_id].append(user_msg)
    _sessions[session_id]["lastMessage"] = req.content[:50]
    _sessions[session_id]["messageCount"] += 1
    _sessions[session_id]["updatedAt"] = datetime.utcnow().isoformat()
    _persist_sessions()
    _persist_messages()

    # Load short-term memory (recent conversation history)
    history = await memory_manager.short_term.get_recent("default", session_id, n=10)
    history_messages = [
        ("human" if m.get("role") == "user" else "ai", m.get("content", ""))
        for m in history
    ]
    history_messages.append(("human", req.content))

    # Build skill context from selected skill IDs
    skill_context = ""
    if req.skillIds:
        skill_parts = []
        for sid in req.skillIds:
            s = get_skill_by_id(sid)
            if s and s.get("enabled"):
                skill_parts.append(f"### {s['name']}\n{s.get('content', '')}")
        if skill_parts:
            skill_context = "\n\n".join(skill_parts)

    # Process through agent graph
    graph = get_graph()
    config = {"configurable": {"thread_id": session_id}}

    # Build initial state with conversation history
    initial_state = {
        "messages": history_messages,
        "user_id": "default",
        "session_id": session_id,
        "intent": "",
        "needs_rag": False,
        "rag_context": [],
        "rag_sources": [],
        "enabled_tools": req.toolIds or [],
        "skill_context": skill_context,
        "tool_calls": [],
        "tool_results": [],
        "tool_call_count": 0,
        "short_term_memories": [],
        "long_term_memories": [],
        "cancelled": False,
        "error": None,
        "final_response": "",
        "total_tokens": 0,
        "start_time": time.time(),
    }

    try:
        result = await graph.ainvoke(initial_state, config)
        response_text = result.get("final_response", "")

        asst_msg = {
            "id": str(uuid.uuid4()),
            "sessionId": session_id,
            "role": "assistant",
            "content": response_text,
            "sources": result.get("rag_sources", []),
            "createdAt": datetime.utcnow().isoformat(),
        }
        _messages[session_id].append(asst_msg)
        _sessions[session_id]["updatedAt"] = datetime.utcnow().isoformat()
        _persist_sessions()
        _persist_messages()

        # Save to short-term memory
        await memory_manager.add_message("default", session_id, {
            "role": "user", "content": req.content
        })
        await memory_manager.add_message("default", session_id, {
            "role": "assistant", "content": response_text
        })

        return {"code": 0, "message": "ok", "data": asst_msg}
    except Exception as e:
        logger.error(f"Graph execution failed: {e}")
        raise HTTPException(500, f"处理消息失败: {str(e)}")


@router.post("/sessions/{session_id}/messages/stream")
async def stream_chat(session_id: str, req: SendMessageRequest):
    """Streaming chat endpoint using SSE."""
    if session_id not in _sessions:
        raise HTTPException(404, "会话不存在")

    # Save user message
    user_msg_id = str(uuid.uuid4())
    user_msg = {
        "id": user_msg_id,
        "sessionId": session_id,
        "role": "user",
        "content": req.content,
        "sources": [],
        "createdAt": datetime.utcnow().isoformat(),
    }
    _messages[session_id].append(user_msg)
    _sessions[session_id]["lastMessage"] = req.content[:50]
    _sessions[session_id]["messageCount"] += 1
    _sessions[session_id]["updatedAt"] = datetime.utcnow().isoformat()
    _persist_sessions()
    _persist_messages()

    cancel_manager.reset(session_id)

    # Load short-term memory (recent conversation history)
    history = await memory_manager.short_term.get_recent("default", session_id, n=10)
    history_messages = [
        ("human" if m.get("role") == "user" else "ai", m.get("content", ""))
        for m in history
    ]
    history_messages.append(("human", req.content))

    # Build skill context from selected skill IDs
    skill_context = ""
    if req.skillIds:
        skill_parts = []
        for sid in req.skillIds:
            s = get_skill_by_id(sid)
            if s and s.get("enabled"):
                skill_parts.append(f"### {s['name']}\n{s.get('content', '')}")
        if skill_parts:
            skill_context = "\n\n".join(skill_parts)

    # Build state for streaming with conversation history
    state = {
        "messages": history_messages,
        "user_id": "default",
        "session_id": session_id,
        "intent": "",
        "needs_rag": False,
        "rag_context": [],
        "rag_sources": [],
        "enabled_tools": req.toolIds or [],
        "skill_context": skill_context,
        "tool_calls": [],
        "tool_results": [],
        "tool_call_count": 0,
        "short_term_memories": [],
        "long_term_memories": [],
        "cancelled": False,
        "error": None,
        "final_response": "",
        "total_tokens": 0,
        "start_time": time.time(),
    }

    async def event_stream():
        asst_msg_id = str(uuid.uuid4())

        # Send user message event
        yield f"event: userMessage\ndata: {json.dumps({'id': user_msg_id, 'content': req.content})}\n\n"

        # First do intent classification
        client = get_llm_client()
        model = get_model_name()

        intent_prompt = (
            "你是意图分类器。分析用户消息，返回JSON格式的意图分类结果。\n"
            "意图类别：\n"
            "- knowledge: 询问知识库相关内容（公司政策、文档、专业知识等需要检索的问题）\n"
            "- chitchat: 日常聊天、问候、闲聊、简单常识\n"
            "- tool_use: 需要调用外部工具（搜索、天气查询、时间查询、计算、文件操作等）\n\n"
            "工具使用示例：\n"
            "- 天气查询：'北京天气'、'武汉今天天气预报'、'明天天气'\n"
            "- 时间查询：'现在几点'、'当前时间'\n"
            "- 计算：'100+200'、'5*8'\n\n"
            '仅返回JSON: {"intent": "...", "reason": "..."}'
        )
        try:
            resp = await client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": intent_prompt},
                    {"role": "user", "content": req.content},
                ],
                temperature=0.1,
                max_tokens=100,
            )
            intent_text = resp.choices[0].message.content.strip()
            if "```" in intent_text:
                intent_text = intent_text.split("```")[1].split("```")[0]
                if intent_text.startswith("json"):
                    intent_text = intent_text[4:]
            intent_data = json.loads(intent_text)
            intent = intent_data.get("intent", "chitchat")
        except Exception as e:
            logger.warning(f"Intent classification failed: {e}")
            intent = "chitchat"

        state["intent"] = intent
        state["needs_rag"] = intent == "knowledge"
        yield f"event: intent\ndata: {json.dumps({'intent': intent, 'needs_rag': state['needs_rag']})}\n\n"

        # Stream through
        try:
            full_content = ""
            async for event_data in stream_response(state):
                event_type = event_data["event"]
                data = event_data["data"]

                if event_type == "token":
                    full_content += data.get("content", "")
                elif event_type == "cancelled":
                    full_content += "\n\n[已取消]"

                yield f"event: {event_type}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"

            # Save assistant message
            asst_msg = {
                "id": asst_msg_id,
                "sessionId": session_id,
                "role": "assistant",
                "content": full_content,
                "sources": state.get("rag_sources", []),
                "createdAt": datetime.utcnow().isoformat(),
            }
            _messages[session_id].append(asst_msg)
            _sessions[session_id]["updatedAt"] = datetime.utcnow().isoformat()
            _persist_sessions()
            _persist_messages()

            # Save to short-term memory
            await memory_manager.add_message("default", session_id, {
                "role": "user", "content": req.content
            })
            await memory_manager.add_message("default", session_id, {
                "role": "assistant", "content": full_content
            })

            yield f"event: assistantMessage\ndata: {json.dumps(asst_msg, ensure_ascii=False)}\n\n"

        except Exception as e:
            logger.error(f"Stream error: {e}")
            yield f"event: error\ndata: {json.dumps({'code': 500, 'message': str(e)})}\n\n"

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
