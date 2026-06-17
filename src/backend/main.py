"""FastAPI main entry point — CS599 Agentic RAG System"""
import os
import sys
import uvicorn
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Add project root (src/) to path so backend is resolved as a package
_project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

from backend.config import settings
from backend.api import chat_router, knowledge_router, mcp_router, skills_router, tools_router

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events."""
    logger.info(f"🚀 CS599 Agentic RAG System starting on {settings.API_HOST}:{settings.API_PORT}")
    logger.info(f"   LLM Model: {settings.DASHSCOPE_MODEL}")
    logger.info(f"   CORS Origins: {settings.API_CORS_ORIGINS}")
    yield
    logger.info("Shutting down...")


app = FastAPI(
    title="CS599 Agentic RAG API",
    description="有记忆的 Agentic RAG 系统后端 API",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.API_CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routers — all prefixed with /api/v1
API_PREFIX = "/api/v1"
app.include_router(chat_router, prefix=API_PREFIX)
app.include_router(knowledge_router, prefix=API_PREFIX)
app.include_router(mcp_router, prefix=API_PREFIX)
app.include_router(skills_router, prefix=API_PREFIX)
app.include_router(tools_router, prefix=API_PREFIX)


@app.get("/")
async def root():
    return {"name": "CS599 Agentic RAG API", "version": "1.0.0", "status": "running"}


@app.get("/health")
async def health():
    return {"status": "healthy"}


if __name__ == "__main__":
    uvicorn.run(
        "backend.main:app",
        host=settings.API_HOST,
        port=settings.API_PORT,
        reload=True,
    )
