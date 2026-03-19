"""Reflection node unit tests (TDD — RED first)."""

from unittest.mock import AsyncMock, MagicMock

from langchain_core.messages import AIMessage, HumanMessage


class TestAfterReflect:
    def test_routes_to_model_when_critique_requests_revision(self):
        from src.agent.reflection import after_reflect

        state = {
            "messages": [HumanMessage(content="hi"), AIMessage(content="bad answer")],
            "reflection_count": 0,
            "user_id": "u1",
            "session_id": "s1",
        }
        critique = AIMessage(content="REVISE: answer is too vague")
        result = after_reflect(state, critique)
        assert result == "model"

    def test_routes_to_end_when_critique_accepts(self):
        from src.agent.reflection import after_reflect

        state = {
            "messages": [HumanMessage(content="hi"), AIMessage(content="good answer")],
            "reflection_count": 1,
            "user_id": "u1",
            "session_id": "s1",
        }
        critique = AIMessage(content="ACCEPT: answer is clear and complete")
        result = after_reflect(state, critique)
        assert result == "__end__"

    def test_routes_to_end_when_max_reflections_reached(self):
        from src.agent.reflection import after_reflect

        state = {
            "messages": [HumanMessage(content="hi"), AIMessage(content="answer")],
            "reflection_count": 3,
            "user_id": "u1",
            "session_id": "s1",
        }
        critique = AIMessage(content="REVISE: still not good enough")
        result = after_reflect(state, critique, max_reflections=3)
        assert result == "__end__"


class TestReflectNode:
    async def test_reflect_node_increments_reflection_count(self):
        from src.agent.reflection import make_node_reflect

        mock_llm = MagicMock()
        mock_llm.ainvoke = AsyncMock(
            return_value=AIMessage(content="ACCEPT: looks good")
        )

        node = make_node_reflect(mock_llm)
        state = {
            "messages": [HumanMessage(content="hi"), AIMessage(content="answer")],
            "reflection_count": 0,
            "user_id": "u1",
            "session_id": "s1",
        }

        result = await node(state)
        assert result["reflection_count"] == 1

    async def test_reflect_node_appends_critique_to_messages(self):
        from src.agent.reflection import make_node_reflect

        mock_llm = MagicMock()
        mock_llm.ainvoke = AsyncMock(
            return_value=AIMessage(content="REVISE: be more specific")
        )

        node = make_node_reflect(mock_llm)
        state = {
            "messages": [HumanMessage(content="hi"), AIMessage(content="answer")],
            "reflection_count": 0,
            "user_id": "u1",
            "session_id": "s1",
        }

        result = await node(state)
        assert len(result["messages"]) == 1
        assert "REVISE" in result["messages"][0].content

    async def test_reflect_node_calls_llm_with_critique_prompt(self):
        from src.agent.reflection import make_node_reflect

        mock_llm = MagicMock()
        mock_llm.ainvoke = AsyncMock(
            return_value=AIMessage(content="ACCEPT: good")
        )

        node = make_node_reflect(mock_llm)
        state = {
            "messages": [HumanMessage(content="What is 2+2?"), AIMessage(content="4")],
            "reflection_count": 0,
            "user_id": "u1",
            "session_id": "s1",
        }

        await node(state)

        call_args = mock_llm.ainvoke.call_args[0][0]
        # 应该包含 system critique prompt
        assert any("ACCEPT" in str(m.content) or "REVISE" in str(m.content) for m in call_args)


class TestAgentSpecReflection:
    def test_spec_has_enable_reflection_field(self):
        from src.agent.spec import AgentSpec

        spec = AgentSpec(name="test", enable_reflection=True, max_reflections=3)
        assert spec.enable_reflection is True
        assert spec.max_reflections == 3

    def test_spec_reflection_defaults(self):
        from src.agent.spec import AgentSpec

        spec = AgentSpec(name="test")
        assert spec.enable_reflection is False
        assert spec.max_reflections == 2


class TestAgentStateReflectionCount:
    def test_state_has_reflection_count_field(self):
        from src.agent.state import AgentState

        state: AgentState = {
            "messages": [],
            "user_id": "u1",
            "session_id": "s1",
            "reflection_count": 0,
        }
        assert state["reflection_count"] == 0


class TestBuildGraphWithReflection:
    def test_graph_includes_reflect_node_when_enabled(self):
        from unittest.mock import MagicMock

        from src.agent.graph import build_graph
        from src.agent.spec import AgentSpec

        mock_llm = MagicMock()
        spec = AgentSpec(name="test", enable_reflection=True)
        graph = build_graph(mock_llm, [], checkpointer=None, spec=spec)

        assert "reflect" in graph.get_graph().nodes

    def test_graph_excludes_reflect_node_when_disabled(self):
        from unittest.mock import MagicMock

        from src.agent.graph import build_graph
        from src.agent.spec import AgentSpec

        mock_llm = MagicMock()
        spec = AgentSpec(name="test", enable_reflection=False)
        graph = build_graph(mock_llm, [], checkpointer=None, spec=spec)

        assert "reflect" not in graph.get_graph().nodes
