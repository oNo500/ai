"""Human-in-the-Loop tests (TDD — RED first)."""

from unittest.mock import AsyncMock, MagicMock, patch


class TestBuildGraphHITL:
    def test_graph_compiled_with_interrupt_before_tools_when_enabled(self):
        from app.agent.graph import build_graph
        from app.agent.spec import AgentSpec

        mock_llm = MagicMock()
        spec = AgentSpec(name="test", enable_human_loop=True)

        with patch("app.agent.graph.StateGraph") as mock_sg:
            mock_builder = MagicMock()
            mock_compiled = MagicMock()
            mock_sg.return_value = mock_builder
            mock_builder.compile.return_value = mock_compiled

            build_graph(mock_llm, [], checkpointer=None, spec=spec)

            compile_kwargs = mock_builder.compile.call_args[1]
            assert compile_kwargs.get("interrupt_before") == ["tools"]

    def test_graph_compiled_without_interrupt_when_disabled(self):
        from app.agent.graph import build_graph
        from app.agent.spec import AgentSpec

        mock_llm = MagicMock()
        spec = AgentSpec(name="test", enable_human_loop=False)

        with patch("app.agent.graph.StateGraph") as mock_sg:
            mock_builder = MagicMock()
            mock_compiled = MagicMock()
            mock_sg.return_value = mock_builder
            mock_builder.compile.return_value = mock_compiled

            build_graph(mock_llm, [], checkpointer=None, spec=spec)

            compile_kwargs = mock_builder.compile.call_args[1]
            assert compile_kwargs.get("interrupt_before") is None


class TestPendingEndpoint:
    async def test_pending_returns_tool_calls_when_interrupted(self):
        from fastapi.testclient import TestClient

        from app.main import app

        mock_agent = MagicMock()
        mock_agent._compiled.get_state = MagicMock(
            return_value=MagicMock(
                next=("tools",),
                values={
                    "messages": [
                        MagicMock(
                            tool_calls=[{"id": "c1", "name": "rag_search", "args": {"query": "AI"}}]
                        )
                    ]
                },
            )
        )

        with patch("app.api.routes.global_registry") as mock_reg:
            mock_reg.get.return_value = mock_agent
            mock_reg.names.return_value = ["default"]

            with TestClient(app) as client:
                resp = client.get(
                    "/sessions/thread-1/pending",
                    params={"agent_name": "default"},
                )

        assert resp.status_code == 200
        data = resp.json()
        assert data["interrupted"] is True
        assert len(data["pending_tool_calls"]) == 1
        assert data["pending_tool_calls"][0]["name"] == "rag_search"

    async def test_pending_returns_not_interrupted_when_running(self):
        from fastapi.testclient import TestClient

        from app.main import app

        mock_agent = MagicMock()
        mock_agent._compiled.get_state = MagicMock(
            return_value=MagicMock(next=(), values={"messages": []})
        )

        with patch("app.api.routes.global_registry") as mock_reg:
            mock_reg.get.return_value = mock_agent
            mock_reg.names.return_value = ["default"]

            with TestClient(app) as client:
                resp = client.get(
                    "/sessions/thread-1/pending",
                    params={"agent_name": "default"},
                )

        assert resp.status_code == 200
        assert resp.json()["interrupted"] is False


class TestApproveEndpoint:
    async def test_approve_resumes_execution(self):
        from fastapi.testclient import TestClient

        from app.main import app

        mock_agent = MagicMock()
        mock_agent._compiled.ainvoke = AsyncMock(
            return_value={"messages": [MagicMock(content="done after approval")]}
        )

        with patch("app.api.routes.global_registry") as mock_reg:
            mock_reg.get.return_value = mock_agent
            mock_reg.names.return_value = ["default"]

            with TestClient(app) as client:
                resp = client.post(
                    "/sessions/thread-1/approve",
                    json={"agent_name": "default", "user_id": "u-1"},
                )

        assert resp.status_code == 200
        assert resp.json()["content"] == "done after approval"

    async def test_approve_calls_ainvoke_with_none_to_resume(self):
        from fastapi.testclient import TestClient

        from app.main import app

        mock_agent = MagicMock()
        mock_agent._compiled.ainvoke = AsyncMock(
            return_value={"messages": [MagicMock(content="resumed")]}
        )

        with patch("app.api.routes.global_registry") as mock_reg:
            mock_reg.get.return_value = mock_agent
            mock_reg.names.return_value = ["default"]

            with TestClient(app) as client:
                client.post(
                    "/sessions/thread-1/approve",
                    json={"agent_name": "default", "user_id": "u-1"},
                )

        call_args = mock_agent._compiled.ainvoke.call_args
        assert call_args[0][0] is None


