"""Structured logging tests (TDD — RED first)."""



class TestRequestIdMiddleware:
    async def test_request_id_header_injected(self):
        from fastapi.testclient import TestClient

        from src.main import app

        with TestClient(app) as client:
            resp = client.get("/health")

        assert "x-request-id" in resp.headers

    async def test_request_id_is_uuid(self):
        import uuid

        from fastapi.testclient import TestClient

        from src.main import app

        with TestClient(app) as client:
            resp = client.get("/health")

        request_id = resp.headers.get("x-request-id", "")
        uuid.UUID(request_id)  # raises if not valid UUID

    async def test_custom_request_id_forwarded(self):
        from fastapi.testclient import TestClient

        from src.main import app

        with TestClient(app) as client:
            resp = client.get("/health", headers={"x-request-id": "my-trace-id"})

        assert resp.headers.get("x-request-id") == "my-trace-id"


class TestStructuredLogger:
    def test_get_logger_returns_logger(self):
        from src.logging import get_logger

        logger = get_logger("test")
        assert logger is not None

    def test_logger_bind_returns_bound_logger(self):
        from src.logging import get_logger

        logger = get_logger("test")
        bound = logger.bind(request_id="r-1", user_id="u-1")
        assert bound is not None
