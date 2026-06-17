"""Skills management API routes"""
import json
import os
import uuid
import logging
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, HTTPException, UploadFile, File
from pydantic import BaseModel

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/skills")

# Persistent file storage
_DATA_DIR = os.environ.get("DATA_DIR", "/app/data")
_SKILLS_FILE = os.path.join(_DATA_DIR, "skills.json")


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


# In-memory cache, backed by JSON file
_skills: dict[str, dict] = _load_json(_SKILLS_FILE, {})


def _persist_skills() -> None:
    _save_json(_SKILLS_FILE, _skills)


def get_skill_by_id(skill_id: str) -> Optional[dict]:
    """Public accessor used by the chat pipeline to inject skill context."""
    return _skills.get(skill_id)


def get_enabled_skills_dict() -> list[dict]:
    """Return all enabled skills as a list (public accessor)."""
    return [s for s in _skills.values() if s.get("enabled")]


class CreateSkillRequest(BaseModel):
    name: str
    description: str = ""
    content: str = ""
    category: str = "custom"
    icon: str = "🧠"
    enabled: bool = True


class UpdateSkillRequest(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    content: Optional[str] = None
    category: Optional[str] = None
    icon: Optional[str] = None
    enabled: Optional[bool] = None


# Seed default skills (only if no persisted file)
_seed_skills = [
    {
        "id": "skill_code_review",
        "name": "代码审查",
        "description": "审查代码质量、安全性和最佳实践",
        "content": "你是一位资深代码审查专家。请仔细审查以下代码，重点关注：\n1. 潜在的错误和逻辑问题\n2. 安全漏洞\n3. 性能问题\n4. 代码风格和可维护性\n5. 最佳实践建议",
        "category": "coding",
        "icon": "🔍",
        "enabled": True,
        "createdAt": "2026-06-01T00:00:00Z",
        "updatedAt": "2026-06-01T00:00:00Z",
    },
    {
        "id": "skill_writing",
        "name": "写作助手",
        "description": "辅助进行各类写作任务",
        "content": "你是一位专业的写作助手。请根据用户的需求：\n1. 提供清晰的写作结构\n2. 使用恰当的语言风格\n3. 注意逻辑连贯性\n4. 如有需要，提供多个版本供选择",
        "category": "writing",
        "icon": "✍️",
        "enabled": True,
        "createdAt": "2026-06-01T00:00:00Z",
        "updatedAt": "2026-06-01T00:00:00Z",
    },
    {
        "id": "skill_translator",
        "name": "翻译专家",
        "description": "专业的多语言翻译服务",
        "content": "你是一位专业翻译。请：\n1. 准确传达原文含义\n2. 符合目标语言表达习惯\n3. 保留原文风格和语气\n4. 对专业术语提供注释",
        "category": "writing",
        "icon": "🌐",
        "enabled": True,
        "createdAt": "2026-06-01T00:00:00Z",
        "updatedAt": "2026-06-01T00:00:00Z",
    },
]

if not _skills:
    for s in _seed_skills:
        _skills[s["id"]] = s
    _persist_skills()


@router.get("")
async def list_skills(page: int = 1, pageSize: int = 20,
                       keyword: Optional[str] = None,
                       category: Optional[str] = None):
    result = list(_skills.values())
    if keyword:
        result = [s for s in result if keyword.lower() in s["name"].lower()]
    if category:
        result = [s for s in result if s.get("category") == category]
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
async def get_enabled_skills():
    result = [s for s in _skills.values() if s.get("enabled")]
    return {"code": 0, "message": "ok", "data": result}


@router.get("/{skill_id}")
async def get_skill(skill_id: str):
    skill = _skills.get(skill_id)
    if not skill:
        raise HTTPException(404, "Skill不存在")
    return {"code": 0, "message": "ok", "data": skill}


@router.post("")
async def create_skill(req: CreateSkillRequest):
    sid = str(uuid.uuid4())
    now = datetime.utcnow().isoformat()
    skill = {
        "id": sid,
        "name": req.name,
        "description": req.description,
        "content": req.content,
        "category": req.category,
        "icon": req.icon,
        "enabled": req.enabled,
        "createdAt": now,
        "updatedAt": now,
    }
    _skills[sid] = skill
    _persist_skills()
    return {"code": 0, "message": "ok", "data": skill}


@router.put("/{skill_id}")
async def update_skill(skill_id: str, req: UpdateSkillRequest):
    skill = _skills.get(skill_id)
    if not skill:
        raise HTTPException(404, "Skill不存在")
    for field in ["name", "description", "content", "category", "icon", "enabled"]:
        val = getattr(req, field, None)
        if val is not None:
            skill[field] = val
    skill["updatedAt"] = datetime.utcnow().isoformat()
    _persist_skills()
    return {"code": 0, "message": "ok", "data": skill}


@router.delete("/{skill_id}")
async def delete_skill(skill_id: str):
    _skills.pop(skill_id, None)
    _persist_skills()
    return {"code": 0, "message": "deleted", "data": None}


@router.post("/import")
async def import_skill(file: UploadFile = File(...)):
    content = await file.read()
    text = content.decode("utf-8", errors="ignore")
    name = file.filename.rsplit(".", 1)[0] if file.filename else "imported_skill"
    sid = str(uuid.uuid4())
    now = datetime.utcnow().isoformat()
    skill = {
        "id": sid,
        "name": name,
        "description": f"从 {file.filename} 导入",
        "content": text,
        "category": "imported",
        "icon": "📥",
        "enabled": True,
        "createdAt": now,
        "updatedAt": now,
    }
    _skills[sid] = skill
    _persist_skills()
    return {"code": 0, "message": "ok", "data": skill}
