# 08 — API 设计规格

## 8.1 概述

后端 API 基于 FastAPI 构建，采用 RESTful 风格，统一返回格式。API 分为以下模块：聊天会话、知识库、Skill、MCP 服务器和工具。

## 8.2 基础配置

### 8.2.1 路由前缀

所有 API 路由前缀为 `/api/v1`

### 8.2.2 统一响应格式

```json
{
  "code": 0,
  "message": "ok",
  "data": {}
}
```

| 字段 | 类型 | 说明 |
|------|------|------|
| `code` | number | 0 表示成功，非 0 表示错误码 |
| `message` | string | 提示信息 |
| `data` | any | 业务数据 |

### 8.2.3 分页响应格式

```json
{
  "code": 0,
  "message": "ok",
  "data": {
    "list": [],
    "total": 0,
    "page": 1,
    "pageSize": 10
  }
}
```

## 8.3 聊天会话 API

### 8.3.1 创建会话

**POST** `/api/v1/chat/sessions`

请求体：
```json
{
  "title": "string"
}
```

响应：
```json
{
  "code": 0,
  "message": "ok",
  "data": {
    "id": "uuid",
    "title": "会话标题",
    "lastMessage": "",
    "messageCount": 0,
    "createdAt": "2026-06-17T08:00:00Z",
    "updatedAt": "2026-06-17T08:00:00Z"
  }
}
```

### 8.3.2 获取会话列表

**GET** `/api/v1/chat/sessions?page=1&pageSize=10`

响应：分页格式

### 8.3.3 获取会话详情

**GET** `/api/v1/chat/sessions/{id}`

响应：单个会话对象

### 8.3.4 获取会话消息

**GET** `/api/v1/chat/sessions/{id}/messages`

响应：
```json
{
  "code": 0,
  "message": "ok",
  "data": [
    {
      "id": "uuid",
      "sessionId": "uuid",
      "role": "user",
      "content": "用户消息",
      "sources": [],
      "createdAt": "2026-06-17T08:00:00Z"
    }
  ]
}
```

### 8.3.5 发送消息（同步）

**POST** `/api/v1/chat/sessions/{id}/messages`

请求体：
```json
{
  "content": "string"
}
```

### 8.3.6 发送消息（流式 SSE）

**POST** `/api/v1/chat/sessions/{id}/messages/stream`

请求体：
```json
{
  "content": "string",
  "skillIds": ["skill_id_1"],
  "toolIds": ["tool_id_1"]
}
```

SSE 事件类型：

| 事件名 | 数据格式 | 说明 |
|--------|----------|------|
| `token` | `{"content": "string"}` | LLM 输出的单个 token |
| `tool_start` | `{"tool_name": "string"}` | 工具调用开始 |
| `tool_end` | `{"tool_name": "string", "result": "string"}` | 工具调用结束 |
| `done` | `{}` | 流式响应结束 |
| `error` | `{"message": "string"}` | 错误发生 |
| `cancelled` | `{}` | 用户取消 |

### 8.3.7 删除会话

**DELETE** `/api/v1/chat/sessions/{id}`

## 8.4 知识库 API

### 8.4.1 上传文档

**POST** `/api/v1/knowledge/documents`

Content-Type: `multipart/form-data`

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `file` | File | 是 | 文档文件 |
| `name` | string | 否 | 自定义文件名 |

### 8.4.2 获取文档列表

**GET** `/api/v1/knowledge/documents?page=1&pageSize=10&keyword=&type=`

### 8.4.3 获取文档详情

**GET** `/api/v1/knowledge/documents/{id}`

### 8.4.4 获取文档分块

**GET** `/api/v1/knowledge/documents/{id}/chunks`

### 8.4.5 删除文档

**DELETE** `/api/v1/knowledge/documents/{id}`

## 8.5 Skill API

### 8.5.1 获取 Skill 列表

**GET** `/api/v1/skills?page=1&pageSize=20&keyword=&category=`

### 8.5.2 获取单个 Skill

**GET** `/api/v1/skills/{id}`

### 8.5.3 获取启用的 Skill

**GET** `/api/v1/skills/enabled`

### 8.5.4 创建 Skill

**POST** `/api/v1/skills`

请求体：
```json
{
  "name": "string",
  "description": "string",
  "content": "string",
  "category": "string",
  "enabled": true,
  "icon": "string"
}
```

