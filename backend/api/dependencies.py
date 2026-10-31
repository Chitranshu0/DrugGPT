"""Shared FastAPI dependencies.

Authentication is verified against Supabase on every request. Routes depend on
``get_current_user`` and receive a local ``AuthUser``; they never decode a JWT
themselves.
"""

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from backend.api.schemas import AuthUser
from backend.core.config import AUTH_REQUIRED
from backend.core.supabase_client import AuthConfigError, verify_token
from backend.memory import users

bearer_scheme = HTTPBearer(auto_error=False)

# Used only when AUTH_REQUIRED=false, which is a local development escape
# hatch. It is never returned while authentication is required.
DEV_USER = AuthUser(id="dev-user", email="dev@localhost", is_admin=True)


def _unauthorized(detail: str) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail=detail,
        headers={"WWW-Authenticate": "Bearer"},
    )


async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
) -> AuthUser:
    """Return the signed-in user, creating their local row on first use."""
    token = credentials.credentials if credentials else ""

    if not token:
        if AUTH_REQUIRED:
            raise _unauthorized("Not authenticated")

        local = await users.upsert_user(
            DEV_USER.id,
            DEV_USER.email,
            is_admin=True,
        )
        return AuthUser(
            id=local["user_id"],
            email=local["email"],
            is_admin=local["is_admin"],
        )

    try:
        profile = verify_token(token)
    except AuthConfigError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(exc),
        ) from exc

    if profile is None:
        raise _unauthorized("Invalid or expired session")

    local = await users.upsert_user(profile["id"], profile["email"])
    return AuthUser(
        id=local["user_id"],
        email=local["email"],
        is_admin=local["is_admin"],
    )
