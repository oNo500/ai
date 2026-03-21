import json
import uuid

from ag_ui.core import (
    EventType,
    RunAgentInput,
    RunErrorEvent,
    RunFinishedEvent,
    RunStartedEvent,
    TextMessageContentEvent,
    TextMessageEndEvent,
    TextMessageStartEvent,
    ToolCallArgsEvent,
    ToolCallEndEvent,
    ToolCallStartEvent,
)
from ag_ui.encoder import EventEncoder
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from src.agent.registry import get_default_agent, global_registry
from src.agent.schemas import InvokeRequest, InvokeResponse
from src.agent.spec import AgentSpec
from src.middleware.ratelimit import RateLimiter
from src.settings import get_settings

router = APIRouter()

_settings = get_settings()


async def check_rate_limit(request: Request, user_id: str) -> tuple[bool, int]:
    redis = getattr(request.app.state, "redis", None)
    if redis is None:
        return True, 0
    limiter = RateLimiter(
        redis=redis,
        max_requests=_settings.rate_limit_requests,
        window_seconds=_settings.rate_limit_window_seconds,
    )
    return await limiter.check(user_id)


class IngestRequest(BaseModel):
    texts: list[str]


class IngestResponse(BaseModel):
    ids: list[str]


class RegisterAgentRequest(BaseModel):
    name: str
    system_prompt: str | None = None
    temperature: float = 0.0
    model_name: str | None = None


class AgentInfo(BaseModel):
    name: str


class OrchestrateRequest(BaseModel):
    task: str
    agent_name: str = "default"
    session_id: str | None = None
    user_id: str = "default"


class ApproveRequest(BaseModel):
    agent_name: str = "default"
    user_id: str = "default"


class RejectRequest(BaseModel):
    agent_name: str = "default"
    user_id: str = "default"
    reason: str = "User rejected tool call"


@router.get("/health")
async def health():
    return {"status": "healthy"}


@router.post("/invoke", response_model=InvokeResponse)
async def invoke(request: InvokeRequest, req: Request):
    allowed, _ = await check_rate_limit(req, request.user_id)
    if not allowed:
        raise HTTPException(status_code=429, detail="Rate limit exceeded")
    from langchain_core.messages import HumanMessage
    agent = get_default_agent()
    result = await agent.ainvoke([HumanMessage(content=request.message)], user_id=request.user_id)
    content = result["messages"][-1].content
    return InvokeResponse(content=content)


@router.post("/stream")
async def stream(request: InvokeRequest):
    from langchain_core.messages import HumanMessage
    agent = get_default_agent()
    user_id = request.user_id
    lc_messages = [HumanMessage(content=request.message)]

    async def event_generator():
        async for chunk, _ in agent.astream(lc_messages, user_id=user_id):
            if hasattr(chunk, "content") and chunk.content:
                data = json.dumps({"type": "token", "content": chunk.content})
                yield f"data: {data}\n\n"
        yield f"data: {json.dumps({'type': 'done', 'content': ''})}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")


def _to_langchain_messages(messages: list) -> list:
    from langchain_core.messages import AIMessage, HumanMessage

    lc = []
    for m in messages:
        content = m.content if isinstance(m.content, str) else str(m.content)
        if m.role == "user":
            lc.append(HumanMessage(content=content))
        elif m.role == "assistant":
            lc.append(AIMessage(content=content))
    return lc


