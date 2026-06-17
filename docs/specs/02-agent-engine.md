# 02 — Agent 引擎规格

## 2.1 概述

Agent 引擎是整个系统的核心，基于 LangGraph 构建有状态的多步骤推理流程。引擎负责接收用户输入、判断意图、路由到合适的处理节点、管理工具调用循环，并最终生成回答。

## 2.2 状态设计

### AgentState 完整定义

```python
from typing import TypedDict, Annotated, Sequence
from langgraph.graph.message import add_messages
from langchain_core.messages import BaseMessage, AIMessage, HumanMessage, ToolMessage

class ToolCall(TypedDict):
    id: str
    name: str
    args: dict
    source: str  # "native" | "mcp"

class ToolResult(TypedDict):
    call_id: str
    name: str
    output: str
    error: str | None

class AgentState(TypedDict):
    # 消息历史（自动合并 add_messages reducer）
    messages: Annotated[Sequence[BaseMessage], add_messages]

    # 会话标识
    user_id: str
    session_id: str

    # 意图分类
    intent: str                    # "knowledge" | "chitchat" | "tool_use" | "complex"
    needs_rag: bool

    # RAG 上下文
    rag_context: list[str]         # 检索到的文档片段
    rag_sources: list[dict]        # 来源信息

    # 工具调用
    tool_calls: list[ToolCall]
    tool_results: list[ToolResult]
    tool_call_count: int           # 防止无限循环

    # 记忆
    short_term_memories: list[dict]
    long_term_memories: list[dict]

    # 控制
    cancelled: bool
    error: str | None
    final_response: str
```

## 2.3 图结构

### 主图 (Main Graph)

```
                    ┌─────────┐
                    │ 入口节点 │
                    └────┬────┘
                         │
                    ┌────▼────┐
                    │意图分类  │
                    └────┬────┘
                         │
                    ┌────▼────┐
                    │条件路由  │
                    └─┬──┬──┬─┘
           ┌──────────┘  │  └──────────┐
           ▼              ▼              ▼
    ┌──────────┐   ┌──────────┐   ┌──────────┐
    │ RAG检索   │   │ 闲聊生成  │   │ 工具调用  │
    └─────┬─────┘   └─────┬────┘   └──────────┘
          │               │
    ┌─────▼─────┐   ┌─────▼─────┐
    │RAG 生成    │   │ 最终回答  │
    └─────┬─────┘   └─────┬────┘
          │               │
          └───────┬───────┘
                  ▼
           ┌──────────┐
           │ 记忆写入  │
           └─────┬────┘
                 ▼
           ┌──────────┐
           │   结束    │
           └──────────┘
```

### 工具调用子图 (Tool Subgraph / ReAct Loop)

```
    ┌───────────┐
    │ 推理节点   │ ← (LLM 决定是否需要工具)
    └─────┬─────┘
          │
    ┌─────▼─────┐
    │ 条件判断   │
    └──┬────┬───┘
       │    │
  无工具  │   有工具
       │    │
       ▼    ▼
  ┌──────┐ ┌──────────┐
  │ 退出  │ │ 工具执行   │
  └──────┘ │(MCP/原生)  │
           └─────┬─────┘
                 │
           ┌─────▼─────┐
           │ 结果处理   │ ──────┐
           └───────────┘       │
                 ▲             │
                 └─────────────┘ (循环回推理节点，最多 10 次)
```

## 2.4 节点详细说明

### 2.4.1 入口节点 (entry_node)

```
职责：
- 从长期记忆检索相关记忆
- 加载短期记忆
- 构建初始消息列表
- 注入系统提示词

输入: 用户消息
输出: 包含 full_context 的 state
```

### 2.4.2 意图分类节点 (intent_classifier)

```
职责：
- 调用 LLM 对用户意图进行分类
- 判断是否需要 RAG 检索

分类类别：
  - "knowledge": 需要从知识库检索 (needs_rag = True)
  - "chitchat": 闲聊，不需 RAG 也不需工具
  - "tool_use": 需要调用外部工具
  - "complex": 复杂多步推理 (可能 RAG + 工具)

Prompt 模板要点：
  - 明确指示判断标准
  - 优先判断是否涉及知识库内容
  - 输出 JSON: { "intent": "...", "reason": "..." }
```

### 2.4.3 条件路由节点 (router)

```python
def route_condition(state: AgentState) -> str:
    if state.get("cancelled"):
        return END
    if state["intent"] == "knowledge":
        return "rag_retrieve"
    elif state["intent"] == "tool_use":
        return "react_loop"
    elif state["intent"] == "complex":
        return "rag_retrieve"  # 先检索
    else:
        return "generate_response"  # 直接回答
```

### 2.4.4 RAG 检索节点 (rag_retrieve)

