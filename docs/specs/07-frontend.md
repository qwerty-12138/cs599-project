# 07 — 前端界面规格

## 7.1 概述

前端基于 Vue 3 + TypeScript + Element Plus 构建，采用组件化架构，支持会话管理、流式对话、MCP 配置、Skill 管理和知识库管理。

## 7.2 技术栈

| 分类 | 技术 | 版本 |
|------|------|------|
| 框架 | Vue | 3.4.x |
| 语言 | TypeScript | 5.4.x |
| UI 组件 | Element Plus | 2.7.x |
| 构建工具 | Vite | 5.4.x |
| 状态管理 | Vue Composition API (reactive/ref) | - |
| HTTP 客户端 | Axios | 1.7.x |
| 图标 | Element Plus Icons | - |

## 7.3 项目结构

```
src/frontend/src/
├── main.ts                 # 应用入口
├── App.vue                 # 根组件
├── router/index.ts         # 路由配置
├── views/                  # 页面组件
│   ├── Chat.vue            # 主聊天界面（会话列表 + 对话区）
│   ├── HistoryView.vue     # 历史记录页面
│   ├── Knowledge.vue       # 知识库管理
│   ├── McpView.vue         # MCP 服务器配置
│   ├── SkillView.vue       # Skill 管理
│   └── ToolsView.vue       # 工具管理
├── api/
│   └── index.ts            # API 调用层（统一封装）
├── types/
│   └── index.ts            # TypeScript 类型定义
├── components/             # 通用组件（如需要）
└── styles/                 # 全局样式
```

## 7.4 路由配置

```typescript
// src/frontend/src/router/index.ts
const routes = [
  {
    path: '/',
    name: 'Chat',
    component: () => import('@/views/Chat.vue')
  },
  {
    path: '/history',
    name: 'History',
    component: () => import('@/views/HistoryView.vue')
  },
  {
    path: '/knowledge',
    name: 'Knowledge',
    component: () => import('@/views/Knowledge.vue')
  },
  {
    path: '/mcp',
    name: 'MCP',
    component: () => import('@/views/McpView.vue')
  },
  {
    path: '/skills',
    name: 'Skills',
    component: () => import('@/views/SkillView.vue')
  },
  {
    path: '/tools',
    name: 'Tools',
    component: () => import('@/views/ToolsView.vue')
  }
]
```

## 7.5 页面组件详解

### 7.5.1 Chat.vue — 主聊天界面

**职责**：会话列表管理、对话消息展示、流式输出渲染、工具/Skill 选择

**核心功能**：

| 功能 | 说明 |
|------|------|
| 会话列表 | 左侧列表，支持创建、选择、删除会话 |
| 消息渲染 | 用户/助手消息气泡，支持 Markdown |
| 流式输出 | SSE 实时 token 渲染，打字机效果 |
| 意图分析动画 | 齿轮旋转动画，显示"正在分析意图..." |
| 工具调用状态 | 工具执行中显示动画，完成后隐藏过程日志 |
| 取消生成 | 支持随时终止正在生成的回答 |
| MCP 服务器开关 | 弹出面板管理服务器启用/禁用状态 |
| Skill 选择 | 弹出面板选择启用的 Skill |

**状态管理**：

```typescript
// 核心响应式状态
const messages = ref<Message[]>([])
const sessions = ref<Session[]>([])
const currentSessionId = ref('')
const inputMessage = ref('')
const sending = ref(false)
const stopping = ref(false)
const analyzingIntent = ref(false)

// MCP 和 Skill 状态
const availableServers = ref<McpServer[]>([])
const availableTools = ref<McpTool[]>([])
const availableSkills = ref<Skill[]>([])
const enabledToolIds = ref<string[]>([])
const enabledSkillIds = ref<string[]>([])
```

**流式处理逻辑**：

```typescript
// SSE 事件处理
stream.on('token', (data) => {
  // 更新消息内容，使用对象展开触发 Vue 响应式
  messages.value[idx] = { ...messages.value[idx], content: newContent }
})

stream.on('tool_start', () => {
  analyzingIntent.value = false
})

stream.on('done', () => {
  sending.value = false
  stopping.value = false
})
```

**意图分析动画**：

```vue
<template v-if="message.role === 'assistant' && message.content === '' && analyzingIntent">
  <div class="intent-analysis">
    <el-icon :size="20" class="gear-icon"><Setting /></el-icon>
    <span class="analysis-text">正在分析意图...</span>
  </div>
</template>
```

### 7.5.2 McpView.vue — MCP 服务器配置

**职责**：MCP 服务器的增删改查、工具发现、连接测试

**功能列表**：

| 功能 | 说明 |
|------|------|
| 服务器列表 | 表格展示所有配置的 MCP 服务器 |
| 启用/禁用 | 开关控制服务器状态，自动管理工具 |
| 添加/编辑 | 对话框配置服务器参数 |
| 测试连接 | 验证服务器可达性和认证 |
| 发现工具 | 调用 MCP 协议发现可用工具 |
| 工具列表 | 查看服务器关联的工具 |