@router.post("/stream/agui")
async def stream_agui(request: RunAgentInput, req: Request):
    agent = get_default_agent()
    user_id = str(request.forwarded_props.get("user_id", "default")) if isinstance(request.forwarded_props, dict) else "default"
    run_id = request.run_id
    thread_id = request.thread_id
    lc_messages = _to_langchain_messages(request.messages or [])
    message_id = str(uuid.uuid4())
    encoder = EventEncoder(accept=req.headers.get("accept"))

    async def event_generator():
        yield encoder.encode(
            RunStartedEvent(type=EventType.RUN_STARTED, thread_id=thread_id, run_id=run_id)
        )
        yield encoder.encode(
            TextMessageStartEvent(
                type=EventType.TEXT_MESSAGE_START, message_id=message_id, role="assistant"
            )
        )

        try:
            async for chunk, _ in agent.astream(lc_messages, user_id=user_id):
                if hasattr(chunk, "content") and chunk.content:
                    yield encoder.encode(
                        TextMessageContentEvent(
                            type=EventType.TEXT_MESSAGE_CONTENT,
                            message_id=message_id,
                            delta=chunk.content,
                        )
                    )
                if hasattr(chunk, "tool_calls") and chunk.tool_calls:
                    for tc in chunk.tool_calls:
                        tc_id = tc.get("id") or str(uuid.uuid4())
                        yield encoder.encode(
                            ToolCallStartEvent(
                                type=EventType.TOOL_CALL_START,
                                tool_call_id=tc_id,
                                tool_call_name=tc.get("name", ""),
                                parent_message_id=message_id,
                            )
                        )
                        if tc.get("args"):
                            yield encoder.encode(
                                ToolCallArgsEvent(
                                    type=EventType.TOOL_CALL_ARGS,
                                    tool_call_id=tc_id,
                                    delta=json.dumps(tc["args"]),
                                )
                            )
                        yield encoder.encode(
                            ToolCallEndEvent(
                                type=EventType.TOOL_CALL_END, tool_call_id=tc_id
                            )
                        )
        except Exception as e:
            yield encoder.encode(RunErrorEvent(type=EventType.RUN_ERROR, message=str(e)))
            return

        yield encoder.encode(
            TextMessageEndEvent(type=EventType.TEXT_MESSAGE_END, message_id=message_id)
        )
        yield encoder.encode(
            RunFinishedEvent(type=EventType.RUN_FINISHED, thread_id=thread_id, run_id=run_id)
        )

    return StreamingResponse(event_generator(), media_type=encoder.get_content_type())


@router.post("/rag/ingest", response_model=IngestResponse)
async def ingest(request: IngestRequest, req: Request):
    vs = req.app.state.vector_store
    ids = await vs.ingest(request.texts)
    return IngestResponse(ids=ids)


@router.get("/agents")
async def list_agents():
    return {"agents": [{"name": n} for n in global_registry.names()]}


@router.post("/agents", response_model=AgentInfo)
async def register_agent(request: RegisterAgentRequest):
    spec = AgentSpec(
        name=request.name,
        system_prompt=request.system_prompt,
        temperature=request.temperature,
        model_name=request.model_name,
    )
    global_registry.register(request.name, spec)
    return AgentInfo(name=request.name)


@router.post("/orchestrate", response_model=InvokeResponse)
async def orchestrate(request: OrchestrateRequest):
    agent = global_registry.get(request.agent_name)
    thread_id = request.session_id or "orchestrate-anonymous"
    result = await agent.ainvoke(request.task, thread_id=thread_id, user_id=request.user_id)
    content = result["messages"][-1].content
    return InvokeResponse(content=content)


@router.get("/sessions/{thread_id}/pending")
async def get_pending(thread_id: str, agent_name: str = "default"):
    agent = global_registry.get(agent_name)
    config = {"configurable": {"thread_id": thread_id}}
    state = agent._compiled.get_state(config)
    interrupted = "tools" in (state.next or ())
    pending_tool_calls = []
    if interrupted:
        messages = state.values.get("messages", [])
        if messages:
            last = messages[-1]
            for tc in getattr(last, "tool_calls", []):
                pending_tool_calls.append({
                    "id": tc.get("id"),
                    "name": tc.get("name"),
                    "args": tc.get("args"),
                })
    return {"interrupted": interrupted, "pending_tool_calls": pending_tool_calls}


@router.post("/sessions/{thread_id}/approve", response_model=InvokeResponse)
async def approve(thread_id: str, request: ApproveRequest):
    agent = global_registry.get(request.agent_name)
    config = {"configurable": {"thread_id": thread_id}}
    result = await agent._compiled.ainvoke(None, config=config)
    content = result["messages"][-1].content
    return InvokeResponse(content=content)


@router.post("/sessions/{thread_id}/reject", response_model=InvokeResponse)
async def reject(thread_id: str, request: RejectRequest):
    from langchain_core.messages import ToolMessage

    agent = global_registry.get(request.agent_name)
    config = {"configurable": {"thread_id": thread_id}}
    state = agent._compiled.get_state(config)
    messages = state.values.get("messages", [])
    last = messages[-1] if messages else None
    tool_messages = [
        ToolMessage(tool_call_id=tc["id"], content=f"Rejected: {request.reason}")
        for tc in getattr(last, "tool_calls", [])
    ] if last else []
    agent._compiled.update_state(config, {"messages": tool_messages}, as_node="tools")
    result = await agent._compiled.ainvoke(None, config=config)
    return InvokeResponse(content=result["messages"][-1].content)
