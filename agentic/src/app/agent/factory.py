from __future__ import annotations

import logging
from collections.abc import AsyncIterator
from dataclasses import dataclass
from typing import Any

from langchain_openai import ChatOpenAI

from app.agent.graph import build_graph
from app.agent.memory import MemoryManager
from app.agent.spec import AgentSpec
from app.settings import get_settings

logger = logging.getLogger(__name__)


def create_production_agent(spec: AgentSpec) -> ProductionAgent:
    settings = get_settings()
    llm = ChatOpenAI(
        model=spec.model_name or settings.openai_model,
        temperature=spec.temperature,
        api_key=settings.openai_api_key,
    ).bind_tools(spec.tools)

    memory = MemoryManager(
        backend=spec.memory_backend,
        enable_long_term=spec.enable_long_term_memory,
        mem0_config=settings.build_mem0_config(),
    )
    compiled = build_graph(llm, spec.tools, memory.checkpointer, spec=spec)
    return ProductionAgent(spec=spec, _compiled=compiled, _memory=memory)


@dataclass
class ProductionAgent:
    spec: AgentSpec
    _compiled: Any
    _memory: MemoryManager | None = None

    async def ainvoke(
        self,
        user_message: str,
        *,
        thread_id: str,
        user_id: str = "default",
    ) -> dict[str, Any]:
        from langchain_core.messages import HumanMessage, SystemMessage

        messages: list[Any] = [HumanMessage(content=user_message)]
        if self.spec.system_prompt:
            messages.insert(0, SystemMessage(content=self.spec.system_prompt))

        if self._memory:
            messages = await self._memory.inject_long_term_context(
                messages, user_id=user_id, agent_id=self.spec.name
            )

        config = {"configurable": {"thread_id": thread_id}}
        state = {
            "messages": messages,
            "user_id": user_id,
            "session_id": thread_id,
            "reflection_count": 0,
            "blocked": False,
            "block_reason": None,
        }
        result = await self._compiled.ainvoke(state, config=config)

        if self._memory:
            await self._memory.save_session(
                result.get("messages", []),
                user_id=user_id,
                session_id=thread_id,
                agent_id=self.spec.name,
            )

        return result

    async def astream(
        self,
        user_message: str,
        *,
        thread_id: str,
        user_id: str = "default",
        stream_mode: str = "messages",
    ) -> AsyncIterator[Any]:
        from langchain_core.messages import HumanMessage, SystemMessage

        messages: list[Any] = [HumanMessage(content=user_message)]
        if self.spec.system_prompt:
            messages.insert(0, SystemMessage(content=self.spec.system_prompt))

        if self._memory:
            messages = await self._memory.inject_long_term_context(
                messages, user_id=user_id, agent_id=self.spec.name
            )

        config = {"configurable": {"thread_id": thread_id}}
        state = {
            "messages": messages,
            "user_id": user_id,
            "session_id": thread_id,
            "reflection_count": 0,
            "blocked": False,
            "block_reason": None,
        }
        async for chunk in self._compiled.astream(state, config=config, stream_mode=stream_mode):
            if isinstance(chunk, tuple):
                yield chunk
            else:
                yield (chunk, {})
