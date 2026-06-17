# CS599 Project — Agentic RAG 对话系统

## 项目简介

一个具备记忆能力、MCP 协议工具调用、条件 RAG 检索、流式输出的 AI Agent 对话系统，解决传统问答系统缺乏上下文记忆和动态工具调用能力的问题。

## 方向

方向一：Agentic AI 原生开发

## 技术栈

- AI IDE: Trae CN
- LLM: DeepSeek API
- 框架: LangGraph >= 0.2.0
- 后端: FastAPI 0.115.x
- 前端: Vue 3 + TypeScript + Element Plus
- 短期记忆: Redis Stack 7.4
- 向量数据库: ChromaDB
- 容器: Docker + Docker Compose
- 可观测性: Prometheus + Grafana

## 目录结构

- `src/backend/api/` — REST API 路由，处理前端请求
- `src/backend/agent/` — Agent 引擎，基于 LangGraph 编排多步骤推理流程
- `src/backend/memory/` — 记忆系统，短期记忆(Redis)与长期记忆管理
- `src/backend/mcp/` — MCP 协议集成，动态工具调用与服务器管理
- `src/backend/rag/` — RAG 管道，文档摄入、混合检索与重排序
- `src/frontend/` — Vue 3 前端，对话界面与管理面板

## 环境搭建

### 1. 依赖安装

```bash
# 后端依赖已包含在 Docker 镜像中
# 前端开发依赖（可选）
cd src/frontend
npm install
```

### 2. 环境变量配置（⚠️ 不硬编码 API Key）

从 `.env.example` 复制创建 `.env` 文件：

```bash
# Linux/Mac
cp .env.example .env

# Windows PowerShell
Copy-Item .env.example .env
```

编辑 `.env` 文件，填写实际的 API Key：

```bash
DEEPSEEK_API_KEY=your_api_key_here
DEEPSEEK_BASE_URL=https://api.deepseek.com
```

### 3. 启动步骤

```bash
# Docker 一键启动所有服务
docker compose -f docker/docker-compose.yml up -d
```

访问地址：
- 前端: http://localhost:3000
- API 文档: http://localhost:8000/docs
- Grafana: http://localhost:3001

## 项目状态

- [x] Proposal
- [x] MVP
- [ ] Final
