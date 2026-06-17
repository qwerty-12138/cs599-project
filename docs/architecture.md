# CS599 Project — 有记忆的 Agentic RAG 系统架构文档

## 1. 系统概述

本项目构建一个具备记忆能力、MCP 协议工具调用、条件 RAG 检索、流式输出的 AI Agent 对话系统。系统采用 LangGraph 编排多步骤推理流程，Docker 容器化部署，前后端分离架构。

### 核心能力矩阵

| 能力 | 技术方案 |
|------|----------|
| 多步推理编排 | LangGraph StateGraph + ReAct 模式 |
| 短期记忆 | Redis (TTL 自动过期) |
| 长期记忆 | PostgreSQL / MySQL |
| 向量检索 | Milvus / ChromaDB (Docker 部署) |
| 工具调用 | MCP 协议 + 原生 Function Calling |
| 流式输出 | SSE (Server-Sent Events) |
| 前端 | React 18 + TailwindCSS |
| 容器化 | Docker Compose 全家桶 |
| 可观测性 | LangSmith / LangFuse + Prometheus |
| 评估 | RAGAS + 自定义 Benchmark |

---

## 2. 系统架构图

```
┌─────────────────────────────────────────────────────────────────────┐
│                         前端 (Vue)                              │
│  ┌──────────┐ ┌───────────┐ ┌──────────┐ ┌──────────────────────┐  │
│  │ 对话界面  │ │ MCP 配置  │ │ 记忆管理  │ │ 评估/可观测性面板    │  │
│  └──────────┘ └───────────┘ └──────────┘ └──────────────────────┘  │
└──────────────────────────────┬──────────────────────────────────────┘
                               │ HTTP/SSE
┌──────────────────────────────▼──────────────────────────────────────┐
│                        API 网关 (FastAPI)                            │
│  ┌──────────────┐  ┌──────────────┐  ┌───────────────────────────┐  │
│  │ /chat/stream │  │ /mcp/        │  │ /memory/ /eval/ /health/  │  │
│  └──────────────┘  └──────────────┘  └───────────────────────────┘  │
└──────────────────────────────┬──────────────────────────────────────┘
                               │
┌──────────────────────────────▼──────────────────────────────────────┐
│                     LangGraph Agent 引擎                             │
│                                                                      │
│  ┌──────────────────────────────────────────────────────┐           │
│  │                  StateGraph (主图)                    │           │
│  │                                                      │           │
│  │  [入口] → [意图分类] → [条件路由]                      │           │
│  │              │              │                         │           │
│  │         ┌────┼────┐    ┌───┴───┐                     │           │
│  │         ▼    ▼    ▼    ▼       ▼                      │           │
│  │       RAG 闲聊 工具  ReAct   SubGraph                  │           │
│  │                         │                              │           │
│  │                    ┌────┴────┐                        │           │
│  │                    ▼         ▼                         │           │
│  │               工具调用   最终回答                       │           │
│  └──────────────────────────────────────────────────────┘           │
│                                                                      │
│  ┌──────────┐ ┌──────────┐ ┌───────────┐ ┌────────────────┐        │
│  │ 记忆管理器│ │ RAG 管道 │ │ MCP 客户端 │ │ 工具注册中心    │        │
│  └──────────┘ └──────────┘ └───────────┘ └────────────────┘        │
└──────────────────────────────────────────────────────────────────────┘
                               │
┌──────────────────────────────▼──────────────────────────────────────┐
│                        Docker 基础设施层                              │
│  ┌────────┐ ┌─────────┐ ┌──────────┐ ┌─────────┐ ┌──────────────┐  │
│  │ Redis  │ │ Postgres│ │ Milvus/  │ │ Prometheus│ │ Sandbox      │  │
│  │(短记忆)│ │(长记忆) │ │ ChromaDB │ │+Grafana  │ │ (工具执行)   │  │
│  └────────┘ └─────────┘ └──────────┘ └─────────┘ └──────────────┘  │
└──────────────────────────────────────────────────────────────────────┘
```

