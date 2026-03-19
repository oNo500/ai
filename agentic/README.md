# AI Agent Service

基于 LangGraph 的生产级 AI Agent 服务，支持 ReAct 循环、Reflection、RAG、多 Agent 编排、Human-in-the-Loop 和 Guardrails。

## 技术栈

| 层次 | 技术 |
|------|------|
| Web 框架 | FastAPI + uvicorn |
| Agent 编排 | LangGraph + LangChain |
| LLM | langchain-openai（GPT-4o-mini） |
| 长期记忆 | Mem0（可切换 qdrant 持久化） |
| 向量检索 | pgvector + langchain-postgres |
| 短期记忆 | LangGraph InMemory checkpointer |
| 缓存 / 限流 | Redis |
| 可观测性 | LangSmith（环境变量接入） |
| MCP | fastmcp |
| 文档 | Scalar |
| 代码质量 | Ruff + pytest |

## 快速开始

```bash
# 1. 安装依赖
uv sync

# 2. 配置环境变量
cp .env.example .env
# 必填：OPENAI_API_KEY

# 3. 启动基础设施（Redis + pgvector）
docker compose up -d

# 4. 启动服务
uv run uvicorn app.main:app --reload
```

访问 `http://localhost:8000/docs` 查看 Scalar API 文档。

## 环境变量

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `OPENAI_API_KEY` | — | 必填 |
| `OPENAI_MODEL` | `gpt-4o-mini` | LLM 模型 |
| `REDIS_URL` | `redis://localhost:6379/0` | Redis 连接 |
| `POSTGRES_URL` | `postgresql+psycopg://postgres:postgres@localhost:5432/agentic` | pgvector |
| `RAG_COLLECTION` | `rag_documents` | 向量集合名 |
| `LANGSMITH_TRACING` | `false` | 开启 LangSmith |
| `LANGSMITH_API_KEY` | — | LangSmith Key |
| `LANGSMITH_PROJECT` | `default` | LangSmith 项目 |
| `MEM0_VECTOR_STORE_PROVIDER` | `memory` | `memory` \| `qdrant` |
| `RATE_LIMIT_REQUESTS` | `60` | 每用户每分钟请求数 |

## API 接口

### Agent

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/invoke` | 同步调用，返回完整响应 |
| POST | `/stream` | SSE 流式输出 |
| POST | `/orchestrate` | 指定 Agent 执行任务 |

### Agent 注册

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/agents` | 列出所有注册 Agent |
| POST | `/agents` | 动态注册新 Agent |

### Human-in-the-Loop

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/sessions/{thread_id}/pending` | 查询待审批 tool call |
| POST | `/sessions/{thread_id}/approve` | 审批并恢复执行 |

### RAG

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/rag/ingest` | 写入文档到向量库 |

### 其他

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/health` | 健康检查 |
| GET | `/docs` | Scalar API 文档 |

## 使用示例

```bash
# 同步调用
curl -X POST http://localhost:8000/invoke \
  -H "Content-Type: application/json" \
  -d '{"message": "What time is it?", "user_id": "alice"}'

# 流式调用
curl -X POST http://localhost:8000/stream \
  -H "Content-Type: application/json" \
  -d '{"message": "Explain LangGraph", "session_id": "s-1"}' --no-buffer

# 写入 RAG 文档
curl -X POST http://localhost:8000/rag/ingest \
  -H "Content-Type: application/json" \
  -d '{"texts": ["LangGraph is a library for building stateful multi-actor applications."]}'

# 注册 worker Agent
curl -X POST http://localhost:8000/agents \
  -H "Content-Type: application/json" \
  -d '{"name": "researcher", "system_prompt": "You are a research expert.", "role": "worker"}'

# 多 Agent 编排
curl -X POST http://localhost:8000/orchestrate \
  -H "Content-Type: application/json" \
  -d '{"task": "Research AI trends", "agent_name": "researcher"}'
```

## AgentSpec 配置

```python
from app.agent.spec import AgentSpec
from app.agent.registry import global_registry

spec = AgentSpec(
    name="my-agent",
    system_prompt="You are a helpful assistant.",
    model_name="gpt-4o",           # 覆盖默认模型
    temperature=0.7,
    enable_long_term_memory=True,  # 接入 Mem0
    enable_reflection=True,        # self-critique 循环
    max_reflections=2,
    enable_guardrails=True,        # 内容安全检查
    enable_human_loop=True,        # tool 执行前人工审批
    role="worker",                 # "worker" | "orchestrator"
)

global_registry.register("my-agent", spec)
```

## 项目结构

```
src/app/
├── main.py                  # FastAPI 入口 + lifespan + request_id middleware
├── settings.py              # 配置（pydantic-settings）
├── logging.py               # BoundLogger（结构化日志）
├── agent/
│   ├── spec.py              # AgentSpec 配置模型
│   ├── state.py             # AgentState TypedDict
│   ├── factory.py           # create_production_agent 工厂
│   ├── registry.py          # AgentRegistry + global_registry
│   ├── graph.py             # LangGraph ReAct 图构建
│   ├── nodes.py             # call_model / should_continue
│   ├── memory.py            # MemoryManager + LongTermMemory（Mem0）
│   ├── reflection.py        # Reflection 节点（self-critique）
│   ├── guardrails.py        # Guardrails 节点（安全检查）
│   ├── schemas.py           # 请求/响应 schema
│   └── tools/
│       ├── base.py          # ToolRegistry
│       ├── builtin.py       # get_current_time
│       ├── rag.py           # VectorStore + rag_search tool
│       └── subagent.py      # SubAgentTool + make_subagent_tool
├── api/
│   └── routes.py            # 所有路由
└── middleware/
    └── ratelimit.py         # Redis 滑动窗口限流

tests/                       # 120 个测试，TDD 全覆盖
mcp_server.py                # MCP Server（stdio transport）
docker-compose.yml           # Redis + pgvector
ROADMAP.md                   # 实现路线图
```

## 常用命令

```bash
uv run uvicorn app.main:app --reload   # 启动开发服务器
uv run pytest                           # 运行测试（120 个）
uv run ruff check .                     # Lint
uv run ruff format .                    # 格式化
docker compose up -d                    # 启动 Redis + pgvector
docker compose down                     # 停止
```

## MCP Server

```bash
uv run python mcp_server.py
```

以 stdio transport 启动，可接入 Claude Desktop 或其他 MCP host。
