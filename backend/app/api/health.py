"""Health and readiness probes.

/health  — process is up
/ready   — dependencies reachable (best-effort; never exposes secrets)
"""

from fastapi import APIRouter
from pydantic import BaseModel
from sqlalchemy import text

from app.core.config import settings
from app.db.session import engine

router = APIRouter(tags=["health"])


class ComponentStatus(BaseModel):
    status: str
    detail: str | None = None


class HealthResponse(BaseModel):
    status: str
    app: str
    env: str
    market_data_mode: str


class ReadyResponse(BaseModel):
    status: str
    components: dict[str, ComponentStatus]


@router.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    return HealthResponse(
        status="ok",
        app=settings.app_name,
        env=settings.app_env,
        market_data_mode=settings.market_data_mode,
    )


async def _check_database() -> ComponentStatus:
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        return ComponentStatus(status="ok")
    except Exception as exc:  # noqa: BLE001 — readiness must not crash
        return ComponentStatus(status="unavailable", detail=type(exc).__name__)


async def _check_redis() -> ComponentStatus:
    try:
        from redis.asyncio import Redis

        client = Redis.from_url(settings.redis_url, socket_connect_timeout=1)
        try:
            pong = await client.ping()
            if pong:
                return ComponentStatus(status="ok")
            return ComponentStatus(status="unavailable", detail="ping_failed")
        finally:
            await client.aclose()
    except Exception as exc:  # noqa: BLE001
        return ComponentStatus(status="unavailable", detail=type(exc).__name__)


@router.get("/ready", response_model=ReadyResponse)
async def ready() -> ReadyResponse:
    components = {
        "api": ComponentStatus(status="ok"),
        "database": await _check_database(),
        "redis": await _check_redis(),
        "market_provider": ComponentStatus(
            status="ok"
            if settings.market_data_mode in {"replay", "mock", "yahoo", "yfinance", "live"}
            else "unknown",
            detail=f"mode={settings.market_data_mode}",
        ),
    }

    critical = {components["database"].status, components["redis"].status}
    if critical == {"ok"}:
        overall = "ok"
    elif "ok" in critical or components["api"].status == "ok":
        overall = "degraded"
    else:
        overall = "unavailable"

    return ReadyResponse(status=overall, components=components)
