"""SubAgent tool: wrap a registered agent as a LangChain Tool."""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING, Any

from langchain_core.tools import BaseTool
from pydantic import PrivateAttr

if TYPE_CHECKING:
    from app.agent.factory import ProductionAgent
    from app.agent.registry import AgentRegistry


class SubAgentTool(BaseTool):
    name: str
    description: str
    _agent: Any = PrivateAttr()
    _thread_id: str = PrivateAttr()
    _user_id: str = PrivateAttr()

    def __init__(self, *, name: str, description: str, agent: Any, thread_id: str, user_id: str):
        super().__init__(name=name, description=description)
        self._agent = agent
        self._thread_id = thread_id
        self._user_id = user_id

    def _run(self, query: str) -> str:
        raise NotImplementedError("SubAgentTool only supports async via _arun")

    async def _arun(self, query: str) -> str:
        result = await self._agent.ainvoke(
            query,
            thread_id=self._thread_id,
            user_id=self._user_id,
        )
        messages = result.get("messages", [])
        if messages:
            return messages[-1].content
        return ""


def make_subagent_tool(
    name: str,
    agent: ProductionAgent,
    *,
    thread_id: str | None = None,
    user_id: str = "default",
) -> SubAgentTool:
    system_prompt = agent.spec.system_prompt
    description = system_prompt if system_prompt else f"Delegate tasks to the {name!r} agent."
    return SubAgentTool(
        name=name,
        description=description,
        agent=agent,
        thread_id=thread_id or f"{name}-{uuid.uuid4().hex[:8]}",
        user_id=user_id,
    )


def make_subagent_tool_from_registry(
    name: str,
    registry: AgentRegistry,
    *,
    thread_id: str | None = None,
    user_id: str = "default",
) -> SubAgentTool:
    agent = registry.get(name)
    return make_subagent_tool(name, agent, thread_id=thread_id, user_id=user_id)
