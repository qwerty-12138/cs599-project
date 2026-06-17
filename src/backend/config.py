"""Application configuration from environment variables"""
import os
from dotenv import load_dotenv

load_dotenv()


class Settings:
    # LLM
    DASHSCOPE_API_KEY: str = os.getenv("DASHSCOPE_API_KEY", "")
    DASHSCOPE_BASE_URL: str = os.getenv("DASHSCOPE_BASE_URL", "https://dashscope.aliyuncs.com/compatible-mode/v1")
    DASHSCOPE_MODEL: str = os.getenv("DASHSCOPE_MODEL", "qwen-plus")
    DASHSCOPE_EMBEDDING_MODEL: str = os.getenv("DASHSCOPE_EMBEDDING_MODEL", "text-embedding-v3")

    # Database
    REDIS_URL: str = os.getenv("REDIS_URL", "redis://localhost:6379")
    DATABASE_URL: str = os.getenv("DATABASE_URL", "postgresql+asyncpg://agent:agent_secret@localhost:5432/agent_db")

    # ChromaDB
    CHROMA_HOST: str = os.getenv("CHROMA_HOST", "localhost")
    CHROMA_PORT: int = int(os.getenv("CHROMA_PORT", "8000"))
    VECTOR_DIM: int = int(os.getenv("VECTOR_DIM", "1536"))

    # API
    API_HOST: str = os.getenv("API_HOST", "0.0.0.0")
    API_PORT: int = int(os.getenv("API_PORT", "8000"))
    API_CORS_ORIGINS: list[str] = os.getenv("API_CORS_ORIGINS", "http://localhost:3000,http://localhost:5173").split(",")

    # Memory
    SHORT_TERM_TTL: int = int(os.getenv("SHORT_TERM_TTL", "86400"))
    MAX_SHORT_TERM_MESSAGES: int = int(os.getenv("MAX_SHORT_TERM_MESSAGES", "50"))
    MAX_LONG_TERM_RESULTS: int = int(os.getenv("MAX_LONG_TERM_RESULTS", "5"))

    # MCP
    MCP_TOOL_TIMEOUT: int = int(os.getenv("MCP_TOOL_TIMEOUT", "30"))
    MCP_MAX_RETRIES: int = int(os.getenv("MCP_MAX_RETRIES", "2"))
    MCP_SERVER_CONFIG_DIR: str = os.getenv("MCP_SERVER_CONFIG_DIR", "./config/mcp")

    # App
    VECTOR_STORE_DB_PATH: str = os.path.join(os.path.dirname(__file__), "..", "data", "chroma")


settings = Settings()