```
职责：
- 将用户问题向量化
- 在 Milvus/ChromaDB 中检索 top-k 相似文档
- (可选) BM25 关键词搜索补充
- 将检索结果写入 state.rag_context

参数：
  - top_k: 5 (向量检索)
  - top_k_bm25: 3 (关键词检索)
  - rerank_top: 3 (最终返回数)
```

### 2.4.5 ReAct 循环节点 (react_loop)

```
职责：
- 实现 ReAct (Reasoning + Acting) 模式
- LLM 推理 → 决定是否使用工具 → 执行工具 → 观察结果 → 循环
- 最大循环次数: 10
- 工具来源: MCP 服务器 + 原生工具
- 支持同时调用多个不同类型工具（已移除工具调用数量限制）

工具列表构建：
  1. 从已注册的原生工具获取
  2. 从启用的 MCP 服务器获取（服务器启用时自动加载）
  3. 根据用户选择过滤

工具调用执行：
  - 移除了单次只能调用一个工具的限制
  - LLM 返回多个工具调用时，按顺序依次执行
  - 每个工具调用结果作为独立的 ToolMessage 追加到消息历史
  - 最终由 LLM 汇总所有工具结果生成回答
```

### 2.4.6 响应生成节点 (generate_response)

```
职责：
- 构建最终 prompt (含 system prompt + 上下文 + 对话历史)
- 调用 LLM 生成回答
- 流式输出 token
- 处理取消信号

输入上下文优先级：
  1. 系统指令
  2. 相关长期记忆
  3. 短期记忆（最近对话）
  4. RAG 检索结果（如果 needs_rag）
  5. 工具调用结果（如果有）
  6. 用户当前问题
```

## 2.5 取消机制

```python
# 通过 checkpointer 中断实现
# 前端发送取消请求 → API 设置 cancel flag → 图检查点检测 → 停止生成

class CancelManager:
    _cancelled: dict[str, bool] = {}

    @classmethod
    def cancel(cls, session_id: str):
        cls._cancelled[session_id] = True

    @classmethod
    def is_cancelled(cls, session_id: str) -> bool:
        return cls._cancelled.get(session_id, False)

    @classmethod
    def reset(cls, session_id: str):
        cls._cancelled.pop(session_id, None)
```

## 2.6 提示词管理

### 系统提示词结构

```
You are 桌面的 AI 助手，具备以下能力：
1. 基于知识库回答问题
2. 使用工具完成复杂任务
3. 记住对话上下文

## 当前上下文
{memory_context}

## 知识库检索结果
{rag_context}

## 工具调用结果
{tool_context}

## 对话规则
- 回答简洁准确
- 不确定时主动说明
- 使用工具前告知用户正在执行的操作
```

### 意图分类提示词

```
分析以下用户消息，判断其意图类别。
仅返回 JSON，不要其他内容。

类别说明：
- knowledge: 询问知识库相关内容（公司政策、文档信息等）
- chitchat: 日常聊天、问候、简单问答
- tool_use: 需要外部工具完成（文件操作、搜索、计算等）
- complex: 需要多步推理、工具+RAG 组合

用户消息: {user_message}

返回格式: {{"intent": "...", "reason": "..."}}
```

## 2.7 图编译配置

```python
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver

def build_graph():
    builder = StateGraph(AgentState)

    # 添加节点
    builder.add_node("entry", entry_node)
    builder.add_node("intent_classifier", intent_classifier)
    builder.add_node("rag_retrieve", rag_retrieve)
    builder.add_node("generate_response", generate_response)
    builder.add_node("react_loop", react_subgraph)
    builder.add_node("write_memory", write_memory)

    # 设置入口
    builder.set_entry_point("entry")

    # 添加边
    builder.add_edge("entry", "intent_classifier")
    builder.add_conditional_edges("intent_classifier", route_condition)

    # 各分支最终汇聚到 write_memory
    builder.add_edge("generate_response", "write_memory")
    builder.add_edge("write_memory", END)

    # 编译
    return builder.compile(checkpointer=MemorySaver())
```

## 2.8 实现文件清单

| 文件 | 职责 |
|------|------|
| `src/agent/state.py` | AgentState 类型定义 |
| `src/agent/graph.py` | 主图构建与编译 |
| `src/agent/nodes/intent.py` | 意图分类节点 |
| `src/agent/nodes/rag.py` | RAG 检索节点 |
| `src/agent/nodes/tool_call.py` | 工具调用与 ReAct |
| `src/agent/nodes/response.py` | 响应生成（含流式） |
| `src/agent/nodes/memory.py` | 记忆读写节点 |
| `src/agent/nodes/cancel.py` | 取消管理 |
| `src/agent/router.py` | 条件路由 |
| `src/agent/prompts/` | YAML 提示词模板 |
