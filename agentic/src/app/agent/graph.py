from typing import Any

from langchain_core.tools import BaseTool
from langgraph.graph import END, StateGraph
from langgraph.prebuilt import ToolNode

from app.agent.nodes import should_continue
from app.agent.state import AgentState


def build_graph(
    llm: Any,
    tools: list[BaseTool],
    checkpointer: Any,
    spec: Any = None,
) -> Any:
    from app.agent.nodes import make_node_call_model

    enable_reflection = spec.enable_reflection if spec is not None else False
    max_reflections = spec.max_reflections if spec is not None else 2
    enable_human_loop = spec.enable_human_loop if spec is not None else False
    enable_guardrails = spec.enable_guardrails if spec is not None else False

    builder = StateGraph(AgentState)
    builder.add_node("model", make_node_call_model(llm))
    builder.add_node("tools", ToolNode(tools))
    builder.set_entry_point("model")

    terminal = END

    if enable_guardrails:
        from app.agent.guardrails import after_guardrail, make_node_guardrail

        builder.add_node("guardrail", make_node_guardrail(llm))
        builder.add_conditional_edges("guardrail", after_guardrail, {"__end__": END})
        terminal = "guardrail"

    if enable_reflection:
        from app.agent.reflection import after_reflect, make_node_reflect

        builder.add_node("reflect", make_node_reflect(llm))
        builder.add_conditional_edges(
            "model",
            should_continue,
            {"tools": "tools", "__end__": "reflect"},
        )
        builder.add_edge("tools", "model")
        builder.add_conditional_edges(
            "reflect",
            lambda state: after_reflect(
                state,
                state["messages"][-1],
                max_reflections=max_reflections,
            ),
            {"model": "model", "__end__": terminal},
        )
    else:
        builder.add_conditional_edges(
            "model", should_continue, {"tools": "tools", "__end__": terminal}
        )
        builder.add_edge("tools", "model")

    compile_kwargs: dict = {"checkpointer": checkpointer}
    if enable_human_loop:
        compile_kwargs["interrupt_before"] = ["tools"]
    return builder.compile(**compile_kwargs)
