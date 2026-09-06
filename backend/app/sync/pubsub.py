"""Redis pub/sub helpers for live fan-out. Degrades gracefully if Redis is down."""

from __future__ import annotations

import json
from typing import Any, AsyncIterator

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)

CHANNEL_PREFIX = "watchlist:live:"


def channel_for_watchlist(watchlist_id: str) -> str:
    return f"{CHANNEL_PREFIX}{watchlist_id}"


async def publish_watchlist_event(watchlist_id: str, payload: dict[str, Any]) -> bool:
    try:
        from redis.asyncio import Redis

        client = Redis.from_url(settings.redis_url, socket_connect_timeout=0.5)
        try:
            await client.publish(channel_for_watchlist(watchlist_id), json.dumps(payload))
            return True
        finally:
            await client.aclose()
    except Exception as exc:  # noqa: BLE001
        logger.warning("redis_publish_failed", extra={"error": type(exc).__name__})
        return False


async def subscribe_watchlist(watchlist_id: str) -> AsyncIterator[dict[str, Any]]:
    """Yield parsed messages; caller must cancel when WS disconnects."""
    from redis.asyncio import Redis

    client = Redis.from_url(settings.redis_url, socket_connect_timeout=1)
    pubsub = client.pubsub()
    await pubsub.subscribe(channel_for_watchlist(watchlist_id))
    try:
        async for message in pubsub.listen():
            if message is None or message.get("type") != "message":
                continue
            data = message.get("data")
            if isinstance(data, bytes):
                data = data.decode("utf-8")
            try:
                yield json.loads(data)
            except json.JSONDecodeError:
                continue
    finally:
        await pubsub.unsubscribe(channel_for_watchlist(watchlist_id))
        await pubsub.aclose()
        await client.aclose()
