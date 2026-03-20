"""AgentSpec + factory unit tests (RED first)."""

from unittest.mock import MagicMock, patch

from langchain_core.tools import BaseTool


class TestAgentSpec:
    def test_default_fields(self):
        from src.agent.spec import AgentSpec

        spec = AgentSpec(name="test")
        assert spec.name == "test"
        assert spec.tools == []
        assert spec.model_name is None
        assert spec.temperature == 0.0
        assert spec.system_prompt is None
        assert spec.memory_backend == "memory"
        assert spec.enable_guardrails is False
        assert spec.enable_human_loop is False
        assert spec.enable_long_term_memory is False

    def test_enable_long_term_memory_can_be_set(self):
        from src.agent.spec import AgentSpec

        spec = AgentSpec(name="test", enable_long_term_memory=True)
        assert spec.enable_long_term_memory is True

    def test_with_tools(self):
        from src.agent.spec import AgentSpec

        mock_tool = MagicMock(spec=BaseTool)
        spec = AgentSpec(name="test", tools=[mock_tool])
        assert len(spec.tools) == 1


class TestProductionAgent:
    def test_create_production_agent_returns_agent(self):
        from src.agent.factory import create_production_agent
        from src.agent.spec import AgentSpec

        mock_tool = MagicMock(spec=BaseTool)
        mock_tool.name = "test_tool"
        spec = AgentSpec(name="test", tools=[mock_tool])

        with patch("src.agent.factory.build_graph") as mock_build:
            mock_compiled = MagicMock()
            mock_build.return_value = mock_compiled

            with patch("src.agent.factory.ChatOpenAI") as mock_llm_cls:
                mock_llm = MagicMock()
                mock_llm.bind_tools.return_value = mock_llm
                mock_llm_cls.return_value = mock_llm

                agent = create_production_agent(spec)

        from src.agent.factory import ProductionAgent

        assert isinstance(agent, ProductionAgent)
        assert agent.spec is spec

    async def test_ainvoke_uses_thread_id(self):
        from unittest.mock import AsyncMock

        from src.agent.factory import ProductionAgent
        from src.agent.spec import AgentSpec

        mock_compiled = MagicMock()
        mock_compiled.ainvoke = AsyncMock(
            return_value={"messages": [MagicMock(content="response")]}
        )

        spec = AgentSpec(name="test")
        agent = ProductionAgent(spec=spec, _compiled=mock_compiled)

        await agent.ainvoke("hello", thread_id="thread-123")

        call_args = mock_compiled.ainvoke.call_args
        config = call_args[1]["config"] if "config" in call_args[1] else call_args[0][1]
        assert config["configurable"]["thread_id"] == "thread-123"

    async def test_astream_yields_chunks(self):
        from src.agent.factory import ProductionAgent
        from src.agent.spec import AgentSpec

        async def mock_astream(state, config=None, stream_mode=None):
            yield (MagicMock(content="Hello"), {})
            yield (MagicMock(content=" world"), {})

        mock_compiled = MagicMock()
        mock_compiled.astream = mock_astream

        spec = AgentSpec(name="test")
        agent = ProductionAgent(spec=spec, _compiled=mock_compiled)

        chunks = []
        async for chunk in agent.astream("hello", thread_id="thread-123"):
            chunks.append(chunk)

        assert len(chunks) == 2


class TestRegistry:
    def test_get_default_agent_returns_production_agent(self):
        from src.agent.factory import ProductionAgent
        from src.agent.registry import get_default_agent

        agent = get_default_agent()
        assert isinstance(agent, ProductionAgent)

    def test_get_default_agent_is_stable(self):
        from src.agent.registry import get_default_agent

        agent1 = get_default_agent()
        agent2 = get_default_agent()
        assert agent1 is agent2
