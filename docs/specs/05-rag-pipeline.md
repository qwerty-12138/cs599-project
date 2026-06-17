# 05 — RAG 管道规格

## 5.1 概述

RAG 管道负责文档摄入、向量化存储、混合检索和重排序。核心设计原则：**条件触发**——仅在用户问题与知识库内容相关时才执行检索，闲聊和通用问题直接走 LLM，避免检索噪声干扰回答质量。

## 5.2 RAG 管道架构

```
┌─────────────────────────────────────────────────────┐
│                    RAG Pipeline                       │
│                                                      │
│  [文档摄入]                                         │
│     │                                                │
│     ▼                                                │
│  ┌──────────┐  ┌──────────┐  ┌─────────────────┐    │
│  │ 文档加载  │→│ 智能分块  │→│ 嵌入生成 + 存储  │    │
│  └──────────┘  └──────────┘  └─────────────────┘    │
│                                                      │
│  [在线检索]                                         │
│     │                                                │
│     ▼                                                │
│  ┌──────────┐  ┌──────────┐  ┌─────────────────┐    │
│  │ 查询改写  │→│ 混合检索  │→│ 重排序 (Reranker)│    │
│  └──────────┘  └──────────┘  └─────────────────┘    │
│                     │                                │
│                     ▼                                │
│              检索结果 → Agent 上下文                  │
└─────────────────────────────────────────────────────┘
```

## 5.3 文档摄入 (Ingestion)

### 5.3.1 支持的文档格式

| 格式 | 加载器 | 说明 |
|------|--------|------|
| `.txt` | TextLoader | 纯文本 |
| `.md` | UnstructuredMarkdownLoader | Markdown |
| `.pdf` | PyPDFLoader | PDF 文档 |
| `.docx` | Docx2txtLoader | Word 文档 |
| `.csv` | CSVLoader | CSV 表格 |

### 5.3.2 分块策略

```python
from langchain.text_splitter import RecursiveCharacterTextSplitter

splitter = RecursiveCharacterTextSplitter(
    chunk_size=500,           # 每块 500 字符
    chunk_overlap=100,        # 重叠 100 字符
    separators=["\n\n", "\n", "。", ".", " ", ""],
    length_function=len
)
```

### 5.3.3 嵌入模型

- 默认使用 DeepSeek Embedding API
- 维度: 1536 (可配置)
- 批量处理: 每次 20 条

### 5.3.4 摄入流程

```python
async def ingest_document(file_path: str, knowledge_base_id: str):
    # 1. 加载文档
    loader = get_loader(file_path)
    raw_docs = loader.load()

    # 2. 分块
    chunks = splitter.split_documents(raw_docs)

    # 3. 生成元数据
    for i, chunk in enumerate(chunks):
        chunk.metadata.update({
            "source": file_path,
            "chunk_index": i,
            "kb_id": knowledge_base_id,
            "timestamp": datetime.now().isoformat()
        })

    # 4. 嵌入 + 存储
    embeddings = await embedding_model.embed_batch(
        [chunk.page_content for chunk in chunks]
    )

    await vector_store.add_documents(chunks, embeddings)

    return len(chunks)
```

## 5.4 混合检索

### 5.4.1 检索策略

```
用户问题
    │
    ▼
┌──────────────┐
│ 查询改写       │  (可选: HyDE - 生成假设文档)
└──────┬───────┘
       │
       ▼
┌──────────────────────────────────────┐
│            混合检索                    │
│                                      │
│  ┌──────────────┐  ┌──────────────┐  │
│  │ 向量检索      │  │ BM25 关键词    │  │
│  │ (语义相似)    │  │ (精确匹配)    │  │
│  │ top-k: 10    │  │ top-k: 5     │  │
│  └──────┬───────┘  └──────┬───────┘  │
│         │                 │          │
│         └────┬───────────┘           │
│              ▼                       │
│       ┌──────────────┐              │
│       │ RRF 融合      │              │
│       │ (Reciprocal  │              │
│       │  Rank Fusion) │              │
│       └──────┬───────┘              │
└──────────────┼──────────────────────┘
               ▼
       ┌──────────────┐
       │ 重排序        │
       │ (Cross-encoder)│
       │ top-k → 3    │
       └──────────────┘
```

