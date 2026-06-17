# 09 — 评估与可观测性规格

## 9.1 概述

评估体系覆盖三个维度：**基准测试**（RAGAS 评估检索和生成质量）、**LLMOps 可观测性**（LangFuse/OpenTelemetry 链路追踪 + Prometheus 指标）、**Docker 沙箱**（安全隔离工具执行）。三管齐下确保系统质量。

## 9.2 评估架构

```
┌──────────────────────────────────────────────────┐
│                  评估体系                          │
│                                                   │
│  ┌─────────────────┐  ┌──────────────────────┐   │
│  │ 基准测试 (RAGAS) │  │ 可观测性 (LangFuse)   │   │
│  │                 │  │                      │   │
│  │ ● 检索质量      │  │ ● 链路追踪            │   │
│  │   - Recall@k   │  │ ● 延迟监控            │   │
│  │   - MRR        │  │ ● Token 用量          │   │
│  │   - NDCG       │  │ ● 工具调用追踪         │   │
│  │                 │  │ ● LLM 调用日志        │   │
│  │ ● 生成质量      │  │                      │   │
│  │   - Faithfulness│  │ 集成:                │   │
│  │   - Relevance  │  │ OpenTelemetry SDK     │   │
│  │   - Correctness│  │ Prometheus Exporter    │   │
│  │                 │  └──────────────────────┘   │
│  └─────────────────┘                            │
│                                                   │
│  ┌──────────────────────────────────────────┐    │
│  │ Docker 沙箱                                │    │
│  │ ● 工具调用隔离执行                         │    │
│  │ ● 资源限制 (CPU/Mem)                       │    │
│  │ ● 文件系统隔离                              │    │
│  │ ● 执行超时控制                              │    │
│  └──────────────────────────────────────────┘    │
└──────────────────────────────────────────────────┘
```

## 9.3 RAGAS 基准测试

### 9.3.1 测试数据集构建

```python
# src/eval/test_dataset.py
RAG_TEST_QUESTIONS = [
    {
        "question": "什么是 RAG？",
        "ground_truth": "RAG（检索增强生成）是一种结合信息检索与文本生成的 AI 技术架构...",
        "relevant_chunks": ["chunk_001", "chunk_003"],
        "knowledge_base": "kb_default"
    },
    # ... 至少 20 条测试用例
]
```

### 9.3.2 评估指标

| 指标 | 公式/说明 | 目标值 |
|------|-----------|--------|
| **Context Recall** | 检索到的相关文档 / 所有相关文档 | > 0.85 |
| **Context Precision** | 检索内容中相关比例 | > 0.80 |
| **Faithfulness** | 回答中可验证事实的比例 | > 0.90 |
| **Answer Relevance** | 回答与问题的语义相关性 | > 0.85 |
| **Answer Correctness** | 与 ground truth 的准确性 | > 0.80 |
| **MRR** | Mean Reciprocal Rank | > 0.80 |
| **NDCG@5** | Normalized Discounted Cumulative Gain | > 0.80 |

### 9.3.3 RAGAS 评估实现

```python
# src/eval/ragas_eval.py
from ragas import evaluate
from ragas.metrics import (
    faithfulness,
    answer_relevancy,
    context_recall,
    context_precision,
    answer_correctness,
)
from datasets import Dataset

class RAGASEvaluator:
    def __init__(self, llm, embeddings):
        self.metrics = [
            faithfulness,
            answer_relevancy,
            context_recall,
            context_precision,
            answer_correctness,
        ]

    async def evaluate(self, test_cases: list[dict]) -> dict:
        dataset = Dataset.from_list(test_cases)
        result = evaluate(
            dataset=dataset,
            metrics=self.metrics,
            llm=self.llm,
            embeddings=self.embeddings,
        )
        return {
            "faithfulness": float(result["faithfulness"]),
            "answer_relevancy": float(result["answer_relevancy"]),
            "context_recall": float(result["context_recall"]),
            "context_precision": float(result["context_precision"]),
            "answer_correctness": result.get("answer_correctness", 0),
        }
```

### 9.3.4 自定义 Benchmark

