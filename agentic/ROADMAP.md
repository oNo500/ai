# AI Agent 工程路线图 2026

## 1. 核心概念

AI Agent = LLM + Tools + Memory + Planning

- **LLM**：推理引擎，负责决策
- **Tools**：外部能力扩展（搜索、代码执行、数据库查询等）
- **Memory**：短期（对话上下文）+ 长期（跨 session 记忆）
- **Planning**：任务分解、ReAct 循环、多步推理

## 2. 自主性谱系

| Level | 描述 | 本项目状态 |
|-------|------|-----------|
| 0 | 单次 LLM 调用 | - |
| 1 | LLM + Tools（ReAct 循环） | **当前** |
| 2 | 多步 Planning + 自我纠错 | Phase 2 目标 |
| 3 | 多 Agent 协作 | Phase 3 目标 |
| 4 | 完全自主（Human-in-the-Loop 可选） | Phase 4 目标 |

## 3. 上下文工程

上下文工程是决定 Agent 质量的核心：如何在有限 token 窗口内放入最有价值的信息。

| 层次 | 技术 | 本项目状态 |
|------|------|-----------|
| System Prompt | `AgentSpec.system_prompt` | Phase 1 已实现 |
| 短期记忆 | LangGraph checkpointer（InMemory） | 已实现 |
| 长期记忆 | Mem0（`enable_long_term_memory`） | Phase 1 接线完成（ainvoke）；astream 补接 Phase 2 |
| RAG 检索 | 向量数据库 + 语义搜索 | Phase 2 规划中 |

## 4. 四大核心设计模式

| 模式 | 描述 | 本项目状态 |
|------|------|-----------|
| Tool Use | ReAct 循环调用外部工具 | 已实现 |
| Reflection | 自我评估 + 输出修正 | Phase 2 已实现 |
| Planning | 任务分解为子步骤 | Phase 3 规划中 |
| Multi-Agent | 多 Agent 协作分工 | Phase 3 规划中 |

## 5. 多 Agent 编排架构（规划方向）

```
Orchestrator Agent
├── SubAgent A (专注研究)
├── SubAgent B (专注代码生成)
└── SubAgent C (专注数据分析)
```

实现路径：`AgentRegistry.register(name, spec)` → `make_subagent_tool(name)` 将 Agent 封装为 LangChain Tool。

## 6. 任务分解策略（规划方向）

- **Sequential**：线性步骤链
- **Parallel**：并发独立子任务
- **Hierarchical**：树形任务分解
- **Dynamic**：运行时根据结果动态调整

## 7. 项目实现路线

### Phase 0 — 骨架（已完成）

- AgentSpec 工厂模式
- ToolRegistry（内置工具注册）
- FastAPI Lifespan（应用生命周期管理）
- Mem0 长期记忆骨架
- LangGraph ReAct 图

### Phase 1 — Bug 修复 + 接线（已完成）

- [x] 删除 `nodes.py` 无用 `call_model()` 函数
- [x] 修复 `/stream` astream 解包 Bug（yield tuple 统一格式）
- [x] `AgentSpec.system_prompt` 真正注入（`ainvoke`/`astream` 前 prepend SystemMessage）
- [x] `AgentSpec.enable_long_term_memory` 字段 + factory 传递给 MemoryManager
- [x] `InvokeRequest.user_id` 字段 + routes 传递给 agent（Mem0 用户隔离）
- [x] `astream` 长期记忆接入（`inject_long_term_context`）→ Phase 2 已完成

### Phase 2 — 基础设施补全（本次）

- [x] **LangSmith 可观测性**：环境变量接入，`LANGCHAIN_TRACING_V2` lifespan 设置（参考项目 Day 1 对齐）
- [x] **AgentState 扩展**：增加 `user_id`/`session_id` 字段（有默认值，不破坏现有图）
- [x] **astream 接入长期记忆**：补全 `inject_long_term_context` 调用，与 ainvoke 路径对称
- [x] Reflection 节点：self-critique 自我评估循环（`enable_reflection` + `max_reflections`）
- [x] RAG 工具：向量检索（pgvector + Docker，`rag_search` tool + `POST /rag/ingest`）
- [x] 长期记忆持久化后端（Mem0 config 化，`mem0_vector_store_provider` 切换 memory/qdrant）

### Phase 3 — 多 Agent（规划中）

#### 3A. AgentRegistry 重构
- [x] `AgentRegistry` 类：`register(name, spec)`、`get(name)`、`all()`
- [x] `get_default_agent()` 迁移为 registry 的默认注册项
- [x] `POST /agents` 动态注册、`GET /agents` 列出所有 Agent

#### 3B. SubAgent Tool
- [x] `make_subagent_tool(name)`：将注册 Agent 封装为 LangChain Tool
- [x] Tool name = agent name，description = spec.system_prompt 摘要
- [x] 异步调用，透传 `user_id`/`thread_id`

#### 3C. Orchestrator 模式
- [x] `AgentSpec.role: "orchestrator" | "worker"`（默认 `worker`）
- [x] Orchestrator 的 tools 自动包含所有 worker subagent tools（`registry.get_worker_tools()`）
- [x] `POST /orchestrate` endpoint：接收任务，由指定 Agent 调度

### Phase 4 — 生产就绪（规划中）

#### 4A. Human-in-the-Loop
- [x] `AgentSpec.enable_human_loop` 真正实现：LangGraph `interrupt_before=["tools"]`
- [x] `POST /sessions/{thread_id}/approve` endpoint：恢复被中断的执行
- [x] `GET /sessions/{thread_id}/pending` endpoint：查询待审批的 tool call

#### 4B. Guardrails
- [x] `agent/guardrails.py`：输入校验（长度限制）+ LLM 安全判断节点
- [x] `AgentSpec.enable_guardrails` 接入图（terminal 节点）
- [x] 输出 `blocked: bool` + `block_reason: str` 写入 AgentState

#### 4C. 结构化日志
- [x] 每个请求生成 `request_id`（UUID），HTTP middleware 注入响应头
- [x] `BoundLogger`（`app/logging.py`），支持 `bind(request_id=, user_id=)` 链式绑定
- [ ] LangSmith trace 携带 `request_id` 作为 metadata

#### 4D. 速率限制 + 成本控制
- [x] Redis 滑动窗口限流（`user_id` 维度），`rate_limit_requests/window_seconds` 配置
- [x] 超限返回 `429 Too Many Requests`
- [ ] Token 用量统计（从 LangChain callback 获取），写入 Redis 计数器

## 架构原则

- **Python 管 AI，不管业务**：Python 端只负责推理，结果打包返回给 NestJS/NextJS 等业务服务
- **无状态优先**：Agent 本身无状态，状态外置到 Redis / PostgreSQL
- **AI/LLM First**：优先用 LLM 解决问题，工具辅助
- **可观测性**：每个推理步骤可追踪、可调试
