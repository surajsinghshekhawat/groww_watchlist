"""Authenticated watchlist WebSocket + public demo tape stream."""

from __future__ import annotations

import asyncio
from uuid import UUID

from fastapi import APIRouter, Query, WebSocket, WebSocketDisconnect
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.core.logging import get_logger
from app.core.tokens import decode_access_token
from app.db.models import User, Watchlist
from app.db.session import AsyncSessionLocal
from app.sync.live_sim import subscribe_tape, unsubscribe_tape
from app.sync.pubsub import subscribe_watchlist

logger = get_logger(__name__)
router = APIRouter(tags=["websocket"])


@router.websocket("/ws/tape")
async def tape_live(websocket: WebSocket) -> None:
    """Unauthenticated demo tape — simulation only."""
    await websocket.accept()
    queue = await subscribe_tape()
    try:
        await websocket.send_json({"type": "subscribed", "channel": "tape", "mode": "live-sim"})
        while True:
            msg = await queue.get()
            await websocket.send_json(msg)
    except WebSocketDisconnect:
        pass
    finally:
        unsubscribe_tape(queue)


@router.websocket("/ws/watchlists/{watchlist_id}")
async def watchlist_live(
    websocket: WebSocket,
    watchlist_id: UUID,
    token: str = Query(...),
) -> None:
    try:
        payload = decode_access_token(token)
        user_id = UUID(str(payload["sub"]))
    except Exception:
        await websocket.close(code=4401)
        return

    async with AsyncSessionLocal() as session:
        user = await session.scalar(select(User).where(User.user_id == user_id))
        if user is None or not user.is_active:
            await websocket.close(code=4401)
            return
        watchlist = await session.scalar(
            select(Watchlist)
            .where(Watchlist.watchlist_id == watchlist_id, Watchlist.user_id == user_id)
            .options(selectinload(Watchlist.items))
        )
        if watchlist is None:
            await websocket.close(code=4404)
            return
        instrument_ids = [str(i.instrument_id) for i in watchlist.items]

    await websocket.accept()
    await websocket.send_json(
        {
            "type": "subscribed",
            "watchlist_id": str(watchlist_id),
            "instruments": instrument_ids,
        }
    )

    stop = asyncio.Event()

    async def pump_redis() -> None:
        try:
            async for msg in subscribe_watchlist(str(watchlist_id)):
                if stop.is_set():
                    break
                await websocket.send_json({"type": "event", "payload": msg})
        except Exception as exc:  # noqa: BLE001
            logger.warning("ws_redis_subscribe_failed", extra={"error": type(exc).__name__})
            await websocket.send_json(
                {
                    "type": "degraded",
                    "message": "Live fan-out unavailable; use polling fallback.",
                }
            )

    async def pump_client() -> None:
        while not stop.is_set():
            try:
                message = await asyncio.wait_for(websocket.receive_text(), timeout=25)
                if message == "ping":
                    await websocket.send_json({"type": "pong"})
            except asyncio.TimeoutError:
                await websocket.send_json({"type": "heartbeat"})
            except WebSocketDisconnect:
                stop.set()
                return

    redis_task = asyncio.create_task(pump_redis())
    try:
        await pump_client()
    finally:
        stop.set()
        redis_task.cancel()
        try:
            await redis_task
        except asyncio.CancelledError:
            pass
