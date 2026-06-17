"""Knowledge base and document management with lightweight parsers + LangChain chunking"""
import os
import re
import uuid
import asyncio
import logging
from typing import Optional
from datetime import datetime

from langchain_text_splitters import RecursiveCharacterTextSplitter

logger = logging.getLogger(__name__)


def _tokenize(text: str) -> set[str]:
    """Split text into tokens, handling both Chinese and English.
    Uses jieba for Chinese and whitespace splitting for English.
    """
    # Remove punctuation
    text = re.sub(r'[^\w\s一-鿿]', ' ', text)

    tokens = set()

    # Whitespace tokens (English words)
    for t in text.split():
        t = t.strip().lower()
        if t and len(t) > 1:
            tokens.add(t)

    # Chinese tokens — only import jieba when actually needed
    if re.search(r'[一-鿿]', text):
        try:
            import jieba
            # Add domain-specific terms for better segmentation
            for t in ["知识库", "RAG", "MCP", "LangGraph", "Agent", "LLM"]:
                jieba.add_word(t)
            for word in jieba.cut(text, cut_all=False):
                word = word.strip().lower()
                if word and len(word) > 1:
                    tokens.add(word)
        except ImportError:
            # Fallback: character bigrams for Chinese
            chars = re.findall(r'[一-鿿]', text)
            for i in range(len(chars) - 1):
                tokens.add(chars[i] + chars[i + 1])

    return tokens

_chunk_splitter = RecursiveCharacterTextSplitter(
    chunk_size=500,
    chunk_overlap=100,
    separators=["\n\n", "\n", "。", ".", " ", ""],
    length_function=len,
)


def _parse_text(file_path: str) -> str:
    """Simple text/markdown reader."""
    with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
        return f.read()


def _parse_pdf(file_path: str) -> str:
    """Parse PDF via PyPDF2."""
    from PyPDF2 import PdfReader
    reader = PdfReader(file_path)
    pages = []
    for page in reader.pages:
        text = page.extract_text()
        if text:
            pages.append(text)
    return "\n\n".join(pages)


def _parse_docx(file_path: str) -> str:
    """Parse DOCX via python-docx."""
    try:
        from docx import Document
        doc = Document(file_path)
        paras = [p.text for p in doc.paragraphs if p.text.strip()]
        return "\n\n".join(paras)
    except ImportError:
        logger.warning("python-docx not installed, falling back to raw read")
        with open(file_path, "rb") as f:
            raw = f.read()
        return raw.decode("utf-8", errors="ignore")


def _parse_file(file_path: str) -> Optional[str]:
    """Detect file type and parse accordingly. Runs in a thread."""
    _, ext = os.path.splitext(file_path)
    ext = ext.lower()

    try:
        if ext == ".pdf":
            return _parse_pdf(file_path)
        elif ext == ".docx":
            return _parse_docx(file_path)
        else:
            # txt, md, csv, etc.
            return _parse_text(file_path)
    except Exception as e:
        logger.error("Failed to parse %s: %s", file_path, e)
        return None


def _chunk_text(text: str) -> list[str]:
    """Split text into chunks using LangChain's recursive splitter."""
    docs = _chunk_splitter.create_documents([text])
    return [d.page_content for d in docs]