```python
# src/eval/benchmark.py
class CustomBenchmark:
    """自定义评估：记忆保持率、工具调用准确率"""

    async def memory_retention_test(self) -> dict:
        """
        测试记忆保持：
        1. 对话 1: 用户告知个人信息
        2. 对话 2（新会话）: 询问之前告知的信息
        3. 检查 Agent 是否能回忆
        """
        pass

    async def tool_call_accuracy_test(self) -> dict:
        """
        测试工具调用准确率：
        1. 发送需要工具的请求
        2. 检查是否调用了正确的工具
        3. 检查参数是否正确
        """
        pass

    async def rag_conditional_test(self) -> dict:
        """
        测试条件 RAG 路由：
        1. 发送知识库相关问题 → 应触发 RAG
        2. 发送闲聊问题 → 不应触发 RAG
        3. 检查回答中是否包含/不包含 RAG 上下文
        """
        pass

    async def run_all(self) -> dict:
        return {
            "memory_retention": await self.memory_retention_test(),
            "tool_call_accuracy": await self.tool_call_accuracy_test(),
            "rag_conditional": await self.rag_conditional_test(),
        }
```

## 9.4 LLMOps 可观测性

### 9.4.1 追踪维度

| 维度 | 采集内容 | 工具 |
|------|----------|------|
| LLM 调用 | 延迟、Token 数、模型、成本 | LangFuse / OpenTelemetry |
| 工具调用 | 工具名、参数、结果、耗时、状态 | LangFuse Span |
| RAG 检索 | 查询、检索结果、分数、延迟 | LangFuse Span |
| 对话会话 | 用户 ID、会话 ID、消息数 | Custom Span |
| 错误 | 类型、消息、堆栈 | Sentry / LangFuse |

### 9.4.2 LangFuse 集成

```python
# src/observability/langfuse_integration.py
from langfuse import Langfuse
from langfuse.callback import CallbackHandler

langfuse_handler = CallbackHandler(
    secret_key=os.getenv("LANGFUSE_SECRET_KEY"),
    public_key=os.getenv("LANGFUSE_PUBLIC_KEY"),
    host=os.getenv("LANGFUSE_HOST", "http://localhost:3000"),
)

# 在 LangGraph 编译时注入
graph = builder.compile(
    checkpointer=MemorySaver(),
)

# 调用时传入 callbacks
result = await graph.ainvoke(
    state,
    config={"callbacks": [langfuse_handler]}
)
```

### 9.4.3 Prometheus 指标

```python
# src/observability/metrics.py
from prometheus_client import Counter, Histogram, Gauge, generate_latest

# 请求计数
chat_requests_total = Counter(
    "chat_requests_total", "Total chat requests",
    ["intent", "status"]
)

# 延迟直方图
chat_latency_seconds = Histogram(
    "chat_latency_seconds", "Chat response latency",
    ["stage"]  # total / intent_classify / rag_retrieve / llm_generate / tool_call
)

# Token 计数
tokens_consumed_total = Counter(
    "tokens_consumed_total", "Total tokens consumed",
    ["model", "type"]  # input / output
)

# 工具调用
tool_calls_total = Counter(
    "tool_calls_total", "Total tool calls",
    ["tool_name", "status"]
)

# RAG 检索
rag_retrieval_size = Histogram(
    "rag_retrieval_size", "RAG retrieval result count"
)

# 活跃会话
active_sessions = Gauge(
    "active_sessions", "Number of active sessions"
)

# 记忆
memory_operations_total = Counter(
    "memory_operations_total", "Memory operations",
    ["memory_type", "operation"]  # short_term/long_term, read/write
)
```

### 9.4.4 链路追踪 Span 设计

```
chat_request (root span)
├── intent_classification
│   └── llm_call (deepseek, 200ms, 50 tokens)
├── memory_load
│   ├── short_term_load (redis, 5ms)
│   └── long_term_search (postgres+vector, 30ms)
├── [conditional] rag_retrieve
│   ├── query_embedding (deepseek-embed, 50ms)
│   ├── vector_search (milvus, 15ms)
│   ├── bm25_search (10ms)
│   └── rerank (cross-encoder, 100ms)
├── [conditional] tool_call_loop
│   ├── llm_reasoning (deepseek, 300ms)
│   ├── tool_execution (mcp: search_web, 1200ms)
│   └── llm_reasoning2 (deepseek, 200ms)
├── response_generation
│   └── llm_stream (deepseek, 2000ms, 500 tokens)
└── memory_write
    ├── short_term_write (redis, 3ms)
    └── [session_end] long_term_summarize + store (deepseek + pg, 500ms)
```

## 9.5 Docker 沙箱

### 9.5.1 沙箱设计

