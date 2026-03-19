"""Guardrails node: input validation + LLM safety check."""

from __future__ import annotations

from typing import Any

from langchain_core.messages import AIMessage, SystemMessage

_MAX_INPUT_LENGTH = 10_000

_GUARDRAIL_SYSTEM = SystemMessage(
    content=(
        "You are a content safety reviewer. Evaluate the last AI response.\n"
        "If the response is safe and appropriate, reply starting with 'SAFE:'.\n"
        "If the response contains harmful, dangerous, or inappropriate content, "
        "reply starting with 'UNSAFE:' and briefly explain why.\n"
        "Be concise."
    )
)


def check_input(text: str) -> dict[str, Any]:
    if len(text) > _MAX_INPUT_LENGTH:
        return {"safe": False, "reason": f"Input too long ({len(text)} chars, max {_MAX_INPUT_LENGTH})"}
    return {"safe": True, "reason": ""}


def make_node_guardrail(llm: Any):
    async def guardrail(state: dict) -> dict:
        messages = [_GUARDRAIL_SYSTEM] + list(state["messages"])
        verdict: AIMessage = await llm.ainvoke(messages)
        content = verdict.content.strip()
        if content.startswith("UNSAFE"):
            reason = content[len("UNSAFE:"):].strip()
            return {"blocked": True, "block_reason": reason}
        return {"blocked": False, "block_reason": None}

    return guardrail


def after_guardrail(state: dict) -> str:
    return "__end__"
