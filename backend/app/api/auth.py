from fastapi import APIRouter, Request

from app.api.dependencies import CurrentUser, DbSession
from app.core.config import settings
from app.core.rate_limit import enforce_rate_limit
from app.schemas.auth import AuthResponse, LoginRequest, RegisterRequest, UserResponse
from app.services.auth_service import AuthService

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=AuthResponse, status_code=201)
async def register(
    request: Request, payload: RegisterRequest, session: DbSession
) -> AuthResponse:
    await enforce_rate_limit(request, scope="auth_register", limit=10, window_seconds=60)
    return await AuthService(session).register(payload)


@router.post("/login", response_model=AuthResponse)
async def login(request: Request, payload: LoginRequest, session: DbSession) -> AuthResponse:
    await enforce_rate_limit(request, scope="auth_login", limit=20, window_seconds=60)
    return await AuthService(session).login(payload)


@router.get("/me", response_model=UserResponse)
async def me(user: CurrentUser) -> UserResponse:
    return UserResponse.model_validate(user)
