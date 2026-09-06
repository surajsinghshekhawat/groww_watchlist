from typing import Annotated
from uuid import UUID

from fastapi import Depends, Header
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AppError
from app.core.tokens import decode_access_token
from app.db.models import User
from app.db.session import get_db_session
from app.repositories.users import UserRepository

bearer_scheme = HTTPBearer(auto_error=False)

DbSession = Annotated[AsyncSession, Depends(get_db_session)]


async def get_current_user(
    session: DbSession,
    credentials: Annotated[
        HTTPAuthorizationCredentials | None, Depends(bearer_scheme)
    ] = None,
    authorization: Annotated[str | None, Header()] = None,
) -> User:
    token: str | None = None
    if credentials and credentials.scheme.lower() == "bearer":
        token = credentials.credentials
    elif authorization and authorization.lower().startswith("bearer "):
        token = authorization.split(" ", 1)[1].strip()

    if not token:
        raise AppError("UNAUTHORIZED", "Authentication required", status_code=401)

    try:
        payload = decode_access_token(token)
        user_id = UUID(str(payload["sub"]))
    except (ValueError, KeyError, TypeError) as exc:
        raise AppError("UNAUTHORIZED", "Invalid or expired token", status_code=401) from exc

    user = await UserRepository(session).get_by_id(user_id)
    if user is None or not user.is_active:
        raise AppError("UNAUTHORIZED", "Invalid or expired token", status_code=401)
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]
