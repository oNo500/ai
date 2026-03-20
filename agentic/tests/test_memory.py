"""Memory manager unit tests (RED first)."""

from unittest.mock import AsyncMock, patch

import pytest
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage


class TestBuildCheckpointer:
    def test_memory_backend_returns_in_memory_saver(self):
        from langgraph.checkpoint.memory import InMemorySaver

        from src.agent.memory import build_checkpointer

        cp = build_checkpointer("memory")
        assert isinstance(cp, InMemorySaver)

    def test_unknown_backend_raises(self):
        from src.agent.memory import build_checkpointer

        with pytest.raises(ValueError, match="Unknown"):
            build_checkpointer("unknown_backend")


class TestMemoryManager:
    def test_init_with_memory_backend(self):
        from src.agent.memory import MemoryManager

        mgr = MemoryManager(backend="memory", enable_long_term=False)
        assert mgr.checkpointer is not None
        assert mgr._long_term is None

    async def test_inject_long_term_context_no_op_when_disabled(self):
        from src.agent.memory import MemoryManager

        mgr = MemoryManager(backend="memory", enable_long_term=False)
        messages = [HumanMessage(content="hello")]
        result = await mgr.inject_long_term_context(messages, user_id="u1", agent_id="a1")
        assert result == messages

    async def test_save_session_no_op_when_disabled(self):
        from src.agent.memory import MemoryManager

        mgr = MemoryManager(backend="memory", enable_long_term=False)
        # Should not raise
        await mgr.save_session(
            [HumanMessage(content="hi"), AIMessage(content="hello")],
            user_id="u1",
            session_id="s1",
            agent_id="a1",
        )

    async def test_inject_long_term_context_with_long_term(self):
        from src.agent.memory import MemoryManager

        mock_lt = AsyncMock()
        mock_lt.format_for_prompt = AsyncMock(return_value="## Memory\n- User likes Python")

        with patch("src.agent.memory.LongTermMemory", return_value=mock_lt):
            mgr = MemoryManager(backend="memory", enable_long_term=True)

        messages = [HumanMessage(content="hello")]
        result = await mgr.inject_long_term_context(messages, user_id="u1", agent_id="a1")
        # Should have prepended a SystemMessage
        assert any(isinstance(m, SystemMessage) for m in result)

    async def test_save_session_calls_long_term(self):
        from src.agent.memory import MemoryManager

        mock_lt = AsyncMock()
        mock_lt.add = AsyncMock(return_value=[])

        with patch("src.agent.memory.LongTermMemory", return_value=mock_lt):
            mgr = MemoryManager(backend="memory", enable_long_term=True)

        messages = [HumanMessage(content="hi"), AIMessage(content="hello")]
        await mgr.save_session(messages, user_id="u1", session_id="s1", agent_id="a1")
        mock_lt.add.assert_called_once()


class TestLongTermMemoryConfig:
    def test_build_client_uses_from_config_when_config_provided(self):
        from src.agent.memory import LongTermMemory

        fake_client = object()
        config = {"vector_store": {"provider": "qdrant", "config": {"host": "localhost"}}}

        with patch("src.agent.memory.Memory") as mock_mem_cls:
            mock_mem_cls.from_config.return_value = fake_client
            lt = LongTermMemory(mem0_config=config)

        mock_mem_cls.from_config.assert_called_once_with(config)
        assert lt._client is fake_client

    def test_build_client_uses_default_when_no_config(self):
        from src.agent.memory import LongTermMemory

        fake_client = object()

        with patch("src.agent.memory.Memory") as mock_mem_cls:
            mock_mem_cls.return_value = fake_client
            lt = LongTermMemory(mem0_config=None)

        mock_mem_cls.assert_called_once_with()
        assert lt._client is fake_client

    def test_memory_manager_passes_config_to_long_term(self):
        from src.agent.memory import LongTermMemory, MemoryManager

        config = {"vector_store": {"provider": "qdrant", "config": {}}}

        with patch.object(LongTermMemory, "__init__", return_value=None) as mock_init:
            MemoryManager(backend="memory", enable_long_term=True, mem0_config=config)

        mock_init.assert_called_once_with(mem0_config=config)


class TestSettingsMem0Config:
    def test_settings_has_mem0_vector_store_provider(self):
        from src.settings import Settings

        s = Settings()
        assert hasattr(s, "mem0_vector_store_provider")
        assert s.mem0_vector_store_provider == "memory"

    def test_settings_builds_mem0_config_for_qdrant(self):
        from src.settings import Settings

        s = Settings(
            mem0_vector_store_provider="qdrant",
            mem0_qdrant_url="http://localhost:6333",
            mem0_qdrant_collection="test",
        )
        cfg = s.build_mem0_config()
        assert cfg["vector_store"]["provider"] == "qdrant"
        assert cfg["vector_store"]["config"]["url"] == "http://localhost:6333"
        assert cfg["vector_store"]["config"]["collection_name"] == "test"

    def test_settings_returns_none_for_memory_provider(self):
        from src.settings import Settings

        s = Settings(mem0_vector_store_provider="memory")
        assert s.build_mem0_config() is None
