"""Guardrails node unit tests (TDD — RED first)."""

from unittest.mock import AsyncMock, MagicMock

from langchain_core.messages import AIMessage, HumanMessage


class TestGuardrailNode:
    async def test_safe_output_passes_through(self):
        from src.agent.guardrails import make_node_guardrail

        mock_llm = MagicMock()
        mock_llm.ainvoke = AsyncMock(
            return_value=AIMessage(content="SAFE: response is appropriate")
        )

        node = make_node_guardrail(mock_llm)
        state = {
            "messages": [HumanMessage(content="hello"), AIMessage(content="Hi there!")],
            "user_id": "u1",
            "session_id": "s1",
            "reflection_count": 0,
        }

        result = await node(state)
        assert result.get("blocked") is False
        assert result.get("block_reason") is None

    async def test_unsafe_output_sets_blocked(self):
        from src.agent.guardrails import make_node_guardrail

        mock_llm = MagicMock()
        mock_llm.ainvoke = AsyncMock(
            return_value=AIMessage(content="UNSAFE: contains harmful content")
        )

        node = make_node_guardrail(mock_llm)
        state = {
            "messages": [HumanMessage(content="bad request"), AIMessage(content="bad response")],
            "user_id": "u1",
            "session_id": "s1",
            "reflection_count": 0,
        }

        result = await node(state)
        assert result.get("blocked") is True
        assert result.get("block_reason") is not None

    async def test_deterministic_length_check_blocks_long_input(self):
        from src.agent.guardrails import check_input

        long_input = "x" * 10001
        result = check_input(long_input)
        assert result["safe"] is False
        assert "too long" in result["reason"].lower()

    async def test_deterministic_length_check_passes_normal_input(self):
        from src.agent.guardrails import check_input

        result = check_input("hello world")
        assert result["safe"] is True


class TestAfterGuardrail:
    def test_routes_to_end_when_safe(self):
        from src.agent.guardrails import after_guardrail

        state = {
            "messages": [],
            "blocked": False,
            "block_reason": None,
            "user_id": "u1",
            "session_id": "s1",
            "reflection_count": 0,
        }
        assert after_guardrail(state) == "__end__"

    def test_routes_to_end_when_blocked(self):
        from src.agent.guardrails import after_guardrail

        state = {
            "messages": [],
            "blocked": True,
            "block_reason": "harmful",
            "user_id": "u1",
            "session_id": "s1",
            "reflection_count": 0,
        }
        assert after_guardrail(state) == "__end__"


class TestAgentStateGuardrailFields:
    def test_state_has_blocked_field(self):
        from src.agent.state import AgentState

        state: AgentState = {
            "messages": [],
            "user_id": "u1",
            "session_id": "s1",
            "reflection_count": 0,
            "blocked": False,
            "block_reason": None,
        }
        assert state["blocked"] is False
        assert state["block_reason"] is None


class TestBuildGraphGuardrails:
    def test_graph_includes_guardrail_node_when_enabled(self):
        from src.agent.graph import build_graph
        from src.agent.spec import AgentSpec

        mock_llm = MagicMock()
        spec = AgentSpec(name="test", enable_guardrails=True)
        graph = build_graph(mock_llm, [], checkpointer=None, spec=spec)

        assert "guardrail" in graph.get_graph().nodes

    def test_graph_excludes_guardrail_node_when_disabled(self):
        from src.agent.graph import build_graph
        from src.agent.spec import AgentSpec

        mock_llm = MagicMock()
        spec = AgentSpec(name="test", enable_guardrails=False)
        graph = build_graph(mock_llm, [], checkpointer=None, spec=spec)

        assert "guardrail" not in graph.get_graph().nodes
