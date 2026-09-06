from app.core.config import settings
from app.core.exceptions import AppError
from app.core.security import hash_password, verify_password
from app.core.tokens import create_access_token
from app.repositories.users import UserRepository
from app.repositories.watchlists import WatchlistRepository
from app.schemas.auth import (
    AuthResponse,
    LoginRequest,
    RegisterRequest,
    TokenResponse,
    UserResponse,
)
from sqlalchemy.ext.asyncio import AsyncSession


class AuthService:
    def __init__(self, session: AsyncSession) -> None:
        self.users = UserRepository(session)
        self.watchlists = WatchlistRepository(session)
        self.session = session

    async def register(self, payload: RegisterRequest) -> AuthResponse:
        existing = await self.users.get_by_email(payload.email)
        if existing:
            raise AppError("EMAIL_TAKEN", "An account with this email already exists", 409)

        user = await self.users.create(
            email=payload.email,
            password_hash=hash_password(payload.password),
            display_name=payload.display_name,
        )
        await self.session.flush()
        # Every account gets a starter watchlist so login never dead-ends
        await self.watchlists.create(user_id=user.user_id, name="My Watchlist")
        await self.session.commit()
        await self.session.refresh(user)
        return self._auth_response(user)

    async def login(self, payload: LoginRequest) -> AuthResponse:
        user = await self.users.get_by_email(payload.email)
        if user is None or not verify_password(payload.password, user.password_hash):
            raise AppError("INVALID_CREDENTIALS", "Invalid email or password", 401)
        if not user.is_active:
            raise AppError("ACCOUNT_DISABLED", "Account is disabled", 403)
        return self._auth_response(user)

    def _auth_response(self, user) -> AuthResponse:
        sens = getattr(user, "sensitivity", None)
        sens_val = sens.value if sens is not None and hasattr(sens, "value") else (str(sens) if sens else "MEDIUM")
        token = create_access_token(subject=user.user_id)
        return AuthResponse(
            user=UserResponse(
                user_id=user.user_id,
                email=user.email,
                display_name=user.display_name,
                sensitivity=sens_val,
                created_at=user.created_at,
            ),
            token=TokenResponse(
                access_token=token,
                expires_in_minutes=settings.access_token_expire_minutes,
            ),
        )
