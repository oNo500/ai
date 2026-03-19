"""Redis sliding-window rate limiter."""

from __future__ import annotations

from typing import Any


class RateLimiter:
    def __init__(self, *, redis: Any, max_requests: int, window_seconds: int) -> None:
        self._redis = redis
        self._max = max_requests
        self._window = window_seconds

    async def check(self, user_id: str) -> tuple[bool, int]:
        key = f"ratelimit:{user_id}"
        count: int = await self._redis.incr(key)
        await self._redis.expire(key, self._window)
        return count <= self._max, count
