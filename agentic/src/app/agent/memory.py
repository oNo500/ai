from __future__ import annotations

import asyncio
import logging
from typing import Any

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

logger = logging.getLogger(__name__)


def build_checkpointer(backend: str = "memory") -> Any:
    if backend == "memory":
        from langgraph.checkpoint.memory import InMemorySaver

        return InMemorySaver()
    raise ValueError(f"Unknown checkpointer backend: {backend}")


try:
    from mem0 import Memory
except ImportError:
    Memory = None  # type: ignore[assignment,misc]


class LongTermMemory:
    def __init__(self, *, mem0_config: dict | None = None) -> None:
        self._client = self._build_client(mem0_config)

    def _build_client(self, config: dict | None) -> Any:
        if Memory is None:
            logger.warning("mem0 not installed; long-term memory disabled")
            return None
        if config:
            return Memory.from_config(config)
        return Memory()

    async def add(
        self,
        messages: list[dict[str, str]],
        *,
        user_id: str,
        session_id: str | None = None,
        agent_id: str | None = None,
    ) -> list[dict[str, Any]]:
        if not self._client:
            return []
        try:
            result = await asyncio.to_thread(
                self._client.add,
                messages,
                user_id=user_id,
                session_id=session_id,
                agent_id=agent_id,
            )
            return result.get("results", [])
        except Exception as exc:
            logger.error("Mem0 add failed: %s", exc)
            return []

    async def format_for_prompt(
        self,
        query: str,
        *,
        user_id: str,
        agent_id: str | None = None,
        limit: int = 5,
    ) -> str:
        if not self._client:
            return ""
        try:
            results = await asyncio.to_thread(
                self._client.search,
                query,
                user_id=user_id,
                agent_id=agent_id,
                limit=limit,
            )
            memories = results.get("results", [])
        except Exception as exc:
            logger.error("Mem0 search failed: %s", exc)
            return ""

        if not memories:
            return ""

        lines = ["## Long-term Memory (from previous sessions)"]
        for m in memories:
            mem_text = m.get("memory", "")
            score = m.get("score", 0.0)
            if mem_text:
                lines.append(f"- {mem_text} (relevance: {score:.2f})")
        return "\n".join(lines)


class MemoryManager:
    def __init__(
        self,
        *,
        backend: str = "memory",
        enable_long_term: bool = False,
        mem0_config: dict | None = None,
    ) -> None:
        self.checkpointer = build_checkpointer(backend)
        self._long_term = LongTermMemory(mem0_config=mem0_config) if enable_long_term else None

    async def inject_long_term_context(
        self,
        messages: list[Any],
        *,
        user_id: str,
        agent_id: str | None = None,
    ) -> list[Any]:
        if not self._long_term:
            return messages

        query = ""
        for msg in reversed(messages):
            if isinstance(msg, HumanMessage) and isinstance(msg.content, str):
                query = msg.content
                break

        if not query:
            return messages

        mem_block = await self._long_term.format_for_prompt(
            query, user_id=user_id, agent_id=agent_id
        )
        if not mem_block:
            return messages

        result = list(messages)
        for i, msg in enumerate(result):
            if isinstance(msg, SystemMessage):
                current = msg.content if isinstance(msg.content, str) else ""
                result[i] = SystemMessage(content=f"{current}\n\n{mem_block}")
                return result

        result.insert(0, SystemMessage(content=mem_block))
        return result

    async def save_session(
        self,
        messages: list[Any],
        *,
        user_id: str,
        session_id: str | None = None,
        agent_id: str | None = None,
    ) -> None:
        if not self._long_term:
            return

        mem0_messages = []
        for msg in messages:
            if isinstance(msg, HumanMessage):
                content = msg.content if isinstance(msg.content, str) else str(msg.content)
                mem0_messages.append({"role": "user", "content": content})
            elif isinstance(msg, AIMessage):
                content = msg.content if isinstance(msg.content, str) else str(msg.content)
                if content:
                    mem0_messages.append({"role": "assistant", "content": content})

        if mem0_messages:
            try:
                await self._long_term.add(
                    mem0_messages,
                    user_id=user_id,
                    session_id=session_id,
                    agent_id=agent_id,
                )
            except Exception as exc:
                logger.error("save_session failed: %s", exc)