---

## 3. 技术栈明细

| 层级 | 技术 | 版本 |
|------|------|------|
| AI IDE | Trae CN / VS Code | latest |
| LLM | DeepSeek API (chat/completions) | v1 |
| 编排框架 | LangGraph | >=0.2.0 |
| 向量数据库 | Milvus Standalone (Docker) | 2.4.x |
| 短期记忆 | Redis Stack | 7.4.x |
| 长期记忆 | PostgreSQL | 16.x |
| 后端框架 | FastAPI | 0.115.x |
| 前端框架 | React 18 + TypeScript | 18.x |
| UI 组件 | TailwindCSS + Radix UI | latest |
| 容器化 | Docker + Docker Compose | latest |
| MCP SDK | mcp (Python) | >=1.0 |
| 可观测性 | LangFuse / OpenTelemetry | latest |
| 评估 | RAGAS | >=0.2.x |

---

## 4. 核心模块设计

### 4.1 Agent 引擎 (src/agent/)

```
agent/
├── graph.py              # LangGraph 主图定义
├── nodes/
│   ├── intent.py         # 意图分类节点
│   ├── rag.py            # RAG 检索节点
│   ├── tool_call.py      # 工具调用节点 (MCP + 原生)
│   ├── memory.py         # 记忆读写节点
│   ├── response.py       # 响应生成节点
│   └── cancel.py         # 取消/中断处理
├── state.py              # AgentState 状态定义
├── router.py             # 条件路由逻辑
└── prompts/              # 提示词模板
    ├── intent.yaml
    ├── rag.yaml
    └── response.yaml
```

**AgentState 核心字段：**

```python
class AgentState(TypedDict):
    messages: list[BaseMessage]      # 对话历史
    user_id: str                     # 用户标识
    session_id: str                  # 会话标识
    intent: str                      # 意图分类结果
    needs_rag: bool                  # 是否需要 RAG
    rag_context: list[str]           # RAG 检索上下文
    tool_calls: list[ToolCall]       # 待执行工具调用
    tool_results: list[ToolResult]   # 工具执行结果
    short_term_memory: list[dict]    # 短期记忆摘要
    long_term_memory: list[dict]     # 长期记忆摘要
    cancelled: bool                  # 是否被取消
    final_response: str              # 最终响应
```

### 4.2 记忆系统 (src/memory/)

```
memory/
├── manager.py             # 记忆管理统一入口
├── short_term.py          # Redis 短期记忆
├── long_term.py           # PostgreSQL 长期记忆
├── vector_store.py        # 向量存储 (Milvus/ChromaDB)
├── summarizer.py          # 记忆摘要与压缩
└── schemas.py             # 记忆数据模型
```

**记忆生命周期：**

```
用户消息 → 写入短期记忆(TTL 24h)
         → Agent 推理完成
         → 会话结束/超时 → 摘要压缩 → 写入长期记忆
         → 下次对话 → 检索相关长期记忆 → 注入上下文
```

### 4.3 MCP 集成 (src/mcp/)

```
mcp/
├── client.py              # MCP 客户端管理器
├── server_registry.py     # MCP 服务器注册表
├── tool_wrapper.py        # 工具包装器 (MCP → LangChain Tool)
├── config.py              # MCP 配置模型
└── servers/               # 内置 MCP 服务器示例
    └── filesystem.py
```

### 4.4 RAG 管道 (src/rag/)

```
rag/
├── pipeline.py            # RAG 管道主流程
├── embedding.py           # 嵌入模型管理
├── retriever.py           # 检索器 (向量 + BM25 混合)
├── reranker.py            # 重排序
├── ingestion.py           # 文档摄入
└── knowledge_base.py      # 知识库管理
```

### 4.5 前端 (frontend/)

