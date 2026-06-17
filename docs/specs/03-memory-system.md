# 03 — 记忆系统规格

## 3.1 概述

记忆系统提供两层记忆能力：短期记忆（Redis，对话上下文）、会话持久化（JSON文件，长期保存）。系统采用内存缓存 + JSON文件备份的方式实现数据持久化。

## 3.2 记忆架构

```
┌─────────────────────────────────────────────────────────┐
│                    记忆管理层 (MemoryManager)             │
│                                                         │
│  ┌──────────────┐  ┌──────────────┐                    │
│  │ 短期记忆      │  │ 会话持久化    │                    │
│  │ (Redis)      │  │ (JSON File)  │                    │
│  │              │  │              │                    │
│  │ TTL: 24h    │  │ 永久存储      │                    │
│  │ 最近 N 轮    │  │ 会话+消息     │                    │
│  └──────────────┘  └──────────────┘                    │
└─────────────────────────────────────────────────────────┘
```

## 3.3 短期记忆 (ShortTermMemory)

### 3.3.1 存储结构

```python
# Redis Key 设计
SHORT_TERM_KEY = "memory:short_term:{user_id}:{session_id}"

# 存储格式 (Redis List)
{
    "role": "user|assistant|tool",
    "content": "message text",
    "timestamp": "2026-06-16T10:30:00Z",
    "token_count": 150,
    "metadata": {
        "intent": "knowledge",
        "tool_calls": []
    }
}
```

### 3.3.2 核心操作

| 操作 | 说明 | 实现 |
|------|------|------|
| `add_turn(user_id, session_id, message)` | 添加一轮对话 | Redis RPUSH + EXPIRE |
| `get_recent(user_id, session_id, n=20)` | 获取最近 N 轮 | Redis LRANGE |
| `get_context(user_id, session_id, max_tokens=4000)` | 获取 token 限制下的上下文 | 遍历最近消息，累计 token |
| `clear_session(user_id, session_id)` | 清除会话 | Redis DEL |
| `summarize_and_promote(user_id, session_id)` | 摘要后移到长期记忆 | 见 3.5 |

### 3.3.3 TTL 策略

- 默认 TTL: 86400 秒 (24 小时)
- 每次新消息入队刷新 TTL
- 会话结束时保留 TTL（可被后续对话复用）

## 3.4 会话持久化 (Session Persistence)

### 3.4.1 文件存储结构

```python
# sessions.json — 会话列表
{
  "session_id": {
    "id": "session_id",
    "title": "会话标题",
    "lastMessage": "最后一条消息",
    "messageCount": 10,
    "createdAt": "2026-06-17T08:00:00Z",
    "updatedAt": "2026-06-17T08:30:00Z"
  }
}

# messages.json — 消息内容
{
  "session_id": [
    {
      "id": "message_id",
      "sessionId": "session_id",
      "role": "user",
      "content": "用户消息",
      "sources": [],
      "createdAt": "2026-06-17T08:00:00Z"
    }
  ]
}
```

### 3.4.2 核心操作

| 操作 | 说明 |
|------|------|
| `_load_json(path, default)` | 从 JSON 文件加载数据 |
| `_save_json(path, data)` | 保存数据到 JSON 文件（原子操作） |
| `create_session(title)` | 创建新会话，写入 JSON |
| `add_message(session_id, message)` | 添加消息，更新 JSON |
| `get_session(session_id)` | 获取会话详情 |
| `get_messages(session_id)` | 获取会话消息列表 |
| `delete_session(session_id)` | 删除会话及消息 |

### 3.4.3 持久化策略

- **内存缓存**: 所有会话和消息首先缓存在内存中，提高访问速度
- **文件备份**: 关键操作后自动写入 JSON 文件
- **原子写入**: 使用临时文件 + 原子替换保证数据一致性
- **容器重启恢复**: 启动时自动从 JSON 文件加载数据

## 3.5 记忆生命周期

### 3.5.1 完整流程

```
[对话开始]
    │
    ▼
[加载会话] ── 从 JSON 文件加载会话列表和消息
    │
    ▼
[加载记忆] ── 短期记忆 (Redis)
    │
    ▼
[Agent 推理] ── 使用当前上下文
    │
    ▼
[写入短期记忆] ── 每轮对话 push 到 Redis
    │
    ▼
[持久化到文件] ── 写入 sessions.json 和 messages.json
    │
    ▼
[对话结束]
    │
    ▼
[数据保留] ── JSON 文件持久化存储，Redis TTL 自动过期
```

## 3.6 MemoryManager 统一接口

```python
class MemoryManager:
    def __init__(self, redis_client):
        self.short_term = ShortTermMemory(redis_client)

    async def load_context(self, user_id: str, session_id: str) -> dict:
        """加载会话完整上下文"""
        short = await self.short_term.get_context(user_id, session_id)
        return {"short_term": short}

    async def add_message(self, user_id: str, session_id: str, message: dict):
        """添加消息到短期记忆"""
        await self.short_term.add_turn(user_id, session_id, message)

    async def clear_session(self, user_id: str, session_id: str):
        """清除会话（取消场景）"""
        await self.short_term.clear_session(user_id, session_id)
```

## 3.7 实现文件清单

| 文件 | 职责 |
|------|------|
| `src/memory/__init__.py` | 模块导出 |
| `src/memory/manager.py` | MemoryManager 统一入口 |
| `src/memory/short_term.py` | Redis 短期记忆 |
| `src/api/chat.py` | 会话和消息的 JSON 文件持久化 |
