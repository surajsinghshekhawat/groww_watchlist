from fastapi import APIRouter, Request

from app.api.dependencies import CurrentUser, DbSession
from app.core.exceptions import AppError
from app.core.rate_limit import enforce_rate_limit
from app.db.models import Sensitivity
from app.schemas.settings import SettingsResponse, SettingsUpdate

router = APIRouter(prefix="/me", tags=["settings"])


@router.get("/settings", response_model=SettingsResponse)
async def get_settings(user: CurrentUser) -> SettingsResponse:
    sens = user.sensitivity.value if hasattr(user.sensitivity, "value") else str(user.sensitivity)
    return SettingsResponse(sensitivity=sens, display_name=user.display_name, email=user.email)


@router.patch("/settings", response_model=SettingsResponse)
async def update_settings(
    payload: SettingsUpdate,
    user: CurrentUser,
    session: DbSession,
    request: Request,
) -> SettingsResponse:
    await enforce_rate_limit(request, scope="settings", limit=30, window_seconds=60)
    try:
        user.sensitivity = Sensitivity(payload.sensitivity)
    except ValueError as exc:
        raise AppError("INVALID_SENSITIVITY", "Use LOW, MEDIUM, or HIGH", 400) from exc
    await session.commit()
    await session.refresh(user)
    return SettingsResponse(
        sensitivity=user.sensitivity.value,
        display_name=user.display_name,
        email=user.email,
    )
