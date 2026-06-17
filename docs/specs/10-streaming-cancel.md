# 10 — 流式输出与取消机制规格

## 10.1 概述

流式输出 (Streaming) 是用户体验的核心——用户发送消息后即时看到 token 逐字渲染。同时提供取消机制，允许用户随时终止生成。对于无法流式输出的阶段（工具调用、RAG 检索），显示进度动画避免用户感知卡顿。

## 10.2 流式输出架构

```
┌──────────┐     SSE Stream      ┌──────────────┐
│  FastAPI  │ ──────────────────→ │  React 前端    │
│  Backend  │   event: token      │              │
│           │   event: tool_start  │  StreamingText
│           │   event: tool_end    │  ToolCallCard
│           │   event: done        │  CancelButton
└──────────┘                      └──────────────┘
```

## 10.3 流式事件类型

### 10.3.1 完整事件协议

```typescript
// 前端事件类型定义
type SSEEvent =
  | { type: 'token'; data: { content: string; index: number } }
  | { type: 'thought'; data: { content: string } }
  | { type: 'tool_start'; data: { tool_name: string; args: Record<string, any>; call_id: string } }
  | { type: 'tool_progress'; data: { tool_name: string; call_id: string; message: string } }
  | { type: 'tool_end'; data: { tool_name: string; result: string; call_id: string; error?: string } }
  | { type: 'rag_sources'; data: { sources: Array<{ file: string; chunk: number; score: number }> } }
  | { type: 'intent'; data: { intent: string; needs_rag: boolean } }
  | { type: 'done'; data: { session_id: string; total_tokens: number; latency_ms: number } }
  | { type: 'error'; data: { code: number; message: string } }
  | { type: 'heartbeat'; data: {} }
  | { type: 'cancelled'; data: { session_id: string } };
```

### 10.3.2 流式输出不同阶段的动画策略

| 阶段 | 是否流式 | 动画策略 |
|------|----------|----------|
| 意图分类 | 否 (~200ms) | 无需动画（快速完成） |
| RAG 检索 | 否 (~300ms) | "正在检索知识库..." + 骨架屏 |
| 工具调用中 | 否 (~1-5s) | 工具调用脉冲动画 + 状态文字 |
| LLM 生成 | **是** (逐 token) | 逐字显现 + 光标闪烁 |
| 记忆写入 | 否 (~10ms) | 无需动画 |

## 10.4 后端流式实现

### 10.4.1 LangGraph 流式节点

```python
# src/agent/nodes/response.py
async def generate_response_stream(state: AgentState):
    """
    流式生成响应节点。
    通过 LangGraph 的 astream_events 实现逐 token 输出。
    """
    messages = build_messages(state)

    full_response = ""
    async for chunk in llm.astream(messages):
        if cancel_manager.is_cancelled(state["session_id"]):
            break

        content = chunk.content
        full_response += content

        # 产出 token 事件
        yield StreamEvent(
            event="token",
            data={"content": content, "index": len(full_response)}
        )

    return {"final_response": full_response}
```

### 10.4.2 主图流式包装

```python
# src/agent/graph.py
async def stream_graph(state: AgentState):
    """流式执行图，yield SSE 事件"""

    # 意图分类（非流式，yield 一次）
    state = await intent_classifier(state)
    yield format_sse("intent", {
        "intent": state["intent"],
        "needs_rag": state["needs_rag"]
    })

    # RAG 检索（如果需要，非流式但有进度通知）
    if state["needs_rag"]:
        yield format_sse("heartbeat", {"stage": "rag_retrieving"})
        state = await rag_retrieve(state)
        yield format_sse("rag_sources", {
            "sources": state.get("rag_sources", [])
        })

    # 工具调用循环（非流式，每个工具调用有进度更新）
    if state["intent"] in ("tool_use", "complex"):
        async for event in react_loop_stream(state):
            yield event
            if event["event"] == "tool_end":
                state = update_state(state, event)

    # 最终生成（流式输出）
    async for token_chunk in generate_response_stream(state):
        yield format_sse(token_chunk.event, token_chunk.data)

    # 完成
    yield format_sse("done", {
        "session_id": state["session_id"],
        "total_tokens": state.get("total_tokens", 0),
        "latency_ms": compute_latency(state)
    })
```

### 10.4.3 取消机制实现

```python
# src/agent/cancel.py
import asyncio
from collections import defaultdict

class CancelManager:
    """管理用户取消请求"""

    def __init__(self):
        self._signals: dict[str, asyncio.Event] = defaultdict(asyncio.Event)

    def cancel(self, session_id: str):
        """设置取消信号"""
        self._signals[session_id].set()

    def is_cancelled(self, session_id: str) -> bool:
        return self._signals[session_id].is_set()

    def reset(self, session_id: str):
        self._signals[session_id].clear()

    async def check_cancel(self, session_id: str):
        """在异步循环中检查取消"""
        if self.is_cancelled(session_id):
            raise GenerationCancelled(session_id)

    async def wait_with_cancel(self, session_id: str, coro):
        """带取消检查的协程包装"""
        task = asyncio.create_task(coro)
        done, pending = await asyncio.wait(
            [task, self._signals[session_id].wait()],
            return_when=asyncio.FIRST_COMPLETED
        )
        if self._signals[session_id].is_set():
            task.cancel()
            raise GenerationCancelled(session_id)
        return task.result()

class GenerationCancelled(Exception):
    def __init__(self, session_id: str):
        self.session_id = session_id
        super().__init__(f"Generation cancelled for session {session_id}")
```

