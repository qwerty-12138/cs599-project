"""Knowledge (RAG) API routes"""
import os
import uuid
import asyncio
import logging
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, HTTPException, UploadFile, File, Form
from starlette.concurrency import run_in_threadpool

from ..rag.knowledge_base import kb_manager

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/knowledge")

UPLOAD_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "data", "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)


@router.post("/documents")
async def upload_document(file: UploadFile = File(...), name: Optional[str] = Form(None)):
    """
    Upload a document.
    - The file is saved to disk synchronously.
    - Parsing+chunking runs in a background task (off the event loop).
    - The response returns immediately with status="processing".
    - Frontend should poll GET /documents/{id} until status="READY".
    """
    file_ext = file.filename.rsplit(".", 1)[-1].lower() if "." in file.filename else "txt"
    safe_name = f"{uuid.uuid4()}.{file_ext}"
    file_path = os.path.join(UPLOAD_DIR, safe_name)

    # Read & write in threadpool so large files don't block
    content = await file.read()
    with open(file_path, "wb") as f:
        f.write(content)

    doc = await kb_manager.upload_document(
        file_path=file_path,
        file_name=file.filename or "unknown",
        file_type=file_ext,
        file_size=len(content),
        name=name or file.filename or "unknown",
    )

    # Fire-and-forget background parse via run_in_threadpool
    # This avoids blocking the event loop if parsing is CPU-intensive
    asyncio.ensure_future(_process_background(file_path, doc["id"]))

    return {"code": 0, "message": "ok", "data": doc}


async def _process_background(file_path: str, doc_id: str):
    """Parse + chunk a document in a background task (off event loop)."""
    try:
        chunk_count = await kb_manager.process_document(file_path, doc_id)
        doc = await kb_manager.get_document(doc_id)
        if doc:
            logger.info("Background processing complete: %s → %d chunks", doc.get("name"), chunk_count)
    except Exception as e:
        logger.error("Background processing failed for doc %s: %s", doc_id, e, exc_info=True)
        doc = await kb_manager.get_document(doc_id)
        if doc:
            doc["status"] = "ERROR"
            doc["error"] = str(e)


@router.get("/documents")
async def list_documents(page: int = 1, pageSize: int = 10,
                          keyword: Optional[str] = None,
                          type: Optional[str] = None):
    docs, total = await kb_manager.get_documents(page, pageSize, keyword, type)
    return {
        "code": 0,
        "message": "ok",
        "data": {
            "list": docs,
            "total": total,
            "page": page,
            "pageSize": pageSize,
        }
    }


@router.get("/documents/{doc_id}")
async def get_document(doc_id: str):
    doc = await kb_manager.get_document(doc_id)
    if not doc:
        raise HTTPException(404, "文档不存在")
    chunks = await kb_manager.get_document_chunks(doc_id)
    doc["chunks"] = chunks
    return {"code": 0, "message": "ok", "data": doc}


@router.get("/documents/{doc_id}/chunks")
async def get_document_chunks(doc_id: str):
    chunks = await kb_manager.get_document_chunks(doc_id)
    return {"code": 0, "message": "ok", "data": chunks}


@router.delete("/documents/{doc_id}")
async def delete_document(doc_id: str):
    await kb_manager.delete_document(doc_id)
    return {"code": 0, "message": "deleted", "data": None}
