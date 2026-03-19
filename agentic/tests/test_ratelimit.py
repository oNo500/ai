"""Rate limiting tests (TDD — RED first)."""

from unittest.mock import AsyncMock, MagicMock, patch


class TestRateLimiter:
    async def test_allows_request_under_limit(self):
        from src.middleware.ratelimit import RateLimiter

        mock_redis = AsyncMock()
        mock_redis.incr = AsyncMock(return_value=1)
        mock_redis.expire = AsyncMock()

        limiter = RateLimiter(redis=mock_redis, max_requests=10, window_seconds=60)
        allowed, count = await limiter.check("user-1")

        assert allowed is True
        assert count == 1

    async def test_blocks_request_over_limit(self):
        from src.middleware.ratelimit import RateLimiter

        mock_redis = AsyncMock()
        mock_redis.incr = AsyncMock(return_value=11)
        mock_redis.expire = AsyncMock()

        limiter = RateLimiter(redis=mock_redis, max_requests=10, window_seconds=60)
        allowed, count = await limiter.check("user-1")

        assert allowed is False
        assert count == 11

    async def test_uses_user_id_as_redis_key(self):
        from src.middleware.ratelimit import RateLimiter

        mock_redis = AsyncMock()
        mock_redis.incr = AsyncMock(return_value=1)
        mock_redis.expire = AsyncMock()

        limiter = RateLimiter(redis=mock_redis, max_requests=10, window_seconds=60)
        await limiter.check("alice")

        call_args = mock_redis.incr.call_args[0][0]
        assert "alice" in call_args

    async def test_sets_expiry_on_first_request(self):
        from src.middleware.ratelimit import RateLimiter

        mock_redis = AsyncMock()
        mock_redis.incr = AsyncMock(return_value=1)
        mock_redis.expire = AsyncMock()

        limiter = RateLimiter(redis=mock_redis, max_requests=10, window_seconds=60)
        await limiter.check("user-1")

        mock_redis.expire.assert_called_once()

    async def test_sets_expiry_on_every_request(self):
        from src.middleware.ratelimit import RateLimiter

        mock_redis = AsyncMock()
        mock_redis.incr = AsyncMock(return_value=5)  # not first request
        mock_redis.expire = AsyncMock()

        limiter = RateLimiter(redis=mock_redis, max_requests=10, window_seconds=60)
        await limiter.check("user-1")

        mock_redis.expire.assert_called_once()


class TestSettingsRateLimit:
    def test_settings_has_rate_limit_fields(self):
        from src.settings import Settings

        s = Settings()
        assert hasattr(s, "rate_limit_requests")
        assert hasattr(s, "rate_limit_window_seconds")
        assert s.rate_limit_requests == 60
        assert s.rate_limit_window_seconds == 60


class TestRateLimitEndpoint:
    async def test_invoke_returns_429_when_rate_limited(self):
        from fastapi.testclient import TestClient

        from src.main import app

        with patch("app.api.routes.check_rate_limit") as mock_check:
            mock_check.return_value = (False, 61)

            with TestClient(app) as client:
                resp = client.post(
                    "/invoke",
                    json={"message": "hello", "user_id": "u-1"},
                )

        assert resp.status_code == 429

    async def test_invoke_proceeds_when_under_limit(self):
        from fastapi.testclient import TestClient

        from src.main import app

        mock_agent = MagicMock()
        mock_agent.ainvoke = AsyncMock(
            return_value={"messages": [MagicMock(content="ok")]}
        )

        with (
            patch("app.api.routes.check_rate_limit") as mock_check,
            patch("app.api.routes.get_default_agent", return_value=mock_agent),
        ):
            mock_check.return_value = (True, 1)

            with TestClient(app) as client:
                resp = client.post(
                    "/invoke",
                    json={"message": "hello", "user_id": "u-1"},
                )

        assert resp.status_code == 200
