"""FastAPI integration tests (mock LLM)."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient
from langchain_core.messages import AIMessage, HumanMessage


@pytest.fixture
def mock_agent():
    agent = MagicMock()
    agent.ainvoke = AsyncMock(
        return_value={"messages": [HumanMessage(content="Hi"), AIMessage(content="Hello!")]}
    )

    async def mock_astream(message, *, thread_id, user_id="default", stream_mode="messages"):
        yield (AIMessage(content="Hello"), {})

    agent.astream = mock_astream
    return agent


@pytest.fixture
def mock_redis():
    redis = AsyncMock()
    redis.ping = AsyncMock(return_value=True)
    redis.aclose = AsyncMock()
    redis.incr = AsyncMock(return_value=1)
    redis.expire = AsyncMock()
    return redis


@pytest.fixture
def client(mock_agent, mock_redis):
    with patch("app.api.routes.get_default_agent", return_value=mock_agent):
        with patch("app.main.aioredis") as mock_aioredis:
            mock_aioredis.from_url.return_value = mock_redis
            from app.main import app

            with TestClient(app) as c:
                yield c


class TestHealth:
    def test_health_returns_200(self, client):
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json() == {"status": "healthy"}


class TestInvoke:
    def test_invoke_returns_200(self, client):
        response = client.post("/invoke", json={"message": "Hello"})
        assert response.status_code == 200

    def test_invoke_returns_content(self, client):
        response = client.post("/invoke", json={"message": "Hello"})
        data = response.json()
        assert "content" in data
        assert isinstance(data["content"], str)

    def test_invoke_uses_session_id_as_thread(self, mock_agent, mock_redis):
        with patch("app.api.routes.get_default_agent", return_value=mock_agent):
            with patch("app.main.aioredis") as mock_aioredis:
                mock_aioredis.from_url.return_value = mock_redis
                from app.main import app

                with TestClient(app) as client:
                    client.post("/invoke", json={"message": "Hello", "session_id": "sess-42"})

        mock_agent.ainvoke.assert_called_once()
        _, kwargs = mock_agent.ainvoke.call_args
        assert kwargs["thread_id"] == "sess-42"

    def test_invoke_uses_anonymous_when_no_session(self, mock_agent, mock_redis):
        with patch("app.api.routes.get_default_agent", return_value=mock_agent):
            with patch("app.main.aioredis") as mock_aioredis:
                mock_aioredis.from_url.return_value = mock_redis
                from app.main import app

                with TestClient(app) as client:
                    client.post("/invoke", json={"message": "Hello"})

        _, kwargs = mock_agent.ainvoke.call_args
        assert kwargs["thread_id"] == "anonymous"

    def test_invoke_passes_user_id(self, mock_agent, mock_redis):
        with patch("app.api.routes.get_default_agent", return_value=mock_agent):
            with patch("app.main.aioredis") as mock_aioredis:
                mock_aioredis.from_url.return_value = mock_redis
                from app.main import app

                with TestClient(app) as client:
                    client.post("/invoke", json={"message": "Hello", "user_id": "alice"})

        _, kwargs = mock_agent.ainvoke.call_args
        assert kwargs["user_id"] == "alice"

    def test_invoke_default_user_id(self, mock_agent, mock_redis):
        with patch("app.api.routes.get_default_agent", return_value=mock_agent):
            with patch("app.main.aioredis") as mock_aioredis:
                mock_aioredis.from_url.return_value = mock_redis
                from app.main import app

                with TestClient(app) as client:
                    client.post("/invoke", json={"message": "Hello"})

        _, kwargs = mock_agent.ainvoke.call_args
        assert kwargs["user_id"] == "default"


class TestStream:
    def test_stream_returns_200(self, client):
        response = client.post("/stream", json={"message": "Hello"})
        assert response.status_code == 200

    def test_stream_content_type(self, client):
        response = client.post("/stream", json={"message": "Hello"})
        assert "text/event-stream" in response.headers["content-type"]

    def test_stream_passes_user_id(self, mock_agent, mock_redis):
        stream_calls = []

        async def capturing_astream(message, *, thread_id, user_id="default", stream_mode="messages"):
            stream_calls.append({"user_id": user_id})
            yield (AIMessage(content="Hi"), {})

        mock_agent.astream = capturing_astream

        with patch("app.api.routes.get_default_agent", return_value=mock_agent):
            with patch("app.main.aioredis") as mock_aioredis:
                mock_aioredis.from_url.return_value = mock_redis
                from app.main import app

                with TestClient(app) as c:
                    c.post("/stream", json={"message": "Hello", "user_id": "bob"})

        assert stream_calls[0]["user_id"] == "bob"