## 10.5 前端流式接收

### 10.5.1 useSSE Hook

```typescript
// frontend/src/hooks/useSSE.ts
import { useState, useRef, useCallback } from 'react';

interface SSEState {
  tokens: string[];
  isStreaming: boolean;
  toolCalls: ToolCallState[];
  ragSources: Source[];
  intent: string | null;
  error: string | null;
}

export function useSSE() {
  const [state, setState] = useState<SSEState>({
    tokens: [],
    isStreaming: false,
    toolCalls: [],
    ragSources: [],
    intent: null,
    error: null,
  });

  const readerRef = useRef<ReadableStreamDefaultReader | null>(null);
  const abortRef = useRef<AbortController | null>(null);

  const startStream = useCallback(async (payload: ChatRequest) => {
    const controller = new AbortController();
    abortRef.current = controller;

    // 重置状态
    setState({
      tokens: [],
      isStreaming: true,
      toolCalls: [],
      ragSources: [],
      intent: null,
      error: null,
    });

    try {
      const response = await fetch('/api/v1/chat/stream', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
        signal: controller.signal,
      });

      const reader = response.body!.getReader();
      readerRef.current = reader;
      const decoder = new TextDecoder();
      let buffer = '';

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });

        // 解析 SSE 事件
        const lines = buffer.split('\n');
        buffer = lines.pop() || '';  // 保留未完成行

        for (let i = 0; i < lines.length; i++) {
          const line = lines[i];
          if (line.startsWith('event: ')) {
            const eventType = line.slice(7).trim();
            const dataLine = lines[i + 1];
            if (dataLine && dataLine.startsWith('data: ')) {
              const data = JSON.parse(dataLine.slice(6));
              handleEvent(eventType, data);
              i++;  // 跳过 data 行
            }
          }
        }
      }
    } catch (err: any) {
      if (err.name === 'AbortError') {
        setState(prev => ({ ...prev, isStreaming: false }));
      } else {
        setState(prev => ({
          ...prev,
          isStreaming: false,
          error: err.message,
        }));
      }
    }
  }, []);

  const handleEvent = useCallback((type: string, data: any) => {
    switch (type) {
      case 'token':
        setState(prev => ({
          ...prev,
          tokens: [...prev.tokens, data.content],
        }));
        break;
      case 'tool_start':
        setState(prev => ({
          ...prev,
          toolCalls: [...prev.toolCalls, {
            id: data.call_id,
            name: data.tool_name,
            status: 'running',
            args: data.args,
          }],
        }));
        break;
      case 'tool_end':
        setState(prev => ({
          ...prev,
          toolCalls: prev.toolCalls.map(tc =>
            tc.id === data.call_id
              ? { ...tc, status: data.error ? 'error' : 'success', result: data.result }
              : tc
          ),
        }));
        break;
      case 'rag_sources':
        setState(prev => ({ ...prev, ragSources: data.sources }));
        break;
      case 'intent':
        setState(prev => ({ ...prev, intent: data.intent }));
        break;
      case 'done':
        setState(prev => ({ ...prev, isStreaming: false }));
        break;
      case 'error':
        setState(prev => ({
          ...prev,
          isStreaming: false,
          error: data.message,
        }));
        break;
      case 'cancelled':
        setState(prev => ({ ...prev, isStreaming: false }));
        break;
    }
  }, []);

  const cancel = useCallback(async () => {
    abortRef.current?.abort();
    readerRef.current?.cancel();
    setState(prev => ({ ...prev, isStreaming: false }));
  }, []);

  return { ...state, startStream, cancel };
}
```

### 10.5.2 取消按钮

```typescript
// frontend/src/components/chat/CancelButton.tsx
function CancelButton({ onCancel, isStreaming }: Props) {
  return (
    <button
      onClick={onCancel}
      disabled={!isStreaming}
      className={`
        flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-sm font-medium
        transition-all duration-200
        ${isStreaming
          ? 'bg-red-600 hover:bg-red-700 text-white cursor-pointer'
          : 'bg-gray-800 text-gray-500 cursor-not-allowed'
        }
      `}
    >
      <StopIcon className="w-4 h-4" />
      {isStreaming ? '停止生成' : '生成中...'}
    </button>
  );
}
```

## 10.6 动画规格

### 10.6.1 工具调用动画

