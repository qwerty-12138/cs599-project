# AGENTS.md — AI Agent 协作指南

## 项目概述

本项目是一个**有记忆的 Agentic RAG 问答系统**，基于 LangGraph 编排多步推理，Docker 全栈部署。

## 技术栈

| 层 | 技术 |
|---|------|
| LLM | 阿里云百炼 DashScope (qwen-plus) |
| 嵌入 | DashScope text-embedding-v3 |
| 编排 | LangGraph >= 0.2.0 |
| 后端 | FastAPI 0.115.x |
| 前端 | React 18 + TypeScript + TailwindCSS |
| 短期记忆 | Redis Stack 7.4 |
| 长期记忆 | PostgreSQL 16 + pgvector |
| 向量库 | ChromaDB (dev) / Milvus (prod) |
| 容器 | Docker Compose |

## 项目结构

```
cs599-project/
├── docs/specs/          # 10 个详细规格文档（先阅读再编码）
├── src/                 # 后端
│   ├── agent/           # LangGraph 图定义 + 节点
│   ├── memory/          # 记忆系统（短期/长期/向量）
│   ├── mcp/             # MCP 客户端 + 工具包装
│   ├── rag/             # 文档摄入、混合检索、重排序
│   ├── api/             # FastAPI 路由
│   ├── eval/            # RAGAS 评估 + 自定义 Benchmark
│   └── observability/   # LangFuse + Prometheus 指标
├── frontend/            # React 前端
├── docker/              # Docker Compose + 各服务 Dockerfile
└── README.md
```

## 核心设计决策

### 条件 RAG 路由
- 意图分类后**仅当问题与知识库相关时才检索**，闲聊直接走 LLM
- 避免无关文档干扰回答质量

### 取消不持久化
- 用户取消的对话不进入长期记忆
- 已接收的 token 保留在 UI 上，标记 "(已取消)"

### 记忆双层体系
- 短期：Redis List，24h TTL，存储最近 N 轮对话
- 长期：PostgreSQL + pgvector，会话摘要 + 关键事实提取

### MCP 工具动态启用
- 前端面板可配置 MCP 服务器、单独开关每个工具
- 对话时仅注入用户启用的工具

## 编码规范

### Python
- 使用 `async/await` 处理所有 I/O（数据库、LLM、MCP）
- Pydantic BaseModel 定义所有数据模型
- 环境变量通过 `os.getenv()` 读取，不硬编码密钥
- LangGraph 节点为纯异步函数，通过 `add_messages` reducer 更新 state

### TypeScript
- Zustand 管理全局状态（chat / mcp / settings 三个 store）
- SSE 事件通过 `useSSE` hook 消费
- 50ms 内 token 批量渲染，避免频繁重绘
- TailwindCSS 暗色主题，使用 surface/dark → surface/light 色调

### API
- 所有接口前缀 `/api/v1`
- 统一响应 `{ code, message, data }`
- 流式接口使用 SSE，事件类型见 `docs/specs/10-streaming-cancel.md`

### 文件命名
- Python 模块：`snake_case.py`
- React 组件：`PascalCase.tsx`
- 类型定义：`types.ts`
- 配置文件：`kebab-case.yml`

## 开发流程

1. 阅读 `docs/specs/` 下对应规格文档
2. 后端从 `src/agent/graph.py` 开始，前端从 `frontend/src/App.tsx` 开始
3. 使用 `docker compose up -d` 启动基础设施
4. 后端 `uvicorn src.api.main:app --reload` 热重载开发
5. 前端 `npm run dev` Vite 开发服务器
6. 提交前确保 `docker compose up` 能完整启动

## 关键约束

- API Key 只存在于 `.env`，不提交到 Git
- Docker 沙箱执行工具，network=none + readonly + 30s 超时
- ReAct 循环最多 10 次，防止无限调用
- SSE 连接 proxy_read_timeout 300s，proxy_buffering off
- 前端自动滚动到底部，除非用户手动上滑

## 评估

- RAGAS: Faithfulness / Relevance / Context Recall / Context Precision
- 自定义: 记忆保持率 / 工具调用准确率 / 条件路由正确率
- 可观测性: LangFuse 链路追踪 + Prometheus 指标 + Grafana 面板
