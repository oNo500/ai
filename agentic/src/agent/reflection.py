"""Reflection node: self-critique loop for output quality improvement."""

from typing import Any

from langchain_core.messages import AIMessage, SystemMessage

_CRITIQUE_SYSTEM = SystemMessage(
    content=(
        "You are a strict critic. Review the last AI response and evaluate its quality.\n"
        "If the response is complete, accurate, and helpful, reply starting with 'ACCEPT:'.\n"
        "If it needs improvement, reply starting with 'REVISE:' and explain what to fix.\n"
        "Be concise."
    )
)


def make_node_reflect(llm: Any):
    async def reflect(state: dict) -> dict:
        messages = [_CRITIQUE_SYSTEM] + list(state["messages"])
        critique: AIMessage = await llm.ainvoke(messages)
        return {
            "messages": [critique],
            "reflection_count": state.get("reflection_count", 0) + 1,
        }

    return reflect


def after_reflect(state: dict, critique: AIMessage, *, max_reflections: int = 2) -> str:
    if state.get("reflection_count", 0) >= max_reflections:
        return "__end__"
    if critique.content.strip().startswith("ACCEPT"):
        return "__end__"
    return "model"