```typescript
// 工具调用状态对应的动画
const toolStatusConfig = {
  running: {
    icon: <Loader2 className="animate-spin text-blue-400" />,
    text: '正在执行',
    className: 'animate-pulse border-blue-500/50',
  },
  success: {
    icon: <CheckCircle className="text-green-400" />,
    text: '执行完成',
    className: 'border-green-500/30',
  },
  error: {
    icon: <XCircle className="text-red-400" />,
    text: '执行失败',
    className: 'border-red-500/30',
  },
};
```

### 10.6.2 流式文本动画

```css
/* 光标闪烁动画 */
@keyframes blink {
  0%, 100% { opacity: 1; }
  50% { opacity: 0; }
}

.cursor-blink::after {
  content: '▌';
  animation: blink 1s step-end infinite;
  color: #6366f1;
}

/* 新 token 淡入 */
.token-fade-in {
  animation: fadeInUp 0.15s ease-out;
}

@keyframes fadeInUp {
  from {
    opacity: 0;
    transform: translateY(2px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}
```

### 10.6.3 加载阶段动画

| 阶段 | 动画组件 | 描述 |
|------|----------|------|
| 思考中 | 三个点波浪 `...` | 意图分类 / 通用等待 |
| 检索中 | 骨架屏 + "检索知识库" | RAG 检索 |
| 工具调用 | 脉冲边框 + 旋转图标 | 工具执行 |
| 生成中 | 逐字 + 光标 | LLM 生成 |

```typescript
// 骨架屏组件
function ThinkingSkeleton({ message }: { message: string }) {
  return (
    <div className="flex items-center gap-3 p-4 bg-surface rounded-lg animate-pulse">
      <div className="flex gap-1">
        <span className="w-2 h-2 bg-primary-500 rounded-full animate-bounce" 
              style={{ animationDelay: '0ms' }} />
        <span className="w-2 h-2 bg-primary-500 rounded-full animate-bounce" 
              style={{ animationDelay: '150ms' }} />
        <span className="w-2 h-2 bg-primary-500 rounded-full animate-bounce" 
              style={{ animationDelay: '300ms' }} />
      </div>
      <span className="text-sm text-gray-400">{message}</span>
    </div>
  );
}
```

## 10.7 取消后的数据清理

```
用户点击取消
    │
    ├─→ [前端] AbortController.abort()
    │   └─→ SSE 连接断开
    │   └─→ 已接收的 token 保留在界面上
    │   └─→ 不完整的消息显示 "(已取消)" 标记
    │
    ├─→ [后端] CancelManager.cancel(session_id)
    │   └─→ LangGraph 节点检查取消信号
    │   └─→ 停止 LLM 生成
    │   └─→ 停止工具执行
    │   └─→ 不写入长期记忆
    │   └─→ 短期记忆中移除本轮不完整对话
    │
    └─→ [状态] session 保持，可继续发送新消息
```

## 10.8 Edge Cases 处理

| 场景 | 处理方式 |
|------|----------|
| 网络断开 | 前端检测 `EventSource` 错误 + 自动重连提示 |
| 后端崩溃 | SSE 连接关闭 + 前端显示"连接已断开，请重试" |
| LLM 超时 | 后端 60s 超时 → yield error 事件 → 前端显示超时错误 |
| 工具调用超时 | 沙箱 30s 超时 → 返回错误 → Agent 尝试替代方案 |
| 用户快速取消 | debounce 防抖，仅处理最后一次取消请求 |
| 取消后立即重发 | 正常处理，取消信号已 reset |
| 流式中断（token 不完整） | 前端拼接已接收的 token 并标记 |

## 10.9 性能优化

1. **Token 批量合并**: 前端 50ms 内累积的 token 批量渲染，避免每个 token 触发一次重渲染
2. **虚拟滚动**: 长对话使用虚拟列表，只渲染可视区域
3. **SSE 连接复用**: 同一会话复用 SSE 连接
4. **防抖滚动**: 自动滚动使用 `requestAnimationFrame` 防抖

```typescript
// Token 批量渲染优化
function useTokenBatcher(tokens: string[], interval = 50) {
  const [display, setDisplay] = useState('');

  useEffect(() => {
    let timer: ReturnType<typeof setTimeout>;
    timer = setTimeout(() => {
      setDisplay(tokens.join(''));
    }, interval);
    return () => clearTimeout(timer);
  }, [tokens.length, interval]);  // 仅在 token 数量变化时触发

  return display;
}
```

## 10.10 实现文件清单

| 文件 | 职责 |
|------|------|
| `src/agent/nodes/response.py` | 流式生成节点 |
| `src/agent/nodes/tool_call.py` | 工具调用流式包装 |
| `src/agent/cancel.py` | CancelManager |
| `src/api/chat.py` | SSE 接口实现 |
| `frontend/src/hooks/useSSE.ts` | 前端 SSE Hook |
| `frontend/src/components/chat/StreamingText.tsx` | 流式文本渲染 |
| `frontend/src/components/chat/ToolCallCard.tsx` | 工具调用卡片 |
| `frontend/src/components/chat/CancelButton.tsx` | 取消按钮 |
| `frontend/src/components/chat/ThinkingSkeleton.tsx` | 等待动画 |
| `frontend/src/styles/animations.css` | 动画样式 |
