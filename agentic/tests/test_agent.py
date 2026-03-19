"""Agent node unit tests (mock LLM)."""

from unittest.mock import AsyncMock, MagicMock

import pytest
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

from app.agent.state import AgentState


@pytest.fixture
def tool_call_state() -> AgentState:
    ai_msg = AIMessage(
        content="",
        tool_calls=[{"id": "call_1", "name": "get_current_time", "args": {}}],
    )
    return {"messages": [HumanMessage(content="What time is it?"), ai_msg]}


@pytest.fixture
def final_state() -> AgentState:
    return {"messages": [HumanMessage(content="Hello"), AIMessage(content="Hi there!")]}


class TestSystemPromptInjection:
    async def test_ainvoke_injects_system_prompt(self):
        from app.agent.factory import ProductionAgent
        from app.agent.spec import AgentSpec

        mock_compiled = MagicMock()
        mock_compiled.ainvoke = AsyncMock(
            return_value={"messages": [AIMessage(content="I am a helper")]}
        )

        spec = AgentSpec(name="test", system_prompt="You are a helpful assistant.")
        agent = ProductionAgent(spec=spec, _compiled=mock_compiled)

        await agent.ainvoke("hello", thread_id="t1")

        call_args = mock_compiled.ainvoke.call_args
        messages = call_args[0][0]["messages"]
        assert isinstance(messages[0], SystemMessage)
        assert messages[0].content == "You are a helpful assistant."

    async def test_ainvoke_no_system_prompt_skips_injection(self):
        from app.agent.factory import ProductionAgent
        from app.agent.spec import AgentSpec

        mock_compiled = MagicMock()
        mock_compiled.ainvoke = AsyncMock(
            return_value={"messages": [AIMessage(content="ok")]}
        )

        spec = AgentSpec(name="test")
        agent = ProductionAgent(spec=spec, _compiled=mock_compiled)

        await agent.ainvoke("hello", thread_id="t1")

        call_args = mock_compiled.ainvoke.call_args
        messages = call_args[0][0]["messages"]
        assert not isinstance(messages[0], SystemMessage)

    async def test_astream_yields_tuples(self):
        from app.agent.factory import ProductionAgent
        from app.agent.spec import AgentSpec

        async def mock_astream(state, config=None, stream_mode=None):
            yield (AIMessage(content="Hi"), {})

        mock_compiled = MagicMock()
        mock_compiled.astream = mock_astream

        spec = AgentSpec(name="test")
        agent = ProductionAgent(spec=spec, _compiled=mock_compiled)

        results = []
        async for item in agent.astream("hello", thread_id="t1"):
            results.append(item)

        assert len(results) == 1
        chunk, meta = results[0]
        assert isinstance(chunk, AIMessage)
        assert meta == {}

    async def test_astream_injects_system_prompt(self):
        from app.agent.factory import ProductionAgent
        from app.agent.spec import AgentSpec

        captured_states = []

        async def mock_astream(state, config=None, stream_mode=None):
            captured_states.append(state)
            yield (AIMessage(content="Hi"), {})

        mock_compiled = MagicMock()
        mock_compiled.astream = mock_astream

        spec = AgentSpec(name="test", system_prompt="You are a robot.")
        agent = ProductionAgent(spec=spec, _compiled=mock_compiled)

        async for _ in agent.astream("hello", thread_id="t1"):
            pass

        messages = captured_states[0]["messages"]
        assert isinstance(messages[0], SystemMessage)
        assert messages[0].content == "You are a robot."


