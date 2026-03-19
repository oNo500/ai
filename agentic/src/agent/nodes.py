from typing import Any

from src.agent.state import AgentState


def make_node_call_model(llm: Any):
    async def call_model(state: AgentState) -> dict:
        response = await llm.ainvoke(state["messages"])
        return {"messages": [response]}

    return call_model


def should_continue(state: AgentState) -> str:
    last = state["messages"][-1]
    if hasattr(last, "tool_calls") and last.tool_calls:
        return "tools"
    return "__end__"
