from __future__ import annotations

from dataclasses import dataclass, field

from langchain_core.tools import BaseTool


@dataclass
class AgentSpec:
    name: str
    tools: list[BaseTool] = field(default_factory=list)
    model_name: str | None = None
    temperature: float = 0.0
    system_prompt: str | None = None
    memory_backend: str = "memory"
    enable_guardrails: bool = False
    enable_human_loop: bool = False
    enable_long_term_memory: bool = False
    enable_reflection: bool = False
    max_reflections: int = 2
    role: str = "worker"  # "worker" | "orchestrator"
