"""SubAgent tool unit tests (TDD — RED first)."""

from unittest.mock import AsyncMock, MagicMock


class TestMakeSubagentTool:
    def test_tool_name_equals_agent_name(self):
        from src.agent.tools.subagent import make_subagent_tool

        mock_agent = MagicMock()
        mock_agent.spec.name = "researcher"
        mock_agent.spec.system_prompt = "You are a researcher."

        tool = make_subagent_tool("researcher", mock_agent)
        assert tool.name == "researcher"

    def test_tool_description_uses_system_prompt(self):
        from src.agent.tools.subagent import make_subagent_tool

        mock_agent = MagicMock()
        mock_agent.spec.name = "coder"
        mock_agent.spec.system_prompt = "You are a Python expert."

        tool = make_subagent_tool("coder", mock_agent)
        assert "Python expert" in tool.description

    def test_tool_description_fallback_when_no_system_prompt(self):
        from src.agent.tools.subagent import make_subagent_tool

        mock_agent = MagicMock()
        mock_agent.spec.name = "helper"
        mock_agent.spec.system_prompt = None

        tool = make_subagent_tool("helper", mock_agent)
        assert "helper" in tool.description

    async def test_tool_arun_calls_agent_ainvoke(self):
        from src.agent.tools.subagent import make_subagent_tool

        mock_agent = MagicMock()
        mock_agent.spec.name = "analyst"
        mock_agent.spec.system_prompt = "You are an analyst."
        mock_agent.ainvoke = AsyncMock(
            return_value={"messages": [MagicMock(content="analysis result")]}
        )

        tool = make_subagent_tool("analyst", mock_agent)
        result = await tool.arun("analyze this data")

        mock_agent.ainvoke.assert_called_once()
        call_kwargs = mock_agent.ainvoke.call_args
        assert call_kwargs[0][0] == "analyze this data"
        assert "analysis result" in result

    async def test_tool_arun_passes_thread_id(self):
        from src.agent.tools.subagent import make_subagent_tool

        mock_agent = MagicMock()
        mock_agent.spec.name = "bot"
        mock_agent.spec.system_prompt = "You are a bot."
        mock_agent.ainvoke = AsyncMock(
            return_value={"messages": [MagicMock(content="ok")]}
        )

        tool = make_subagent_tool("bot", mock_agent, thread_id="t-123", user_id="u-1")
        await tool.arun("hello")

        call_kwargs = mock_agent.ainvoke.call_args[1]
        assert call_kwargs["thread_id"] == "t-123"
        assert call_kwargs["user_id"] == "u-1"


class TestSubagentToolRun:
    def test_sync_run_raises_not_implemented(self):
        import pytest

        from src.agent.tools.subagent import make_subagent_tool

        mock_agent = MagicMock()
        mock_agent.spec.name = "bot"
        mock_agent.spec.system_prompt = "You are a bot."

        tool = make_subagent_tool("bot", mock_agent)
        with pytest.raises(NotImplementedError):
            tool._run("hello")


class TestSubagentToolFromRegistry:
    def test_make_subagent_tool_from_registry(self):
        from src.agent.tools.subagent import make_subagent_tool_from_registry

        mock_agent = MagicMock()
        mock_agent.spec.name = "researcher"
        mock_agent.spec.system_prompt = "You research things."

        mock_registry = MagicMock()
        mock_registry.get.return_value = mock_agent

        tool = make_subagent_tool_from_registry("researcher", mock_registry)
        assert tool.name == "researcher"
        mock_registry.get.assert_called_once_with("researcher")

    def test_unknown_agent_raises(self):
        import pytest

        from src.agent.tools.subagent import make_subagent_tool_from_registry

        mock_registry = MagicMock()
        mock_registry.get.side_effect = KeyError("ghost")

        with pytest.raises(KeyError):
            make_subagent_tool_from_registry("ghost", mock_registry)