```
frontend/
├── src/
│   ├── components/
│   │   ├── Chat/
│   │   │   ├── ChatContainer.tsx    # 聊天主容器
│   │   │   ├── MessageList.tsx      # 消息列表
│   │   │   ├── MessageBubble.tsx    # 消息气泡
│   │   │   ├── InputArea.tsx        # 输入区域
│   │   │   ├── StreamingText.tsx    # 流式文本渲染
│   │   │   └── CancelButton.tsx     # 取消按钮
│   │   ├── MCP/
│   │   │   ├── MCPSettings.tsx      # MCP 配置面板
│   │   │   ├── ServerCard.tsx       # 服务器卡片
│   │   │   └── ToolToggle.tsx       # 工具开关
│   │   ├── Memory/
│   │   │   ├── MemoryPanel.tsx      # 记忆管理面板
│   │   │   └── MemoryViewer.tsx     # 记忆查看器
│   │   ├── Eval/
│   │   │   ├── EvalDashboard.tsx    # 评估面板
│   │   │   └── MetricsChart.tsx     # 指标图表
│   │   └── Layout/
│   │       ├── Sidebar.tsx
│   │       ├── Header.tsx
│   │       └── Layout.tsx
│   ├── hooks/
│   │   ├── useSSE.ts               # SSE 流式 Hook
│   │   ├── useChat.ts              # 聊天逻辑 Hook
│   │   └── useMCP.ts               # MCP 管理 Hook
│   ├── services/
│   │   └── api.ts                  # API 客户端
│   └── App.tsx
└── package.json
```

---

## 5. 数据流

### 5.1 对话请求完整流程

```
1. 用户输入 → 前端 POST /chat/stream (SSE)
2. API Gateway 接收 → 创建/恢复会话
3. 进入 LangGraph:
   a. [意图分类] → LLM 判断: RAG / 闲聊 / 工具调用 / 复杂推理
   b. [条件路由]:
      - RAG 路径: 检索知识库 → 注入上下文 → 生成回答
      - 闲聊路径: 直接生成回答 (不注入 RAG)
      - 工具路径: ReAct 循环 → 调用 MCP/Function → 生成回答
      - 复杂推理: 多步推理 → 可能多次工具调用 → 最终回答
   c. [记忆节点] → 写入短期记忆 → 检查是否需要摘要
4. 流式输出每个 token → SSE → 前端渲染
5. 对话完成 → 会话摘要 → 写入长期记忆
```

### 5.2 RAG 条件路由逻辑

```python
def should_use_rag(state: AgentState) -> bool:
    """意图分类为 knowledge_question 时启用 RAG，否则跳过"""
    return state["intent"] == "knowledge_question"
```

---

## 6. Docker 部署架构

```yaml
# docker-compose.yml 核心服务
services:
  api:        # FastAPI 后端
  frontend:   # Nginx + React 静态文件
  redis:      # 短期记忆 + 会话缓存
  postgres:   # 长期记忆持久化
  milvus:     # 向量数据库
    - etcd
    - minio
  prometheus: # 指标采集
  grafana:    # 可视化面板
  sandbox:    # 安全工具执行环境
```

---

## 7. 安全设计

- API Key 通过环境变量注入，不硬编码
- Docker Sandbox 隔离工具执行
- 用户会话隔离 (session_id + user_id)
- MCP 服务器白名单机制
- 前端输入消毒 (XSS 防护)
- API 速率限制

---

## 8. 评估体系

| 维度 | 指标 | 工具 |
|------|------|------|
| 检索质量 | Recall@k, MRR, NDCG | RAGAS |
| 生成质量 | Faithfulness, Relevance | RAGAS |
| 延迟 | P50/P95/P99 响应时间 | Prometheus + Grafana |
| 工具调用 | 准确率、失败率 | LangFuse |
| 记忆 | 上下文保持率 | 自定义 Benchmark |

## 