### 8.5.5 更新 Skill

**PUT** `/api/v1/skills/{id}`

请求体：与创建相同，字段可选

### 8.5.6 删除 Skill

**DELETE** `/api/v1/skills/{id}`

### 8.5.7 导入 Skill

**POST** `/api/v1/skills/import`

Content-Type: `multipart/form-data`

## 8.6 MCP 服务器 API

### 8.6.1 获取服务器列表

**GET** `/api/v1/mcp/servers`

### 8.6.2 获取启用的服务器

**GET** `/api/v1/mcp/servers/enabled`

### 8.6.3 获取单个服务器

**GET** `/api/v1/mcp/servers/{id}`

### 8.6.4 创建服务器

**POST** `/api/v1/mcp/servers`

请求体：
```json
{
  "name": "string",
  "description": "string",
  "url": "string",
  "transportType": "SSE",
  "command": "string",
  "configJson": "string",
  "enabled": true
}
```

### 8.6.5 更新服务器

**PUT** `/api/v1/mcp/servers/{id}`

请求体：字段可选

**特殊逻辑**：当 `enabled` 字段改变时，自动管理关联工具的启用/禁用状态。

### 8.6.6 删除服务器

**DELETE** `/api/v1/mcp/servers/{id}`

### 8.6.7 测试连接

**POST** `/api/v1/mcp/servers/{id}/test`

### 8.6.8 发现工具

**POST** `/api/v1/mcp/servers/{id}/discover`

### 8.6.9 获取服务器工具

**GET** `/api/v1/mcp/servers/{id}/tools`

## 8.7 MCP 工具 API

### 8.7.1 获取启用的工具

**GET** `/api/v1/mcp/tools/enabled`

### 8.7.2 启用/禁用工具

**PUT** `/api/v1/mcp/tools/{tool_id}/toggle`

请求体：
```json
{
  "enabled": true
}
```

### 8.7.3 调用工具

**POST** `/api/v1/mcp/tools/{tool_id}/call`

请求体：工具参数（动态）

## 8.8 工具 API（通用）

### 8.8.1 获取工具列表

**GET** `/api/v1/tools?page=1&pageSize=20&keyword=&toolType=`

### 8.8.2 获取单个工具

**GET** `/api/v1/tools/{id}`

### 8.8.3 获取启用的工具

**GET** `/api/v1/tools/enabled`

### 8.8.4 创建工具

**POST** `/api/v1/tools`

### 8.8.5 更新工具

**PUT** `/api/v1/tools/{id}`

### 8.8.6 删除工具

**DELETE** `/api/v1/tools/{id}`

## 8.9 数据持久化

### 8.9.1 文件存储

会话和消息数据通过 JSON 文件持久化：

| 文件 | 路径 | 说明 |
|------|------|------|
| sessions.json | `/app/data/sessions.json` | 会话列表 |
| messages.json | `/app/data/messages.json` | 消息内容 |
| mcp_servers.json | `/app/data/mcp_servers.json` | MCP 服务器配置 |
| mcp_tools.json | `/app/data/mcp_tools.json` | MCP 工具列表 |
| skills.json | `/app/data/skills.json` | Skill 数据 |

### 8.9.2 持久化策略

- 采用内存缓存 + JSON 文件备份的方式
- 关键操作后自动触发文件写入
- 使用临时文件写入 + 原子替换保证数据一致性

## 8.10 安全考虑

### 8.10.1 敏感信息保护

- **API Key**：通过环境变量注入，不在代码中硬编码
- **MCP 配置**：`configJson` 字段可能包含认证信息，仅本地存储，不记录到日志
- **数据文件**：包含敏感数据的 JSON 文件已加入 `.gitignore`

### 8.10.2 CORS 配置

```python
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

## 8.11 API 文档

### 8.11.1 Swagger UI

访问地址：`http://localhost:8000/docs`

### 8.11.2 ReDoc

访问地址：`http://localhost:8000/redoc`

## 8.12 实现文件清单

| 文件 | 职责 |
|------|------|
| `src/backend/api/chat.py` | 聊天会话 API |
| `src/backend/api/knowledge.py` | 知识库 API |
| `src/backend/api/skills.py` | Skill API |
| `src/backend/api/mcp.py` | MCP 服务器和工具 API |
| `src/backend/api/tools.py` | 通用工具 API |
| `src/backend/api/main.py` | API 入口和路由注册 |