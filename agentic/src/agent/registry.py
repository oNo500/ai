from __future__ import annotations

from langchain_core.tools import BaseTool

from src.agent.factory import ProductionAgent, create_production_agent
from src.agent.spec import AgentSpec


class AgentRegistry:
    def __init__(self) -> None:
        self._agents: dict[str, ProductionAgent] = {}

    def register(self, name: str, spec: AgentSpec) -> ProductionAgent:
        agent = create_production_agent(spec)
        self._agents[name] = agent
        return agent

    def get(self, name: str) -> ProductionAgent:
        if name not in self._agents:
            raise KeyError(f"Agent not found: {name!r}")
        return self._agents[name]

    def all(self) -> list[ProductionAgent]:
        return list(self._agents.values())

    def names(self) -> list[str]:
        return list(self._agents.keys())

    def get_worker_tools(self) -> list[BaseTool]:
        from src.agent.tools.subagent import make_subagent_tool

        return [
            make_subagent_tool(name, agent)
            for name, agent in self._agents.items()
            if agent.spec.role == "worker"
        ]


def _build_global_registry() -> AgentRegistry:
    from src.agent.tools import registry as tool_registry

    reg = AgentRegistry()
    spec = AgentSpec(
        name="default",
        tools=[tool_registry.get("get_current_time")],
    )
    reg.register("default", spec)
    return reg


global_registry = _build_global_registry()


def get_default_agent() -> ProductionAgent:
    return global_registry.get("default")