```python
# src/sandbox/executor.py
import docker
from docker.types import Mount

class SandboxExecutor:
    """在 Docker 容器中安全执行工具命令"""

    def __init__(self):
        self.client = docker.from_env()
        self.image = "python:3.12-slim"
        self.timeout = 30  # 秒

    async def execute(self, command: str, workdir: str = "/workspace") -> dict:
        container = self.client.containers.run(
            image=self.image,
            command=["bash", "-c", command],
            working_dir=workdir,
            detach=True,
            mem_limit="256m",
            cpu_shares=512,
            network_mode="none",  # 无网络
            read_only=True,
            mounts=[
                Mount(
                    target="/workspace",
                    source="cs599-sandbox-data",
                    type="volume",
                    read_only=False
                )
            ],
            security_opt=["no-new-privileges:true"],
        )

        try:
            result = container.wait(timeout=self.timeout)
            logs = container.logs(stdout=True, stderr=True).decode()
            return {
                "exit_code": result["StatusCode"],
                "output": logs,
                "error": None,
            }
        except Exception as e:
            return {
                "exit_code": -1,
                "output": "",
                "error": str(e),
            }
        finally:
            container.remove(force=True)
```

### 9.5.2 沙箱安全策略

| 策略 | 配置 |
|------|------|
| 无网络访问 | `network_mode: "none"` |
| 只读文件系统 | `read_only: True` |
| 内存限制 | `mem_limit: 256m` |
| CPU 限制 | `cpu_shares: 512` |
| 禁止特权提升 | `no-new-privileges: true` |
| 执行超时 | 30 秒 |
| 卷挂载隔离 | 仅挂载 sandbox 专用卷 |

## 9.6 Grafana Dashboard

### 9.6.1 预置面板

```json
{
  "dashboard": {
    "title": "CS599 Agent 监控",
    "panels": [
      {
        "title": "请求延迟 (P50/P95/P99)",
        "type": "graph",
        "targets": [
          { "expr": "histogram_quantile(0.50, rate(chat_latency_seconds_bucket[5m]))" },
          { "expr": "histogram_quantile(0.95, rate(chat_latency_seconds_bucket[5m]))" },
          { "expr": "histogram_quantile(0.99, rate(chat_latency_seconds_bucket[5m]))" }
        ]
      },
      {
        "title": "请求量 (按意图)",
        "type": "graph",
        "targets": [
          { "expr": "rate(chat_requests_total[5m])" }
        ]
      },
      {
        "title": "Token 消耗",
        "type": "graph",
        "targets": [
          { "expr": "rate(tokens_consumed_total[5m])" }
        ]
      },
      {
        "title": "工具调用成功率",
        "type": "stat",
        "targets": [
          { "expr": "sum(rate(tool_calls_total{status='success'}[5m])) / sum(rate(tool_calls_total[5m]))" }
        ]
      },
      {
        "title": "RAG 检索延迟",
        "type": "graph",
        "targets": [
          { "expr": "histogram_quantile(0.95, rate(chat_latency_seconds_bucket{stage='rag_retrieve'}[5m]))" }
        ]
      },
      {
        "title": "活跃会话数",
        "type": "gauge",
        "targets": [
          { "expr": "active_sessions" }
        ]
      }
    ]
  }
}
```

## 9.7 评估 CLI

```bash
# 运行完整评估套件
python -m src.eval.run --suite all

# 运行特定评估
python -m src.eval.run --suite ragas       # RAGAS 基准
python -m src.eval.run --suite benchmark   # 自定义基准
python -m src.eval.run --suite latency     # 延迟压测

# 输出报告
python -m src.eval.run --suite all --output docs/eval_report.json
```

## 9.8 实现文件清单

| 文件 | 职责 |
|------|------|
| `src/eval/__init__.py` | 模块导出 |
| `src/eval/ragas_eval.py` | RAGAS 评估器 |
| `src/eval/benchmark.py` | 自定义基准测试 |
| `src/eval/test_dataset.py` | 测试数据集 |
| `src/eval/run.py` | 评估 CLI |
| `src/observability/__init__.py` | 模块导出 |
| `src/observability/metrics.py` | Prometheus 指标 |
| `src/observability/tracing.py` | LangFuse/OTEL 追踪 |
| `src/observability/langfuse_integration.py` | LangFuse 回调 |
| `src/sandbox/executor.py` | Docker 沙箱执行器 |
| `docker/config/grafana-dashboards/agent.json` | Grafana 面板 |
