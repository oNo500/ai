"""AgentRegistry unit tests (TDD — RED first)."""

from unittest.mock import MagicMock, patch


class TestAgentRegistry:
    def test_register_and_get(self):
        from app.agent.registry import AgentRegistry
        from app.agent.spec import AgentSpec

        reg = AgentRegistry()
        spec = AgentSpec(name="researcher")

        with patch("app.agent.registry.create_production_agent") as mock_create:
            mock_agent = MagicMock()
            mock_create.return_value = mock_agent
            reg.register("researcher", spec)

        assert reg.get("researcher") is mock_agent

    def test_get_unknown_raises(self):
        from app.agent.registry import AgentRegistry

        reg = AgentRegistry()
        import pytest

        with pytest.raises(KeyError, match="nonexistent"):
            reg.get("nonexistent")

    def test_all_returns_all_agents(self):
        from app.agent.registry import AgentRegistry
        from app.agent.spec import AgentSpec

        reg = AgentRegistry()

        with patch("app.agent.registry.create_production_agent") as mock_create:
            mock_create.side_effect = [MagicMock(), MagicMock()]
            reg.register("a", AgentSpec(name="a"))
            reg.register("b", AgentSpec(name="b"))

        assert len(reg.all()) == 2

    def test_names_returns_registered_names(self):
        from app.agent.registry import AgentRegistry
        from app.agent.spec import AgentSpec

        reg = AgentRegistry()

        with patch("app.agent.registry.create_production_agent") as mock_create:
            mock_create.return_value = MagicMock()
            reg.register("alpha", AgentSpec(name="alpha"))

        assert "alpha" in reg.names()

    def test_register_overwrites_existing(self):
        from app.agent.registry import AgentRegistry
        from app.agent.spec import AgentSpec

        reg = AgentRegistry()
        agent_v1 = MagicMock()
        agent_v2 = MagicMock()

        with patch("app.agent.registry.create_production_agent") as mock_create:
            mock_create.side_effect = [agent_v1, agent_v2]
            reg.register("bot", AgentSpec(name="bot"))
            reg.register("bot", AgentSpec(name="bot"))

        assert reg.get("bot") is agent_v2


class TestGlobalRegistry:
    def test_global_registry_has_default_agent(self):
        from app.agent.registry import global_registry

        assert "default" in global_registry.names()

    def test_get_default_agent_returns_same_instance(self):
        from app.agent.registry import get_default_agent, global_registry

        agent = get_default_agent()
        assert agent is global_registry.get("default")


class TestRegistryEndpoints:
    async def test_list_agents_endpoint(self):
        from fastapi.testclient import TestClient

        from app.main import app

        with TestClient(app) as client:
            resp = client.get("/agents")

        assert resp.status_code == 200
        data = resp.json()
        assert "agents" in data
        assert any(a["name"] == "default" for a in data["agents"])

    async def test_register_agent_endpoint(self):
        from fastapi.testclient import TestClient

        from app.main import app

        with TestClient(app) as client:
            resp = client.post(
                "/agents",
                json={
                    "name": "test-bot",
                    "system_prompt": "You are a test bot.",
                    "temperature": 0.5,
                },
            )

        assert resp.status_code == 200
        assert resp.json()["name"] == "test-bot"
