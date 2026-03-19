"""ToolRegistry unit tests (RED first)."""

import pytest


class TestToolRegistry:
    def test_register_and_get(self):
        from langchain_core.tools import tool

        from src.agent.tools.base import ToolRegistry

        @tool
        def dummy_tool() -> str:
            """A dummy tool."""
            return "dummy"

        reg = ToolRegistry()
        reg.register(dummy_tool, tags=["test"])
        result = reg.get("dummy_tool")
        assert result is dummy_tool

    def test_get_missing_raises_key_error(self):
        from src.agent.tools.base import ToolRegistry

        reg = ToolRegistry()
        with pytest.raises(KeyError):
            reg.get("nonexistent")

    def test_by_tags_returns_matching(self):
        from langchain_core.tools import tool

        from src.agent.tools.base import ToolRegistry

        @tool
        def tool_a() -> str:
            """Tool A."""
            return "a"

        @tool
        def tool_b() -> str:
            """Tool B."""
            return "b"

        reg = ToolRegistry()
        reg.register(tool_a, tags=["utility", "time"])
        reg.register(tool_b, tags=["search"])

        result = reg.by_tags("utility")
        assert tool_a in result
        assert tool_b not in result

    def test_names_returns_all_names(self):
        from langchain_core.tools import tool

        from src.agent.tools.base import ToolRegistry

        @tool
        def my_tool() -> str:
            """My tool."""
            return "x"

        reg = ToolRegistry()
        reg.register(my_tool)
        assert "my_tool" in reg.names()

    def test_all_returns_all_tools(self):
        from langchain_core.tools import tool

        from src.agent.tools.base import ToolRegistry

        @tool
        def another_tool() -> str:
            """Another tool."""
            return "y"

        reg = ToolRegistry()
        reg.register(another_tool)
        assert another_tool in reg.all()


class TestBuiltinTools:
    def test_get_current_time_registered(self):
        from src.agent.tools import registry

        assert "get_current_time" in registry.names()

    def test_get_current_time_has_utility_tag(self):
        from src.agent.tools import registry

        time_tools = registry.by_tags("utility")
        names = [t.name for t in time_tools]
        assert "get_current_time" in names

    def test_get_current_time_returns_string(self):
        from src.agent.tools import registry

        tool = registry.get("get_current_time")
        result = tool.invoke({})
        assert isinstance(result, str)
        assert "UTC" in result
