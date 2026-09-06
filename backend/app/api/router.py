from fastapi import APIRouter

from app.api import auth, digest, feedback, health, market, notifications, push, settings, watchlists, websocket
from app.core.config import settings as app_settings

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(websocket.router)

v1_router = APIRouter(prefix=app_settings.api_prefix)
v1_router.include_router(auth.router)
v1_router.include_router(watchlists.router)
v1_router.include_router(digest.router)
v1_router.include_router(feedback.router)
v1_router.include_router(notifications.router)
v1_router.include_router(push.router)
v1_router.include_router(settings.router)
v1_router.include_router(market.router)
api_router.include_router(v1_router)