class KnowledgeBaseManager:
    """Manages knowledge bases and their documents."""

    def __init__(self):
        self._documents: dict[str, dict] = {}
        self._chunks: dict[str, list[dict]] = {}
        self._collections: dict[str, list[dict]] = {}

    # ── upload / process ────────────────────────────────────

    async def upload_document(self, file_path: str, file_name: str,
                               file_type: str, file_size: int,
                               name: Optional[str] = None,
                               kb_id: str = "default") -> dict:
        doc_id = str(uuid.uuid4())
        now = datetime.utcnow().isoformat()
        doc = {
            "id": doc_id,
            "name": name or file_name,
            "type": file_type.lower(),
            "size": file_size,
            "chunkCount": 0,
            "status": "processing",
            "kb_id": kb_id,
            "createdAt": now,
            "updatedAt": now,
        }
        self._documents[doc_id] = doc
        return doc

    async def process_document(self, file_path: str, doc_id: str) -> int:
        """
        Parse the file then chunk — both CPU-bound, run in executor.
        Returns chunk count.
        """
        loop = asyncio.get_event_loop()

        # 1. Parse (thread)
        raw_text = await loop.run_in_executor(None, _parse_file, file_path)
        if not raw_text or not raw_text.strip():
            logger.warning("No text extracted from %s", file_path)
            self._documents[doc_id]["status"] = "READY"
            self._documents[doc_id]["chunkCount"] = 0
            return 0

        # 2. Chunk (thread)
        chunks = await loop.run_in_executor(None, _chunk_text, raw_text)

        # 3. Store results
        chunk_entries = [
            {"id": f"{doc_id}_chunk_{i}", "chunkIndex": i, "content": text, "embedding": None}
            for i, text in enumerate(chunks)
        ]

        self._chunks[doc_id] = chunk_entries
        kb_id = self._documents[doc_id].get("kb_id", "default")
        self._collections.setdefault(kb_id, []).extend(chunk_entries)

        doc = self._documents[doc_id]
        doc["chunkCount"] = len(chunks)
        doc["status"] = "READY"
        doc["updatedAt"] = datetime.utcnow().isoformat()

        logger.info("Processed %s: %d chars → %d chunks", doc["name"], len(raw_text), len(chunks))
        return len(chunks)

    # ── CRUD ────────────────────────────────────────────────

    async def get_documents(self, page: int = 1, page_size: int = 10,
                             keyword: Optional[str] = None,
                             file_type: Optional[str] = None) -> tuple[list[dict], int]:
        docs = list(self._documents.values())
        if keyword:
            docs = [d for d in docs if keyword.lower() in d["name"].lower()]
        if file_type:
            docs = [d for d in docs if d["type"].lower() == file_type.lower()]
        docs.sort(key=lambda d: d.get("createdAt", ""), reverse=True)
        total = len(docs)
        start = (page - 1) * page_size
        return docs[start:start + page_size], total

    async def get_document(self, doc_id: str) -> Optional[dict]:
        return self._documents.get(doc_id)

    async def get_document_chunks(self, doc_id: str) -> list[dict]:
        return self._chunks.get(doc_id, [])

    async def delete_document(self, doc_id: str):
        doc = self._documents.pop(doc_id, None)
        chunks = self._chunks.pop(doc_id, [])
        if doc and chunks:
            kb_id = doc.get("kb_id", "default")
            removed = {ch["id"] for ch in chunks}
            if kb_id in self._collections:
                self._collections[kb_id] = [
                    c for c in self._collections[kb_id] if c["id"] not in removed
                ]

    # ── search ──────────────────────────────────────────────

    async def search(self, kb_id: str, query: str, top_k: int = 5) -> list[dict]:
        """BM25‑style keyword search with Chinese word segmentation."""
        chunks = self._collections.get(kb_id, [])
        if not chunks:
            return []

        query_tokens = _tokenize(query)
        if not query_tokens:
            return []

        # Pre‑tokenize all chunks once (lazy cache)
        if not hasattr(self, '_token_cache'):
            self._token_cache: dict[str, set[str]] = {}

        scored = []
        for ch in chunks:
            cid = ch["id"]
            if cid not in self._token_cache:
                self._token_cache[cid] = _tokenize(ch.get("content", ""))
            chunk_tokens = self._token_cache[cid]

            if not chunk_tokens:
                continue

            overlap = len(query_tokens & chunk_tokens)
            if overlap > 0:
                score = overlap / max(len(query_tokens), 1)
                scored.append((ch, score))

        scored.sort(key=lambda x: x[1], reverse=True)
        results = []
        for ch, score in scored[:top_k]:
            doc_id = ch["id"].rsplit("_chunk_", 1)[0]
            results.append({
                "chunkId": ch["id"],
                "chunkIndex": ch["chunkIndex"],
                "content": ch["content"][:500],
                "score": round(score, 4),
                "documentId": doc_id,
                "documentName": self._documents.get(doc_id, {}).get("name", "Unknown"),
            })
        return results


kb_manager = KnowledgeBaseManager()
