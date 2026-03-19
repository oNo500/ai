from __future__ import annotations

import logging

from langchain_core.tools import BaseTool

logger = logging.getLogger(__name__)


class ToolRegistry:
    def __init__(self) -> None:
        self._tools: dict[str, BaseTool] = {}
        self._tags: dict[str, set[str]] = {}

    def register(self, t: BaseTool, *, tags: list[str] | None = None) -> None:
        self._tools[t.name] = t
        self._tags[t.name] = set(tags or [])
        logger.debug("Registered tool: %s (tags=%s)", t.name, tags)

    def get(self, name: str) -> BaseTool:
        if name not in self._tools:
            raise KeyError(f"Tool not found: {name}")
        return self._tools[name]

    def all(self) -> list[BaseTool]:
        return list(self._tools.values())

    def by_tags(self, *tags: str) -> list[BaseTool]:
        return [
            t
            for name, t in self._tools.items()
            if set(tags).issubset(self._tags.get(name, set()))
        ]

    def names(self) -> list[str]:
        return list(self._tools.keys())