class TestRejectEndpoint:
    async def test_reject_returns_final_answer(self):
        from fastapi.testclient import TestClient

        from app.main import app

        mock_agent = MagicMock()
        mock_agent._compiled.get_state = MagicMock(
            return_value=MagicMock(
                values={
                    "messages": [
                        MagicMock(tool_calls=[{"id": "c1", "name": "search", "args": {}}])
                    ]
                }
            )
        )
        mock_agent._compiled.update_state = MagicMock()
        mock_agent._compiled.ainvoke = AsyncMock(
            return_value={"messages": [MagicMock(content="final answer without tool")]}
        )

        with patch("app.api.routes.global_registry") as mock_reg:
            mock_reg.get.return_value = mock_agent
            mock_reg.names.return_value = ["default"]

            with TestClient(app) as client:
                resp = client.post(
                    "/sessions/thread-1/reject",
                    json={"agent_name": "default", "user_id": "u-1", "reason": "not needed"},
                )

        assert resp.status_code == 200
        assert resp.json()["content"] == "final answer without tool"

    async def test_reject_injects_tool_messages_as_node_tools(self):
        from fastapi.testclient import TestClient

        from app.main import app

        mock_agent = MagicMock()
        mock_agent._compiled.get_state = MagicMock(
            return_value=MagicMock(
                values={
                    "messages": [
                        MagicMock(tool_calls=[{"id": "c1", "name": "search", "args": {}}])
                    ]
                }
            )
        )
        mock_agent._compiled.update_state = MagicMock()
        mock_agent._compiled.ainvoke = AsyncMock(
            return_value={"messages": [MagicMock(content="ok")]}
        )

        with patch("app.api.routes.global_registry") as mock_reg:
            mock_reg.get.return_value = mock_agent
            mock_reg.names.return_value = ["default"]

            with TestClient(app) as client:
                client.post(
                    "/sessions/thread-1/reject",
                    json={"agent_name": "default", "user_id": "u-1", "reason": "no"},
                )

        call_kwargs = mock_agent._compiled.update_state.call_args[1]
        assert call_kwargs.get("as_node") == "tools"

    async def test_reject_uses_reason_in_tool_message_content(self):
        from fastapi.testclient import TestClient

        from app.main import app

        mock_agent = MagicMock()
        mock_agent._compiled.get_state = MagicMock(
            return_value=MagicMock(
                values={
                    "messages": [
                        MagicMock(tool_calls=[{"id": "c1", "name": "search", "args": {}}])
                    ]
                }
            )
        )
        mock_agent._compiled.update_state = MagicMock()
        mock_agent._compiled.ainvoke = AsyncMock(
            return_value={"messages": [MagicMock(content="ok")]}
        )

        with patch("app.api.routes.global_registry") as mock_reg:
            mock_reg.get.return_value = mock_agent
            mock_reg.names.return_value = ["default"]

            with TestClient(app) as client:
                client.post(
                    "/sessions/thread-1/reject",
                    json={"agent_name": "default", "user_id": "u-1", "reason": "my reason"},
                )

        call_args = mock_agent._compiled.update_state.call_args
        messages = call_args[0][1]["messages"]
        assert len(messages) == 1
        assert "my reason" in messages[0].content

    async def test_reject_resumes_with_ainvoke_none(self):
        from fastapi.testclient import TestClient

        from app.main import app

        mock_agent = MagicMock()
        mock_agent._compiled.get_state = MagicMock(
            return_value=MagicMock(
                values={
                    "messages": [
                        MagicMock(tool_calls=[{"id": "c1", "name": "search", "args": {}}])
                    ]
                }
            )
        )
        mock_agent._compiled.update_state = MagicMock()
        mock_agent._compiled.ainvoke = AsyncMock(
            return_value={"messages": [MagicMock(content="ok")]}
        )

        with patch("app.api.routes.global_registry") as mock_reg:
            mock_reg.get.return_value = mock_agent
            mock_reg.names.return_value = ["default"]

            with TestClient(app) as client:
                client.post(
                    "/sessions/thread-1/reject",
                    json={"agent_name": "default", "user_id": "u-1", "reason": "no"},
                )

        call_args = mock_agent._compiled.ainvoke.call_args
        assert call_args[0][0] is None
