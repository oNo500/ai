"""Lifespan integration tests (RED first)."""

import os
from unittest.mock import AsyncMock, MagicMock, patch


class TestLifespan:
    async def test_redis_initialized_on_startup(self):
        mock_redis = AsyncMock()
        mock_redis.ping = AsyncMock(return_value=True)
        mock_redis.aclose = AsyncMock()

        with patch("app.main.aioredis") as mock_aioredis:
            mock_aioredis.from_url.return_value = mock_redis

            from fastapi.testclient import TestClient

            from src.main import app

            with TestClient(app):
                assert hasattr(app.state, "redis")

    async def test_redis_closed_on_shutdown(self):
        mock_redis = AsyncMock()
        mock_redis.ping = AsyncMock(return_value=True)
        mock_redis.aclose = AsyncMock()

        with patch("app.main.aioredis") as mock_aioredis:
            mock_aioredis.from_url.return_value = mock_redis

            from fastapi.testclient import TestClient

            from src.main import app

            with TestClient(app):
                pass

            mock_redis.aclose.assert_called_once()


class TestLangSmithLifespan:
    async def test_langsmith_env_vars_set_when_tracing_enabled(self):
        mock_redis = AsyncMock()
        mock_redis.ping = AsyncMock(return_value=True)
        mock_redis.aclose = AsyncMock()

        mock_settings = MagicMock()
        mock_settings.redis_url = "redis://localhost:6379/0"
        mock_settings.app_name = "test"
        mock_settings.langsmith_tracing = True
        mock_settings.langsmith_api_key = "ls-test-key"
        mock_settings.langsmith_project = "test-project"

        with (
            patch("app.main.aioredis") as mock_aioredis,
            patch("app.main.settings", mock_settings),
            patch.dict(os.environ, {}, clear=False),
        ):
            mock_aioredis.from_url.return_value = mock_redis

            from fastapi.testclient import TestClient

            from src.main import app

            with TestClient(app):
                assert os.environ.get("LANGCHAIN_TRACING_V2") == "true"
                assert os.environ.get("LANGCHAIN_API_KEY") == "ls-test-key"
                assert os.environ.get("LANGCHAIN_PROJECT") == "test-project"

    async def test_langsmith_env_vars_not_set_when_tracing_disabled(self):
        mock_redis = AsyncMock()
        mock_redis.ping = AsyncMock(return_value=True)
        mock_redis.aclose = AsyncMock()

        for key in ("LANGCHAIN_TRACING_V2", "LANGCHAIN_API_KEY", "LANGCHAIN_PROJECT"):
            os.environ.pop(key, None)

        with patch("app.main.aioredis") as mock_aioredis:
            mock_aioredis.from_url.return_value = mock_redis

            from fastapi.testclient import TestClient

            from src.main import app

            with TestClient(app):
                assert "LANGCHAIN_TRACING_V2" not in os.environ