**服务器配置字段**：

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| name | string | 是 | 显示名称 |
| description | string | 否 | 描述 |
| url | string | 是 | 服务器地址 |
| transportType | enum | 是 | SSE/STREAMABLE_HTTP/STDIO |
| command | string | 否 | STDIO 模式下的启动命令 |
| configJson | string | 否 | 额外配置（认证头、API Key 等） |

### 7.5.3 SkillView.vue — Skill 管理

**职责**：Skill 的增删改查、导入导出

### 7.5.4 Knowledge.vue — 知识库管理

**职责**：文档上传、分块展示、删除

### 7.5.5 HistoryView.vue — 历史记录

**职责**：查看历史会话记录

### 7.5.6 ToolsView.vue — 工具管理

**职责**：查看和管理可用工具

## 7.6 API 调用层

### 7.6.1 统一封装

```typescript
// src/frontend/src/api/index.ts
const api = axios.create({
  baseURL: '/api/v1',
  timeout: 30000
})
```

### 7.6.2 API 模块

| 模块 | 说明 |
|------|------|
| `chatApi` | 会话管理、消息发送（含流式） |
| `knowledgeApi` | 文档上传、检索、删除 |
| `skillApi` | Skill CRUD |
| `mcpApi` | MCP 服务器和工具管理 |
| `toolsApi` | 工具 CRUD |

### 7.6.3 流式 API 设计

```typescript
sendMessageStream(sessionId, content, skillIds, toolIds): Promise<{
  on: (event: string, handler: (data: any) => void) => void
  abort: () => void
}>
```

支持的 SSE 事件：

| 事件名 | 说明 |
|--------|------|
| `token` | LLM 输出的单个 token |
| `tool_start` | 工具调用开始 |
| `tool_end` | 工具调用结束 |
| `done` | 流式响应结束 |
| `error` | 错误发生 |

## 7.7 TypeScript 类型定义

### 7.7.1 核心类型

```typescript
interface Session {
  id: string
  title: string
  lastMessage: string
  messageCount: number
  createdAt: string
  updatedAt: string
}

interface Message {
  id: string
  sessionId: string
  role: 'user' | 'assistant'
  content: string
  sources: Source[]
  createdAt: string
}

interface McpServer {
  id: string
  name: string
  url: string
  transportType: 'SSE' | 'STREAMABLE_HTTP' | 'STDIO'
  enabled: boolean
  status: 'CONNECTED' | 'DISCONNECTED' | 'ERROR'
  configJson: string
}

interface McpTool {
  id: string
  server: McpServer
  name: string
  description: string
  inputSchema: string
  enabled: boolean
}

interface Skill {
  id: string
  name: string
  content: string
  category: string
  enabled: boolean
}
```

## 7.8 安全考虑

### 7.8.1 敏感数据保护

- **API Key**：通过 `configJson` 字段配置，仅存储在本地数据文件
- **MCP 配置**：包含认证信息的配置仅在前端和后端本地存储，不传输到外部
- **会话数据**：本地持久化，不随代码提交

### 7.8.2 输入安全

- 使用 Element Plus 组件自带的 XSS 防护
- 后端对用户输入进行参数化处理

## 7.9 构建配置

### 7.9.1 Vite 配置

```typescript
// vite.config.ts
export default defineConfig({
  plugins: [vue(), vueJsx()],
  resolve: {
    alias: {
      '@': fileURLToPath(new URL('./src', import.meta.url))
    }
  },
  build: {
    outDir: 'dist',
    sourcemap: false
  }
})
```

### 7.9.2 Docker 构建

```dockerfile
# docker/Dockerfile.frontend
FROM node:20-alpine AS builder
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci
COPY . .
RUN npm run build

FROM nginx:alpine
COPY --from=builder /app/dist /usr/share/nginx/html
COPY docker/config/nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
```

## 7.10 实现文件清单

| 文件 | 职责 |
|------|------|
| `src/frontend/src/main.ts` | 应用入口 |
| `src/frontend/src/App.vue` | 根组件 |
| `src/frontend/src/router/index.ts` | 路由配置 |
| `src/frontend/src/views/Chat.vue` | 主聊天界面 |
| `src/frontend/src/views/McpView.vue` | MCP 服务器配置 |
| `src/frontend/src/views/SkillView.vue` | Skill 管理 |
| `src/frontend/src/views/Knowledge.vue` | 知识库管理 |
| `src/frontend/src/views/HistoryView.vue` | 历史记录 |
| `src/frontend/src/views/ToolsView.vue` | 工具管理 |
| `src/frontend/src/api/index.ts` | API 调用层 |
| `src/frontend/src/types/index.ts` | 类型定义 |
| `src/frontend/package.json` | 依赖配置 |
| `src/frontend/vite.config.ts` | Vite 配置 |