class TestAgentStateFields:
    def test_agent_state_has_user_id_field(self):
        from app.agent.state import AgentState

        state: AgentState = {
            "messages": [],
            "user_id": "user-123",
            "session_id": "sess-abc",
        }
        assert state["user_id"] == "user-123"
        assert state["session_id"] == "sess-abc"

    async def test_ainvoke_passes_user_id_and_session_id_in_state(self):
        from app.agent.factory import ProductionAgent
        from app.agent.spec import AgentSpec

        captured_states = []

        mock_compiled = MagicMock()

        async def fake_ainvoke(state, config=None):
            captured_states.append(state)
            return {"messages": [AIMessage(content="ok")]}

        mock_compiled.ainvoke = fake_ainvoke

        spec = AgentSpec(name="test")
        agent = ProductionAgent(spec=spec, _compiled=mock_compiled)

        await agent.ainvoke("hello", thread_id="t42", user_id="alice")

        assert captured_states[0]["user_id"] == "alice"
        assert captured_states[0]["session_id"] == "t42"

    async def test_ainvoke_state_has_all_fields(self):
        from app.agent.factory import ProductionAgent
        from app.agent.spec import AgentSpec

        captured_states = []

        mock_compiled = MagicMock()

        async def fake_ainvoke(state, config=None):
            captured_states.append(state)
            return {"messages": [AIMessage(content="ok")]}

        mock_compiled.ainvoke = fake_ainvoke

        spec = AgentSpec(name="test")
        agent = ProductionAgent(spec=spec, _compiled=mock_compiled)

        await agent.ainvoke("hello", thread_id="t1")

        state = captured_states[0]
        assert "reflection_count" in state
        assert state["reflection_count"] == 0
        assert "blocked" in state
        assert state["blocked"] is False
        assert "block_reason" in state
        assert state["block_reason"] is None

    async def test_astream_state_has_all_fields(self):
        from app.agent.factory import ProductionAgent
        from app.agent.spec import AgentSpec

        captured_states = []

        async def mock_astream(state, config=None, stream_mode=None):
            captured_states.append(state)
            yield (AIMessage(content="Hi"), {})

        mock_compiled = MagicMock()
        mock_compiled.astream = mock_astream

        spec = AgentSpec(name="test")
        agent = ProductionAgent(spec=spec, _compiled=mock_compiled)

        async for _ in agent.astream("hello", thread_id="t1"):
            pass

        state = captured_states[0]
        assert "reflection_count" in state
        assert state["reflection_count"] == 0
        assert "blocked" in state
        assert state["blocked"] is False
        assert "block_reason" in state
        assert state["block_reason"] is None


class TestAstreamMemory:
    async def test_astream_calls_inject_long_term_context_when_memory_exists(self):
        from app.agent.factory import ProductionAgent
        from app.agent.spec import AgentSpec

        mock_memory = AsyncMock()
        mock_memory.inject_long_term_context = AsyncMock(
            side_effect=lambda messages, **kwargs: messages
        )

        async def mock_astream(state, config=None, stream_mode=None):
            yield (AIMessage(content="Hi"), {})

        mock_compiled = MagicMock()
        mock_compiled.astream = mock_astream

        spec = AgentSpec(name="test", enable_long_term_memory=True)
        agent = ProductionAgent(spec=spec, _compiled=mock_compiled, _memory=mock_memory)

        async for _ in agent.astream("hello", thread_id="t1", user_id="bob"):
            pass

        mock_memory.inject_long_term_context.assert_called_once_with(
            [HumanMessage(content="hello")],
            user_id="bob",
            agent_id="test",
        )

    async def test_astream_skips_inject_when_no_memory(self):
        from app.agent.factory import ProductionAgent
        from app.agent.spec import AgentSpec

        async def mock_astream(state, config=None, stream_mode=None):
            yield (AIMessage(content="Hi"), {})

        mock_compiled = MagicMock()
        mock_compiled.astream = mock_astream

        spec = AgentSpec(name="test")
        agent = ProductionAgent(spec=spec, _compiled=mock_compiled, _memory=None)

        results = []
        async for item in agent.astream("hello", thread_id="t1"):
            results.append(item)

        assert len(results) == 1


class TestShouldContinue:
    def test_continues_when_tool_calls_present(self, tool_call_state):
        from app.agent.nodes import should_continue

        result = should_continue(tool_call_state)
        assert result == "tools"

    def test_ends_when_no_tool_calls(self, final_state):
        from app.agent.nodes import should_continue

        result = should_continue(final_state)
        assert result == "__end__"