### 5.4.2 RRF 融合算法

```python
def reciprocal_rank_fusion(results_list, k=60):
    """融合多个检索结果列表"""
    scores = {}
    for results in results_list:
        for rank, doc in enumerate(results):
            doc_id = doc.metadata["chunk_index"]
            scores[doc_id] = scores.get(doc_id, 0) + 1 / (k + rank + 1)
    return sorted(scores.items(), key=lambda x: x[1], reverse=True)
```

### 5.4.3 BM25 实现

```python
# 使用 langchain 的 BM25Retriever 或自定义实现
from langchain_community.retrievers import BM25Retriever

bm25_retriever = BM25Retriever.from_documents(
    documents=all_chunks,
    k=5
)
```

## 5.5 条件路由逻辑

### 5.5.1 为什么需要条件路由

如果对所有问题都执行 RAG 检索：
1. 闲聊问题会携带无关文档片段，干扰回答
2. 浪费检索计算资源和延迟
3. 用户感知差（无关内容的回答）

### 5.5.2 路由决策

```python
def should_use_rag(state: AgentState) -> bool:
    """
    以下情况使用 RAG:
    - 意图分类为 "knowledge"
    - 意图分类为 "complex" 且涉及知识库

    以下情况不使用 RAG:
    - 意图分类为 "chitchat"
    - 意图分类为 "tool_use"（工具调用时单独处理）
    """
    if state["intent"] == "knowledge":
        return True
    if state["intent"] == "complex":
        return _check_knowledge_relevance(state)
    return False
```

### 5.5.3 不相关时直接回答

```python
if not state["needs_rag"]:
    # 直接生成回答，只携带：
    # - 系统提示词
    # - 相关长期记忆
    # - 短期记忆（最近对话）
    # - 用户问题（不包含 RAG 检索结果）
    response = await llm.ainvoke(
        messages=build_messages(
            system=system_prompt,
            memories=state["long_term_memories"][:3],
            history=state["messages"][-10:],
            user_query=user_message
        )
    )
```

## 5.6 知识库管理

### 5.6.1 多知识库支持

```python
class KnowledgeBase:
    id: str
    name: str
    description: str
    collection_name: str   # Milvus/Chroma 集合名
    document_count: int
    created_at: datetime
```

### 5.6.2 操作接口

| 操作 | 说明 |
|------|------|
| `create_kb(name, description)` | 创建知识库 |
| `delete_kb(kb_id)` | 删除知识库及所有文档 |
| `upload_document(kb_id, file)` | 上传文档到知识库 |
| `list_documents(kb_id)` | 列出文档 |
| `delete_document(doc_id)` | 删除单个文档 |
| `search(kb_id, query, top_k)` | 检索知识库 |

## 5.7 向量数据库配置

### 5.7.1 选项 A: Milvus (推荐生产)

```python
from pymilvus import connections, Collection

connections.connect(host="milvus", port="19530")

# Collection Schema
fields = [
    FieldSchema(name="id", dtype=DataType.VARCHAR, max_length=64, is_primary=True),
    FieldSchema(name="text", dtype=DataType.VARCHAR, max_length=65535),
    FieldSchema(name="embedding", dtype=DataType.FLOAT_VECTOR, dim=1536),
    FieldSchema(name="kb_id", dtype=DataType.VARCHAR, max_length=64),
    FieldSchema(name="source", dtype=DataType.VARCHAR, max_length=512),
]
```

### 5.7.2 选项 B: ChromaDB (轻量开发)

```python
import chromadb

client = chromadb.HttpClient(host="chromadb", port=8000)
collection = client.get_or_create_collection("knowledge_base")
```

## 5.8 实现文件清单

| 文件 | 职责 |
|------|------|
| `src/rag/__init__.py` | 模块导出 |
| `src/rag/pipeline.py` | RAG 管道主流程 |
| `src/rag/embedding.py` | 嵌入模型管理 |
| `src/rag/retriever.py` | 混合检索器 |
| `src/rag/reranker.py` | 重排序 |
| `src/rag/ingestion.py` | 文档摄入 |
| `src/rag/knowledge_base.py` | 知识库管理 |
