"""Simple Redis-backed rate limiter with in-memory fallback."""

from __future__ import annotations

import time
from collections import defaultdict, deque

from fastapi import Request

from app.core.config import settings
from app.core.exceptions import AppError
from app.core.logging import get_logger

logger = get_logger(__name__)

_memory_hits: dict[str, deque[float]] = defaultdict(deque)


async def _redis_hit(key: str, limit: int, window_seconds: int) -> bool:
    try:
        from redis.asyncio import Redis

        client = Redis.from_url(settings.redis_url, socket_connect_timeout=0.5)
        try:
            pipe = client.pipeline()
            now = time.time()
            pipe.zremrangebyscore(key, 0, now - window_seconds)
            pipe.zadd(key, {str(now): now})
            pipe.zcard(key)
            pipe.expire(key, window_seconds)
            results = await pipe.execute()
            count = int(results[2])
            return count <= limit
        finally:
            await client.aclose()
    except Exception as exc:  # noqa: BLE001
        logger.warning("rate_limit_redis_fallback", extra={"error": type(exc).__name__})
        return _memory_allow(key, limit, window_seconds)


def _memory_allow(key: str, limit: int, window_seconds: int) -> bool:
    now = time.time()
    q = _memory_hits[key]
    while q and q[0] < now - window_seconds:
        q.popleft()
    if len(q) >= limit:
        return False
    q.append(now)
    return True


async def enforce_rate_limit(
    request: Request,
    *,
    scope: str,
    limit: int,
    window_seconds: int = 60,
) -> None:
    client_host = request.client.host if request.client else "unknown"
    key = f"rl:{scope}:{client_host}"
    allowed = await _redis_hit(key, limit, window_seconds)
    if not allowed:
        raise AppError(
            code="RATE_LIMITED",
            message="Too many requests. Please retry shortly.",
            status_code=429,
        )
