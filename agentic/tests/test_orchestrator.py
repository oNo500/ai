"""Orchestrator pattern unit tests (TDD — RED first)."""

from unittest.mock import AsyncMock, MagicMock, patch


class TestAgentSpecRole:
    def test_spec_default_role_is_worker(self):
        from app.agent.spec import AgentSpec

        spec = AgentSpec(name="bot")
        assert spec.role == "worker"

    def test_spec_orchestrator_role(self):
        from app.agent.spec import AgentSpec

        spec = AgentSpec(name="orchestrator", role="orchestrator")
        assert spec.role == "orchestrator"


class TestOrchestratorTools:
    def test_orchestrator_tools_include_all_workers(self):
        from app.agent.registry import AgentRegistry
        from app.agent.spec import AgentSpec

        reg = AgentRegistry()

        worker_a = MagicMock()
        worker_a.spec.name = "researcher"
        worker_a.spec.system_prompt = "You research things."
        worker_a.spec.role = "worker"

        worker_b = MagicMock()
        worker_b.spec.name = "coder"
        worker_b.spec.system_prompt = "You write code."
        worker_b.spec.role = "worker"

        with patch("app.agent.registry.create_production_agent") as mock_create:
            mock_create.side_effect = [worker_a, worker_b]
            reg.register("researcher", AgentSpec(name="researcher", role="worker"))
            reg.register("coder", AgentSpec(name="coder", role="worker"))

        tools = reg.get_worker_tools()
        assert len(tools) == 2
        tool_names = [t.name for t in tools]
        assert "researcher" in tool_names
        assert "coder" in tool_names

    def test_get_worker_tools_excludes_orchestrators(self):
        from app.agent.registry import AgentRegistry
        from app.agent.spec import AgentSpec

        reg = AgentRegistry()

        worker = MagicMock()
        worker.spec.name = "helper"
        worker.spec.system_prompt = "You help."
        worker.spec.role = "worker"

        orchestrator = MagicMock()
        orchestrator.spec.name = "boss"
        orchestrator.spec.role = "orchestrator"

        with patch("app.agent.registry.create_production_agent") as mock_create:
            mock_create.side_effect = [worker, orchestrator]
            reg.register("helper", AgentSpec(name="helper", role="worker"))
            reg.register("boss", AgentSpec(name="boss", role="orchestrator"))

        tools = reg.get_worker_tools()
        tool_names = [t.name for t in tools]
        assert "helper" in tool_names
        assert "boss" not in tool_names


class TestOrchestrateEndpoint:
    async def test_orchestrate_endpoint_returns_result(self):
        from fastapi.testclient import TestClient

        from app.main import app

        mock_agent = MagicMock()
        mock_agent.ainvoke = AsyncMock(
            return_value={"messages": [MagicMock(content="task done")]}
        )

        with patch("app.api.routes.global_registry") as mock_reg:
            mock_reg.get.return_value = mock_agent
            mock_reg.names.return_value = ["default", "orchestrator"]

            with TestClient(app) as client:
                resp = client.post(
                    "/orchestrate",
                    json={
                        "task": "research and summarize AI trends",
                        "agent_name": "default",
                        "session_id": "s-1",
                        "user_id": "u-1",
                    },
                )

        assert resp.status_code == 200
        assert resp.json()["content"] == "task done"
